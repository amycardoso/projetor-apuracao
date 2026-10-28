from pathlib import Path

import duckdb
import pandas as pd

from projetor.ingest import _sql_secoes, normalizar_cabecalho

CABECALHO_2018 = '"SG_ UF";"CD_MUNICIPIO";"NM_MUNICIPIO";"NR_ZONA";"NR_SECAO";"NR_LOCAL_VOTACAO";"CD_CARGO_PERGUNTA";"QT_APTOS";"QT_COMPARECIMENTO";"QT_ABSTENCOES";"DS_TIPO_URNA";"NR_VOTAVEL";"QT_VOTOS";"CD_FLASCARD_URNA_EFETIVADA";"DT_ENCERRAMENTO"'


def test_normalizar_cabecalho_corrige_grafias_de_2018():
    nomes = normalizar_cabecalho(CABECALHO_2018.split(";"))
    assert nomes[0] == "SG_UF"
    assert "CD_FLASHCARD_URNA_EFETIVADA" in nomes


def test_sql_secoes_agrega_votos_em_formato_largo(tmp_path: Path):
    linhas = [
        CABECALHO_2018,
        *(
            f'"SE";"31054";"ARACAJU";"1";"3";"1023";"{cargo}";"399";"322";"77";"Apurada";"{nr}";"{votos}";"X";"28/10/2018 17:01:52"'
            for cargo, nr, votos in [("1", 13, 169), ("1", 17, 128), ("1", 95, 9), ("1", 96, 16), ("3", 45, 200)]
        ),
    ]
    csv = tmp_path / "bu.csv"
    csv.write_text("\n".join(linhas) + "\n", encoding="latin-1")

    linha = duckdb.sql(_sql_secoes(csv, 2018, 2)).df().iloc[0]

    assert (linha.votos_pt, linha.votos_adversario, linha.votos_branco, linha.votos_nulo) == (169, 128, 9, 16)
    assert pd.isna(linha.votos_outros)  # governador fica de fora
    assert linha.uf == "SE" and linha.nr_local_votacao == 1023
    assert str(linha.dt_encerramento) == "2018-10-28 17:01:52"


def test_sql_secoes_le_layout_sem_cabecalho_de_2014(tmp_path: Path):
    linha = '"28/10/2014";"11:44:50";"158";"144";"AC";"1";"PRESIDENTE";"1";"3";"1279";"13";"PT";"01392";"RIO BRANCO";"26/10/2014";"230";"22";"208";"1";"1";"APURADA";"{nr}";"X";"{votos}";"1";"1023842";"a";"b";"26/09/2014";"F";"1 - 3"'
    csv = tmp_path / "bu.txt"
    csv.write_text("\n".join(linha.format(nr=nr, votos=v) for nr, v in [(13, 65), (45, 133)]) + "\n", encoding="latin-1")

    linha = duckdb.sql(_sql_secoes(csv, 2014, 2)).df().iloc[0]

    assert (linha.votos_pt, linha.votos_adversario, linha.cd_municipio, linha.qt_aptos) == (65, 133, 1392, 230)
    assert pd.isna(linha.dt_encerramento) and pd.isna(linha.dt_bu_recebido)
