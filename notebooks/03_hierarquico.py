# %% [markdown]
# # 03 — Modelo hierárquico bayesiano no 2º turno
#
# Compara `SwingHierarquico` (PyMC, ADVI) com `SwingCamadasInterceptoPorte`, o
# melhor modelo da fase 2, no mesmo backtest. NUTS (nutpie) roda em 2,5%, 10%
# e 50% de 2022 para checar o ADVI. As amostras posteriores do % PT final vão
# para `data/processed/` (não versionado), para a fase 4.
#
#     python notebooks/03_hierarquico.py

# %%
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from projetor.backtest import dividir, pct_pt, rodar, tempo_ate_cravar
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.locais import carregar_secoes
from projetor.models.baseline import SwingUniforme, SwingUniformeUF
from projetor.models.camadas import SwingCamadasInterceptoPorte
from projetor.models.hierarquico import SwingHierarquico

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
PROCESSED = RAIZ / "data" / "processed"
for pasta in (REPORTS / "figures", PROCESSED):
    pasta.mkdir(parents=True, exist_ok=True)
ORDEM = {2022: "observada", 2018: "simulada a partir de 2022"}

secoes = {
    ano: anexar_historico(pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet"), carregar_secoes(ANTERIOR[ano]))
    for ano in (2022, 2018)
}


def cronometrar(modelo, ano):
    inicio = time.perf_counter()
    r = rodar(modelo, secoes[ano]).assign(ano=ano)
    return r, (time.perf_counter() - inicio) / len(r)


# %% Backtest
modelos = [SwingUniforme(), SwingUniformeUF(min_secoes=30), SwingCamadasInterceptoPorte(k=30, min_locais=1000)]
partes, tempos = [], {}
for ano in (2022, 2018):
    for modelo in [*modelos, SwingHierarquico()]:
        r, seg = cronometrar(modelo, ano)
        partes.append(r)
        tempos[(ano, modelo.nome)] = seg
        print(ano, modelo.nome, f"{seg:.1f}s/ponto", r["erro"].abs().mean().round(3), flush=True)
res = pd.concat(partes, ignore_index=True)
res["abs_erro"] = res["erro"].abs()
nomes = [*[m.nome for m in modelos], "SwingHierarquico"]

hier = res[res["modelo"] == "SwingHierarquico"].copy()
for ano, g in hier.groupby("ano"):
    np.savez_compressed(
        PROCESSED / f"amostras_hierarquico_{ano}_2t.npz",
        t=g["t"].to_numpy(),
        final=g["final"].to_numpy(),
        amostras=np.stack(g["amostras"].to_list()),
    )

# %% Tabelas
tabelas = {}
for ano in (2022, 2018):
    r = res[res["ano"] == ano]
    tab = r.pivot(index="t", columns="modelo", values="abs_erro")[nomes]
    tab.index = [f"{100 * t:g}%" for t in tab.index]
    tab.loc["média"] = tab.mean()
    cravar = {m: tempo_ate_cravar(g) for m, g in r.groupby("modelo")}
    tab.loc["tempo até cravar (|erro| < 0,5)"] = [100 * cravar[n] for n in nomes]
    tab.loc["segundos por ponto"] = [tempos[(ano, n)] for n in nomes]
    tabelas[ano] = tab.round(2)
    print(ano, "\n", tabelas[ano].to_string(), "\n")

taus = pd.DataFrame(
    [
        {"ano": ano, "seções": f"{100 * t:g}%", **{k: v for k, v in resumo.items() if k != "segundos"}}
        for ano, t, resumo in hier[hier["t"].isin([0.05, 0.25, 0.50])][["ano", "t", "resumo"]].itertuples(index=False)
    ]
).set_index(["ano", "seções"]).round(2)
print(taus.to_string())


def intervalo(g: pd.DataFrame) -> pd.Series:
    lo = g["amostras"].map(lambda a: np.percentile(a, 5))
    hi = g["amostras"].map(lambda a: np.percentile(a, 95))
    return pd.Series(
        {
            "largura média do IC 90% (p.p.)": (hi - lo).mean(),
            "pontos com o final dentro do IC 90%": f"{((g['final'] >= lo) & (g['final'] <= hi)).sum()}/{len(g)}",
        }
    )


previa = hier.groupby("ano").apply(intervalo, include_groups=False)
print(previa.to_string())

# %% ADVI x NUTS em 2022
comparacao = []
for t in (0.025, 0.10, 0.50):
    linha = {"seções": f"{100 * t:g}%"}
    for metodo in ("advi", "nuts"):
        m = SwingHierarquico(metodo=metodo)
        inicio = time.perf_counter()
        p = m.projetar(*dividir(secoes[2022], t))
        lo, hi = np.percentile(m.ultimas_amostras, [5, 95])
        linha |= {
            f"{metodo} erro": p - pct_pt(secoes[2022]),
            f"{metodo} IC 90%": f"[{lo:.2f}, {hi:.2f}]",
            f"{metodo} tau_uf": m.ultimo_resumo["tau_uf"],
            f"{metodo} seg": time.perf_counter() - inicio,
        }
    comparacao.append(linha)
    print(linha, flush=True)
comparacao = pd.DataFrame(comparacao).set_index("seções").round(3)

# %% Figura
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, ano in zip(axes, (2022, 2018), strict=True):
    for nome in nomes:
        r = res[(res["ano"] == ano) & (res["modelo"] == nome)]
        estilo = ":" if nome.startswith("SwingUniforme") else "-"
        ax.plot(100 * r["t"], r["abs_erro"], estilo, marker="o", markersize=3, label=nome)
    ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8)
    ax.set(title=f"{ano} (ordem {ORDEM[ano]})", xlabel="% de seções divulgadas", yscale="log")
axes[0].set_ylabel("|erro| do % PT final (p.p.)")
axes[0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(REPORTS / "figures" / "03_erro_vs_apurado.png", dpi=130)

# %% Relatório
ANALISE = Path(__file__).with_name("03_hierarquico_analise.md").read_text(encoding="utf-8")
linhas = [
    "# 03 — Modelo hierárquico bayesiano no 2º turno\n",
    "Pergunta: o pooling aprendido supera os pesos escolhidos à mão?\n",
    "`SwingHierarquico`: swing por local ~ Normal(mu, sigma/sqrt(peso)), com mu = alpha + beta·X + a_ufcap e "
    "a_regiao ~ N(0, tau_regiao), a_uf ~ N(a_regiao, tau_uf), a_ufcap ~ N(a_uf, tau_ufcap) (UF × capital). "
    "PyMC, ADVI (30 mil iterações), 1.000 amostras. Detalhes no docstring de `projetor.models.hierarquico`. "
    "`SwingCamadasInterceptoPorte` usa k = 30 e min_locais = 1000, escolhidos em 2018 na fase 2.\n",
    "![|erro| x % apurado](figures/03_erro_vs_apurado.png)\n",
]
for ano in (2022, 2018):
    linhas += [f"\n## {ano} — ordem {ORDEM[ano]}, histórico de {ANTERIOR[ano]}\n", tabelas[ano].to_markdown() + "\n"]
linhas += [
    "\n## Pooling aprendido (média posterior, p.p. de swing)\n",
    "tau = desvio entre grupos de cada nível; sigma = ruído de um local de peso médio.\n",
    taus.to_markdown() + "\n",
    "\n## ADVI x NUTS (2022)\n",
    "NUTS via nutpie, 4 cadeias × 250 amostras após 500 de aquecimento.\n",
    comparacao.to_markdown() + "\n",
    "\n## Prévia dos intervalos (para a fase 4)\n",
    intervalo.__doc__ or "",
    previa.to_markdown() + "\n",
    "\n## Conclusão\n",
    ANALISE,
]
(REPORTS / "03_hierarquico.md").write_text("\n".join(linhas), encoding="utf-8")
print("gravado", REPORTS / "03_hierarquico.md")
