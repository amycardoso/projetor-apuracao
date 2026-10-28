"""Ordem de chegada das seções como um relógio de 0 a 1.

`relogio` é a fração de seções já divulgadas quando a seção entra: 0 é o
início da apuração e 1 é a última seção.

- 2022: ordem observada, pelo momento de divulgação (DT_BU_RECEBIDO em hora de
  Brasília, nunca antes das 17h; ver `tempo.py`).
- 2018: ordem SIMULADA. O BU de 2018 não tem horário de recebimento, então
  cada seção herda a distribuição de chegada do local equivalente em 2022
  (pareamento de `locais.py`), depois da zona, do município e, em último caso,
  da UF. Dentro de um mesmo grupo, as seções de 2018 são ordenadas por
  NR_SECAO e recebem quantis igualmente espaçados da distribuição de 2022. Por
  isso, o backtest de 2018 mede o projetor sob a ordem de 2022, não sob a ordem
  real daquela noite.

No 1º turno vale o mesmo: 2022 observado e 2018 simulado a partir do 1º
turno de 2022.

Uso:
    python -m projetor.ordem --turno 2
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from projetor import tempo
from projetor.ingest import DATA_INTERIM
from projetor.locais import CHAVE_LOCAL, carregar_secoes, locais, parear

log = logging.getLogger(__name__)

NIVEIS_FONTE = ["local", "zona", "municipio", "uf"]


def relogio_2022(secoes: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta `momento` (divulgação, com fuso) e `relogio` às seções de 2022."""
    out = secoes.copy()
    turno = int(out["turno"].iloc[0])
    out["momento"] = tempo.momento_divulgacao(tempo.recebido_em_brasilia(out), 2022, turno)
    ordem = out.sort_values(["momento", *CHAVE_LOCAL, "nr_secao"]).index
    out.loc[ordem, "relogio"] = np.arange(1, len(out) + 1) / len(out)
    return out


def _quantis_por_grupo(fonte: pd.Series, alvo: pd.DataFrame, chave: list[str]) -> pd.Series:
    """Para cada grupo de `alvo`, distribui quantis do relógio de 2022 do mesmo grupo."""
    distribuicoes = {k: np.sort(v.to_numpy()) for k, v in fonte.groupby(level=list(range(len(chave))))}
    resultado = pd.Series(np.nan, index=alvo.index)
    for k, grupo in alvo.groupby(chave, sort=False):
        dist = distribuicoes.get(k if isinstance(k, tuple) else (k,))
        if dist is None:
            continue
        grupo = grupo.sort_values("nr_secao")
        q = (np.arange(len(grupo)) + 0.5) / len(grupo)
        resultado.loc[grupo.index] = np.quantile(dist, q)
    return resultado


def ordem_2018(secoes_2018: pd.DataFrame, secoes_2022: pd.DataFrame, pares: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta `fonte_ordem` e `relogio` (simulado) às seções de 2018."""
    r22 = relogio_2022(secoes_2022)
    out = secoes_2018.merge(pares[[*CHAVE_LOCAL, "tipo_par", "nr_zona_2022", "nr_local_2022"]], on=CHAVE_LOCAL)
    if len(out) != len(secoes_2018):
        raise RuntimeError("pareamento de locais não cobre todas as seções de 2018")

    # Chaves de 2022 para cada nível; quem não tem par fica com NA e cai no nível seguinte.
    out["_zona"] = out["nr_zona_2022"]
    out["_local"] = out["nr_local_2022"]
    niveis = {
        "local": (["cd_municipio", "_zona", "_local"], ["cd_municipio", "nr_zona", "nr_local_votacao"]),
        "zona": (["cd_municipio", "_zona"], ["cd_municipio", "nr_zona"]),
        "municipio": (["cd_municipio"], ["cd_municipio"]),
        "uf": (["uf"], ["uf"]),
    }
    bruto = pd.Series(np.nan, index=out.index)
    fonte = pd.Series(pd.NA, index=out.index, dtype="object")
    for nivel in NIVEIS_FONTE:
        chave_2018, chave_2022 = niveis[nivel]
        pendentes = out[bruto.isna()].dropna(subset=chave_2018)
        if pendentes.empty:
            continue
        dist_2022 = r22.set_index(chave_2022)["relogio"]
        valores = _quantis_por_grupo(dist_2022, pendentes, chave_2018)
        achados = valores.dropna().index
        bruto.loc[achados] = valores.loc[achados]
        fonte.loc[achados] = nivel
    if bruto.isna().any():
        raise RuntimeError(f"{bruto.isna().sum()} seções de 2018 sem ordem")

    out["fonte_ordem"] = pd.Categorical(fonte, categories=NIVEIS_FONTE)
    ordem = pd.DataFrame({"bruto": bruto, "m": out["cd_municipio"], "s": out["nr_secao"]}).sort_values(["bruto", "m", "s"]).index
    out.loc[ordem, "relogio"] = np.arange(1, len(out) + 1) / len(out)
    return out.drop(columns=["_zona", "_local"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--turno", type=int, choices=(1, 2), default=2)
    turno = parser.parse_args().turno
    s18, s22 = carregar_secoes(2018, turno), carregar_secoes(2022, turno)
    pares = parear(locais(s18), locais(s22))
    r22 = relogio_2022(s22)
    r18 = ordem_2018(s18, s22, pares)
    r22.to_parquet(DATA_INTERIM / f"ordem_2022_{turno}t.parquet", index=False)
    r18.to_parquet(DATA_INTERIM / f"ordem_2018_{turno}t.parquet", index=False)
    print(r18["fonte_ordem"].value_counts().reindex(NIVEIS_FONTE).to_string())


if __name__ == "__main__":
    main()
