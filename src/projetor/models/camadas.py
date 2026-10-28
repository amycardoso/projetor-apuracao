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

Com `modo="intercepto"`, só o nacional é uma regressão completa; região, UF e
os níveis extras estimam apenas um deslocamento, a média ponderada do resíduo
dos seus locais em relação ao nível de cima. É um efeito fixo encolhido, com
3 parâmetros a menos por grupo.

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
    modo: str = "regressao"
    nome: str = "SwingCamadas"

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float:
        div, pend = anexar_features(divulgadas, pendentes)
        locais = por_local(div)
        if len(locais) < self.min_locais:
            return projetar_com_swing(divulgadas, pendentes, swing_uniforme(locais))

        x_pend, x_loc = matriz(pend), matriz(locais)
        coef = wls(locais)
        previsao, previsao_loc = x_pend @ coef, x_loc @ coef
        swing_loc = locais["swing"].to_numpy()
        peso_loc = locais["validos_esperados"].to_numpy(dtype=float)
        for colunas in [["regiao"], ["uf"], *self.niveis_extras]:
            g_loc, g_pend = _grupo(locais, colunas).to_numpy(), _grupo(pend, colunas).to_numpy()
            nivel, nivel_loc = previsao.copy(), previsao_loc.copy()
            pesos, pesos_loc = np.zeros(len(pend)), np.zeros(len(locais))
            for grupo in np.unique(g_loc):
                no_grupo = g_loc == grupo
                n = int(no_grupo.sum())
                if n < self.min_locais_grupo:
                    continue
                alvo = g_pend == grupo
                if self.modo == "intercepto":
                    residuo = swing_loc[no_grupo] - previsao_loc[no_grupo]
                    desloc = np.average(residuo, weights=peso_loc[no_grupo])
                    nivel[alvo] += desloc
                    nivel_loc[no_grupo] += desloc
                else:
                    c = wls(locais[no_grupo])
                    nivel[alvo] = x_pend[alvo] @ c
                    nivel_loc[no_grupo] = x_loc[no_grupo] @ c
                pesos[alvo] = pesos_loc[no_grupo] = n / (n + self.k)
            previsao = pesos * nivel + (1 - pesos) * previsao
            previsao_loc = pesos_loc * nivel_loc + (1 - pesos_loc) * previsao_loc
        return projetar_com_swing(divulgadas, pendentes, pd.Series(previsao, index=pend.index))


def SwingCamadasPorte(k: float = 100.0, **kwargs) -> SwingCamadas:  # noqa: N802 - fábricas com cara de classe
    return SwingCamadas(k=k, niveis_extras=[["uf", "capital"]], nome="SwingCamadasPorte", **kwargs)


def SwingCamadasIntercepto(k: float = 100.0, **kwargs) -> SwingCamadas:  # noqa: N802
    return SwingCamadas(k=k, modo="intercepto", nome="SwingCamadasIntercepto", **kwargs)


def SwingCamadasInterceptoPorte(k: float = 100.0, **kwargs) -> SwingCamadas:  # noqa: N802
    return SwingCamadas(
        k=k, modo="intercepto", niveis_extras=[["uf", "capital"]], nome="SwingCamadasInterceptoPorte", **kwargs
    )
