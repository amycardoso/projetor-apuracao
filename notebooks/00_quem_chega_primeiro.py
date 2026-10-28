# %% [markdown]
# # 00 — Quem chega primeiro na apuração
#
# 2º turno de 2022, ordem observada (DT_BU_RECEBIDO). O 2018 usa a ordem
# simulada de `projetor.ordem` e aparece só para comparação.
#
# Rode da raiz do repositório:
#
#     python notebooks/00_quem_chega_primeiro.py
#
# O script grava `reports/00_quem_chega_primeiro.md` e as figuras em
# `reports/figures/`. Só sai agregado; nenhum dado por seção é gravado.

# %%
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from projetor.ingest import DATA_INTERIM
from projetor.locais import CHAVE_LOCAL
from projetor.replay import estado_em, parcial

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
FIGURAS = REPORTS / "figures"
FIGURAS.mkdir(parents=True, exist_ok=True)

REGIAO = {
    **dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
    "ZZ": "Exterior",
}
CAPITAIS = {
    "AC": "RIO BRANCO", "AL": "MACEIÓ", "AM": "MANAUS", "AP": "MACAPÁ", "BA": "SALVADOR",
    "CE": "FORTALEZA", "DF": "BRASÍLIA", "ES": "VITÓRIA", "GO": "GOIÂNIA", "MA": "SÃO LUÍS",
    "MG": "BELO HORIZONTE", "MS": "CAMPO GRANDE", "MT": "CUIABÁ", "PA": "BELÉM", "PB": "JOÃO PESSOA",
    "PE": "RECIFE", "PI": "TERESINA", "PR": "CURITIBA", "RJ": "RIO DE JANEIRO", "RN": "NATAL",
    "RO": "PORTO VELHO", "RR": "BOA VISTA", "RS": "PORTO ALEGRE", "SC": "FLORIANÓPOLIS",
    "SE": "ARACAJU", "SP": "SÃO PAULO", "TO": "PALMAS",
}  # fmt: skip

relatorio: list[str] = ["# 00 — Quem chega primeiro na apuração (2º turno)\n"]


def secao(titulo: str, texto: str = "") -> None:
    relatorio.append(f"\n## {titulo}\n\n{texto}\n")


def tabela(df: pd.DataFrame) -> None:
    relatorio.append(df.to_markdown() + "\n")
    print(df.to_string(), "\n")


def figura(fig: plt.Figure, nome: str, legenda: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURAS / nome, dpi=130)
    plt.close(fig)
    relatorio.append(f"![{legenda}](figures/{nome})\n")


# %%
def preparar(ano: int) -> pd.DataFrame:
    df = pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet")
    df["regiao"] = df["uf"].map(REGIAO)
    df["capital"] = np.where(df["nm_municipio"] == df["uf"].map(CAPITAIS), "Capital", "Interior")
    df.loc[df["uf"] == "ZZ", "capital"] = "Exterior"
    df["validos"] = df["votos_pt"] + df["votos_adversario"]
    # Porte: quintis de municípios ponderados pelo eleitorado (cada quintil ~20% dos aptos).
    mun = df.groupby("cd_municipio")["qt_aptos"].sum().sort_values()
    quintil = np.ceil(5 * mun.cumsum() / mun.sum()).clip(1, 5).astype(int)
    df["porte"] = df["cd_municipio"].map(quintil).map(lambda q: f"Q{q}")
    return df


d22, d18 = preparar(2022), preparar(2018)
assert (d22["capital"] == "Capital").groupby(d22["uf"]).any().drop("ZZ").all(), "capital sem par"

limites_porte = d22.groupby("porte").apply(
    lambda g: g.groupby("cd_municipio")["qt_aptos"].sum().agg(["min", "max", "size"]), include_groups=False
).rename(columns={"min": "menor município (aptos)", "max": "maior município (aptos)", "size": "municípios"})

# %% [markdown]
# ## Viés das primeiras seções
#
# Para cada grupo: participação nos votos válidos finais e entre as seções
# divulgadas até 10% e 25% do relógio. Razão acima de 1 indica grupo que
# chega adiantado.


# %%
def vies(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    total = df.groupby(coluna)["validos"].sum()
    linhas = {"% válidos final": 100 * total / total.sum()}
    for t in (0.10, 0.25, 0.50):
        cedo = estado_em(df, t).groupby(coluna)["validos"].sum().reindex(total.index, fill_value=0)
        linhas[f"% até {t:.0%}"] = 100 * cedo / cedo.sum()
    out = pd.DataFrame(linhas)
    out["razão até 10%"] = out["% até 10%"] / out["% válidos final"]
    out["% PT no grupo"] = 100 * df.groupby(coluna)["votos_pt"].sum() / total
    return out.round(2)


secao(
    "Viés das primeiras seções — 2022",
    "Participação de cada grupo nos votos válidos finais e entre as seções divulgadas até 10%, 25% e 50% do relógio.",
)
for coluna in ("regiao", "porte", "capital"):
    tabela(vies(d22, coluna))
relatorio.append("Limites dos quintis de porte (2022):\n")
tabela(limites_porte)

fig, ax = plt.subplots(figsize=(8, 4))
grade = np.linspace(0.01, 1, 100)
ordem_reg = ["Sudeste", "Nordeste", "Sul", "Norte", "Centro-Oeste", "Exterior"]
comp = pd.DataFrame(
    {t: estado_em(d22, t).groupby("regiao")["validos"].sum() for t in grade}
).T.reindex(columns=ordem_reg).fillna(0)
comp = 100 * comp.div(comp.sum(axis=1), axis=0)
ax.stackplot(100 * grade, comp.T.to_numpy(), labels=ordem_reg)
ax.set(xlabel="% de seções divulgadas", ylabel="% dos válidos já divulgados", xlim=(1, 100), ylim=(0, 100))
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), frameon=False)
figura(fig, "00_composicao_regiao_2022.png", "Composição regional dos válidos divulgados, 2022")

# %% [markdown]
# ## Parcial do PT x % apurado


# %%
def curva(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("relogio")
    pt, val = df["votos_pt"].cumsum().to_numpy(), df["validos"].cumsum().to_numpy()
    idx = np.clip(np.searchsorted(df["relogio"].to_numpy(), grade, side="right") - 1, 0, None)
    return pd.DataFrame({"pct_pt": 100 * pt[idx] / val[idx], "pct_validos": 100 * val[idx] / val[-1]}, index=grade)


c22, c18 = curva(d22), curva(d18)
final22, final18 = parcial(d22)["pct_pt"], parcial(d18)["pct_pt"]
marcos = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90]
pontos = pd.DataFrame(
    {
        "2022 % PT parcial": [parcial(estado_em(d22, t))["pct_pt"] for t in marcos],
        "2022 erro vs final (p.p.)": [parcial(estado_em(d22, t))["pct_pt"] - final22 for t in marcos],
        "2018 (simulado) % PT parcial": [parcial(estado_em(d18, t))["pct_pt"] for t in marcos],
        "2018 erro vs final (p.p.)": [parcial(estado_em(d18, t))["pct_pt"] - final18 for t in marcos],
    },
    index=[f"{t:.0%} das seções" for t in marcos],
).round(2)
virada = c22.index[(c22["pct_pt"] >= 50).to_numpy().argmax()]
secao(
    "Parcial do PT x % apurado",
    f"Final 2022: {final22:.2f}% (Lula). Final 2018: {final18:.2f}% (Haddad). "
    f"Em 2022 a parcial de Lula passa de 50% com ~{100 * virada:.0f}% das seções divulgadas.",
)
tabela(pontos)

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(100 * grade, c22["pct_pt"], label="2022 (Lula), ordem observada")
ax.plot(100 * grade, c18["pct_pt"], label="2018 (Haddad), ordem simulada", linestyle="--")
ax.axhline(final22, color="C0", linewidth=0.8, alpha=0.6)
ax.axhline(final18, color="C1", linewidth=0.8, alpha=0.6)
ax.axhline(50, color="gray", linewidth=0.6, linestyle=":")
ax.set(xlabel="% de seções divulgadas", ylabel="% PT nos válidos (parcial)", xlim=(1, 100))
ax.legend(frameon=False)
figura(fig, "00_parcial_pt_vs_apurado.png", "Parcial do PT contra % apurado")

# %% [markdown]
# ## Swing local 2018 → 2022
#
# Variação do % PT nos válidos por local de votação com par direto ou
# rezoneado. Ponderado pelos válidos de 2022.

# %%
pares = pd.read_parquet(DATA_INTERIM / "locais_2018_2022.parquet")
pares = pares[pares["tipo_par"].isin(["direto", "rezoneado"])]
loc18 = d18.groupby(CHAVE_LOCAL)[["votos_pt", "validos"]].sum()
loc22 = d22.groupby(CHAVE_LOCAL).agg(
    votos_pt=("votos_pt", "sum"), validos=("validos", "sum"), regiao=("regiao", "first"), relogio=("relogio", "median")
)
p = pares.set_index(CHAVE_LOCAL).join(loc18.add_suffix("_18"))
p = p.reset_index()
p["nr_zona"] = p["nr_zona_2022"].astype(int)
p = p.set_index(CHAVE_LOCAL).join(loc22, how="inner")
p = p[(p["validos_18"] > 0) & (p["validos"] > 0)]
p["swing"] = 100 * p["votos_pt"] / p["validos"] - 100 * p["votos_pt_18"] / p["validos_18"]


def resumo_swing(g: pd.DataFrame) -> pd.Series:
    w = g["validos"]
    media = np.average(g["swing"], weights=w)
    q = g["swing"].quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    return pd.Series(
        {
            "locais": len(g),
            "média pond.": media,
            "desvio pond.": np.sqrt(np.average((g["swing"] - media) ** 2, weights=w)),
            "p05": q[0.05], "p25": q[0.25], "mediana": q[0.5], "p75": q[0.75], "p95": q[0.95],
        }
    )  # fmt: skip


sw = pd.concat(
    [resumo_swing(p).rename("Brasil"), p.groupby("regiao").apply(resumo_swing, include_groups=False).T], axis=1
).T.round(2)
p["fase"] = pd.cut(p["relogio"], [0, 0.25, 0.5, 0.75, 1], labels=["1º quarto", "2º quarto", "3º quarto", "4º quarto"])
sw_fase = p.groupby("fase", observed=True).apply(resumo_swing, include_groups=False).round(2)
nacional = parcial(d22)["pct_pt"] - parcial(d18)["pct_pt"]
secao(
    "Swing local 2018 → 2022",
    f"{len(p):,} locais pareados. Swing nacional: {nacional:+.2f} p.p. "
    "Desvio e média ponderados pelos válidos de 2022; quantis sem peso.",
)
tabela(sw)
relatorio.append("Por fase de chegada do local em 2022 (mediana do relógio das suas seções):\n")
tabela(sw_fase)

fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(p["swing"].clip(-40, 60), bins=100, weights=p["validos"], color="C2")
ax.axvline(nacional, color="black", linewidth=0.8)
ax.set(xlabel="swing do % PT nos válidos, 2018 → 2022 (p.p.)", ylabel="válidos 2022 (peso)")
figura(fig, "00_swing_local.png", "Distribuição do swing local")

# %%
(REPORTS / "00_quem_chega_primeiro.md").write_text("\n".join(relatorio), encoding="utf-8")
print("gravado", REPORTS / "00_quem_chega_primeiro.md")
