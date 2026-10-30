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


def de_arquivo(caminho: Path, rotulo: str, ano: int, turno: int, alvo: str, perfis: pd.DataFrame | None = None) -> Noite:
    """Lê um npz do hierárquico; o perfil vem do resumo de cada instante ou de `perfis`."""
    d = np.load(caminho)
    resumos = [json.loads(r) for r in d["resumo"]]
    if perfis is None:
        perfis = pd.DataFrame(resumos)[["fracao_pendente", "distancia"]]
    assert len(perfis) == len(resumos)
    lista = [
        Perfil(f, x, r["sigma"])
        for f, x, r in zip(perfis["fracao_pendente"], perfis["distancia"], resumos, strict=True)
    ]
    return Noite(rotulo, ano, turno, alvo, d["t"], d["final"], d["amostras"], lista)


def carregar(ano: int, turno: int, alvo: str = "pt", pasta: Path = PROCESSED) -> Noite:
    """Uma noite presidencial; o 2º turno de 2018/2022 tem os perfis num parquet à parte."""
    rotulo = f"{ano} {turno}T {'PT' if alvo == 'pt' else 'adversário'}"
    if turno == 2 and ano in (2018, 2022):
        p = pd.read_parquet(pasta / f"perfis_{ano}_2t.parquet")
        n = de_arquivo(pasta / f"amostras_hier_t_comp_{ano}_2t.npz", rotulo, ano, turno, alvo, p)
        assert np.allclose(p["t"], n.t)
        return n
    return de_arquivo(pasta / f"amostras_hier_t_comp_{ano}_{turno}t_{alvo}.npz", rotulo, ano, turno, alvo)


def governador(ano: int, uf: str, pasta: Path = PROCESSED) -> Noite:
    return de_arquivo(pasta / f"amostras_gov_{ano}_{uf}.npz", f"gov {ano} {uf}", ano, 2, "governador")


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
