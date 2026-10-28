# %% [markdown]
# # 06a — Backtest do 1º turno e perfis das pendentes
#
# Para cada noite de 1º turno (2022 ← 2018 e 2018 ← 2014) e cada alvo (% PT e
# % do principal adversário nos válidos), roda Apurado, SwingUniformeUF,
# SwingCamadasInterceptoPorte e o hierárquico Student-t com incerteza de
# comparecimento. Grava os erros e as amostras do hierárquico em
# `data/processed/`. Também mede, nas noites de 2º turno, o perfil das
# pendentes (fração que falta e distância de composição) em cada ponto da
# grade, que a calibração do termo de discrepância usa. Leva ~1 h.
#
#     python notebooks/06a_primeiro_turno.py

# %%
import json
from pathlib import Path

import numpy as np
import pandas as pd

from projetor import discrepancia
from projetor.backtest import GRADE, dividir, rodar
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.locais import carregar_secoes
from projetor.models.baseline import Apurado, SwingUniformeUF
from projetor.models.camadas import SwingCamadasInterceptoPorte
from projetor.models.hierarquico import SwingHierarquico
from projetor.votos import trocar_alvo

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


def secoes_da_noite(ano: int, turno: int, alvo: str = "pt") -> pd.DataFrame:
    """Seções com relógio e histórico; `alvo="adversario"` troca os candidatos nos dois anos."""
    atual = pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_{turno}t.parquet")
    anterior = carregar_secoes(ANTERIOR[ano], turno)
    if alvo == "adversario":
        atual, anterior = trocar_alvo(atual), trocar_alvo(anterior)
    return anexar_historico(atual, anterior)


# %% Perfis das noites de 2º turno (as do 1º turno saem do resumo do hierárquico)
for ano in (2018, 2022):
    secoes = secoes_da_noite(ano, 2)
    perfis = [discrepancia.perfil(*dividir(secoes, t)) for t in GRADE]
    pd.DataFrame(
        {"t": GRADE, "fracao_pendente": [p.fracao_pendente for p in perfis], "distancia": [p.distancia for p in perfis]}
    ).to_parquet(PROCESSED / f"perfis_{ano}_2t.parquet", index=False)
    print(ano, "2t perfis prontos", flush=True)

# %% Backtest do 1º turno
erros = []
for ano in (2022, 2018):
    for alvo in ("pt", "adversario"):
        secoes = secoes_da_noite(ano, 1, alvo)
        for modelo in (Apurado(), SwingUniformeUF(min_secoes=30), SwingCamadasInterceptoPorte(k=30, min_locais=1000)):
            r = rodar(modelo, secoes)
            erros.append(r.assign(ano=ano, alvo=alvo))
            print(ano, alvo, modelo.nome, "erro médio", r["erro"].abs().mean().round(3), flush=True)

        hier = SwingHierarquico(verossimilhanca="t", incerteza_comparecimento=True, nome="SwingHierarquico-t")
        r = rodar(hier, secoes)
        erros.append(r.drop(columns=["amostras", "resumo"]).assign(ano=ano, alvo=alvo))
        np.savez_compressed(
            PROCESSED / f"amostras_hier_t_comp_{ano}_1t_{alvo}.npz",
            t=r["t"].to_numpy(),
            final=r["final"].to_numpy(),
            projecao=r["projecao"].to_numpy(),
            amostras=np.stack(r["amostras"].to_list()),
            resumo=np.array([json.dumps(x) for x in r["resumo"]]),
        )
        print(ano, alvo, hier.nome, "erro médio", r["erro"].abs().mean().round(3), flush=True)
        pd.concat(erros, ignore_index=True).to_parquet(PROCESSED / "erros_1t.parquet", index=False)
