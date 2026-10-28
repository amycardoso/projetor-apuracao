import pandas as pd

from projetor.locais import parear


def _locais(linhas):
    return pd.DataFrame(linhas, columns=["cd_municipio", "nr_zona", "nr_local_votacao"]).assign(
        uf="SE", n_secoes=1, qt_aptos=100
    )


def test_parear_classifica_cada_caso_na_ordem_de_prioridade():
    l2022 = _locais([(1, 1, 10), (1, 2, 20), (2, 5, 99)])
    l2018 = _locais(
        [
            (1, 1, 10),  # direto
            (1, 3, 20),  # mesmo local em outra zona -> rezoneado
            (1, 1, 77),  # zona existe, local não
            (2, 9, 55),  # só o município existe
            (3, 1, 10),  # município sumiu
        ]
    )

    pares = parear(l2018, l2022)

    assert pares["tipo_par"].tolist() == ["direto", "rezoneado", "zona", "municipio", "sem_par"]
    assert pares["nr_zona_2022"].tolist()[:3] == [1, 2, 1]
    assert pares["nr_local_2022"].tolist()[:2] == [10, 20]
    assert pares["nr_local_2022"].isna().tolist()[2:] == [True, True, True]
