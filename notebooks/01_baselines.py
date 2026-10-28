# %% [markdown]
# # 01 — Baselines no 2º turno
#
# Backtest de `Apurado`, `SwingUniforme` e `SwingUniformeUF` em 2022 (ordem
# observada, histórico de 2018) e 2018 (ordem simulada a partir de 2022,
# histórico de 2014).
#
#     python notebooks/01_baselines.py
#
# Grava `reports/01_baselines.md` e `reports/figures/01_erro_vs_apurado.png`.

# %%
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from projetor.backtest import rodar, tempo_ate_cravar
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.locais import carregar_secoes
from projetor.models.baseline import Apurado, SwingUniforme, SwingUniformeUF

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
(REPORTS / "figures").mkdir(parents=True, exist_ok=True)

MODELOS = [Apurado(), SwingUniforme(), SwingUniformeUF(min_secoes=30)]
ORDEM = {2022: "observada", 2018: "simulada a partir de 2022"}

# %%
resultados = []
fontes = {}
for ano in (2022, 2018):
    secoes = pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet")
    secoes = anexar_historico(secoes, carregar_secoes(ANTERIOR[ano]))
    fontes[ano] = secoes["ant_fonte"].value_counts(normalize=True).mul(100).round(1)
    for modelo in MODELOS:
        resultados.append(rodar(modelo, secoes).assign(ano=ano))
res = pd.concat(resultados, ignore_index=True)
res["abs_erro"] = res["erro"].abs()

# %%
tabelas = {}
for ano in (2022, 2018):
    r = res[res["ano"] == ano]
    tab = r.pivot(index="t", columns="modelo", values="abs_erro")[[m.nome for m in MODELOS]]
    tab.index = [f"{100 * t:g}%" for t in tab.index]
    cravar = {m: tempo_ate_cravar(g) for m, g in r.groupby("modelo")}
    tab.loc["média"] = tab.mean()
    tab.loc["tempo até cravar (|erro| < 0,5)"] = [cravar[m.nome] * 100 for m in MODELOS]
    tabelas[ano] = tab.round(2)
    print(ano, "\n", tabelas[ano].to_string(), "\n")

fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, ano in zip(axes, (2022, 2018), strict=True):
    for modelo in MODELOS:
        r = res[(res["ano"] == ano) & (res["modelo"] == modelo.nome)]
        ax.plot(100 * r["t"], r["abs_erro"], marker="o", markersize=3, label=modelo.nome)
    ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8)
    ax.set(title=f"{ano} (ordem {ORDEM[ano]})", xlabel="% de seções divulgadas", yscale="log")
axes[0].set_ylabel("|erro| do % PT final (p.p.)")
axes[0].legend(frameon=False)
fig.tight_layout()
fig.savefig(REPORTS / "figures" / "01_erro_vs_apurado.png", dpi=130)

# %%
linhas = [
    "# 01 — Baselines no 2º turno\n",
    "Erro absoluto, em pontos percentuais, do % PT final nos válidos projetado em cada ponto do relógio. "
    "\"Tempo até cravar\" é o primeiro % de seções a partir do qual o |erro| fica abaixo de 0,5 p.p. "
    "e não sai mais (na grade até 95%).\n",
    "- `Apurado`: a parcial.",
    "- `SwingUniforme`: swing nacional das seções divulgadas contra a eleição anterior, aplicado ao "
    "% PT anterior de cada pendente; peso das pendentes = aptos × (válidos/aptos da eleição anterior).",
    "- `SwingUniformeUF`: swing por UF (mínimo de 30 seções divulgadas; senão, o nacional).\n",
    "![|erro| x % apurado](figures/01_erro_vs_apurado.png)\n",
]
for ano in (2022, 2018):
    linhas += [
        f"\n## {ano} — ordem {ORDEM[ano]}, histórico de {ANTERIOR[ano]}\n",
        f"Nível do histórico usado (% das seções): {fontes[ano].to_dict()}\n",
        tabelas[ano].to_markdown() + "\n",
    ]
linhas.append(
    "\nEm 2018 a ordem de chegada é simulada (herdada de 2022, ver `projetor.ordem`); o erro mede o "
    "modelo sob a ordem de 2022, não sob a da noite de 2018.\n"
)
(REPORTS / "01_baselines.md").write_text("\n".join(linhas), encoding="utf-8")
print("gravado", REPORTS / "01_baselines.md")
