"""Discrepância comum às pendentes: um erro de swing que todas compartilham.

O hierárquico trata o ruído de cada local pendente como independente, então a
incerteza do total encolhe rápido com o número de locais. Na noite real, as
seções que faltam diferem das divulgadas de um jeito que as covariáveis não
capturam (outro horário, outra cidade, outro eleitorado), e esse erro é comum
a todas elas. Aqui ele vira um termo

    delta ~ Normal(0, tau_delta),   somado ao swing de todos os locais pendentes,

que desloca o % final em `fracao_pendente × delta`, porque o total pondera
divulgadas e pendentes pelos válidos.

`tau_delta = c × h`, com duas escalas:

- `"fracao"`: h = 1. O efeito no total cresce com a fração que falta.
- `"distancia"`: h = distância de variação total entre a composição
  UF × capital/interior dos válidos esperados divulgados e a dos pendentes.
  Pesa mais quando o que falta é diferente do que já chegou.
- `"ruido"`: h = sigma / 10, com sigma o desvio posterior do swing de um
  local em torno do que o modelo explica (p.p.). Pesa mais quando o histórico
  explica pouco do swing já divulgado.

O swing não é observável nas pendentes, então `c` não sai da própria noite: é
calibrado por máxima verossimilhança nos erros de outras noites
(`calibrar`, usado em leave-one-night-out).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize

from projetor.models.features import anexar_features
from projetor.votos import validos

ESCALAS = ("fracao", "distancia", "ruido")


@dataclass(frozen=True)
class Perfil:
    """Quanto falta e o quanto o que falta difere do que já chegou, num instante."""

    fracao_pendente: float
    distancia: float
    ruido: float = float("nan")

    def h(self, escala: str) -> float:
        if escala == "fracao":
            return 1.0
        if escala == "distancia":
            return self.distancia
        if escala == "ruido":
            return self.ruido / 10
        raise ValueError(f"escala desconhecida: {escala}")


def perfil(divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> Perfil:
    """Fração pendente dos válidos e distância entre os perfis divulgado e pendente.

    Os dois lados usam os válidos esperados (aptos × taxa anterior), que são
    conhecidos para as pendentes. A fração pendente usa os válidos reais das
    divulgadas, como o total da projeção.
    """
    div, pend = anexar_features(divulgadas, pendentes)
    esperados_pend = pend["validos_esperados"].sum()
    fracao = esperados_pend / (validos(divulgadas).sum() + esperados_pend)

    def composicao(df: pd.DataFrame) -> pd.Series:
        g = df.groupby([df["uf"], df["capital"]])["validos_esperados"].sum()
        return g / g.sum()

    if pend.empty or div.empty:
        return Perfil(float(fracao), 0.0 if pend.empty else 1.0)
    a, b = composicao(div).align(composicao(pend), fill_value=0.0)
    return Perfil(float(fracao), float(0.5 * np.abs(a - b).sum()))


def desvio(perfis: list[Perfil], c: float, escala: str) -> np.ndarray:
    """Desvio-padrão do deslocamento do % final: fração × c × h."""
    return np.array([p.fracao_pendente * c * p.h(escala) for p in perfis])


def aplicar(amostras: np.ndarray, perfis: list[Perfil], c: float, escala: str, semente: int = 0) -> np.ndarray:
    """Soma às amostras (pontos × amostras) um delta comum por amostra."""
    rng = np.random.default_rng(semente)
    sd = desvio(perfis, c, escala)[:, None]
    return amostras + sd * rng.standard_normal(amostras.shape)


def calibrar(erro: np.ndarray, var_posterior: np.ndarray, perfis: list[Perfil], escala: str) -> float:
    """`c` de máxima verossimilhança com erro ~ Normal(0, var_posterior + (fração·c·h)²).

    `erro` é projeção − final e `var_posterior` a variância das amostras do
    modelo sem o termo, nos mesmos instantes. Devolve 0 quando a posterior já
    cobre os erros.
    """
    s = desvio(perfis, 1.0, escala)

    def nll(log_c: float) -> float:
        v = var_posterior + (np.exp(log_c) * s) ** 2
        return float(np.sum(np.log(v) + erro**2 / v))

    res = optimize.minimize_scalar(nll, bounds=(np.log(1e-3), np.log(100.0)), method="bounded")
    c = float(np.exp(res.x))
    return c if nll(res.x) < nll(np.log(1e-3)) - 1e-9 else 0.0
