import pandas as pd

from projetor.locais import locais, parear
from projetor.ordem import ordem_2018, relogio_2022


def _secoes(ano, linhas):
    df = pd.DataFrame(linhas, columns=["cd_municipio", "nr_zona", "nr_local_votacao", "nr_secao", "recebido"])
    df["uf"] = "SE"
    df["qt_aptos"] = 100
    df["votos_pt"] = df["votos_adversario"] = 1
    df["dt_bu_recebido"] = pd.to_datetime(df.pop("recebido"))
    return df


def test_2018_herda_a_ordem_do_local_de_2022():
    s22 = _secoes(
        2022,
        [(1, 1, 10, 1, "2022-10-30 17:10"), (1, 1, 10, 2, "2022-10-30 17:11"), (1, 1, 20, 3, "2022-10-30 19:00")],
    )
    # Local 20 chegou por último em 2022; em 2018 deve continuar por último.
    s18 = _secoes(2018, [(1, 1, 20, 7, None), (1, 1, 10, 8, None), (1, 1, 10, 9, None)])

    r18 = ordem_2018(s18, s22, parear(locais(s18), locais(s22)))

    assert r18.sort_values("relogio")["nr_local_votacao"].tolist() == [10, 10, 20]
    assert r18["fonte_ordem"].eq("local").all()
    assert sorted(r18["relogio"]) == [1 / 3, 2 / 3, 1.0]


def test_relogio_2022_respeita_o_inicio_da_divulgacao():
    s22 = _secoes(2022, [(1, 1, 10, 1, "2022-10-30 03:00"), (1, 1, 10, 2, "2022-10-30 17:30")])
    r22 = relogio_2022(s22)
    assert r22["momento"].min() == pd.Timestamp("2022-10-30 17:00", tz="America/Sao_Paulo")
    assert r22.sort_values("relogio")["nr_secao"].tolist() == [1, 2]
