"""2º turnos de governador como noites extras de calibração.

Cada UF com 2º turno de governador em 2018 ou 2022 vira uma noite:

- alvo: % do candidato A nos válidos (A + B), com A o de menor número;
- histórico: o 1º turno de governador do mesmo ano, nas mesmas seções, com o
  % de A entre A e B (os demais candidatos ficam de fora). O 1º turno é
  público três semanas antes, então não há vazamento;
- ordem: a da noite presidencial do mesmo dia (`ordem_{ano}_2t.parquet`),
  restrita à UF e reescalada para ir de 0 a 1. Em 2018 ela é simulada.

O 2º turno sai dos mesmos zips do presidencial (já em cache). Do 1º turno só
as UFs com 2º turno de governador são baixadas, e os zips são apagados depois.

Uso:
    python -m projetor.governador --anos 2018 2022
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from projetor.historico import anexar_historico
from projetor.ingest import (
    DATA_INTERIM,
    NR_BRANCO,
    NR_NULO,
    _sql_secoes,
    baixar,
    csv_extraido,
    ler_cabecalho,
    listar_recursos,
    normalizar_cabecalho,
)

log = logging.getLogger(__name__)

CHAVE_SECAO = ["cd_municipio", "nr_zona", "nr_secao"]


def _finalistas(csv_path: Path) -> tuple[int, int] | None:
    """Os dois números com mais votos para governador no 2º turno, ou None se não houve."""
    nomes = normalizar_cabecalho(ler_cabecalho(csv_path))
    linhas = duckdb.sql(
        f"""SELECT nr, sum(v) AS total FROM (
                SELECT TRY_CAST(NR_VOTAVEL AS INTEGER) AS nr, TRY_CAST(QT_VOTOS AS BIGINT) AS v
                FROM read_csv('{csv_path}', delim=';', quote='"', encoding='latin-1',
                              all_varchar=true, header=true, names={nomes!r})
                WHERE CD_CARGO_PERGUNTA = '3')
            WHERE nr IS NOT NULL AND nr NOT IN ({NR_BRANCO}, {NR_NULO})
            GROUP BY nr ORDER BY total DESC"""
    ).fetchall()
    if not linhas:
        return None
    if len(linhas) != 2:
        raise RuntimeError(f"{csv_path.name}: esperava 2 finalistas, achei {linhas}")
    a, b = sorted(nr for nr, _ in linhas)
    return a, b


def _secoes(csv_path: Path, ano: int, turno: int, uf: str, finalistas: tuple[int, int]) -> pd.DataFrame:
    a, b = finalistas
    df = duckdb.sql(_sql_secoes(csv_path, ano, turno, cargo="governador", candidatos={"pt": a, "adversario": b})).df()
    df = df.drop(columns=["_n_locais", "_n_aptos"])
    for c in ("votos_pt", "votos_adversario", "votos_branco", "votos_nulo", "votos_outros"):
        df[c] = df[c].fillna(0).astype("int64")
    return df.assign(uf=uf, nr_a=a, nr_b=b)


def processar(ano: int) -> tuple[Path, Path]:
    """Grava `gov_{ano}_2t.parquet` e `gov_{ano}_1t.parquet` só com as UFs que tiveram 2º turno."""
    finalistas: dict[str, tuple[int, int]] = {}
    segundo = []
    for recurso in listar_recursos(ano, 2):
        with csv_extraido(baixar(recurso), cargo="governador") as csv_path:
            par = _finalistas(csv_path)
            if par is None:
                continue
            finalistas[recurso.uf] = par
            segundo.append(_secoes(csv_path, ano, 2, recurso.uf, par))
            log.info("%s %s: 2º turno de governador entre %s e %s", ano, recurso.uf, *par)

    primeiro = []
    for recurso in listar_recursos(ano, 1):
        if recurso.uf not in finalistas:
            continue
        zip_path = baixar(recurso)
        with csv_extraido(zip_path, cargo="governador") as csv_path:
            primeiro.append(_secoes(csv_path, ano, 1, recurso.uf, finalistas[recurso.uf]))
        zip_path.unlink()

    saidas = []
    for turno, partes in ((2, segundo), (1, primeiro)):
        df = pd.concat(partes, ignore_index=True)
        if df.duplicated(CHAVE_SECAO).any():
            raise RuntimeError(f"governador {ano} {turno}t: seções duplicadas")
        if turno == 2 and df["votos_outros"].sum():
            raise RuntimeError(f"governador {ano} 2t: votos para números fora dos finalistas")
        saida = DATA_INTERIM / f"gov_{ano}_{turno}t.parquet"
        df.to_parquet(saida, index=False)
        saidas.append(saida)
        log.info("gravado %s (%d UFs, %d seções)", saida, df["uf"].nunique(), len(df))
    return saidas[0], saidas[1]


def carregar(ano: int, turno: int) -> pd.DataFrame:
    df = pd.read_parquet(DATA_INTERIM / f"gov_{ano}_{turno}t.parquet")
    contagens = [c for c in df.columns if c.startswith(("qt_", "votos_"))]
    return df.astype(dict.fromkeys(contagens, "int64"))


def noite(ano: int, uf: str) -> pd.DataFrame:
    """Seções do 2º turno de governador na UF, com relógio e histórico do 1º turno."""
    segundo = carregar(ano, 2).query("uf == @uf")
    primeiro = carregar(ano, 1).query("uf == @uf").assign(votos_outros=0)  # % de A entre A e B
    relogio = pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet", columns=[*CHAVE_SECAO, "relogio"])
    secoes = segundo.merge(relogio, on=CHAVE_SECAO, how="left")
    if secoes["relogio"].isna().any():
        raise RuntimeError(f"{ano} {uf}: {secoes['relogio'].isna().sum()} seções sem relógio presidencial")
    ordem = secoes.sort_values(["relogio", *CHAVE_SECAO]).index
    secoes.loc[ordem, "relogio"] = np.arange(1, len(secoes) + 1) / len(secoes)
    return anexar_historico(secoes, primeiro)


def ufs(ano: int) -> list[str]:
    return sorted(carregar(ano, 2)["uf"].unique())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--anos", type=int, nargs="+", default=[2018, 2022])
    for ano in parser.parse_args().anos:
        processar(ano)


if __name__ == "__main__":
    main()
