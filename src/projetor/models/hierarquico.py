"""`SwingHierarquico`: swing por local com partial pooling bayesiano (PyMC).

Para cada local divulgado `i`, com peso `w_i` (válidos esperados, normalizados
para média 1):

    swing_i ~ Normal(mu_i, sigma / sqrt(w_i))
    mu_i    = alpha + X_i · beta + a_ufcap[g(i)]

    a_regiao[r] ~ Normal(0, tau_regiao)
    a_uf[u]     ~ Normal(a_regiao[r(u)], tau_uf)
    a_ufcap[g]  ~ Normal(a_uf[u(g)], tau_ufcap)        g = UF × capital/interior

`X` traz `ant_pct_pt`, o log do eleitorado do município e a dummy de capital,
padronizados com constantes fixas para que o mesmo grafo sirva a todos os
instantes. O exterior é sua própria região e UF. Os efeitos são não
centrados. Os tau aprendem quanto encolher cada nível, papel que o `k` fazia à
mão em `SwingCamadas`.

O modelo é montado uma vez com `pm.Data`. A cada instante, só os dados mudam
(`pm.set_data`) e o ajuste roda de novo, por ADVI (padrão) ou por NUTS via
nutpie (`metodo="nuts"`).

Projeção: as pendentes são agregadas por local. Para cada amostra posterior, o
swing de um local pendente é `mu + ruído local` (sigma / sqrt(peso)), somado ao
seu `ant_pct_pt`. O total das pendentes junta-se aos votos já divulgados. A
média dessas amostras é a projeção pontual. As amostras do % PT final ficam em
`ultimas_amostras`, para os intervalos da fase 4.

`verossimilhanca="t"` troca a normal por uma Student-t com ν aprendido
(ν = 1 + Exponential(média 10)), mais robusta a locais com swing extremo; o
ruído de previsão das pendentes passa a ser t também.

`discrepancia=c` soma às amostras um erro de swing comum a todas as pendentes,
delta ~ Normal(0, c × h), com h dado por `escala_discrepancia` (ver
`projetor.discrepancia`). Com `c=0` (padrão), o modelo é o mesmo de antes. A
fração pendente e a distância de perfil ficam sempre em `ultimo_resumo`, para
calibrar `c` em outras noites.

`incerteza_comparecimento=True` sorteia também os válidos de cada local
pendente: `esperados × exp(m + s·z / sqrt(peso))`, com `m` e `s` medidos em
log(válidos reais / esperados) nos locais divulgados (`features.comparecimento`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pymc as pm
from pymc.variational.callbacks import CheckParametersConvergence

from projetor import discrepancia as _discrepancia
from projetor.models.features import REGIAO, anexar_features, comparecimento, pendentes_por_local, por_local
from projetor.votos import validos as _validos

REGIOES = sorted(set(REGIAO.values()))
UFS = sorted(REGIAO)
GRUPOS_UFCAP = [(uf, cap) for uf in UFS for cap in (0, 1)]
_IDX_UFCAP = {g: i for i, g in enumerate(GRUPOS_UFCAP)}

# Padronização fixa (conhecida antes da noite): % PT anterior e log do eleitorado.
CENTRO = np.array([50.0, 11.0, 0.0])
ESCALA = np.array([15.0, 2.0, 1.0])


def _x(df: pd.DataFrame) -> np.ndarray:
    return (df[["ant_pct_pt", "log_aptos_mun", "capital"]].to_numpy(dtype=float) - CENTRO) / ESCALA


def _idx_ufcap(df: pd.DataFrame) -> np.ndarray:
    return np.array([_IDX_UFCAP[(uf, int(c))] for uf, c in zip(df["uf"], df["capital"], strict=True)])


def _construir_modelo(verossimilhanca: str) -> pm.Model:
    uf_da_regiao = np.array([REGIOES.index(REGIAO[uf]) for uf in UFS])
    uf_do_grupo = np.array([UFS.index(uf) for uf, _ in GRUPOS_UFCAP])
    with pm.Model() as modelo:
        x = pm.Data("x", np.zeros((1, 3)))
        g = pm.Data("g", np.zeros(1, dtype="int64"))
        peso = pm.Data("peso", np.ones(1))
        y = pm.Data("y", np.zeros(1))

        alpha = pm.Normal("alpha", 0, 10)
        beta = pm.Normal("beta", 0, 5, shape=3)
        tau_regiao = pm.HalfNormal("tau_regiao", 5)
        tau_uf = pm.HalfNormal("tau_uf", 5)
        tau_ufcap = pm.HalfNormal("tau_ufcap", 5)
        z_regiao = pm.Normal("z_regiao", 0, 1, shape=len(REGIOES))
        z_uf = pm.Normal("z_uf", 0, 1, shape=len(UFS))
        z_ufcap = pm.Normal("z_ufcap", 0, 1, shape=len(GRUPOS_UFCAP))
        a_regiao = pm.Deterministic("a_regiao", tau_regiao * z_regiao)
        a_uf = pm.Deterministic("a_uf", a_regiao[uf_da_regiao] + tau_uf * z_uf)
        a_ufcap = pm.Deterministic("a_ufcap", a_uf[uf_do_grupo] + tau_ufcap * z_ufcap)
        sigma = pm.HalfNormal("sigma", 20)

        mu = alpha + pm.math.dot(x, beta) + a_ufcap[g]
        escala = sigma / pm.math.sqrt(peso)
        if verossimilhanca == "t":
            nu = pm.Deterministic("nu", 1 + pm.Exponential("nu_menos_1", 1 / 10))
            pm.StudentT("swing", nu=nu, mu=mu, sigma=escala, observed=y, shape=y.shape)
        elif verossimilhanca == "normal":
            pm.Normal("swing", mu, escala, observed=y, shape=y.shape)
        else:
            raise ValueError(f"verossimilhança desconhecida: {verossimilhanca}")
    return modelo


@dataclass
class SwingHierarquico:
    metodo: str = "advi"
    n_advi: int = 30_000
    n_amostras: int = 1000
    semente: int = 0
    ruido_local: bool = True
    verossimilhanca: str = "normal"
    incerteza_comparecimento: bool = False
    discrepancia: float = 0.0
    escala_discrepancia: str = "fracao"
    nome: str = "SwingHierarquico"
    ultimas_amostras: np.ndarray | None = field(default=None, repr=False)
    ultimo_resumo: dict[str, float] = field(default_factory=dict, repr=False)
    _modelo: pm.Model | None = field(default=None, repr=False)

    def _ajustar(self, locais: pd.DataFrame) -> dict[str, np.ndarray]:
        if self._modelo is None:
            self._modelo = _construir_modelo(self.verossimilhanca)
        w = locais["validos_esperados"].to_numpy(dtype=float)
        with self._modelo:
            pm.set_data(
                {"x": _x(locais), "g": _idx_ufcap(locais), "peso": w / w.mean(), "y": locais["swing"].to_numpy()}
            )
            if self.metodo == "advi":
                aprox = pm.fit(
                    self.n_advi,
                    method="advi",
                    random_seed=self.semente,
                    progressbar=False,
                    callbacks=[CheckParametersConvergence(tolerance=1e-3, diff="relative")],
                )
                post = aprox.sample(self.n_amostras, random_seed=self.semente).posterior
            elif self.metodo == "nuts":
                import nutpie

                compilado = nutpie.compile_pymc_model(self._modelo)
                post = nutpie.sample(
                    compilado, draws=self.n_amostras // 4, tune=500, chains=4, seed=self.semente, progress_bar=False
                ).posterior
            else:
                raise ValueError(f"método desconhecido: {self.metodo}")
        nomes = ["alpha", "beta", "a_ufcap", "sigma", "tau_regiao", "tau_uf", "tau_ufcap"]
        if self.verossimilhanca == "t":
            nomes.append("nu")
        return {n: post[n].stack(amostra=("chain", "draw")).transpose("amostra", ...).to_numpy() for n in nomes}

    def projetar(self, divulgadas: pd.DataFrame, pendentes: pd.DataFrame) -> float:
        inicio = time.perf_counter()
        div, pend = anexar_features(divulgadas, pendentes)
        locais = por_local(div)
        post = self._ajustar(locais)

        p = pendentes_por_local(pend)
        w_ref = locais["validos_esperados"].mean()
        esperados = p["validos_esperados"].to_numpy()
        escala_rel = 1 / np.sqrt(esperados / w_ref)
        x, g, ant = _x(p), _idx_ufcap(p), p["ant_pct_pt"].to_numpy()
        rng = np.random.default_rng(self.semente)
        pt_div = divulgadas["votos_pt"].sum()
        val_div = _validos(divulgadas).sum()
        m_comp, s_comp = comparecimento(locais) if self.incerteza_comparecimento else (0.0, 0.0)

        n = post["alpha"].shape[0]
        amostras = np.empty(n)
        for s in range(n):
            mu = post["alpha"][s] + x @ post["beta"][s] + post["a_ufcap"][s][g]
            if not self.ruido_local:
                ruido = 0.0
            elif self.verossimilhanca == "t":
                ruido = post["sigma"][s] * escala_rel * rng.standard_t(post["nu"][s], len(p))
            else:
                ruido = post["sigma"][s] * escala_rel * rng.standard_normal(len(p))
            validos = esperados
            if self.incerteza_comparecimento:
                validos = esperados * np.exp(m_comp + s_comp * escala_rel * rng.standard_normal(len(p)))
            pct = np.clip(ant + mu + ruido, 0, 100)
            amostras[s] = 100 * (pt_div + validos @ pct / 100) / (val_div + validos.sum())

        perfil = _discrepancia.perfil(divulgadas, pendentes)
        if self.discrepancia > 0:
            amostras = _discrepancia.aplicar(
                amostras[None, :], [perfil], self.discrepancia, self.escala_discrepancia, self.semente
            )[0]

        self.ultimas_amostras = amostras
        self.ultimo_resumo = {
            "locais": len(locais),
            "tau_regiao": float(post["tau_regiao"].mean()),
            "tau_uf": float(post["tau_uf"].mean()),
            "tau_ufcap": float(post["tau_ufcap"].mean()),
            "sigma": float(post["sigma"].mean()),
            "fracao_pendente": perfil.fracao_pendente,
            "distancia": perfil.distancia,
            **({"nu": float(post["nu"].mean())} if "nu" in post else {}),
            "segundos": time.perf_counter() - inicio,
        }
        return float(amostras.mean())
