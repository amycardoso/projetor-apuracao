"""Noites já rodadas do hierárquico-t, lidas de `data/processed/`.

Cada noite traz, por ponto da grade, as amostras do % final e o perfil das
pendentes (fração que falta e distância de composição). É o que a calibração
do erro comum (`discrepancia.calibrar`) e da faixa (e) consome.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from projetor import discrepancia
from projetor.discrepancia import Perfil
from projetor.intervals import conformal_normalizado

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"


@dataclass
class Noite:
    rotulo: str
    ano: int
    turno: int
    alvo: str
    t: np.ndarray
    final: np.ndarray
    amostras: np.ndarray
    perfis: list[Perfil]

    @property
    def erro(self) -> np.ndarray:
        return self.amostras.mean(axis=1) - self.final

    @property
    def var(self) -> np.ndarray:
        return self.amostras.var(axis=1)


def carregar(ano: int, turno: int, alvo: str = "pt", pasta: Path = PROCESSED) -> Noite:
    """Lê as amostras de uma noite; o 2º turno de 2018/2022 tem os perfis num parquet à parte."""
    if turno == 2 and ano in (2018, 2022):
        d = np.load(pasta / f"amostras_hier_t_comp_{ano}_2t.npz")
        p = pd.read_parquet(pasta / f"perfis_{ano}_2t.parquet")
        assert np.allclose(p["t"], d["t"])
        perfis = [Perfil(f, x) for f, x in zip(p["fracao_pendente"], p["distancia"], strict=True)]
    else:
        d = np.load(pasta / f"amostras_hier_t_comp_{ano}_{turno}t_{alvo}.npz")
        resumos = [json.loads(r) for r in d["resumo"]]
        perfis = [Perfil(r["fracao_pendente"], r["distancia"]) for r in resumos]
    nome = {"pt": "PT", "adversario": "adversário"}[alvo]
    return Noite(f"{ano} {turno}T {nome}", ano, turno, alvo, d["t"], d["final"], d["amostras"], perfis)


def calibrar_c(noites: list[Noite], escala: str) -> float:
    """`c` do erro comum por máxima verossimilhança nas noites dadas."""
    return discrepancia.calibrar(
        np.concatenate([n.erro for n in noites]),
        np.concatenate([n.var for n in noites]),
        [p for n in noites for p in n.perfis],
        escala,
    )


def multiplicador_e(noites: list[Noite], nivel: float) -> float:
    """Multiplicador conformal do desvio posterior (faixa (e)) nas noites dadas."""
    erro = np.concatenate([n.erro for n in noites])
    desvio = np.sqrt(np.concatenate([n.var for n in noites]))
    return conformal_normalizado(erro, desvio, [nivel])[nivel]
