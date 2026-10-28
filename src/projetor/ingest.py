"""Ingestão dos boletins de urna (BU) do TSE.

Baixa os BUs por UF a partir do portal de dados abertos (CKAN), verifica o
sha512 publicado ao lado de cada zip, normaliza o cabeçalho e grava um parquet
por ano e turno em `data/interim/`, com uma linha por seção e só o cargo de
Presidente.

Uso:
    python -m projetor.ingest --anos 2018 2022 --turno 2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[2]
DATA_RAW = RAIZ / "data" / "raw"
DATA_INTERIM = RAIZ / "data" / "interim"

CKAN = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id={}"
DATASETS = {
    2018: "resultados-2018-boletim-de-urna",
    2022: "resultados-2022-boletim-de-urna",
}

# NR_VOTAVEL do candidato do PT e do adversário no 2º turno.
CANDIDATOS = {
    2018: {"pt": 13, "adversario": 17},  # Haddad x Bolsonaro (PSL)
    2022: {"pt": 13, "adversario": 22},  # Lula x Bolsonaro (PL)
}
NR_BRANCO = 95
NR_NULO = 96

# Grafias do cabeçalho que mudam entre anos.
CORRECOES_CABECALHO = {
    "CD_FLASCARD_URNA_EFETIVADA": "CD_FLASHCARD_URNA_EFETIVADA",
}


@dataclass(frozen=True)
class Recurso:
    ano: int
    turno: int
    uf: str
    url: str
    url_sha512: str | None

    @property
    def nome_zip(self) -> str:
        return self.url.rsplit("/", 1)[-1]


def listar_recursos(ano: int, turno: int) -> list[Recurso]:
    """Lista os zips de BU do dataset CKAN do ano para o turno pedido."""
    with urllib.request.urlopen(CKAN.format(DATASETS[ano]), timeout=60) as resp:
        pacote = json.load(resp)
    if not pacote.get("success"):
        raise RuntimeError(f"CKAN recusou o dataset {DATASETS[ano]}: {pacote.get('error')}")

    urls = {r["url"] for r in pacote["result"]["resources"]}
    padrao = re.compile(rf"_{turno}t_([A-Z]{{2}})_\d+\.zip$", re.IGNORECASE)
    recursos = []
    for url in sorted(urls):
        m = padrao.search(url)
        if not m:
            continue
        sha = url + ".sha512"
        recursos.append(Recurso(ano, turno, m.group(1).upper(), url, sha if sha in urls else None))
    if not recursos:
        raise RuntimeError(f"Nenhum BU do {turno}º turno encontrado em {DATASETS[ano]}")
    return recursos


def _sha512(caminho: Path) -> str:
    h = hashlib.sha512()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _sha512_publicado(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode().split()[0].lower()


def baixar(recurso: Recurso, destino: Path = DATA_RAW) -> Path:
    """Baixa o zip para `destino/{ano}_{turno}t/` e devolve o caminho.

    Se o arquivo já existe e confere com o sha512 publicado, não baixa de novo.
    Um arquivo que não confere é apagado e a função falha.
    """
    pasta = destino / f"{recurso.ano}_{recurso.turno}t"
    pasta.mkdir(parents=True, exist_ok=True)
    zip_path = pasta / recurso.nome_zip
    esperado = _sha512_publicado(recurso.url_sha512) if recurso.url_sha512 else None

    if zip_path.exists() and (esperado is None or _sha512(zip_path) == esperado):
        log.info("cache: %s", zip_path.name)
        return zip_path

    log.info("baixando %s", recurso.url)
    parcial = zip_path.with_suffix(".zip.part")
    urllib.request.urlretrieve(recurso.url, parcial)
    if esperado is not None and (obtido := _sha512(parcial)) != esperado:
        parcial.unlink()
        raise RuntimeError(f"sha512 não confere para {recurso.url}: {obtido[:16]}… != {esperado[:16]}…")
    if esperado is None:
        log.warning("sem sha512 publicado para %s", recurso.url)
    parcial.rename(zip_path)
    return zip_path


def extrair_csv(zip_path: Path) -> Path:
    """Extrai o CSV do zip para a mesma pasta (uma vez) e devolve o caminho."""
    with zipfile.ZipFile(zip_path) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(nomes) != 1:
            raise RuntimeError(f"{zip_path.name}: esperava 1 CSV, achei {nomes}")
        csv_path = zip_path.parent / Path(nomes[0]).name
        if not csv_path.exists():
            with z.open(nomes[0]) as origem, csv_path.open("wb") as alvo:
                while bloco := origem.read(1 << 20):
                    alvo.write(bloco)
    return csv_path


def normalizar_cabecalho(colunas: list[str]) -> list[str]:
    """Remove espaços (`SG_ UF` em 2018) e corrige grafias divergentes."""
    limpas = [re.sub(r"\s+", "", c.strip().strip('"')).upper() for c in colunas]
    return [CORRECOES_CABECALHO.get(c, c) for c in limpas]


def ler_cabecalho(csv_path: Path) -> list[str]:
    with csv_path.open(encoding="latin-1") as f:
        return f.readline().rstrip("\r\n").split(";")


def _sql_secoes(csv_path: Path, ano: int, turno: int) -> str:
    """SQL que agrega o BU (formato longo) em uma linha por seção, só Presidente."""
    nomes = normalizar_cabecalho(ler_cabecalho(csv_path))
    tem_recebido = "DT_BU_RECEBIDO" in nomes
    cand = CANDIDATOS[ano]
    ts = "try_strptime({}, '%d/%m/%Y %H:%M:%S')"
    recebido = f"max({ts.format('DT_BU_RECEBIDO')})" if tem_recebido else "CAST(NULL AS TIMESTAMP)"
    return f"""
    SELECT
        {ano} AS ano,
        {turno} AS turno,
        any_value(SG_UF) AS uf,
        CAST(CD_MUNICIPIO AS INTEGER) AS cd_municipio,
        any_value(NM_MUNICIPIO) AS nm_municipio,
        CAST(NR_ZONA AS INTEGER) AS nr_zona,
        CAST(NR_SECAO AS INTEGER) AS nr_secao,
        CAST(any_value(NR_LOCAL_VOTACAO) AS INTEGER) AS nr_local_votacao,
        CAST(any_value(QT_APTOS) AS INTEGER) AS qt_aptos,
        CAST(any_value(QT_COMPARECIMENTO) AS INTEGER) AS qt_comparecimento,
        CAST(any_value(QT_ABSTENCOES) AS INTEGER) AS qt_abstencoes,
        CAST(sum(QT_VOTOS) FILTER (NR_VOTAVEL = {cand['pt']}) AS INTEGER) AS votos_pt,
        CAST(sum(QT_VOTOS) FILTER (NR_VOTAVEL = {cand['adversario']}) AS INTEGER) AS votos_adversario,
        CAST(sum(QT_VOTOS) FILTER (NR_VOTAVEL = {NR_BRANCO}) AS INTEGER) AS votos_branco,
        CAST(sum(QT_VOTOS) FILTER (NR_VOTAVEL = {NR_NULO}) AS INTEGER) AS votos_nulo,
        CAST(sum(QT_VOTOS) FILTER (NR_VOTAVEL NOT IN ({cand['pt']}, {cand['adversario']}, {NR_BRANCO}, {NR_NULO}))
             AS INTEGER) AS votos_outros,
        any_value(DS_TIPO_URNA) AS ds_tipo_urna,
        min({ts.format('DT_ENCERRAMENTO')}) AS dt_encerramento,
        {recebido} AS dt_bu_recebido,
        count(DISTINCT NR_LOCAL_VOTACAO) AS _n_locais,
        count(DISTINCT QT_APTOS) AS _n_aptos
    FROM (
        SELECT * REPLACE (CAST(NR_VOTAVEL AS INTEGER) AS NR_VOTAVEL, CAST(QT_VOTOS AS BIGINT) AS QT_VOTOS)
        FROM read_csv('{csv_path}', delim=';', quote='"', header=true, encoding='latin-1',
                      all_varchar=true, names={nomes!r})
        WHERE CD_CARGO_PERGUNTA = '1'
    )
    GROUP BY CD_MUNICIPIO, NR_ZONA, NR_SECAO
    """


def processar(ano: int, turno: int, destino: Path = DATA_INTERIM) -> Path:
    """Baixa todos os BUs do ano e turno e grava `bu_{ano}_{turno}t.parquet`."""
    con = duckdb.connect()
    partes = []
    for recurso in listar_recursos(ano, turno):
        csv_path = extrair_csv(baixar(recurso))
        partes.append(f"({_sql_secoes(csv_path, ano, turno)})")
    con.execute("CREATE TABLE secoes AS " + "\nUNION ALL BY NAME\n".join(partes))

    # Uma seção não pode aparecer em duas UFs nem ter metadados divergentes.
    dup = con.execute(
        "SELECT count(*) - count(DISTINCT (cd_municipio, nr_zona, nr_secao)) FROM secoes"
    ).fetchone()[0]
    inconsistentes = con.execute("SELECT count(*) FROM secoes WHERE _n_locais > 1 OR _n_aptos > 1").fetchone()[0]
    if dup or inconsistentes:
        raise RuntimeError(f"{ano} {turno}t: {dup} seções duplicadas, {inconsistentes} com metadados divergentes")
    if turno == 2:
        outros = con.execute("SELECT coalesce(sum(votos_outros), 0) FROM secoes").fetchone()[0]
        if outros:
            raise RuntimeError(f"{ano} 2t: {outros} votos para NR_VOTAVEL inesperado")

    destino.mkdir(parents=True, exist_ok=True)
    saida = destino / f"bu_{ano}_{turno}t.parquet"
    con.execute(
        f"""COPY (
            SELECT * EXCLUDE (_n_locais, _n_aptos)
            REPLACE (coalesce(votos_pt, 0) AS votos_pt, coalesce(votos_adversario, 0) AS votos_adversario,
                     coalesce(votos_branco, 0) AS votos_branco, coalesce(votos_nulo, 0) AS votos_nulo,
                     coalesce(votos_outros, 0) AS votos_outros)
            FROM secoes ORDER BY uf, cd_municipio, nr_zona, nr_secao
        ) TO '{saida}' (FORMAT parquet)"""
    )
    log.info("gravado %s", saida)
    return saida


def processar_primeiro_turno(ano: int) -> Path:
    """1º turno: mesmo pipeline. Baixa ~1,3 GiB por ano; votos de terceiros vão para `votos_outros`."""
    return processar(ano, turno=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--anos", type=int, nargs="+", default=sorted(DATASETS))
    parser.add_argument("--turno", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for ano in args.anos:
        processar(ano, args.turno)


if __name__ == "__main__":
    main()
