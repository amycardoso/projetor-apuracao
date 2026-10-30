# %% [markdown]
# # 06 — 1º turno e erro comum das pendentes
#
# Lê o que `06a_primeiro_turno.py` e `04a_amostras_hierarquico.py` gravaram
# em `data/processed/` e escreve `reports/06_melhorias.md`:
#
# 1. totais do 1º turno contra o resultado oficial do TSE;
# 2. erro dos modelos nas noites de 1º turno, para o PT e para o principal
#    adversário;
# 3. faixas do hierárquico com e sem o termo de discrepância comum, avaliadas
#    em leave-one-night-out nas quatro noites do PT (2018 e 2022, 1º e 2º
#    turnos).
#
#     python notebooks/06_melhorias.py

# %%
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from projetor import discrepancia, noites
from projetor.backtest import tempo_ate_cravar
from projetor.intervals import faixa_amostras, winkler
from projetor.locais import carregar_secoes
from projetor.votos import validos

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
PROCESSED = RAIZ / "data" / "processed"
NIVEIS = [0.9, 0.95]

# %% 1. Totais do 1º turno contra o oficial
# Votos nominais do TSE (resultado oficial divulgado), 1º turno, Brasil + exterior.
# 2018: totalização concluída em 8/10/2018 (tse.jus.br, "Concluída totalização de
# votos do 1º turno das Eleições 2018").
OFICIAL_1T = {
    2014: {"pt": 43_267_668, "adversario": 34_897_211, "validos": 104_023_802},  # Dilma, Aécio
    2018: {"pt": 31_342_005, "adversario": 49_276_990, "validos": 107_050_673},  # Haddad, Bolsonaro
    2022: {"pt": 57_259_504, "adversario": 51_072_345, "validos": 118_229_719},  # Lula, Bolsonaro
}
linhas_totais = []
for ano, oficial in OFICIAL_1T.items():
    s = carregar_secoes(ano, 1)
    nosso = {"pt": s["votos_pt"].sum(), "adversario": s["votos_adversario"].sum(), "validos": validos(s).sum()}
    for campo in ("pt", "adversario", "validos"):
        linhas_totais.append(
            {"ano": ano, "campo": campo, "BU agregado": int(nosso[campo]), "oficial": oficial[campo],
             "diferença": int(nosso[campo]) - oficial[campo]}
        )  # fmt: skip
totais = pd.DataFrame(linhas_totais).astype({"ano": str})
print(totais.to_string(index=False))
secoes_1t = {ano: len(carregar_secoes(ano, 1)) for ano in OFICIAL_1T}

# %% 2. Erros no 1º turno
erros = pd.read_parquet(PROCESSED / "erros_1t.parquet")
ORDEM_MODELOS = ["Apurado", "SwingUniformeUF", "SwingCamadasInterceptoPorte", "SwingHierarquico-t"]


def _metricas(g: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
            "erro médio": g["erro"].abs().mean(),
            "erro até 2,5%": g.loc[g["t"] <= 0.025, "erro"].abs().mean(),
            "erro 5–95%": g.loc[g["t"] >= 0.05, "erro"].abs().mean(),
            "tempo até cravar": 100 * tempo_ate_cravar(g),
        }
    )


tab_erros = erros.groupby(["alvo", "ano", "modelo"]).apply(_metricas, include_groups=False)
tab_erros = tab_erros.reindex(ORDEM_MODELOS, level="modelo").round(3)
finais_1t = erros.groupby(["alvo", "ano"])["final"].first().round(3)
print(tab_erros.to_string())


# %% 3. Noites para as faixas
NOITES_PT = [noites.carregar(a, tr) for a in (2018, 2022) for tr in (1, 2)]
NOITES_ADV = [noites.carregar(a, 1, "adversario") for a in (2018, 2022)]


def treino(alvo: noites.Noite) -> list[noites.Noite]:
    """Noites do PT de outras eleições (ano e turno diferentes do alvo)."""
    return [n for n in NOITES_PT if (n.ano, n.turno) != (alvo.ano, alvo.turno)]


METODOS = ["(c) posterior", "(c) + δ fração", "(c) + δ distância", "(e) recalibrada"]


def faixas(alvo: noites.Noite, metodo: str, nivel: float) -> tuple[np.ndarray, np.ndarray, float]:
    """Limites da faixa e o parâmetro calibrado no treino (c ou multiplicador)."""
    tr = treino(alvo)
    if metodo == "(c) posterior":
        return *faixa_amostras(alvo.amostras, nivel), np.nan
    if metodo.startswith("(c) + δ"):
        escala = "fracao" if "fração" in metodo else "distancia"
        c = noites.calibrar_c(tr, escala)
        a = discrepancia.aplicar(alvo.amostras, alvo.perfis, c, escala, semente=1)
        return *faixa_amostras(a, nivel), c
    m = noites.multiplicador_e(tr, nivel)
    centro, sd = alvo.amostras.mean(axis=1), alvo.amostras.std(axis=1)
    return centro - m * sd, centro + m * sd, m


registros = []
for alvo in NOITES_PT + NOITES_ADV:
    for metodo in METODOS:
        for nivel in NIVEIS:
            lo, hi, param = faixas(alvo, metodo, nivel)
            registros.append(
                pd.DataFrame(
                    {
                        "noite": alvo.rotulo, "alvo": alvo.alvo, "metodo": metodo, "nivel": nivel, "t": alvo.t,
                        "lo": lo, "hi": hi, "final": alvo.final, "param": param,
                        "cobre": (lo <= alvo.final) & (alvo.final <= hi), "largura": hi - lo,
                        "winkler": winkler(lo, hi, alvo.final, nivel),
                    }
                )  # fmt: skip
            )
f = pd.concat(registros, ignore_index=True)


def _resumo(g: pd.DataFrame) -> pd.Series:
    return pd.Series({"cobertura": g["cobre"].mean(), "largura": g["largura"].mean(), "winkler": g["winkler"].mean()})


def tabela(df: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    t = df.groupby([*por, "nivel"]).apply(_resumo, include_groups=False).unstack("nivel")
    t.columns = [f"{m} {int(100 * n)}%" for m, n in t.columns]
    t = t[[f"{m} {n}%" for n in (90, 95) for m in ("cobertura", "largura", "winkler")]]
    for n in (90, 95):
        t[f"cobertura {n}%"] = t[f"cobertura {n}%"].map(lambda v: f"{100 * v:.0f}%")
    return t.round(2).reset_index()


pt = f[f["alvo"] == "pt"]
tab_geral = tabela(pt, ["metodo"]).set_index("metodo").reindex(METODOS)
tab_noite = tabela(pt, ["noite", "metodo"])
tab_adv = tabela(f[f["alvo"] == "adversario"], ["noite", "metodo"])
params = (
    f[f["nivel"] == 0.9].groupby(["noite", "metodo"])["param"].first().unstack("metodo")[METODOS[1:]].round(2)
)
# Valores que valeriam para uma noite nova: calibrados nas quatro noites do PT.
c_final = {escala: noites.calibrar_c(NOITES_PT, escala) for escala in discrepancia.ESCALAS}
print(tab_geral.to_string())
print(tab_noite.to_string())
print(params.to_string())
print("c com as quatro noites:", c_final)

# %% Figura: 2022 1º turno, faixa (c) com e sem δ
alvo = next(n for n in NOITES_PT if (n.ano, n.turno) == (2022, 1))
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, metodo in zip(axes, ["(c) posterior", "(c) + δ fração"], strict=True):
    g90 = f[(f["noite"] == alvo.rotulo) & (f["metodo"] == metodo) & (f["nivel"] == 0.9)]
    g95 = f[(f["noite"] == alvo.rotulo) & (f["metodo"] == metodo) & (f["nivel"] == 0.95)]
    x = 100 * g90["t"]
    ax.fill_between(x, g95["lo"], g95["hi"], alpha=0.18, color="C3", label="faixa 95%")
    ax.fill_between(x, g90["lo"], g90["hi"], alpha=0.35, color="C3", label="faixa 90%")
    ax.plot(x, alvo.amostras.mean(axis=1), color="C3", marker="o", markersize=3, label="projeção")
    ax.axhline(alvo.final[0], color="black", linewidth=1, label=f"final ({alvo.final[0]:.2f}%)")
    ax.set(title=metodo, xscale="log", xlabel="% de seções divulgadas (escala log)")
axes[0].set_ylabel("% Lula nos válidos")
axes[0].legend(frameon=False, fontsize=8)
fig.suptitle("2022, 1º turno: faixas do hierárquico sem e com o erro comum das pendentes")
fig.tight_layout()
fig.savefig(REPORTS / "figures" / "06_faixa_1t_2022.png", dpi=130)

# %% Relatório
ANALISE = Path(__file__).with_name("06_melhorias_analise.md").read_text(encoding="utf-8")
blocos = {
    "TOTAIS": totais.to_markdown(index=False, intfmt=","),
    "SECOES": ", ".join(f"{ano}: {n:,}".replace(",", ".") for ano, n in secoes_1t.items()),
    "FINAIS": finais_1t.unstack("ano").to_markdown(),
    "ERROS_PT": tab_erros.loc["pt"].reset_index().to_markdown(index=False),
    "ERROS_ADV": tab_erros.loc["adversario"].reset_index().to_markdown(index=False),
    "FAIXAS_GERAL": tab_geral.to_markdown(),
    "FAIXAS_NOITE": tab_noite.to_markdown(index=False),
    "FAIXAS_ADV": tab_adv.to_markdown(index=False),
    "PARAMS": params.to_markdown(),
    "C_FRACAO": f"{c_final['fracao']:.2f}".replace(".", ","),
    "C_DISTANCIA": f"{c_final['distancia']:.2f}".replace(".", ","),
}
texto = ANALISE
for chave, valor in blocos.items():
    texto = texto.replace(f"{{{{{chave}}}}}", valor)
(REPORTS / "06_melhorias.md").write_text(texto, encoding="utf-8")
print("gravado reports/06_melhorias.md")
