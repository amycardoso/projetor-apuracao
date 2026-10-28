# %% [markdown]
# # 05 — Agregados leves para o replay interativo
#
# Para cada ano, roda os modelos principais numa grade de ~100 pontos do relógio
# e grava `app/data/replay_{ano}.json`, só com agregados nacionais (nada por
# seção): % apurado, horário (2022), parcial e projeções do PT, faixa (e) de
# 90% e 95% e composição regional dos válidos divulgados. Leva ~1 h, por causa
# do hierárquico.
#
#     python notebooks/05_exportar_app.py

# %%
import json
from pathlib import Path

import numpy as np
import pandas as pd

from projetor.backtest import dividir, pct_pt
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.intervals import conformal_normalizado
from projetor.locais import carregar_secoes
from projetor.models.baseline import Apurado, SwingUniformeUF
from projetor.models.camadas import SwingCamadasInterceptoPorte
from projetor.models.features import REGIAO
from projetor.models.hierarquico import SwingHierarquico

RAIZ = Path(__file__).resolve().parents[1]
APP_DATA = RAIZ / "app" / "data"
PROCESSED = RAIZ / "data" / "processed"
APP_DATA.mkdir(parents=True, exist_ok=True)

GRADE = np.unique(np.round(np.concatenate([np.arange(0.005, 0.05, 0.0025), np.arange(0.05, 0.996, 0.0125)]), 4))
CANDIDATOS = {2018: {"pt": "Haddad", "adversario": "Bolsonaro"}, 2022: {"pt": "Lula", "adversario": "Bolsonaro"}}
NIVEIS = [0.9, 0.95]
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul", "Exterior"]


def multiplicadores(ano: int) -> dict[float, float]:
    """Faixa (e): multiplicador do desvio posterior calibrado no OUTRO ano (fase 4)."""
    outro = {2018: 2022, 2022: 2018}[ano]
    d = np.load(PROCESSED / f"amostras_hier_t_comp_{outro}_2t.npz")
    return conformal_normalizado(d["amostras"].mean(axis=1) - d["final"], d["amostras"].std(axis=1), NIVEIS)


for ano in (2022, 2018):
    secoes = anexar_historico(pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet"), carregar_secoes(ANTERIOR[ano]))
    secoes["regiao"] = secoes["uf"].map(REGIAO)
    final = pct_pt(secoes)
    mult = multiplicadores(ano)
    modelos = {
        "apurado": Apurado(),
        "swing_uf": SwingUniformeUF(min_secoes=30),
        "camadas": SwingCamadasInterceptoPorte(k=30, min_locais=1000),
        "hierarquico": SwingHierarquico(verossimilhanca="t", incerteza_comparecimento=True),
    }
    pontos = []
    for t in GRADE:
        divulgadas, pendentes = dividir(secoes, float(t))
        validos = divulgadas["votos_pt"] + divulgadas["votos_adversario"]
        ponto = {
            "relogio": float(t),
            "secoes_pct": round(100 * len(divulgadas) / len(secoes), 3),
            "validos_pct": round(100 * validos.sum() / (secoes["votos_pt"] + secoes["votos_adversario"]).sum(), 3),
            "horario": divulgadas["momento"].max().strftime("%H:%M") if "momento" in divulgadas else None,
            "regioes": {
                r: round(100 * v, 2)
                for r, v in (validos.groupby(divulgadas["regiao"]).sum() / validos.sum()).reindex(REGIOES, fill_value=0).items()
            },
        }
        for nome, modelo in modelos.items():
            ponto[nome] = round(modelo.projetar(divulgadas, pendentes), 3)
        amostras = modelos["hierarquico"].ultimas_amostras
        centro, desvio = amostras.mean(), amostras.std()
        for nivel in NIVEIS:
            ponto[f"faixa{int(100 * nivel)}"] = [round(centro - mult[nivel] * desvio, 3), round(centro + mult[nivel] * desvio, 3)]
        pontos.append(ponto)
        print(ano, t, ponto["hierarquico"] - final, flush=True)

    saida = {
        "ano": ano,
        "turno": 2,
        "candidatos": CANDIDATOS[ano],
        "final_pt": round(final, 3),
        "ordem": "observada (DT_BU_RECEBIDO)" if ano == 2022 else "simulada a partir de 2022",
        "historico": ANTERIOR[ano],
        "multiplicador_faixa": {str(k): round(v, 3) for k, v in mult.items()},
        "pontos": pontos,
    }
    (APP_DATA / f"replay_{ano}.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
