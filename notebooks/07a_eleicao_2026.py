# %% [markdown]
# # 07a — Backtest de 2026 com os modelos congelados
#
# Roda 2026 ← 2022 nos dois turnos com os mesmos modelos e hiperparâmetros
# das fases 2–6 (nada é reescolhido olhando 2026). A grade é a de sempre mais
# os instantes usados na comparação com o modelo de Rodrigo Mahlmeister: 2,2%
# das seções no 1º turno e 2,42% no 2º. Grava erros e amostras em
# `data/processed/`. Leva ~40 min.
#
#     python notebooks/07a_eleicao_2026.py        # os dois turnos
#     python notebooks/07a_eleicao_2026.py 2      # só o 2º

# %%
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from projetor.backtest import GRADE, rodar
from projetor.historico import anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.locais import carregar_secoes
from projetor.models.baseline import Apurado, SwingUniformeUF
from projetor.models.camadas import SwingCamadasInterceptoPorte
from projetor.models.hierarquico import SwingHierarquico
from projetor.votos import trocar_alvo

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
PONTO_RODRIGO = {1: 0.022, 2: 0.0242}
ALVOS = {1: ("pt", "adversario"), 2: ("pt",)}


def secoes_2026(turno: int, alvo: str) -> pd.DataFrame:
    atual = pd.read_parquet(DATA_INTERIM / f"ordem_2026_{turno}t.parquet")
    anterior = carregar_secoes(2022, turno)
    if alvo == "adversario":
        atual, anterior = trocar_alvo(atual), trocar_alvo(anterior)
    return anexar_historico(atual, anterior)


for turno in [int(x) for x in sys.argv[1:]] or [2, 1]:
    erros = []
    grade = sorted({*GRADE, PONTO_RODRIGO[turno]})
    for alvo in ALVOS[turno]:
        secoes = secoes_2026(turno, alvo)
        for modelo in (Apurado(), SwingUniformeUF(min_secoes=30), SwingCamadasInterceptoPorte(k=30, min_locais=1000)):
            r = rodar(modelo, secoes, grade)
            erros.append(r.assign(turno=turno, alvo=alvo))
            print(turno, alvo, modelo.nome, "erro médio", r["erro"].abs().mean().round(3), flush=True)
        hier = SwingHierarquico(verossimilhanca="t", incerteza_comparecimento=True, nome="SwingHierarquico-t")
        r = rodar(hier, secoes, grade)
        erros.append(r.drop(columns=["amostras", "resumo"]).assign(turno=turno, alvo=alvo))
        np.savez_compressed(
            PROCESSED / f"amostras_hier_t_comp_2026_{turno}t_{alvo}.npz",
            t=r["t"].to_numpy(),
            final=r["final"].to_numpy(),
            projecao=r["projecao"].to_numpy(),
            amostras=np.stack(r["amostras"].to_list()),
            resumo=np.array([json.dumps(x) for x in r["resumo"]]),
        )
        print(turno, alvo, hier.nome, "erro médio", r["erro"].abs().mean().round(3), flush=True)
        pd.concat(erros, ignore_index=True).to_parquet(PROCESSED / f"erros_2026_{turno}t.parquet", index=False)
