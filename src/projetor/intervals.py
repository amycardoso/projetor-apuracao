"""Faixas para o % PT final e métricas de calibração.

Quatro métodos, todos avaliados nos mesmos pontos da grade do backtest:

- (a) `analitico_camadas`: erro de previsão do `SwingCamadas` propagado para o
  total, em forma fechada (aproximação normal). Ver o docstring da função.
- (b) `bootstrap_camadas`: reamostra os locais divulgados, reajusta o modelo e
  soma às pendentes um resíduo de swing e de comparecimento sorteado dos
  próprios locais divulgados (bootstrap preditivo).
- (c) posterior do `SwingHierarquico`: as amostras gravadas pelo backtest.
- (d) `conformal_por_faixa`: quantis de |erro| do modelo pontual em outro ano,
  por faixa de relógio (split conformal no tempo).
- (e) `conformal_normalizado`: recalibra uma faixa probabilística (c) pelo
  quantil de |erro|/desvio observado no outro ano. Mantém a forma da faixa ao
  longo da noite e corrige só a escala.

As faixas de (a), (b) e (c) incluem a incerteza do comparecimento das
pendentes: log(válidos reais / esperados) por local, medido nos divulgados.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from projetor.models.camadas import SwingCamadas, _grupo
from projetor.models.features import (
    anexar_features,
    comparecimento,
    matriz,
    pendentes_por_local,
    por_local,
)

FAIXAS_RELOGIO = [0.0, 0.025, 0.10, 0.25, 0.50, 1.0]
ROTULOS_FAIXA = ["até 2,5%", "2,5–10%", "10–25%", "25–50%", "50–95%"]


def faixa_de(t: float | np.ndarray) -> pd.Categorical:
    return pd.cut(np.atleast_1d(t), FAIXAS_RELOGIO, labels=ROTULOS_FAIXA)


@dataclass
class Preparo:
    """Locais divulgados e locais pendentes já com covariáveis, para um instante."""

    locais: pd.DataFrame
    pend: pd.DataFrame
    pt_div: float
    val_div: float

    @classmethod
    def de(cls, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> Preparo:
        div, pend = anexar_features(divulgadas, pendentes)
        return cls(
            locais=por_local(div),
            pend=pendentes_por_local(pend),
            pt_div=float(divulgadas["votos_pt"].sum()),
            val_div=float((divulgadas["votos_pt"] + divulgadas["votos_adversario"]).sum()),
        )

    def total(self, pct_pend: np.ndarray, validos_pend: np.ndarray | None = None) -> float:
        v = self.pend["validos_esperados"].to_numpy() if validos_pend is None else validos_pend
        return 100 * (self.pt_div + v @ pct_pend / 100) / (self.val_div + v.sum())


def analitico_camadas(modelo: SwingCamadas, prep: Preparo) -> tuple[float, float]:
    """Centro e desvio-padrão do % PT final, em forma fechada.

    Var(Σ e_j·swing_j) soma quatro termos, com e_j = válidos esperados do local
    pendente j, W = pesos normalizados pela média dos divulgados e σ² a
    variância residual ponderada dos locais divulgados em torno da previsão
    final do modelo:

    1. coeficientes da WLS nacional: g'·Cov(b)·g, com g = Σ e_j x_j;
    2. deslocamentos de cada nível (modo intercepto): o deslocamento d_L de um
       grupo entra na previsão com peso w_L = n/(n+k) e tem variância
       σ²/ΣW_grupo; é comum a todas as pendentes do grupo;
    3. ruído local: Σ e_j² σ² / W_j;
    4. comparecimento: Σ (e_j (pct_j − P)/D)² s²/W_j.

    Termos 1–3 são divididos por D² (D = válidos divulgados + esperados).
    A aproximação ignora a covariância entre níveis e trata k como fixo.
    """
    loc, pend = prep.locais, prep.pend
    e = pend["validos_esperados"].to_numpy()
    w_medio = loc["validos_esperados"].mean()
    w_loc = loc["validos_esperados"].to_numpy() / w_medio
    w_pend = e / w_medio
    d = prep.val_div + e.sum()

    swing_pend = modelo.prever_swing(loc, pend)
    pct_pend = np.clip(pend["ant_pct_pt"].to_numpy() + swing_pend, 0, 100)
    centro = prep.total(pct_pend)

    residuo = loc["swing"].to_numpy() - modelo.prever_swing(loc, loc)
    uniforme = len(loc) < modelo.min_locais
    p = 1 if uniforme else matriz(loc).shape[1]
    sigma2 = float(np.sum(w_loc * residuo**2) / max(len(loc) - p, 1))

    if uniforme:
        var_coef = e.sum() ** 2 * sigma2 / w_loc.sum()
        var_desloc = 0.0
    else:
        x = matriz(loc)
        cov = sigma2 * np.linalg.pinv(x.T @ (x * w_loc[:, None]))
        g = matriz(pend).T @ e
        var_coef = float(g @ cov @ g)
        var_desloc = 0.0
        if modelo.modo == "intercepto":
            for colunas in [["regiao"], ["uf"], *modelo.niveis_extras]:
                g_loc, g_pend = _grupo(loc, colunas).to_numpy(), _grupo(pend, colunas).to_numpy()
                for grupo in np.unique(g_loc):
                    no_grupo = g_loc == grupo
                    n = int(no_grupo.sum())
                    if n < modelo.min_locais_grupo:
                        continue
                    peso = n / (n + modelo.k)
                    e_g = e[g_pend == grupo].sum()
                    var_desloc += (peso * e_g) ** 2 * sigma2 / w_loc[no_grupo].sum()
    var_ruido = float(np.sum(e**2 * sigma2 / w_pend))

    _, s_comp = comparecimento(loc)
    var_comp = float(np.sum((e * (pct_pend - centro) / d) ** 2 * s_comp**2 / w_pend))
    return centro, float(np.sqrt((var_coef + var_desloc + var_ruido) / d**2 + var_comp))


def bootstrap_camadas(modelo: SwingCamadas, prep: Preparo, b: int = 200, semente: int = 0) -> np.ndarray:
    """Amostras preditivas do % PT final por bootstrap de locais.

    Em cada réplica: reamostra os locais divulgados com reposição, reajusta o
    modelo e prevê o swing das pendentes; a cada local pendente soma o resíduo
    padronizado (swing e log do comparecimento, do mesmo local, para manter a
    correlação) de um local divulgado sorteado, reescalado pelo seu peso.
    """
    rng = np.random.default_rng(semente)
    loc, pend = prep.locais, prep.pend
    e = pend["validos_esperados"].to_numpy()
    ant = pend["ant_pct_pt"].to_numpy()
    w_medio = loc["validos_esperados"].mean()
    raiz_w_loc = np.sqrt(loc["validos_esperados"].to_numpy() / w_medio)
    raiz_w_pend = np.sqrt(e / w_medio)

    res_swing = (loc["swing"].to_numpy() - modelo.prever_swing(loc, loc)) * raiz_w_loc
    log_comp = np.log(loc["validos"].to_numpy() / loc["validos_esperados"].to_numpy())
    m_comp = np.average(log_comp, weights=loc["validos_esperados"])
    res_comp = (log_comp - m_comp) * raiz_w_loc
    # Os sorteios são uniformes entre locais, então os resíduos padronizados precisam de média zero.
    res_swing -= res_swing.mean()
    res_comp -= res_comp.mean()

    amostras = np.empty(b)
    for i in range(b):
        idx = rng.integers(0, len(loc), len(loc))
        swing = modelo.prever_swing(loc.iloc[idx].reset_index(drop=True), pend)
        sorteio = rng.integers(0, len(loc), len(pend))
        pct = np.clip(ant + swing + res_swing[sorteio] / raiz_w_pend, 0, 100)
        validos = e * np.exp(m_comp + res_comp[sorteio] / raiz_w_pend)
        amostras[i] = prep.total(pct, validos)
    return amostras


def conformal_por_faixa(calibracao: pd.DataFrame, niveis: list[float]) -> pd.DataFrame:
    """Quantil conformal de |erro| por faixa de relógio.

    `calibracao` tem `t` e `erro` do modelo pontual no ano de calibração. Para
    cada faixa com n pontos, usa o quantil de ordem ⌈(n+1)·nível⌉/n (o máximo
    quando passa de n).
    """
    c = calibracao.assign(faixa=faixa_de(calibracao["t"].to_numpy()), abs_erro=calibracao["erro"].abs())
    linhas = {}
    for faixa, g in c.groupby("faixa", observed=True):
        n = len(g)
        ordenado = np.sort(g["abs_erro"].to_numpy())
        linhas[faixa] = {nivel: ordenado[min(int(np.ceil((n + 1) * nivel)), n) - 1] for nivel in niveis}
    return pd.DataFrame(linhas).T.rename_axis("faixa")


def conformal_normalizado(erro: np.ndarray, desvio: np.ndarray, niveis: list[float]) -> dict[float, float]:
    """Multiplicador conformal do desvio: quantil de ordem ⌈(n+1)·nível⌉/n de |erro|/desvio."""
    escores = np.sort(np.abs(erro) / desvio)
    n = len(escores)
    return {nivel: float(escores[min(int(np.ceil((n + 1) * nivel)), n) - 1]) for nivel in niveis}


def winkler(lo: np.ndarray, hi: np.ndarray, y: np.ndarray, nivel: float) -> np.ndarray:
    """Interval score: largura + (2/α)·distância até a faixa quando o valor fica fora."""
    alfa = 1 - nivel
    return (hi - lo) + (2 / alfa) * np.clip(lo - y, 0, None) + (2 / alfa) * np.clip(y - hi, 0, None)


def faixa_normal(centro: np.ndarray, sd: np.ndarray, nivel: float) -> tuple[np.ndarray, np.ndarray]:
    z = stats.norm.ppf(0.5 + nivel / 2)
    return centro - z * sd, centro + z * sd


def faixa_amostras(amostras: np.ndarray, nivel: float) -> tuple[np.ndarray, np.ndarray]:
    """`amostras` com forma (pontos, amostras)."""
    a = (1 - nivel) / 2
    return np.percentile(amostras, 100 * a, axis=1), np.percentile(amostras, 100 * (1 - a), axis=1)
