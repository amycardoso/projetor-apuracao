import numpy as np
import pandas as pd
import pytest

from projetor import discrepancia
from projetor.discrepancia import Perfil


def _secoes(ufs: list[str]) -> pd.DataFrame:
    n = len(ufs)
    return pd.DataFrame(
        {
            "uf": ufs,
            "nm_municipio": ["X"] * n,
            "cd_municipio": range(n),
            "qt_aptos": [100] * n,
            "ant_taxa_validos": [0.8] * n,
            "votos_pt": [40] * n,
            "votos_adversario": [40] * n,
            "votos_outros": [0] * n,
        }
    )


def test_perfil_igual_tem_distancia_zero():
    p = discrepancia.perfil(_secoes(["SP", "BA"]), _secoes(["SP", "BA"]))
    assert p.distancia == pytest.approx(0.0)
    assert p.fracao_pendente == pytest.approx(0.5)


def test_perfil_disjunto_tem_distancia_um():
    p = discrepancia.perfil(_secoes(["SP"]), _secoes(["BA", "BA", "BA"]))
    assert p.distancia == pytest.approx(1.0)
    assert p.fracao_pendente == pytest.approx(240 / (80 + 240))


def test_aplicar_desloca_na_escala_da_fracao_pendente():
    amostras = np.zeros((2, 20_000))
    perfis = [Perfil(0.5, 0.2), Perfil(0.1, 0.2)]
    sd = discrepancia.aplicar(amostras, perfis, c=2.0, escala="fracao").std(axis=1)
    assert sd == pytest.approx([1.0, 0.2], rel=0.03)


def test_calibrar_recupera_c_e_zera_quando_a_posterior_basta():
    rng = np.random.default_rng(0)
    perfis = [Perfil(f, 1.0) for f in rng.uniform(0.1, 0.9, 4000)]
    s = discrepancia.desvio(perfis, 1.0, "fracao")
    erro = rng.normal(0, np.sqrt(0.01 + (1.5 * s) ** 2))
    assert discrepancia.calibrar(erro, np.full(4000, 0.01), perfis, "fracao") == pytest.approx(1.5, rel=0.05)
    pequeno = rng.normal(0, 0.1, 4000)
    assert discrepancia.calibrar(pequeno, np.full(4000, 1.0), perfis, "fracao") == 0.0
