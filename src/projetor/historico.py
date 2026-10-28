"""Covariáveis da eleição anterior para cada seção.

Cada seção da eleição-alvo recebe o resultado da eleição anterior no local de
votação equivalente (pareamento de `locais.py`). Na falta dele, recebe o da
zona, do município e, por último, da UF:

- `ant_pct_pt`: % do PT nos válidos da eleição anterior;
- `ant_taxa_validos`: válidos / aptos da eleição anterior no mesmo nível;
- `ant_fonte`: nível usado (`local`, `zona`, `municipio` ou `uf`).

Os válidos esperados de uma seção são `qt_aptos × ant_taxa_validos`, ou seja,
o comparecimento válido anterior reescalado pelos aptos atuais.

Pares de eleição usados no backtest: 2022 ← 2018 e 2018 ← 2014.
"""

from __future__ import annotations

import pandas as pd

from projetor.locais import CHAVE_LOCAL, locais, parear
from projetor.votos import validos

ANTERIOR = {2018: 2014, 2022: 2018}


def _agregar(secoes_ant: pd.DataFrame, chave: list[str]) -> pd.DataFrame:
    g = secoes_ant.assign(_validos=validos(secoes_ant)).groupby(chave)[["votos_pt", "_validos", "qt_aptos"]].sum()
    return pd.DataFrame(
        {"ant_pct_pt": 100 * g["votos_pt"] / g["_validos"], "ant_taxa_validos": g["_validos"] / g["qt_aptos"]}
    ).dropna()


def anexar_historico(secoes: pd.DataFrame, secoes_ant: pd.DataFrame) -> pd.DataFrame:
    """Devolve `secoes` com `ant_pct_pt`, `ant_taxa_validos` e `ant_fonte`."""
    pares = parear(locais(secoes), locais(secoes_ant))
    # `parear` nomeia as chaves de referência como *_2022; aqui são da eleição anterior.
    chaves_ant = pares[[*CHAVE_LOCAL, "nr_zona_2022", "nr_local_2022"]].rename(
        columns={"nr_zona_2022": "_zona_ant", "nr_local_2022": "_local_ant"}
    )
    out = secoes.merge(chaves_ant, on=CHAVE_LOCAL, how="left")
    if len(out) != len(secoes):
        raise RuntimeError("pareamento duplicou seções")

    niveis = [
        ("local", ["cd_municipio", "_zona_ant", "_local_ant"], CHAVE_LOCAL),
        ("zona", ["cd_municipio", "_zona_ant"], ["cd_municipio", "nr_zona"]),
        ("municipio", ["cd_municipio"], ["cd_municipio"]),
        ("uf", ["uf"], ["uf"]),
    ]
    out["ant_pct_pt"] = float("nan")
    out["ant_taxa_validos"] = float("nan")
    out["ant_fonte"] = pd.NA
    for nivel, chave_alvo, chave_ant in niveis:
        pendente = out["ant_pct_pt"].isna() & out[chave_alvo].notna().all(axis=1)
        if not pendente.any():
            continue
        ref = _agregar(secoes_ant, chave_ant)
        ref.index.names = chave_alvo
        achado = out.loc[pendente, chave_alvo].astype({c: "int64" for c in chave_alvo if c != "uf"}).join(ref, on=chave_alvo)
        ok = achado["ant_pct_pt"].notna()
        idx = achado.index[ok]
        out.loc[idx, ["ant_pct_pt", "ant_taxa_validos"]] = achado.loc[ok, ["ant_pct_pt", "ant_taxa_validos"]].to_numpy()
        out.loc[idx, "ant_fonte"] = nivel
    if out["ant_pct_pt"].isna().any():
        raise RuntimeError(f"{out['ant_pct_pt'].isna().sum()} seções sem histórico")
    out["ant_fonte"] = pd.Categorical(out["ant_fonte"], categories=[n for n, *_ in niveis])
    return out.drop(columns=["_zona_ant", "_local_ant"])
