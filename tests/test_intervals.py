import numpy as np
import pandas as pd

from projetor.backtest import dividir
from projetor.intervals import (
    Preparo,
    analitico_camadas,
    bootstrap_camadas,
    conformal_por_faixa,
    faixa_amostras,
    faixa_normal,
    winkler,
)
from projetor.models.camadas import SwingCamadasInterceptoPorte

from .test_backtest import secoes  # noqa: F401 - fixture


def test_winkler_penaliza_so_fora_da_faixa():
    lo, hi = np.array([49.0, 49.0, 49.0]), np.array([51.0, 51.0, 51.0])
    y = np.array([50.0, 48.0, 52.5])
    assert np.allclose(winkler(lo, hi, y, 0.9), [2.0, 2 + 20 * 1.0, 2 + 20 * 1.5])


def test_conformal_usa_o_quantil_de_ordem_corrigida():
    calib = pd.DataFrame({"t": np.linspace(0.3, 0.45, 10), "erro": np.arange(1, 11) / 10})
    q = conformal_por_faixa(calib, [0.5, 0.9])
    # n = 10: nível 0,5 -> ordem 6; nível 0,9 -> ordem 10 (o máximo).
    assert q.loc["25–50%", 0.5] == 0.6
    assert q.loc["25–50%", 0.9] == 1.0


def test_faixas_normal_e_de_amostras_coincidem_para_normal():
    rng = np.random.default_rng(0)
    amostras = rng.normal(50, 1, (1, 200_000))
    lo_a, hi_a = faixa_amostras(amostras, 0.9)
    lo_n, hi_n = faixa_normal(np.array([50.0]), np.array([1.0]), 0.9)
    assert np.allclose([lo_a[0], hi_a[0]], [lo_n[0], hi_n[0]], atol=0.02)


def test_analitico_e_bootstrap_dao_faixas_finitas_e_centradas(secoes):  # noqa: F811
    modelo = SwingCamadasInterceptoPorte(k=10, min_locais=20, min_locais_grupo=5)
    prep = Preparo.de(*dividir(secoes, 0.3))
    centro, sd = analitico_camadas(modelo, prep)
    amostras = bootstrap_camadas(modelo, prep, b=30)
    assert np.isfinite(centro) and sd > 0
    assert abs(amostras.mean() - centro) < 3 * max(sd, amostras.std())
