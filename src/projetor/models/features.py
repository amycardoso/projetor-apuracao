"""Covariáveis conhecidas antes da noite e agregação por local.

Todas vêm de colunas permitidas nas pendentes (`backtest.COLUNAS_PENDENTES`):
UF, município, aptos e histórico da eleição anterior. O eleitorado do
município soma os aptos de todas as seções, divulgadas ou não, porque o
número de aptos é publicado antes da eleição.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from projetor.votos import validos as _validos

CHAVE_LOCAL = ["cd_municipio", "nr_zona", "nr_local_votacao"]

REGIAO = {
    **dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
    "ZZ": "Exterior",
}
CAPITAIS = {
    "AC": "RIO BRANCO", "AL": "MACEIÓ", "AM": "MANAUS", "AP": "MACAPÁ", "BA": "SALVADOR",
    "CE": "FORTALEZA", "DF": "BRASÍLIA", "ES": "VITÓRIA", "GO": "GOIÂNIA", "MA": "SÃO LUÍS",
    "MG": "BELO HORIZONTE", "MS": "CAMPO GRANDE", "MT": "CUIABÁ", "PA": "BELÉM", "PB": "JOÃO PESSOA",
    "PE": "RECIFE", "PI": "TERESINA", "PR": "CURITIBA", "RJ": "RIO DE JANEIRO", "RN": "NATAL",
    "RO": "PORTO VELHO", "RR": "BOA VISTA", "RS": "PORTO ALEGRE", "SC": "FLORIANÓPOLIS",
    "SE": "ARACAJU", "SP": "SÃO PAULO", "TO": "PALMAS",
}  # fmt: skip

REGRESSORES = ["ant_pct_pt", "log_aptos_mun", "capital"]


def anexar_features(divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Acrescenta região, capital, log do eleitorado do município e válidos esperados."""
    ids = pd.concat([divulgadas[["cd_municipio", "qt_aptos"]], pendentes[["cd_municipio", "qt_aptos"]]])
    aptos_mun = ids.groupby("cd_municipio")["qt_aptos"].sum()

    def _anexar(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["regiao"] = df["uf"].map(REGIAO)
        df["capital"] = (df["nm_municipio"] == df["uf"].map(CAPITAIS)).astype(float)
        df["log_aptos_mun"] = np.log(df["cd_municipio"].map(aptos_mun))
        df["validos_esperados"] = df["qt_aptos"] * df["ant_taxa_validos"]
        return df

    return _anexar(divulgadas), _anexar(pendentes)


def por_local(divulgadas: pd.DataFrame) -> pd.DataFrame:
    """Agrega as seções divulgadas por local; `swing` em p.p. contra a eleição anterior.

    Espera `divulgadas` já com `anexar_features`.
    """
    d = divulgadas.assign(
        validos=_validos(divulgadas),
        _ant_x_peso=divulgadas["ant_pct_pt"] * divulgadas["validos_esperados"],
    )
    g = d.groupby(CHAVE_LOCAL).agg(
        uf=("uf", "first"),
        regiao=("regiao", "first"),
        capital=("capital", "first"),
        log_aptos_mun=("log_aptos_mun", "first"),
        votos_pt=("votos_pt", "sum"),
        validos=("validos", "sum"),
        validos_esperados=("validos_esperados", "sum"),
        _ant_x_peso=("_ant_x_peso", "sum"),
    )
    g = g[(g["validos"] > 0) & (g["validos_esperados"] > 0)]
    g["ant_pct_pt"] = g.pop("_ant_x_peso") / g["validos_esperados"]
    g["swing"] = 100 * g["votos_pt"] / g["validos"] - g["ant_pct_pt"]
    return g.reset_index()


def matriz(df: pd.DataFrame) -> np.ndarray:
    return np.column_stack([np.ones(len(df)), df[REGRESSORES].to_numpy(dtype=float)])


def wls(locais: pd.DataFrame) -> np.ndarray:
    """Coeficientes de swing ~ 1 + REGRESSORES, ponderados pelos válidos esperados."""
    raiz_w = np.sqrt(locais["validos_esperados"].to_numpy(dtype=float))
    coef, *_ = np.linalg.lstsq(matriz(locais) * raiz_w[:, None], locais["swing"].to_numpy() * raiz_w, rcond=None)
    return coef


def projetar_com_swing(divulgadas: pd.DataFrame, pendentes: pd.DataFrame, swing: pd.Series | float) -> float:
    """Soma os votos divulgados com os das pendentes projetados por `ant_pct_pt + swing`."""
    pt_div = divulgadas["votos_pt"].sum()
    val_div = _validos(divulgadas).sum()
    esperados = pendentes["qt_aptos"] * pendentes["ant_taxa_validos"]
    pct = (pendentes["ant_pct_pt"] + swing).clip(0, 100)
    return 100 * (pt_div + (esperados * pct / 100).sum()) / (val_div + esperados.sum())


def pendentes_por_local(pendentes: pd.DataFrame) -> pd.DataFrame:
    """Agrega as pendentes (já com `anexar_features`) por local.

    O ruído de previsão é de local, então a parte pendente de cada local vira
    uma unidade, com peso igual aos seus válidos esperados.
    """
    p = pendentes.assign(_ant_x_w=pendentes["ant_pct_pt"] * pendentes["validos_esperados"])
    g = p.groupby(CHAVE_LOCAL).agg(
        uf=("uf", "first"),
        regiao=("regiao", "first"),
        capital=("capital", "first"),
        log_aptos_mun=("log_aptos_mun", "first"),
        qt_aptos=("qt_aptos", "sum"),
        validos_esperados=("validos_esperados", "sum"),
        _ant_x_w=("_ant_x_w", "sum"),
    )
    g = g[g["validos_esperados"] > 0]
    g["ant_pct_pt"] = g.pop("_ant_x_w") / g["validos_esperados"]
    g["ant_taxa_validos"] = g["validos_esperados"] / g["qt_aptos"]
    return g.reset_index()


def comparecimento(locais: pd.DataFrame) -> tuple[float, float]:
    """Média e desvio (ponderados) de log(válidos reais / esperados) nos locais divulgados.

    O desvio vale para um local de peso médio; um local com peso `w` tem desvio
    `s / sqrt(w / w_medio)`.
    """
    w = locais["validos_esperados"].to_numpy(dtype=float)
    r = np.log(locais["validos"].to_numpy(dtype=float) / w)
    m = float(np.average(r, weights=w))
    s = float(np.sqrt(np.average((r - m) ** 2 * w / w.mean(), weights=np.ones_like(w))))
    return m, s
