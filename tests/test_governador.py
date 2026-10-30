from pathlib import Path

import pytest

from projetor.governador import _finalistas

CABECALHO = '"SG_UF";"CD_MUNICIPIO";"NM_MUNICIPIO";"NR_ZONA";"NR_SECAO";"NR_LOCAL_VOTACAO";"CD_CARGO_PERGUNTA";"DS_CARGO_PERGUNTA";"QT_APTOS";"QT_COMPARECIMENTO";"QT_ABSTENCOES";"DS_TIPO_URNA";"NR_VOTAVEL";"QT_VOTOS"'


def _csv(tmp_path: Path, votos: list[tuple[int, int]]) -> Path:
    linhas = [CABECALHO] + [
        f'"SP";"1";"X";"1";"{i}";"10";"3";"Governador";"100";"90";"10";"Apurada";"{nr}";"{v}"'
        for i, (nr, v) in enumerate(votos)
    ]
    csv = tmp_path / "bu.csv"
    csv.write_text("\n".join(linhas) + "\n", encoding="latin-1")
    return csv


def test_finalistas_ignora_branco_e_nulo_e_ordena_por_numero(tmp_path: Path):
    assert _finalistas(_csv(tmp_path, [(45, 50), (40, 30), (95, 5), (96, 7)])) == (40, 45)


def test_sem_segundo_turno_de_governador(tmp_path: Path):
    assert _finalistas(_csv(tmp_path, [])) is None


def test_mais_de_dois_candidatos_no_segundo_turno_falha(tmp_path: Path):
    with pytest.raises(RuntimeError, match="2 finalistas"):
        _finalistas(_csv(tmp_path, [(45, 50), (40, 30), (12, 1)]))
