import numpy as np
import pandas as pd
import pytest

from projetor.replay import estado_em, parcial

FUSO = "America/Sao_Paulo"


@pytest.fixture
def secoes():
    n = 100
    rng = np.random.default_rng(0)
    momento = pd.Timestamp("2022-10-30 17:00", tz=FUSO) + pd.to_timedelta(rng.permutation(n), unit="min")
    df = pd.DataFrame({"momento": momento, "votos_pt": rng.integers(0, 200, n), "votos_adversario": rng.integers(0, 200, n)})
    df["relogio"] = df["momento"].rank(method="first") / n
    return df.sample(frac=1, random_state=1)  # ordem das linhas não deve importar


def test_estado_por_fracao_nunca_inclui_secao_futura(secoes):
    for t in np.linspace(0, 1, 21):
        estado = estado_em(secoes, t)
        assert (estado["relogio"] <= t).all()
        assert len(estado) == int(np.floor(t * len(secoes) + 1e-9))


def test_estado_por_instante_nunca_inclui_secao_futura(secoes):
    t = pd.Timestamp("2022-10-30 17:30", tz=FUSO)
    estado = estado_em(secoes, t)
    assert (estado["momento"] <= t).all()
    assert len(estado) == 31
    assert secoes.drop(estado.index)["momento"].gt(t).all()


def test_estados_sao_encaixados_e_terminam_no_total(secoes):
    anterior = set()
    for t in np.linspace(0, 1, 11):
        atual = set(estado_em(secoes, t).index)
        assert anterior <= atual
        anterior = atual
    assert parcial(estado_em(secoes, 1.0)).equals(parcial(secoes))


def test_estado_nao_altera_a_entrada(secoes):
    copia = secoes.copy()
    estado_em(secoes, 0.5)
    pd.testing.assert_frame_equal(secoes, copia)


def test_instante_sem_fuso_e_fracao_invalida_falham(secoes):
    with pytest.raises(ValueError):
        estado_em(secoes, pd.Timestamp("2022-10-30 18:00"))
    with pytest.raises(ValueError):
        estado_em(secoes, 1.5)
