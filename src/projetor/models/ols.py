"""`SwingOLS`: regressão do swing por local, no estilo das projeções de TV.

Em cada instante, agrega as seções divulgadas por local e ajusta uma WLS,
ponderada pelos válidos esperados:

    swing ~ 1 + ant_pct_pt + log(aptos do município) + capital

O swing previsto de cada pendente é somado ao seu `ant_pct_pt`. Com menos de
`min_locais` locais divulgados, a regressão não é confiável e o modelo usa o
swing uniforme.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from projetor.models.features import anexar_features, matriz, por_local, projetar_com_swing, wls


def swing_uniforme(locais: pd.DataFrame) -> float:
    if locais.empty:
        return 0.0
    return float(np.average(locais["swing"], weights=locais["validos"]))


@dataclass
class SwingOLS:
    min_locais: int = 200
    nome: str = "SwingOLS"

    def coeficientes(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> pd.Series:
        div, _ = anexar_features(divulgadas, pendentes)
        return pd.Series(wls(por_local(div)), index=["intercepto", "ant_pct_pt", "log_aptos_mun", "capital"])

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float:
        div, pend = anexar_features(divulgadas, pendentes)
        locais = por_local(div)
        if len(locais) < self.min_locais:
            return projetar_com_swing(divulgadas, pendentes, swing_uniforme(locais))
        swing = pd.Series(matriz(pend) @ wls(locais), index=pend.index)
        return projetar_com_swing(divulgadas, pendentes, swing)
