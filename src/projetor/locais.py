"""Pareamento dos locais de votação de 2018 com os de 2022.

Um local é identificado por município + zona + NR_LOCAL_VOTACAO. Para cada
local de 2018, o pareamento tenta, nesta ordem:

1. `direto`: a mesma chave existe em 2022.
2. `rezoneado`: o mesmo município + local existe em 2022, em uma única zona
   diferente. Isso cobre os rezoneamentos entre os dois pleitos.
3. `zona`: sem par de local, mas a zona (município + zona) existe em 2022.
4. `municipio`: só o município existe em 2022.
5. `sem_par`: nem o município existe em 2022 (cidades do exterior que
   deixaram de ter seção, por exemplo).

O número do local é reaproveitado pelos cartórios, então um par `direto` não
garante que seja o mesmo prédio. Para o propósito daqui (herdar a ordem de
chegada), o vizinho de mesmo número na mesma zona já é uma boa aproximação.

Uso:
    python -m projetor.locais
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from projetor.ingest import DATA_INTERIM

log = logging.getLogger(__name__)

CHAVE_LOCAL = ["cd_municipio", "nr_zona", "nr_local_votacao"]
TIPOS_PAR = ["direto", "rezoneado", "zona", "municipio", "sem_par"]


def carregar_secoes(ano: int, turno: int = 2, pasta: Path = DATA_INTERIM) -> pd.DataFrame:
    """Lê o parquet de seções com contagens em int64.

    O parquet guarda int32, e o pandas mantém esse tipo em somas e produtos.
    Uma conta como `100 * votos_da_regiao` passa de 2,1 bilhões e estoura sem
    aviso (32 milhões de válidos no Nordeste × 100).
    """
    secoes = pd.read_parquet(pasta / f"bu_{ano}_{turno}t.parquet")
    contagens = [c for c in secoes.columns if c.startswith(("qt_", "votos_"))]
    return secoes.astype(dict.fromkeys(contagens, "int64"))


def locais(secoes: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por local, com UF, número de seções e aptos."""
    return (
        secoes.groupby(CHAVE_LOCAL, as_index=False)
        .agg(uf=("uf", "first"), n_secoes=("nr_secao", "size"), qt_aptos=("qt_aptos", "sum"))
    )


def parear(locais_2018: pd.DataFrame, locais_2022: pd.DataFrame) -> pd.DataFrame:
    """Devolve os locais de 2018 com `tipo_par` e a zona e o local de 2022 usados."""
    base = locais_2018[CHAVE_LOCAL + ["uf", "n_secoes", "qt_aptos"]].copy()
    chaves_2022 = locais_2022[CHAVE_LOCAL]

    direto = base.merge(chaves_2022, on=CHAVE_LOCAL, how="left", indicator=True)["_merge"].eq("both").to_numpy()

    # Município + local que aparecem em uma única zona de 2022.
    por_local = chaves_2022.groupby(["cd_municipio", "nr_local_votacao"])["nr_zona"]
    unicos = por_local.agg(["nunique", "first"]).query("nunique == 1")["first"].rename("zona_2022_rezoneada")
    base = base.join(unicos, on=["cd_municipio", "nr_local_votacao"])
    rezoneado = ~direto & base["zona_2022_rezoneada"].notna().to_numpy()

    zonas_2022 = set(map(tuple, chaves_2022[["cd_municipio", "nr_zona"]].drop_duplicates().to_numpy()))
    tem_zona = [z in zonas_2022 for z in map(tuple, base[["cd_municipio", "nr_zona"]].to_numpy())]
    tem_municipio = base["cd_municipio"].isin(chaves_2022["cd_municipio"]).to_numpy()

    tipo = pd.Series("sem_par", index=base.index)
    tipo[tem_municipio] = "municipio"
    tipo[tem_zona] = "zona"
    tipo[rezoneado] = "rezoneado"
    tipo[direto] = "direto"
    base["tipo_par"] = pd.Categorical(tipo, categories=TIPOS_PAR)

    # Chave de 2022 usada para herdar a ordem (zona/local), quando existe.
    base["nr_zona_2022"] = base["nr_zona"].where(base["tipo_par"] != "rezoneado", base["zona_2022_rezoneada"])
    base.loc[base["tipo_par"].isin(["municipio", "sem_par"]), "nr_zona_2022"] = pd.NA
    base["nr_local_2022"] = base["nr_local_votacao"].where(base["tipo_par"].isin(["direto", "rezoneado"]))
    return base.drop(columns="zona_2022_rezoneada").astype({"nr_zona_2022": "Int64", "nr_local_2022": "Int64"})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    pares = parear(locais(carregar_secoes(2018)), locais(carregar_secoes(2022)))
    saida = DATA_INTERIM / "locais_2018_2022.parquet"
    pares.to_parquet(saida, index=False)
    resumo = pares.groupby("tipo_par", observed=False).agg(locais=("n_secoes", "size"), secoes=("n_secoes", "sum"))
    resumo["pct_locais"] = (100 * resumo["locais"] / resumo["locais"].sum()).round(2)
    print(resumo.to_string())
    log.info("gravado %s", saida)


if __name__ == "__main__":
    main()
