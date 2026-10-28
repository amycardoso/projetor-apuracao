import pandas as pd

from projetor import tempo


def _secoes(linhas):
    return pd.DataFrame(linhas, columns=["uf", "cd_municipio", "dt_encerramento"]).assign(
        dt_encerramento=lambda d: pd.to_datetime(d.dt_encerramento)
    )


def test_deslocamento_vem_da_hora_local_de_encerramento_em_2022():
    secoes = _secoes(
        [
            ("SP", 1, "2022-10-30 17:01"),
            ("AC", 2, "2022-10-30 15:02"),
            ("PE", 3, "2022-10-30 18:01"),
            ("ZZ", 4, "2022-10-30 17:05"),
        ]
    )
    assert tempo.deslocamento_por_municipio(secoes).to_dict() == {1: 0, 2: 2, 3: -1}


def test_encerramento_de_2018_vira_hora_de_brasilia_e_exterior_fica_nat():
    deslocamento = pd.Series({2: 2})
    secoes = _secoes([("AC", 2, "2018-10-28 17:00"), ("ZZ", 9, "2018-10-28 17:00")])

    convertido = tempo.encerramento_em_brasilia(secoes, deslocamento)

    assert convertido.iloc[0] == pd.Timestamp("2018-10-28 19:00", tz=tempo.FUSO_BRASILIA)
    assert pd.isna(convertido.iloc[1])


def test_divulgacao_nao_comeca_antes_do_horario_oficial():
    recebido = pd.Series(pd.to_datetime(["2022-10-30 03:24", "2022-10-30 18:10"])).dt.tz_localize(tempo.FUSO_BRASILIA)
    divulgado = tempo.momento_divulgacao(recebido, 2022)
    assert divulgado.dt.strftime("%H:%M").tolist() == ["17:00", "18:10"]
