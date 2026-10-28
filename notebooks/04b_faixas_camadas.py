# %% [markdown]
# # 04b — Faixas do SwingCamadasInterceptoPorte para a fase 4
#
# Em cada ponto da grade dos dois backtests, grava a faixa analítica (centro e
# desvio) e 200 réplicas do bootstrap preditivo. Grava também o erro pontual
# numa grade fina (0,5% a 95%, passo de 0,5%) para calibrar o conformal.
# Saída em `data/processed/` (não versionado). Leva ~40 min.
#
#     python notebooks/04b_faixas_camadas.py

# %%
from pathlib import Path

import numpy as np
import pandas as pd

from projetor.backtest import GRADE, dividir, pct_pt, rodar
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.intervals import Preparo, analitico_camadas, bootstrap_camadas
from projetor.locais import carregar_secoes
from projetor.models.camadas import SwingCamadasInterceptoPorte

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)
MODELO = SwingCamadasInterceptoPorte(k=30, min_locais=1000)
GRADE_FINA = np.round(np.arange(0.005, 0.951, 0.005), 3).tolist()

for ano in (2018, 2022):
    secoes = anexar_historico(pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet"), carregar_secoes(ANTERIOR[ano]))
    final = pct_pt(secoes)
    rodar(MODELO, secoes, grade=GRADE_FINA).to_parquet(PROCESSED / f"erros_camadas_fina_{ano}_2t.parquet", index=False)
    print(ano, "grade fina pronta", flush=True)

    centros, sds, projecoes, boots = [], [], [], []
    for t in GRADE:
        divulgadas, pendentes = dividir(secoes, t)
        prep = Preparo.de(divulgadas, pendentes)
        centro, sd = analitico_camadas(MODELO, prep)
        centros.append(centro)
        sds.append(sd)
        projecoes.append(MODELO.projetar(divulgadas, pendentes))
        boots.append(bootstrap_camadas(MODELO, prep, b=200, semente=int(1000 * t)))
        print(ano, t, round(centro - final, 3), round(sd, 3), round(boots[-1].std(), 3), flush=True)
    np.savez_compressed(
        PROCESSED / f"faixas_camadas_{ano}_2t.npz",
        t=np.array(GRADE),
        final=np.full(len(GRADE), final),
        projecao=np.array(projecoes),
        centro=np.array(centros),
        sd=np.array(sds),
        bootstrap=np.stack(boots),
    )
