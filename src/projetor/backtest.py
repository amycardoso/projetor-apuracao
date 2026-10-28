"""Simulador da noite eleitoral.

Em cada ponto de uma grade de relógio, o modelo recebe:

- `divulgadas`: as seções já divulgadas, com tudo (votos da noite inclusive);
- `pendentes`: as seções que faltam, só com as colunas de `COLUNAS_PENDENTES`
  (identificadores, aptos e histórico da eleição anterior). Votos, comparecimento,
  horários e a própria posição no relógio ficam de fora.

O modelo devolve o % PT final nos válidos, comparado com o resultado real.
O relatório dos baselines sai de `notebooks/01_baselines.py`.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
import pandas as pd

from projetor.replay import estado_em

GRADE = [0.005, 0.01, 0.025, 0.05, *np.round(np.arange(0.10, 0.951, 0.05), 2).tolist()]

COLUNAS_PENDENTES = [
    "ano", "turno", "uf", "cd_municipio", "nm_municipio", "nr_zona", "nr_secao", "nr_local_votacao",
    "qt_aptos", "ant_pct_pt", "ant_taxa_validos", "ant_fonte",
]  # fmt: skip


class Modelo(Protocol):
    nome: str

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float: ...


def pct_pt(secoes: pd.DataFrame) -> float:
    return 100 * secoes["votos_pt"].sum() / (secoes["votos_pt"].sum() + secoes["votos_adversario"].sum())


def dividir(secoes: pd.DataFrame, t: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa divulgadas e pendentes em `t`; pendentes só com colunas permitidas."""
    divulgadas = estado_em(secoes, t)
    pendentes = secoes.drop(divulgadas.index)[COLUNAS_PENDENTES].copy()
    return divulgadas, pendentes


def rodar(modelo: Modelo, secoes: pd.DataFrame, grade: list[float] = GRADE) -> pd.DataFrame:
    """Uma linha por ponto da grade: projeção, final e erro em p.p.

    Modelos probabilísticos que expõem `ultimas_amostras` e `ultimo_resumo`
    ganham as colunas `amostras` (array do % PT final) e `resumo` (dict).
    """
    final = pct_pt(secoes)
    linhas = []
    for t in grade:
        divulgadas, pendentes = dividir(secoes, t)
        projecao = modelo.projetar(divulgadas, pendentes)
        linha = {"modelo": modelo.nome, "t": t, "projecao": projecao, "final": final, "erro": projecao - final}
        if (amostras := getattr(modelo, "ultimas_amostras", None)) is not None:
            linha["amostras"] = amostras
            linha["resumo"] = dict(getattr(modelo, "ultimo_resumo", {}))
        linhas.append(linha)
    return pd.DataFrame(linhas)


def tempo_ate_cravar(resultado: pd.DataFrame, limite: float = 0.5) -> float:
    """Primeiro `t` da grade a partir do qual |erro| < limite em todos os pontos seguintes."""
    fora = resultado.sort_values("t")["erro"].abs().ge(limite).to_numpy()
    if fora[-1]:
        return float("nan")
    ultimo_fora = np.flatnonzero(fora)
    return float(resultado.sort_values("t")["t"].iloc[ultimo_fora[-1] + 1 if len(ultimo_fora) else 0])
