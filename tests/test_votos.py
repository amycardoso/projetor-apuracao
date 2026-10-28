import pandas as pd

from projetor.backtest import pct_pt
from projetor.votos import trocar_alvo, validos


def _secoes() -> pd.DataFrame:
    return pd.DataFrame({"votos_pt": [40, 10], "votos_adversario": [30, 20], "votos_outros": [30, 0]})


def test_validos_inclui_outros_candidatos():
    assert validos(_secoes()).tolist() == [100, 30]


def test_validos_sem_coluna_de_outros():
    assert validos(_secoes().drop(columns="votos_outros")).tolist() == [70, 30]


def test_pct_no_primeiro_turno_usa_todos_os_validos():
    assert pct_pt(_secoes()) == 100 * 50 / 130


def test_trocar_alvo_projeta_o_adversario():
    assert pct_pt(trocar_alvo(_secoes())) == 100 * 50 / 130
    assert trocar_alvo(_secoes())["votos_pt"].tolist() == [30, 20]
