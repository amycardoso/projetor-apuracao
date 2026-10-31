# %% [markdown]
# # 08 — Agregados pequenos para `notebooks/analise.ipynb`
#
# Lê os parquets e as amostras de `data/processed/` (fora do git) e grava em
# `notebooks/data/` só agregados nacionais, regionais ou por UF, nada por seção:
#
# - `erros.csv`: erro de cada modelo em cada ponto da grade, nas seis noites
#   presidenciais do PT. O hierárquico vem das amostras já rodadas; os outros
#   três modelos do 2º turno de 2018 e 2022 são rodados aqui (alguns minutos).
# - `cobertura.csv`: cobertura empírica de cada faixa em níveis nominais de 50%
#   a 99%, por noite. 2018 e 2022 deixam a data de fora da calibração; 2026 usa
#   a calibração congelada nas 30 noites de 2018 e 2022 (e inclui o adversário
#   no 1º turno, como em `07_eleicao_2026.py`).
# - `swing_regiao.csv` e `swing_uf.csv`: swing do % PT por local de votação,
#   2018 → 2022, resumido por região (histograma e quantis) e por UF.
# - `composicao_final.csv`: participação final de cada região nos válidos.
# - `ufs.geojson`: malha simplificada das UFs (IBGE, qualidade mínima).
#
#     python notebooks/08_exportar_notebook.py

# %%
import gzip
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from projetor import discrepancia, governador, noites
from projetor.backtest import rodar
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.intervals import faixa_amostras
from projetor.locais import CHAVE_LOCAL, carregar_secoes
from projetor.models.baseline import Apurado, SwingUniformeUF
from projetor.models.camadas import SwingCamadasInterceptoPorte
from projetor.models.features import REGIAO
from projetor.votos import validos

RAIZ = Path(__file__).resolve().parents[1]
PROCESSED = RAIZ / "data" / "processed"
SAIDA = RAIZ / "notebooks" / "data"
SAIDA.mkdir(parents=True, exist_ok=True)
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul", "Exterior"]

# %% Erros nas seis noites presidenciais (alvo: PT)
erros = [
    pd.read_parquet(PROCESSED / "erros_1t.parquet").query("alvo == 'pt'").assign(turno=1),
    pd.read_parquet(PROCESSED / "erros_2026_1t.parquet").query("alvo == 'pt'").assign(ano=2026),
    pd.read_parquet(PROCESSED / "erros_2026_2t.parquet").assign(ano=2026),
]
for ano in (2018, 2022):
    secoes = anexar_historico(pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet"), carregar_secoes(ANTERIOR[ano]))
    for modelo in (Apurado(), SwingUniformeUF(min_secoes=30), SwingCamadasInterceptoPorte(k=30, min_locais=1000)):
        erros.append(rodar(modelo, secoes).assign(ano=ano, turno=2))
    n = noites.carregar(ano, 2)
    projecao = n.amostras.mean(axis=1)
    erros.append(
        pd.DataFrame({"modelo": "SwingHierarquico-t", "t": n.t, "projecao": projecao, "final": n.final,
                      "erro": projecao - n.final, "ano": ano, "turno": 2})
    )  # fmt: skip
erros = pd.concat(erros, ignore_index=True)[["ano", "turno", "modelo", "t", "projecao", "final", "erro"]]
erros.round(4).to_csv(SAIDA / "erros.csv", index=False)
print(erros.groupby(["ano", "turno", "modelo"])["erro"].apply(lambda e: e.abs().mean()).unstack().round(3))

# %% Cobertura nominal × empírica
NIVEIS = np.round(np.arange(0.50, 0.951, 0.05).tolist() + [0.99], 2)
PRESIDENCIAIS = [noites.carregar(a, tr) for a in (2018, 2022) for tr in (1, 2)]
GOVERNADOR = [noites.governador(a, uf) for a in (2018, 2022) for uf in governador.ufs(a)]
TODAS = PRESIDENCIAIS + GOVERNADOR
NOVAS = [noites.carregar(2026, 2), noites.carregar(2026, 1), noites.carregar(2026, 1, "adversario")]


def faixa(alvo: noites.Noite, metodo: str, nivel: float, treino: list[noites.Noite]) -> tuple[np.ndarray, np.ndarray]:
    if metodo == "posterior":
        return faixa_amostras(alvo.amostras, nivel)
    if metodo == "recalibrada":
        m = noites.multiplicador_e(treino, nivel)
        centro, sd = alvo.amostras.mean(axis=1), alvo.amostras.std(axis=1)
        return centro - m * sd, centro + m * sd
    c = noites.calibrar_c(treino, "ruido")
    return faixa_amostras(discrepancia.aplicar(alvo.amostras, alvo.perfis, c, "ruido", semente=1), nivel)


linhas = []
for alvo in PRESIDENCIAIS + GOVERNADOR + NOVAS:
    if alvo.ano == 2026:
        grupo, treino = "2026 (congelada)", TODAS
    else:
        grupo = "governador" if alvo.alvo == "governador" else "presidencial 2018–2022"
        treino = [n for n in TODAS if (n.ano, n.turno) != (alvo.ano, alvo.turno)]
    # Os instantes extras de 2026 (comparação com Rodrigo) ficam fora da grade.
    na_grade = ~np.isin(np.round(alvo.t, 4), [0.022, 0.0242])
    for metodo in ("posterior", "recalibrada", "erro comum"):
        # Em 2026, o multiplicador congelado é o das quatro noites do PT (fase 6).
        tr = PRESIDENCIAIS if (alvo.ano, metodo) == (2026, "recalibrada") else treino
        for nivel in NIVEIS:
            lo, hi = faixa(alvo, metodo, float(nivel), tr)
            cobre = (lo <= alvo.final) & (alvo.final <= hi)
            linhas.append(
                {"grupo": grupo, "noite": alvo.rotulo, "metodo": metodo, "nivel": nivel,
                 "cobertura": cobre[na_grade].mean(), "largura": (hi - lo)[na_grade].mean()}
            )  # fmt: skip
cobertura = pd.DataFrame(linhas)
cobertura.round(4).to_csv(SAIDA / "cobertura.csv", index=False)
print(cobertura[cobertura["nivel"] == 0.9].groupby(["grupo", "metodo"])[["cobertura", "largura"]].mean().round(2))

# %% Swing local 2018 → 2022, como em 00_quem_chega_primeiro.py
d18 = pd.read_parquet(DATA_INTERIM / "ordem_2018_2t.parquet")
d22 = pd.read_parquet(DATA_INTERIM / "ordem_2022_2t.parquet")
for d in (d18, d22):
    d["validos"] = d["votos_pt"] + d["votos_adversario"]
pares = pd.read_parquet(DATA_INTERIM / "locais_2018_2022.parquet")
pares = pares[pares["tipo_par"].isin(["direto", "rezoneado"])]
p = pares.set_index(CHAVE_LOCAL).join(d18.groupby(CHAVE_LOCAL)[["votos_pt", "validos"]].sum().add_suffix("_18"))
p = p.reset_index()
p["nr_zona"] = p["nr_zona_2022"].astype(int)
p = p.drop(columns="uf").set_index(CHAVE_LOCAL).join(
    d22.groupby(CHAVE_LOCAL).agg(votos_pt=("votos_pt", "sum"), validos=("validos", "sum"), uf=("uf", "first")),
    how="inner",
)
p = p[(p["validos_18"] > 0) & (p["validos"] > 0)]
p["swing"] = 100 * p["votos_pt"] / p["validos"] - 100 * p["votos_pt_18"] / p["validos_18"]
p["regiao"] = p["uf"].map(REGIAO)


def quantis_ponderados(x: np.ndarray, w: np.ndarray, qs: list[float]) -> np.ndarray:
    ordem = np.argsort(x)
    acum = np.cumsum(w[ordem]) / w.sum()
    return np.interp(qs, acum, x[ordem])


BORDAS = np.arange(-30, 50.5, 1.0)
linhas = []
for regiao, g in p.groupby("regiao"):
    x, w = g["swing"].to_numpy(), g["validos"].to_numpy(float)
    contagem, _ = np.histogram(x.clip(BORDAS[0], BORDAS[-1] - 1e-9), bins=BORDAS, weights=w)
    q = quantis_ponderados(x, w, [0.05, 0.25, 0.5, 0.75, 0.95])
    linhas.append(
        {"regiao": regiao, "locais": len(g), "validos_2022": int(w.sum()), "media": np.average(x, weights=w),
         **{f"q{int(100 * k)}": v for k, v in zip([0.05, 0.25, 0.5, 0.75, 0.95], q, strict=True)},
         "hist": json.dumps((contagem / w.sum()).round(5).tolist())}
    )  # fmt: skip
swing_regiao = pd.DataFrame(linhas).set_index("regiao").reindex(REGIOES).dropna(how="all").reset_index()
swing_regiao.round(3).to_csv(SAIDA / "swing_regiao.csv", index=False)

swing_uf = p.groupby("uf").apply(
    lambda g: pd.Series({"locais": len(g), "swing_medio": np.average(g["swing"], weights=g["validos"])}),
    include_groups=False,
).reset_index()
swing_uf["regiao"] = swing_uf["uf"].map(REGIAO)
swing_uf.round(3).to_csv(SAIDA / "swing_uf.csv", index=False)
print(swing_regiao.drop(columns="hist").round(2).to_string(index=False))

# %% Composição final dos válidos por região (2º turno)
linhas = []
for ano in (2018, 2022, 2026):
    s = carregar_secoes(ano, 2)
    v = validos(s)
    for regiao, x in (v.groupby(s["uf"].map(REGIAO)).sum() / v.sum()).reindex(REGIOES).items():
        linhas.append({"ano": ano, "regiao": regiao, "pct_validos": 100 * x})
pd.DataFrame(linhas).round(3).to_csv(SAIDA / "composicao_final.csv", index=False)

# %% Malha das UFs (IBGE, API de malhas v3, qualidade mínima)
URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao=UF"
)
CODIGO_UF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
    "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}  # fmt: skip
with urllib.request.urlopen(URL, timeout=60) as r:
    bruto = r.read()
malha = json.loads(gzip.decompress(bruto) if bruto[:2] == b"\x1f\x8b" else bruto)


def arredondar(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 3), round(coords[1], 3)]
    return [arredondar(c) for c in coords]


for f in malha["features"]:
    f["properties"] = {"uf": CODIGO_UF[f["properties"]["codarea"]]}
    f["geometry"]["coordinates"] = arredondar(f["geometry"]["coordinates"])
(SAIDA / "ufs.geojson").write_text(json.dumps(malha, separators=(",", ":")), encoding="utf-8")

print({f.name: f"{f.stat().st_size / 1024:.0f} KB" for f in sorted(SAIDA.iterdir())})
