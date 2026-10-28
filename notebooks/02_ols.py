# %% [markdown]
# # 02 — Regressões de swing no 2º turno
#
# Mesmo backtest e métricas da fase 1. O `k` de `SwingCamadas` (e da variante
# com UF × capital) é escolhido só em 2018 e depois aplicado em 2022, que fica
# como teste.
#
#     python notebooks/02_ols.py

# %%
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from projetor.backtest import dividir, rodar, tempo_ate_cravar
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.locais import carregar_secoes
from projetor.models.baseline import Apurado, SwingUniforme, SwingUniformeUF
from projetor.models.camadas import (
    SwingCamadas,
    SwingCamadasIntercepto,
    SwingCamadasInterceptoPorte,
    SwingCamadasPorte,
)
from projetor.models.ols import SwingOLS

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
(REPORTS / "figures").mkdir(parents=True, exist_ok=True)
ORDEM = {2022: "observada", 2018: "simulada a partir de 2022"}
GRADE_K = [30, 100, 300, 1000, 3000, 10000, 30000, 100000]
GRADE_MIN_LOCAIS = [200, 1000]
CAMADAS = {
    "SwingCamadas": SwingCamadas,
    "SwingCamadasPorte": SwingCamadasPorte,
    "SwingCamadasIntercepto": SwingCamadasIntercepto,
    "SwingCamadasInterceptoPorte": SwingCamadasInterceptoPorte,
}

secoes = {
    ano: anexar_historico(pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet"), carregar_secoes(ANTERIOR[ano]))
    for ano in (2018, 2022)
}


def media_abs(modelo, ano: int) -> float:
    return rodar(modelo, secoes[ano])["erro"].abs().mean()


# %% Escolha de k e do mínimo de locais em 2018 (treino)
indice = pd.MultiIndex.from_product([GRADE_MIN_LOCAIS, GRADE_K], names=["min_locais", "k"])
busca = pd.DataFrame(
    {nome: [media_abs(fabrica(k=k, min_locais=m), 2018) for m, k in indice] for nome, fabrica in CAMADAS.items()},
    index=indice,
).round(3)
escolha = {nome: busca[nome].idxmin() for nome in CAMADAS}
print(busca.to_string(), "\n", escolha)

# %% Avaliação
modelos = [
    Apurado(),
    SwingUniforme(),
    SwingUniformeUF(min_secoes=30),
    SwingOLS(),
    *[fabrica(k=escolha[nome][1], min_locais=escolha[nome][0]) for nome, fabrica in CAMADAS.items()],
]
nomes = [m.nome for m in modelos]
res = pd.concat([rodar(m, secoes[ano]).assign(ano=ano) for ano in (2022, 2018) for m in modelos], ignore_index=True)
res["abs_erro"] = res["erro"].abs()

tabelas = {}
for ano in (2022, 2018):
    r = res[res["ano"] == ano]
    tab = r.pivot(index="t", columns="modelo", values="abs_erro")[nomes]
    tab.index = [f"{100 * t:g}%" for t in tab.index]
    tab.loc["média"] = tab.mean()
    cravar = {m: tempo_ate_cravar(g) for m, g in r.groupby("modelo")}
    tab.loc["tempo até cravar (|erro| < 0,5)"] = [100 * cravar[n] for n in nomes]
    tabelas[ano] = tab.round(2)
    print(ano, "\n", tabelas[ano].to_string(), "\n")

sinal = res[res["t"].isin([0.01, 0.05, 0.10, 0.25, 0.50])].pivot_table(
    index=["ano", "t"], columns="modelo", values="erro"
)[nomes].round(2)

# %% Coeficientes do nacional em 2022
coefs = pd.DataFrame(
    {f"{100 * t:g}%": SwingOLS().coeficientes(*dividir(secoes[2022], t)) for t in (0.10, 0.50)}
).round(3)
print(coefs.to_string())

# %% Figura
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
for ax, ano in zip(axes, (2022, 2018), strict=True):
    for i, nome in enumerate(nomes):
        r = res[(res["ano"] == ano) & (res["modelo"] == nome)]
        estilo = ":" if i < 3 else "-"
        ax.plot(100 * r["t"], r["abs_erro"], estilo, marker="o", markersize=3, label=nome)
    ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8)
    ax.set(title=f"{ano} (ordem {ORDEM[ano]})", xlabel="% de seções divulgadas", yscale="log")
axes[0].set_ylabel("|erro| do % PT final (p.p.)")
axes[0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(REPORTS / "figures" / "02_erro_vs_apurado.png", dpi=130)

# %% Relatório
ANALISE = Path(__file__).with_name("02_ols_analise.md").read_text(encoding="utf-8")
linhas = [
    "# 02 — Regressões de swing no 2º turno\n",
    "Mesmo backtest e métricas da fase 1: |erro| em p.p. do % PT final nos válidos; tempo até cravar = "
    "primeiro % de seções a partir do qual o |erro| fica abaixo de 0,5 p.p. até 95%.\n",
    "- `SwingOLS`: WLS por local, `swing ~ 1 + ant_pct_pt + log(aptos do município) + capital`, ponderada pelos "
    "válidos esperados; swing uniforme até 200 locais divulgados.",
    "- `SwingCamadas`: a mesma WLS no nacional, na região e na UF, cada nível encolhido para o de cima com "
    "peso n/(n + k); grupos com menos de 20 locais têm peso 0.",
    "- `SwingCamadasPorte`: `SwingCamadas` com um quarto nível, UF × capital/interior.",
    "- `SwingCamadasIntercepto`: regressão só no nacional; região e UF estimam um deslocamento (efeito fixo) "
    "encolhido com o mesmo n/(n + k).",
    "- `SwingCamadasInterceptoPorte`: o anterior com o nível UF × capital/interior.\n",
    "![|erro| x % apurado](figures/02_erro_vs_apurado.png)\n",
    "\n## Escolha de k e do mínimo de locais (só em 2018)\n",
    "Erro absoluto médio em 2018. A combinação de menor erro foi fixada e só então o modelo rodou em 2022.\n",
    busca.to_markdown() + "\n",
    "Escolhas (min_locais, k): " + "; ".join(f"`{n}` = {escolha[n]}" for n in CAMADAS) + ".\n",
]
for ano in (2022, 2018):
    linhas += [f"\n## {ano} — ordem {ORDEM[ano]}, histórico de {ANTERIOR[ano]}\n", tabelas[ano].to_markdown() + "\n"]
linhas += [
    "\n## Erro com sinal (projeção − final, p.p.)\n",
    sinal.to_markdown() + "\n",
    "\n## Coeficientes do nacional em 2022 (`SwingOLS`)\n",
    "Swing em p.p.; `log_aptos_mun` por unidade de log do eleitorado do município.\n",
    coefs.to_markdown() + "\n",
    "\n## O que funcionou e o que não funcionou\n",
    ANALISE,
]
(REPORTS / "02_ols.md").write_text("\n".join(linhas), encoding="utf-8")
print("gravado", REPORTS / "02_ols.md")
