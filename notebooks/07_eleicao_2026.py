# %% [markdown]
# # 07 — Eleição de 2026, fora da amostra
#
# Lê o que `07a_eleicao_2026.py` gravou e escreve `reports/07_eleicao_2026.md`.
# Tudo o que tem parâmetro foi fixado antes de olhar 2026: os modelos e seus
# hiperparâmetros (fases 2–4), o `c` do erro comum e o multiplicador da faixa
# (e), calibrados nas quatro noites do PT de 2018 e 2022 (fase 6).
#
#     python notebooks/07_eleicao_2026.py

# %%
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from projetor import discrepancia, noites, tempo
from projetor.backtest import tempo_ate_cravar
from projetor.intervals import faixa_amostras, winkler
from projetor.locais import carregar_secoes
from projetor.votos import validos

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
PROCESSED = RAIZ / "data" / "processed"
NIVEIS = [0.9, 0.95]
PONTO_RODRIGO = {1: 0.022, 2: 0.0242}

# %% Dados: totais e horário de recebimento
linhas = []
for turno in (1, 2):
    s = carregar_secoes(2026, turno)
    linhas.append(
        {"turno": f"{turno}º", "seções": len(s), "UFs": s["uf"].nunique(), "Lula": int(s["votos_pt"].sum()),
         "Flávio Bolsonaro": int(s["votos_adversario"].sum()), "válidos": int(validos(s).sum()),
         "% Lula": 100 * s["votos_pt"].sum() / validos(s).sum(),
         "% Flávio": 100 * s["votos_adversario"].sum() / validos(s).sum()}
    )  # fmt: skip
totais = pd.DataFrame(linhas).round(3)
print(totais.to_string(index=False))

s2 = carregar_secoes(2026, 2)
recebido = tempo.recebido_em_brasilia(s2)
primeiro_por_uf = recebido.groupby(s2["uf"]).min().dt.strftime("%H:%M")
sem_recebido = int(s2["dt_bu_recebido"].isna().sum())
print(primeiro_por_uf.to_string(), sem_recebido)

# %% Erros
erros = pd.concat([pd.read_parquet(PROCESSED / f"erros_2026_{t}t.parquet") for t in (1, 2)], ignore_index=True)
ORDEM_MODELOS = ["Apurado", "SwingUniformeUF", "SwingCamadasInterceptoPorte", "SwingHierarquico-t"]
grade = erros[~erros["t"].isin(PONTO_RODRIGO.values())]


def _metricas(g: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
            "erro médio": g["erro"].abs().mean(),
            "erro até 2,5%": g.loc[g["t"] <= 0.025, "erro"].abs().mean(),
            "erro 5–95%": g.loc[g["t"] >= 0.05, "erro"].abs().mean(),
            "tempo até cravar": 100 * tempo_ate_cravar(g),
        }
    )


tab_erros = (
    grade.groupby(["turno", "alvo", "modelo"]).apply(_metricas, include_groups=False)
    .reindex(ORDEM_MODELOS, level="modelo").round(3).reset_index()
)  # fmt: skip
tab_erros["turno"] = tab_erros["turno"].map({1: "1º", 2: "2º"})
print(tab_erros.to_string(index=False))

# %% Faixas congeladas
anteriores = [noites.carregar(a, tr) for a in (2018, 2022) for tr in (1, 2)]
C = noites.calibrar_c(anteriores, "fracao")
MULT = {n: noites.multiplicador_e(anteriores, n) for n in NIVEIS}
print("c congelado:", C, "multiplicadores (e):", MULT)

METODOS = ["(c) posterior", "(c) + δ fração", "(e) recalibrada"]
alvos_2026 = [noites.carregar(2026, 2, "pt"), noites.carregar(2026, 1, "pt"), noites.carregar(2026, 1, "adversario")]


def faixa(n: noites.Noite, metodo: str, nivel: float) -> tuple[np.ndarray, np.ndarray]:
    if metodo == "(c) posterior":
        return faixa_amostras(n.amostras, nivel)
    if metodo == "(c) + δ fração":
        return faixa_amostras(discrepancia.aplicar(n.amostras, n.perfis, C, "fracao", semente=1), nivel)
    centro, sd = n.amostras.mean(axis=1), n.amostras.std(axis=1)
    return centro - MULT[nivel] * sd, centro + MULT[nivel] * sd


registros = []
for n in alvos_2026:
    for metodo in METODOS:
        for nivel in NIVEIS:
            lo, hi = faixa(n, metodo, nivel)
            registros.append(
                pd.DataFrame(
                    {"noite": n.rotulo, "metodo": metodo, "nivel": nivel, "t": n.t, "centro": n.amostras.mean(axis=1),
                     "lo": lo, "hi": hi, "final": n.final, "cobre": (lo <= n.final) & (n.final <= hi),
                     "largura": hi - lo, "winkler": winkler(lo, hi, n.final, nivel)}
                )  # fmt: skip
            )
f = pd.concat(registros, ignore_index=True)
f_grade = f[~f["t"].isin(PONTO_RODRIGO.values())]


def _resumo(g: pd.DataFrame) -> pd.Series:
    return pd.Series({"cobertura": g["cobre"].mean(), "largura": g["largura"].mean(), "winkler": g["winkler"].mean()})


tab_faixas = f_grade.groupby(["noite", "metodo", "nivel"]).apply(_resumo, include_groups=False).unstack("nivel")
tab_faixas.columns = [f"{m} {int(100 * n)}%" for m, n in tab_faixas.columns]
tab_faixas = tab_faixas[[f"{m} {n}%" for n in (90, 95) for m in ("cobertura", "largura", "winkler")]]
for n in (90, 95):
    tab_faixas[f"cobertura {n}%"] = tab_faixas[f"cobertura {n}%"].map(lambda v: f"{100 * v:.0f}%")
tab_faixas = tab_faixas.round(2).reset_index()
print(tab_faixas.to_string(index=False))

# %% Comparação com o modelo de Rodrigo Mahlmeister
# Números públicos do modelo dele, como repassados no briefing do projeto.
RODRIGO = [
    {"turno": 1, "candidato": "Flávio Bolsonaro", "alvo": "adversario", "secoes": 2.2, "rodrigo": "47,01", "final_rodrigo": "47,03"},
    {"turno": 1, "candidato": "Lula", "alvo": "pt", "secoes": 2.2, "rodrigo": "45,50", "final_rodrigo": "45,16"},
    {"turno": 2, "candidato": "Lula", "alvo": "pt", "secoes": 2.42, "rodrigo": "51,6 (50,8–52,2)", "final_rodrigo": "—"},
]  # fmt: skip
comp = []
for r in RODRIGO:
    t = PONTO_RODRIGO[r["turno"]]
    e = erros[(erros["turno"] == r["turno"]) & (erros["alvo"] == r["alvo"]) & np.isclose(erros["t"], t)]
    hier = e[e["modelo"] == "SwingHierarquico-t"].iloc[0]
    ap = e[e["modelo"] == "Apurado"].iloc[0]
    rot = f"2026 {r['turno']}T {'PT' if r['alvo'] == 'pt' else 'adversário'}"
    fx = f[(f["noite"] == rot) & (f["metodo"] == "(c) + δ fração") & (f["nivel"] == 0.95) & np.isclose(f["t"], t)].iloc[0]
    comp.append(
        {"turno": f"{r['turno']}º", "candidato": r["candidato"], "% seções": r["secoes"],
         "apurado": round(ap["projecao"], 2), "Rodrigo": r["rodrigo"],
         "este projeto": f"{hier['projecao']:.2f} ({fx['lo']:.2f}–{fx['hi']:.2f})",
         "final": round(hier["final"], 2)}
    )  # fmt: skip
tab_comp = pd.DataFrame(comp)
print(tab_comp.to_string(index=False))

# %% Figura: 2026 2º turno
n = alvos_2026[0]
g90 = f[(f["noite"] == n.rotulo) & (f["metodo"] == "(c) + δ fração") & (f["nivel"] == 0.9)]
g95 = f[(f["noite"] == n.rotulo) & (f["metodo"] == "(c) + δ fração") & (f["nivel"] == 0.95)]
ap = erros[(erros["turno"] == 2) & (erros["modelo"] == "Apurado")].sort_values("t")
fig, ax = plt.subplots(figsize=(8, 4.2))
x = 100 * g90["t"]
ax.fill_between(x, g95["lo"], g95["hi"], alpha=0.18, color="C3", label="faixa 95%")
ax.fill_between(x, g90["lo"], g90["hi"], alpha=0.35, color="C3", label="faixa 90%")
ax.plot(x, g90["centro"], color="C3", marker="o", markersize=3, label="hierárquico-t")
ax.plot(100 * ap["t"], ap["projecao"], color="black", linestyle="--", label="apurado")
ax.axhline(n.final[0], color="black", linewidth=1, label=f"final ({n.final[0]:.2f}%)")
ax.axhline(50, color="gray", linestyle=":", linewidth=0.8)
ax.set(xscale="log", xlabel="% de seções divulgadas (escala log)", ylabel="% Lula nos válidos",
       title="2026, 2º turno: projeção congelada e faixa com erro comum")  # fmt: skip
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(REPORTS / "figures" / "07_2026_2t.png", dpi=130)

# %% Relatório
ANALISE = Path(__file__).with_name("07_eleicao_2026_analise.md").read_text(encoding="utf-8")
blocos = {
    "TOTAIS": totais.to_markdown(index=False, intfmt=","),
    "RECEBIDO": ", ".join(f"{uf} {h}" for uf, h in primeiro_por_uf.items()),
    "SEM_RECEBIDO": str(sem_recebido),
    "ERROS": tab_erros.to_markdown(index=False),
    "C": f"{C:.2f}".replace(".", ","),
    "MULT90": f"{MULT[0.9]:.2f}".replace(".", ","),
    "MULT95": f"{MULT[0.95]:.2f}".replace(".", ","),
    "FAIXAS": tab_faixas.to_markdown(index=False),
    "RODRIGO": tab_comp.to_markdown(index=False),
}
texto = ANALISE
for chave, valor in blocos.items():
    texto = texto.replace(f"{{{{{chave}}}}}", valor)
(REPORTS / "07_eleicao_2026.md").write_text(texto, encoding="utf-8")
print("gravado reports/07_eleicao_2026.md")
