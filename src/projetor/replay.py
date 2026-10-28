"""Reprodução da apuração: o que já tinha sido divulgado em um instante.

Toda projeção do backtest deve partir de `estado_em`, para que nenhuma
informação de seções ainda não divulgadas vaze para o modelo.
"""

from __future__ import annotations

import pandas as pd


def estado_em(secoes: pd.DataFrame, t: float | pd.Timestamp) -> pd.DataFrame:
    """Seções já divulgadas até `t`.

    `t` pode ser uma fração de seções entre 0 e 1 (usa a coluna `relogio`) ou um
    instante com fuso (usa a coluna `momento`, só existente em 2022).
    """
    if isinstance(t, pd.Timestamp):
        if t.tzinfo is None:
            raise ValueError("instante sem fuso; use pd.Timestamp(..., tz='America/Sao_Paulo')")
        if "momento" not in secoes:
            raise ValueError("estas seções não têm `momento`; use uma fração de 0 a 1")
        return secoes[secoes["momento"] <= t]
    if not 0 <= t <= 1:
        raise ValueError(f"fração fora de [0, 1]: {t}")
    return secoes[secoes["relogio"] <= t]


def parcial(secoes: pd.DataFrame) -> pd.Series:
    """Totais e % do PT nos votos válidos de um conjunto de seções."""
    validos = secoes["votos_pt"].sum() + secoes["votos_adversario"].sum()
    return pd.Series(
        {
            "secoes": len(secoes),
            "votos_pt": secoes["votos_pt"].sum(),
            "votos_adversario": secoes["votos_adversario"].sum(),
            "pct_pt": 100 * secoes["votos_pt"].sum() / validos if validos else float("nan"),
        }
    )
