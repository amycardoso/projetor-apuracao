# %% [markdown]
# # 07b — Noites de governador
#
# Roda o Apurado, o swing uniforme da UF e o hierárquico-t (com incerteza de
# comparecimento) em cada 2º turno de governador de 2018 e 2022, com o 1º
# turno do mesmo ano como histórico (`projetor.governador`). Grava erros e
# amostras em `data/processed/`. Leva ~1–2 h.
#
#     python notebooks/07b_governador.py

# %%
import json
from pathlib import Path

import numpy as np
import pandas as pd

from projetor import governador
from projetor.backtest import rodar
from projetor.models.baseline import Apurado, SwingUniforme
from projetor.models.hierarquico import SwingHierarquico

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

erros = []
for ano in (2018, 2022):
    for uf in governador.ufs(ano):
        destino = PROCESSED / f"amostras_gov_{ano}_{uf}.npz"
        secoes = governador.noite(ano, uf)
        for modelo in (Apurado(), SwingUniforme()):
            erros.append(rodar(modelo, secoes).assign(ano=ano, uf=uf))
        if destino.exists():  # retoma de onde parou
            continue
        hier = SwingHierarquico(verossimilhanca="t", incerteza_comparecimento=True, nome="SwingHierarquico-t")
        r = rodar(hier, secoes)
        np.savez_compressed(
            destino,
            t=r["t"].to_numpy(),
            final=r["final"].to_numpy(),
            projecao=r["projecao"].to_numpy(),
            amostras=np.stack(r["amostras"].to_list()),
            resumo=np.array([json.dumps(x) for x in r["resumo"]]),
        )
        print(ano, uf, len(secoes), "seções; erro médio", r["erro"].abs().mean().round(3), flush=True)
pd.concat(erros, ignore_index=True).to_parquet(PROCESSED / "erros_gov_baselines.parquet", index=False)
