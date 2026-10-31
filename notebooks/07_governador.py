# %% [markdown]
# # 07 — Governador: mais noites para calibrar o erro comum
#
# Junta as 4 noites presidenciais do PT (1º e 2º turnos de 2018 e 2022) às
# noites de 2º turno de governador de 2018 e 2022 (`07b_governador.py`) e
# avalia as faixas do hierárquico deixando de fora uma data inteira: ao
# avaliar uma noite, o treino exclui todas as disputas do mesmo dia, que
# compartilham a ordem de chegada. Escreve `reports/07_governador.md`.
#
#     python notebooks/07_governador.py

# %%
from pathlib import Path

import numpy as np
import pandas as pd

from projetor import discrepancia, governador, noites
from projetor.backtest import tempo_ate_cravar
from projetor.intervals import faixa_amostras, winkler

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
PROCESSED = RAIZ / "data" / "processed"
NIVEIS = [0.9, 0.95]

PRESIDENCIAIS = [noites.carregar(a, tr) for a in (2018, 2022) for tr in (1, 2)]
GOVERNADOR = [noites.governador(a, uf) for a in (2018, 2022) for uf in governador.ufs(a)]
TODAS = PRESIDENCIAIS + GOVERNADOR


def data(n: noites.Noite) -> tuple[int, int]:
    return n.ano, n.turno


# %% Erro pontual nas noites de governador
linhas = []
for n in GOVERNADOR:
    uf = n.rotulo.split()[-1]
    base = pd.read_parquet(PROCESSED / f"erros_gov_baselines_{n.ano}.parquet").query("uf == @uf")
    erro_h = n.erro
    linha = {"ano": n.ano, "UF": uf, "final A": round(float(n.final[0]), 2)}
    for nome, g in base.groupby("modelo"):
        linha[nome] = g["erro"].abs().mean()
    linha["SwingHierarquico-t"] = np.abs(erro_h).mean()
    linha["cravar (hier.)"] = 100 * tempo_ate_cravar(pd.DataFrame({"t": n.t, "erro": erro_h}))
    linha["sigma médio"] = np.mean([p.ruido for p in n.perfis])
    linhas.append(linha)
tab_gov = pd.DataFrame(linhas).round(3)
print(tab_gov.to_string(index=False))

# %% Faixas, deixando uma data de fora
ESCALAS = ["fracao", "ruido"]
METODOS = ["(c) posterior", "(c) + δ fração", "(c) + δ ruído", "(e) recalibrada"]


def faixas(alvo: noites.Noite, metodo: str, nivel: float, tr: list[noites.Noite]) -> tuple[np.ndarray, np.ndarray, float]:
    if metodo == "(c) posterior":
        return *faixa_amostras(alvo.amostras, nivel), np.nan
    if metodo.startswith("(c) + δ"):
        escala = "fracao" if "fração" in metodo else "ruido"
        c = noites.calibrar_c(tr, escala)
        return *faixa_amostras(discrepancia.aplicar(alvo.amostras, alvo.perfis, c, escala, semente=1), nivel), c
    m = noites.multiplicador_e(tr, nivel)
    centro, sd = alvo.amostras.mean(axis=1), alvo.amostras.std(axis=1)
    return centro - m * sd, centro + m * sd, m


treinos = {d: [n for n in TODAS if data(n) != d] for d in {data(n) for n in TODAS}}
registros = []
for alvo in TODAS:
    tr = treinos[data(alvo)]
    for metodo in METODOS:
        for nivel in NIVEIS:
            lo, hi, param = faixas(alvo, metodo, nivel, tr)
            registros.append(
                pd.DataFrame(
                    {"noite": alvo.rotulo, "tipo": "presidente" if alvo.alvo == "pt" else "governador",
                     "data": f"{alvo.ano} {alvo.turno}T", "metodo": metodo, "nivel": nivel, "t": alvo.t,
                     "param": param, "cobre": (lo <= alvo.final) & (alvo.final <= hi), "largura": hi - lo,
                     "winkler": winkler(lo, hi, alvo.final, nivel)}
                )  # fmt: skip
            )
f = pd.concat(registros, ignore_index=True)


def _resumo(g: pd.DataFrame) -> pd.Series:
    por_noite = g.groupby("noite")["cobre"].mean()
    return pd.Series(
        {"cobertura": g["cobre"].mean(), "noites ≥ 80%": f"{(por_noite >= 0.8).sum()}/{len(por_noite)}",
         "largura": g["largura"].mean(), "winkler": g["winkler"].mean()}
    )  # fmt: skip


def tabela(df: pd.DataFrame, por: list[str], nivel: float = 0.9) -> pd.DataFrame:
    t = df[df["nivel"] == nivel].groupby(por).apply(_resumo, include_groups=False)
    t["cobertura"] = t["cobertura"].map(lambda v: f"{100 * v:.0f}%")
    return t.round(2)


tab_tipo = tabela(f, ["tipo", "metodo"]).reset_index()
tab_tipo95 = tabela(f, ["tipo", "metodo"], 0.95).reset_index()
tab_pres = (
    f[(f["tipo"] == "presidente") & (f["nivel"] == 0.9)]
    .groupby(["noite", "metodo"])["cobre"].mean().map(lambda v: f"{100 * v:.0f}%").unstack("metodo")[METODOS]
)  # fmt: skip
params = f[f["nivel"] == 0.9].groupby(["data", "metodo"])["param"].first().unstack("metodo")[METODOS[1:]].round(2)
print(tab_tipo.to_string(index=False))
print(tab_pres.to_string())
print(params.to_string())

# %% A hipótese: o erro comum cresce quando o histórico explica pouco?
# Por noite: |erro| médio do hierárquico de 5% a 95% contra o sigma médio no mesmo trecho.
pares = pd.DataFrame(
    [
        {"noite": n.rotulo, "erro": np.abs(n.erro[n.t >= 0.05]).mean(),
         "sigma": np.mean([p.ruido for p, t in zip(n.perfis, n.t, strict=True) if t >= 0.05])}
        for n in TODAS
    ]
)  # fmt: skip
correlacao = pares[["erro", "sigma"]].corr(method="spearman").iloc[0, 1]
print("Spearman erro × sigma:", round(correlacao, 2))

# Valores calibrados com todas as noites anteriores a 2026 (usados em 2026).
c_final = {e: noites.calibrar_c(TODAS, e) for e in ESCALAS}
mult_final = {n: noites.multiplicador_e(TODAS, n) for n in NIVEIS}
print("c final:", c_final, "multiplicador (e):", mult_final)
pd.Series({**{f"c_{e}": v for e, v in c_final.items()}, **{f"mult_{int(100 * n)}": v for n, v in mult_final.items()}}).to_json(
    PROCESSED / "calibracao_07.json"
)

# %% Relatório
ANALISE = Path(__file__).with_name("07_governador_analise.md").read_text(encoding="utf-8")


def br(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


blocos = {
    "N_GOV": str(len(GOVERNADOR)),
    "UFS_2018": ", ".join(governador.ufs(2018)),
    "UFS_2022": ", ".join(governador.ufs(2022)),
    "GOV": tab_gov.to_markdown(index=False),
    "FAIXAS90": tab_tipo.to_markdown(index=False),
    "FAIXAS95": tab_tipo95.to_markdown(index=False),
    "PRES": tab_pres.to_markdown(),
    "PARAMS": params.to_markdown(),
    "SPEARMAN": br(correlacao),
    "C_FRACAO": br(c_final["fracao"]),
    "C_RUIDO": br(c_final["ruido"]),
    "MULT90": br(mult_final[0.9]),
}
texto = ANALISE
for chave, valor in blocos.items():
    texto = texto.replace(f"{{{{{chave}}}}}", valor)
(REPORTS / "07_governador.md").write_text(texto, encoding="utf-8")
print("gravado reports/07_governador.md")
