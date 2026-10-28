# %% [markdown]
# # 04a — Amostras do hierárquico para a fase 4
#
# Roda `SwingHierarquico` com incerteza de comparecimento, nas verossimilhanças
# normal e Student-t, nos dois backtests. Grava as amostras do % PT final por
# ponto da grade em `data/processed/` (não versionado). Leva ~30 min.
#
#     python notebooks/04a_amostras_hierarquico.py

# %%
import json
from pathlib import Path

import numpy as np
import pandas as pd

from projetor.backtest import rodar
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.locais import carregar_secoes
from projetor.models.hierarquico import SwingHierarquico

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

for ano in (2018, 2022):
    secoes = anexar_historico(pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet"), carregar_secoes(ANTERIOR[ano]))
    for verossimilhanca in ("normal", "t"):
        modelo = SwingHierarquico(verossimilhanca=verossimilhanca, incerteza_comparecimento=True)
        r = rodar(modelo, secoes)
        np.savez_compressed(
            PROCESSED / f"amostras_hier_{verossimilhanca}_comp_{ano}_2t.npz",
            t=r["t"].to_numpy(),
            final=r["final"].to_numpy(),
            projecao=r["projecao"].to_numpy(),
            amostras=np.stack(r["amostras"].to_list()),
            resumo=np.array([json.dumps(x) for x in r["resumo"]]),
        )
        print(ano, verossimilhanca, "erro médio", r["erro"].abs().mean().round(3), flush=True)
