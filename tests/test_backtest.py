import numpy as np
import pandas as pd
import pytest

from projetor.backtest import COLUNAS_PENDENTES, dividir, rodar, tempo_ate_cravar
from projetor.models.baseline import Apurado, SwingUniforme, SwingUniformeUF

PROIBIDAS = ("votos_", "qt_comparecimento", "qt_abstencoes", "dt_", "momento", "relogio", "ds_tipo_urna")


@pytest.fixture
def secoes():
    rng = np.random.default_rng(42)
    n = 400
    df = pd.DataFrame(
        {
            "ano": 2022, "turno": 2, "uf": rng.choice(["SP", "BA", "RS"], n), "cd_municipio": rng.integers(1, 20, n),
            "nm_municipio": "X", "nr_zona": 1, "nr_secao": np.arange(n), "nr_local_votacao": rng.integers(1, 50, n),
            "qt_aptos": 300, "qt_comparecimento": 250, "qt_abstencoes": 50,
            "ant_pct_pt": rng.uniform(30, 70, n), "ant_taxa_validos": 0.75, "ant_fonte": "local",
            "ds_tipo_urna": "APURADA", "dt_encerramento": pd.Timestamp("2022-10-30 17:00"),
        }
    )  # fmt: skip
    pct = (df["ant_pct_pt"] + 5).clip(0, 100) / 100
    df["votos_pt"] = (225 * pct).round().astype(int)
    df["votos_adversario"] = 225 - df["votos_pt"]
    df["votos_branco"] = df["votos_nulo"] = 0
    df["relogio"] = rng.permutation(n) / n + 1 / n
    return df


def test_pendentes_so_trazem_covariaveis_permitidas(secoes):
    for t in (0.005, 0.3, 0.95):
        divulgadas, pendentes = dividir(secoes, t)
        assert list(pendentes.columns) == COLUNAS_PENDENTES
        assert not [c for c in pendentes.columns if c.startswith(PROIBIDAS)]
        assert set(divulgadas.index).isdisjoint(pendentes.index)
        assert len(divulgadas) + len(pendentes) == len(secoes)


@pytest.mark.parametrize("modelo", [Apurado(), SwingUniforme(), SwingUniformeUF(min_secoes=5)])
def test_projecao_nao_depende_dos_votos_das_pendentes(secoes, modelo):
    t = 0.3
    embaralhado = secoes.copy()
    futuras = embaralhado["relogio"] > t
    embaralhado.loc[futuras, "votos_pt"] = 0
    embaralhado.loc[futuras, "votos_adversario"] = 999

    original = modelo.projetar(*dividir(secoes, t))
    alterado = modelo.projetar(*dividir(embaralhado, t))

    assert original == pytest.approx(alterado)


def test_swing_uniforme_acerta_quando_o_swing_e_de_fato_uniforme(secoes):
    resultado = rodar(SwingUniforme(), secoes, grade=[0.1, 0.5])
    assert resultado["erro"].abs().max() < 0.1


def test_tempo_ate_cravar_exige_ficar_dentro_ate_o_fim():
    r = pd.DataFrame({"t": [0.1, 0.2, 0.3, 0.4], "erro": [1.0, 0.2, 0.6, 0.1]})
    assert tempo_ate_cravar(r) == 0.4
    assert np.isnan(tempo_ate_cravar(r.assign(erro=[0.1, 0.1, 0.1, 0.7])))
    assert tempo_ate_cravar(r.assign(erro=0.0)) == 0.1
