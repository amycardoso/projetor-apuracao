"""Modelos de referência para o backtest.

- `Apurado`: a parcial atual, sem projeção nenhuma.
- `SwingUniforme`: mede o swing contra a eleição anterior nas seções já
  divulgadas (média de `pct_pt - ant_pct_pt` ponderada pelos válidos) e o
  aplica ao `ant_pct_pt` de cada seção pendente. As pendentes pesam pelos
  válidos esperados, `qt_aptos × ant_taxa_validos`.
- `SwingUniformeUF`: igual, com um swing por UF; uma UF com menos de
  `min_secoes` divulgadas usa o swing nacional.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _validos(secoes: pd.DataFrame) -> pd.Series:
    return secoes["votos_pt"] + secoes["votos_adversario"]


def _projetar_com_swing(divulgadas: pd.DataFrame, pendentes: pd.DataFrame, swing: pd.Series | float) -> float:
    pt_div = divulgadas["votos_pt"].sum()
    val_div = _validos(divulgadas).sum()
    esperados = pendentes["qt_aptos"] * pendentes["ant_taxa_validos"]
    pct = (pendentes["ant_pct_pt"] + swing).clip(0, 100)
    return 100 * (pt_div + (esperados * pct / 100).sum()) / (val_div + esperados.sum())


def _swing(divulgadas: pd.DataFrame) -> float:
    validos = _validos(divulgadas)
    if validos.sum() == 0:
        return 0.0
    pct = 100 * divulgadas["votos_pt"] / validos.where(validos > 0)
    return float(np.average((pct - divulgadas["ant_pct_pt"]).fillna(0), weights=validos))


@dataclass
class Apurado:
    nome: str = "Apurado"

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float:
        return 100 * divulgadas["votos_pt"].sum() / _validos(divulgadas).sum()


@dataclass
class SwingUniforme:
    nome: str = "SwingUniforme"

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float:
        return _projetar_com_swing(divulgadas, pendentes, _swing(divulgadas))


@dataclass
class SwingUniformeUF:
    min_secoes: int = 30
    nome: str = "SwingUniformeUF"

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float:
        nacional = _swing(divulgadas)
        por_uf = {uf: _swing(g) for uf, g in divulgadas.groupby("uf") if len(g) >= self.min_secoes}
        swing = pendentes["uf"].map(por_uf).fillna(nacional)
        return _projetar_com_swing(divulgadas, pendentes, swing)
