"""`SwingCamadas`: regressões de swing em camadas, com encolhimento.

A mesma WLS de `SwingOLS` é ajustada separadamente em cada nível: nacional,
região (5 + exterior) e UF (27 + ZZ). O exterior é sua própria região e UF,
então só divide o nível nacional com o Brasil.

A previsão de uma pendente encolhe cada nível em direção ao de cima, do
nacional para baixo:

    p_regiao* = w_r · p_regiao + (1 - w_r) · p_nacional
    p_uf*     = w_u · p_uf     + (1 - w_u) · p_regiao*

com `w_j = n_j / (n_j + k)`, onde `n_j` é o número de locais divulgados no
grupo. Um grupo com menos de `min_locais_grupo` locais tem peso 0. O nacional
usa o swing uniforme enquanto houver menos de `min_locais` locais.

`niveis_extras` acrescenta camadas abaixo da UF. A variante `SwingCamadasPorte`
usa UF × capital/interior, sugerida pela fase 1.

O hiperparâmetro `k` é escolhido no backtest de 2018 e só depois avaliado em
2022 (ver `notebooks/02_ols.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from projetor.models.features import anexar_features, matriz, por_local, projetar_com_swing, wls
from projetor.models.ols import swing_uniforme


def _grupo(df: pd.DataFrame, colunas: list[str]) -> pd.Series:
    chave = df[colunas[0]].astype(str)
    for c in colunas[1:]:
        chave = chave + "|" + df[c].astype(str)
    return chave


@dataclass
class SwingCamadas:
    k: float = 100.0
    min_locais: int = 200
    min_locais_grupo: int = 20
    niveis_extras: list[list[str]] = field(default_factory=list)
    nome: str = "SwingCamadas"

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float:
        div, pend = anexar_features(divulgadas, pendentes)
        locais = por_local(div)
        if len(locais) < self.min_locais:
            return projetar_com_swing(divulgadas, pendentes, swing_uniforme(locais))

        x_pend = matriz(pend)
        previsao = x_pend @ wls(locais)
        for colunas in [["regiao"], ["uf"], *self.niveis_extras]:
            g_loc, g_pend = _grupo(locais, colunas), _grupo(pend, colunas)
            nivel = previsao.copy()
            pesos = np.zeros(len(pend))
            for grupo, loc_g in locais.groupby(g_loc):
                if len(loc_g) < self.min_locais_grupo:
                    continue
                alvo = (g_pend == grupo).to_numpy()
                if not alvo.any():
                    continue
                nivel[alvo] = x_pend[alvo] @ wls(loc_g)
                pesos[alvo] = len(loc_g) / (len(loc_g) + self.k)
            previsao = pesos * nivel + (1 - pesos) * previsao
        return projetar_com_swing(divulgadas, pendentes, pd.Series(previsao, index=pend.index))


def SwingCamadasPorte(k: float = 100.0, **kwargs) -> SwingCamadas:  # noqa: N802 - fábrica com cara de classe
    return SwingCamadas(k=k, niveis_extras=[["uf", "capital"]], nome="SwingCamadasPorte", **kwargs)
