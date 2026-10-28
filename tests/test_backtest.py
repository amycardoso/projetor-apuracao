import numpy as np
import pandas as pd
import pytest

from projetor.backtest import COLUNAS_PENDENTES, dividir, rodar, tempo_ate_cravar
from projetor.models.baseline import Apurado, SwingUniforme, SwingUniformeUF
from projetor.models.camadas import SwingCamadas, SwingCamadasIntercepto, SwingCamadasInterceptoPorte, SwingCamadasPorte
from projetor.models.hierarquico import SwingHierarquico
from projetor.models.ols import SwingOLS

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


@pytest.mark.parametrize(
    "modelo",
    [
        Apurado(),
        SwingUniforme(),
        SwingUniformeUF(min_secoes=5),
        SwingOLS(min_locais=20),
        SwingCamadas(k=10, min_locais=20, min_locais_grupo=5),
        SwingCamadasPorte(k=10, min_locais=20, min_locais_grupo=5),
        SwingCamadasIntercepto(k=10, min_locais=20, min_locais_grupo=5),
        SwingCamadasInterceptoPorte(k=10, min_locais=20, min_locais_grupo=5),
        SwingHierarquico(n_advi=500, n_amostras=50),
        SwingHierarquico(
            n_advi=500, n_amostras=50, discrepancia=1.0, escala_discrepancia="distancia", nome="SwingHierarquicoDelta"
        ),
    ],
    ids=lambda m: m.nome,
)
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


def test_ols_recupera_swing_que_depende_do_voto_anterior(secoes):
    # swing = 10 - 0,1 * ant_pct_pt, sem ruído: a regressão deve acertar o final.
    pct = (secoes["ant_pct_pt"] + 10 - 0.1 * secoes["ant_pct_pt"]) / 100
    secoes = secoes.assign(votos_pt=225 * pct, votos_adversario=225 * (1 - pct))
    assert rodar(SwingOLS(min_locais=20), secoes, grade=[0.3])["erro"].abs().max() < 1e-6


def test_camadas_intercepto_captura_swing_diferente_por_uf(secoes):
    swing_uf = secoes["uf"].map({"SP": 12.0, "BA": -2.0, "RS": 5.0})
    pct = (secoes["ant_pct_pt"] + swing_uf).clip(0, 100) / 100
    # Um local por seção, para que nenhum local misture UFs.
    secoes = secoes.assign(votos_pt=225 * pct, votos_adversario=225 * (1 - pct), nr_local_votacao=secoes["nr_secao"])
    modelo = SwingCamadasIntercepto(k=0.001, min_locais=20, min_locais_grupo=5)
    assert rodar(modelo, secoes, grade=[0.3])["erro"].abs().max() < 0.05


def test_hierarquico_guarda_amostras_e_taus(secoes):
    resultado = rodar(SwingHierarquico(n_advi=500, n_amostras=50), secoes, grade=[0.3])
    assert resultado["amostras"].iloc[0].shape == (50,)
    assert {"tau_regiao", "tau_uf", "tau_ufcap", "sigma", "fracao_pendente", "distancia"} <= set(resultado["resumo"].iloc[0])


def test_discrepancia_alarga_as_amostras_sem_mover_o_centro(secoes):
    sem = rodar(SwingHierarquico(n_advi=500, n_amostras=400), secoes, grade=[0.3])
    com = rodar(SwingHierarquico(n_advi=500, n_amostras=400, discrepancia=5.0), secoes, grade=[0.3])
    # Mesma semente: a diferença entre as amostras é o próprio delta, na escala fração × c.
    delta = com["amostras"].iloc[0] - sem["amostras"].iloc[0]
    assert delta.std() == pytest.approx(5.0 * com["resumo"].iloc[0]["fracao_pendente"], rel=0.15)
    assert abs(delta.mean()) < 0.5
