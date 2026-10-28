# %% [markdown]
# # 04 — Faixas calibradas no 2º turno
#
# Lê o que `04a_amostras_hierarquico.py` e `04b_faixas_camadas.py` gravaram em
# `data/processed/` e avalia quatro métodos de faixa:
#
# - (a) analítico do `SwingCamadasInterceptoPorte`;
# - (b) bootstrap preditivo por local do mesmo modelo (B = 200);
# - (c) posterior do `SwingHierarquico` (com incerteza de comparecimento);
# - (d) conformal por faixa de relógio sobre o `SwingCamadasInterceptoPorte`,
#   calibrado no outro ano (2018 → 2022 é o teste principal; 2022 → 2018 é o
#   inverso);
# - (e) posterior de (c) recalibrada: o desvio posterior multiplicado pelo
#   quantil conformal de |erro|/desvio do outro ano.
#
#     python notebooks/04_intervalos.py

# %%
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from projetor.backtest import tempo_ate_cravar
from projetor.intervals import (
    ROTULOS_FAIXA,
    conformal_normalizado,
    conformal_por_faixa,
    faixa_amostras,
    faixa_de,
    faixa_normal,
    winkler,
)

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
PROCESSED = RAIZ / "data" / "processed"
(REPORTS / "figures").mkdir(parents=True, exist_ok=True)
NIVEIS = [0.5, 0.8, 0.9, 0.95]
ANOS = (2022, 2018)
OUTRO = {2022: 2018, 2018: 2022}

# %% Passo 0: normal x Student-t no hierárquico
hier = {(v, ano): dict(np.load(PROCESSED / f"amostras_hier_{v}_comp_{ano}_2t.npz")) for v in ("normal", "t") for ano in ANOS}
linhas_t = []
for (v, ano), d in hier.items():
    erro = d["projecao"] - d["final"]
    nu = [json.loads(r).get("nu") for r in d["resumo"]]
    linhas_t.append(
        {
            "verossimilhança": v,
            "ano": ano,
            "erro médio": np.abs(erro).mean(),
            "erro até 2,5%": np.abs(erro[d["t"] <= 0.025]).mean(),
            "erro 5–95%": np.abs(erro[d["t"] >= 0.05]).mean(),
            "tempo até cravar": 100 * tempo_ate_cravar(pd.DataFrame({"t": d["t"], "erro": erro})),
            "ν médio": np.nanmean([x for x in nu if x is not None]) if v == "t" else np.nan,
        }
    )
tab_t = pd.DataFrame(linhas_t).set_index(["verossimilhança", "ano"]).round(3)
print(tab_t.to_string())
media = tab_t["erro médio"].unstack("ano")
# Fica com a t se melhorar 2018 sem piorar 2022 em mais de 0,05 p.p.
usar_t = media.loc["t", 2018] < media.loc["normal", 2018] and media.loc["t", 2022] <= media.loc["normal", 2022] + 0.05
VEROSSIMILHANCA = "t" if usar_t else "normal"
print("verossimilhança escolhida:", VEROSSIMILHANCA)

# %% Faixas de cada método
camadas = {ano: dict(np.load(PROCESSED / f"faixas_camadas_{ano}_2t.npz")) for ano in ANOS}
fina = {ano: pd.read_parquet(PROCESSED / f"erros_camadas_fina_{ano}_2t.parquet") for ano in ANOS}
conformal_q = {ano: conformal_por_faixa(fina[OUTRO[ano]], NIVEIS) for ano in ANOS}

METODOS = ["(a) analítico", "(b) bootstrap", "(c) posterior", "(d) conformal", "(e) posterior recalibrada"]


def _posterior(ano: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = hier[(VEROSSIMILHANCA, ano)]
    return d["amostras"].mean(axis=1), d["amostras"].std(axis=1), d["final"]


multiplicador = {}
for ano in ANOS:
    centro, desvio, final = _posterior(OUTRO[ano])
    multiplicador[ano] = conformal_normalizado(centro - final, desvio, NIVEIS)


def faixas(ano: int, metodo: str, nivel: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Centro, limite inferior e superior em cada ponto da grade."""
    c = camadas[ano]
    if metodo == "(a) analítico":
        return c["centro"], *faixa_normal(c["centro"], c["sd"], nivel)
    if metodo == "(b) bootstrap":
        return np.median(c["bootstrap"], axis=1), *faixa_amostras(c["bootstrap"], nivel)
    if metodo == "(c) posterior":
        a = hier[(VEROSSIMILHANCA, ano)]["amostras"]
        return a.mean(axis=1), *faixa_amostras(a, nivel)
    if metodo == "(d) conformal":
        q = conformal_q[ano][nivel].reindex(faixa_de(c["t"])).to_numpy()
        return c["projecao"], c["projecao"] - q, c["projecao"] + q
    centro, desvio, _ = _posterior(ano)
    m = multiplicador[ano][nivel]
    return centro, centro - m * desvio, centro + m * desvio


registros = []
for ano in ANOS:
    t, y = camadas[ano]["t"], camadas[ano]["final"]
    assert np.allclose(t, hier[(VEROSSIMILHANCA, ano)]["t"])
    for metodo in METODOS:
        for nivel in NIVEIS:
            centro, lo, hi = faixas(ano, metodo, nivel)
            registros.append(
                pd.DataFrame(
                    {
                        "ano": ano, "metodo": metodo, "nivel": nivel, "t": t, "faixa": faixa_de(t),
                        "centro": centro, "lo": lo, "hi": hi, "final": y,
                        "cobre": (lo <= y) & (y <= hi), "largura": hi - lo, "winkler": winkler(lo, hi, y, nivel),
                    }
                )  # fmt: skip
            )
f = pd.concat(registros, ignore_index=True)

# %% Métricas
def resumo(g: pd.DataFrame) -> pd.Series:
    return pd.Series({"cobertura": g["cobre"].mean(), "largura": g["largura"].mean(), "winkler": g["winkler"].mean()})


metricas = f[f["nivel"].isin([0.9, 0.95])].groupby(["ano", "metodo", "nivel"]).apply(resumo, include_groups=False)
tabela = metricas.unstack("nivel")
tabela.columns = [f"{m} {int(100 * n)}%" for m, n in tabela.columns]
tabela = tabela[[f"{m} {n}%" for n in (90, 95) for m in ("cobertura", "largura", "winkler")]]


def marcar(valor: float, nominal: float) -> str:
    texto = f"{100 * valor:.0f}%"
    return texto + " ⚠️" if valor < nominal - 0.15 else texto


tabela_md = tabela.copy().astype(object)
for n in (90, 95):
    tabela_md[f"cobertura {n}%"] = tabela[f"cobertura {n}%"].map(lambda v, n=n: marcar(v, n / 100))
    for m in ("largura", "winkler"):
        tabela_md[f"{m} {n}%"] = tabela[f"{m} {n}%"].round(2)
print(tabela_md.to_string())

por_faixa = (
    f[f["nivel"] == 0.9]
    .groupby(["ano", "metodo", "faixa"], observed=True)["cobre"]
    .agg(lambda s: f"{s.sum()}/{len(s)}")
    .unstack("faixa")[ROTULOS_FAIXA]
)
print(por_faixa.to_string())

calibracao = f.groupby(["ano", "metodo", "nivel"])["cobre"].mean().unstack("nivel")

# %% Figuras
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, ano in zip(axes, ANOS, strict=True):
    ax.plot([0.4, 1], [0.4, 1], color="gray", linestyle=":", linewidth=0.8)
    for metodo in METODOS:
        ax.plot(NIVEIS, calibracao.loc[(ano, metodo)], marker="o", label=metodo)
    ax.set(title=str(ano), xlabel="cobertura nominal", xlim=(0.45, 1), ylim=(0, 1.02))
axes[0].set_ylabel("cobertura empírica (22 pontos da grade)")
axes[0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(REPORTS / "figures" / "04_cobertura.png", dpi=130)

fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharex=True, sharey=True)
axes.flat[-1].axis("off")
y_final = camadas[2022]["final"][0]
for ax, metodo in zip(axes.flat, METODOS, strict=False):
    g90 = f[(f["ano"] == 2022) & (f["metodo"] == metodo) & (f["nivel"] == 0.9)]
    g95 = f[(f["ano"] == 2022) & (f["metodo"] == metodo) & (f["nivel"] == 0.95)]
    x = 100 * g90["t"]
    ax.fill_between(x, g95["lo"], g95["hi"], alpha=0.18, color="C0", label="faixa 95%")
    ax.fill_between(x, g90["lo"], g90["hi"], alpha=0.35, color="C0", label="faixa 90%")
    ax.plot(x, g90["centro"], color="C0", marker="o", markersize=3, label="projeção")
    ax.axhline(y_final, color="black", linewidth=1, label=f"final ({y_final:.2f}%)")
    ax.axhline(50, color="gray", linestyle=":", linewidth=0.8)
    ax.set(title=metodo, xscale="log", ylim=(48.5, 53))
for ax in axes[1, :2]:
    ax.set_xlabel("% de seções divulgadas (escala log)")
for ax in axes[:, 0]:
    ax.set_ylabel("% Lula nos válidos")
axes[0, 0].legend(frameon=False, fontsize=8, loc="lower right")
fig.suptitle("2022, 2º turno: projeção e faixas ao longo da apuração")
fig.tight_layout()
fig.savefig(REPORTS / "figures" / "04_faixa_2022.png", dpi=130)

# %% Relatório
ANALISE = Path(__file__).with_name("04_intervalos_analise.md").read_text(encoding="utf-8")
linhas = [
    "# 04 — Faixas calibradas no 2º turno\n",
    "Faixas de 90% e 95% para o % PT final em cada um dos 22 pontos da grade, nos dois backtests. "
    "Cobertura = fração dos pontos em que o resultado final ficou dentro da faixa. ⚠️ marca cobertura "
    "mais de 15 p.p. abaixo da prometida, o que tratamos como bug. Winkler (interval score) = largura + "
    "(2/α) × distância até a faixa quando o final fica fora; menor é melhor. Os 22 pontos de uma noite "
    "são fortemente correlacionados, então cada cobertura é uma estimativa ruidosa.\n",
    "- (a) analítico: erro de previsão do `SwingCamadasInterceptoPorte` propagado em forma fechada "
    "(coeficientes, deslocamentos por nível, ruído local e comparecimento).",
    "- (b) bootstrap: 200 réplicas reamostrando locais divulgados, com resíduo de swing e de comparecimento "
    "sorteado para cada local pendente.",
    f"- (c) posterior: amostras do `SwingHierarquico` (verossimilhança {VEROSSIMILHANCA}) com incerteza de "
    "comparecimento.",
    "- (d) conformal: quantil de |erro| do `SwingCamadasInterceptoPorte` por faixa de relógio, numa grade fina "
    "(190 pontos) do outro ano. Em 2022 a calibração vem de 2018 (teste principal, sem olhar 2022); em 2018, "
    "vem de 2022.",
    "- (e) posterior recalibrada: centro e desvio de (c), com o desvio multiplicado pelo quantil conformal de "
    "|erro|/desvio nos 22 pontos do outro ano.\n",
    "\n## Passo 0 — normal × Student-t no hierárquico\n",
    "Erro absoluto do % PT final (p.p.), ambos com incerteza de comparecimento.\n",
    tab_t.to_markdown() + "\n",
    f"Escolha: **{VEROSSIMILHANCA}** (regra: a t fica se melhorar 2018 sem piorar 2022 em mais de 0,05 p.p.).\n",
    "\n## Cobertura, largura e Winkler\n",
    tabela_md.to_markdown() + "\n",
    "\n## Cobertura de 90% por faixa de relógio\n",
    por_faixa.to_markdown() + "\n",
    "\n## Quantis conformais usados (|erro| em p.p.)\n",
    "Calibrados em 2018, aplicados em 2022:\n",
    conformal_q[2022].round(3).to_markdown() + "\n",
    "Calibrados em 2022, aplicados em 2018:\n",
    conformal_q[2018].round(3).to_markdown() + "\n",
    "\nMultiplicadores do desvio posterior em (e), calibrados no outro ano:\n",
    pd.DataFrame(multiplicador).T.rename_axis("aplicado em").round(2).to_markdown() + "\n",
    "\n![Calibração](figures/04_cobertura.png)\n",
    "\n![Faixas em 2022](figures/04_faixa_2022.png)\n",
    "\n## Leitura\n",
    ANALISE,
]
(REPORTS / "04_intervalos.md").write_text("\n".join(linhas), encoding="utf-8")
print("gravado", REPORTS / "04_intervalos.md")
