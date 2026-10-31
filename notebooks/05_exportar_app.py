# %% [markdown]
# # 05 — Agregados leves para o replay interativo
#
# Para cada ano, roda os modelos principais numa grade de ~100 pontos do relógio
# e grava `docs/data/replay_{ano}.json`, só com agregados nacionais (nada por
# seção): % apurado, horário (2022 e 2026), parcial e projeções do PT, faixas
# de 90% e 95% e composição regional dos válidos divulgados. Leva ~40 min por
# ano, por causa do hierárquico.
#
# A faixa é a do hierárquico com o erro comum às pendentes na escala de ruído
# (fase 7). O `c` de cada ano é calibrado nas noites presidenciais e de
# governador de OUTRAS datas; para 2026, nas 30 noites de 2018 e 2022.
#
#     python notebooks/05_exportar_app.py            # 2026, 2022 e 2018
#     python notebooks/05_exportar_app.py 2026

# %%
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from projetor import discrepancia, governador, noites, votos
from projetor.backtest import dividir, pct_pt
from projetor.discrepancia import Perfil
from projetor.historico import ANTERIOR, anexar_historico
from projetor.ingest import DATA_INTERIM
from projetor.locais import carregar_secoes
from projetor.models.baseline import Apurado, SwingUniformeUF
from projetor.models.camadas import SwingCamadasInterceptoPorte
from projetor.models.features import REGIAO
from projetor.models.hierarquico import SwingHierarquico

RAIZ = Path(__file__).resolve().parents[1]
APP_DATA = RAIZ / "docs" / "data"
PROCESSED = RAIZ / "data" / "processed"
APP_DATA.mkdir(parents=True, exist_ok=True)

GRADE = np.unique(np.round(np.concatenate([np.arange(0.005, 0.05, 0.0025), np.arange(0.05, 0.996, 0.0125)]), 4))
CANDIDATOS = {
    2018: {"pt": "Haddad", "adversario": "Bolsonaro"},
    2022: {"pt": "Lula", "adversario": "Bolsonaro"},
    2026: {"pt": "Lula", "adversario": "Flávio Bolsonaro"},
}
ESCALA = "ruido"
NIVEIS = [0.9, 0.95]
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul", "Exterior"]


CALIBRACAO = [noites.carregar(a, tr) for a in (2018, 2022) for tr in (1, 2)] + [
    noites.governador(a, uf) for a in (2018, 2022) for uf in governador.ufs(a)
]


def c_do_erro_comum(ano: int) -> float:
    """`c` calibrado sem as disputas do 2º turno do próprio ano."""
    return noites.calibrar_c([n for n in CALIBRACAO if (n.ano, n.turno) != (ano, 2)], ESCALA)


for ano in [int(x) for x in sys.argv[1:]] or [2026, 2022, 2018]:
    secoes = anexar_historico(pd.read_parquet(DATA_INTERIM / f"ordem_{ano}_2t.parquet"), carregar_secoes(ANTERIOR[ano]))
    secoes["regiao"] = secoes["uf"].map(REGIAO)
    final = pct_pt(secoes)
    c = c_do_erro_comum(ano)
    modelos = {
        "apurado": Apurado(),
        "swing_uf": SwingUniformeUF(min_secoes=30),
        "camadas": SwingCamadasInterceptoPorte(k=30, min_locais=1000),
        "hierarquico": SwingHierarquico(verossimilhanca="t", incerteza_comparecimento=True),
    }
    pontos = []
    for t in GRADE:
        divulgadas, pendentes = dividir(secoes, float(t))
        validos = votos.validos(divulgadas)
        ponto = {
            "relogio": float(t),
            "secoes_pct": round(100 * len(divulgadas) / len(secoes), 3),
            "validos_pct": round(100 * validos.sum() / votos.validos(secoes).sum(), 3),
            "horario": divulgadas["momento"].max().strftime("%H:%M") if "momento" in divulgadas else None,
            "regioes": {
                r: round(100 * v, 2)
                for r, v in (validos.groupby(divulgadas["regiao"]).sum() / validos.sum()).reindex(REGIOES, fill_value=0).items()
            },
        }
        for nome, modelo in modelos.items():
            ponto[nome] = round(modelo.projetar(divulgadas, pendentes), 3)
        hier = modelos["hierarquico"]
        r = hier.ultimo_resumo
        perfil = Perfil(r["fracao_pendente"], r["distancia"], r["sigma"])
        amostras = discrepancia.aplicar(hier.ultimas_amostras[None, :], [perfil], c, ESCALA, semente=1)[0]
        for nivel in NIVEIS:
            a = (1 - nivel) / 2
            ponto[f"faixa{int(100 * nivel)}"] = [round(float(np.quantile(amostras, q)), 3) for q in (a, 1 - a)]
        pontos.append(ponto)
        print(ano, t, ponto["hierarquico"] - final, flush=True)

    saida = {
        "ano": ano,
        "turno": 2,
        "candidatos": CANDIDATOS[ano],
        "final_pt": round(final, 3),
        "ordem": "simulada a partir de 2022" if ano == 2018 else "observada (DT_BU_RECEBIDO)",
        "historico": ANTERIOR[ano],
        "faixa": {"metodo": "hierárquico-t com erro comum às pendentes (escala de ruído)", "c": round(c, 3)},
        "pontos": pontos,
    }
    (APP_DATA / f"replay_{ano}.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
