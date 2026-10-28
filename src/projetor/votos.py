"""Votos válidos e troca de candidato-alvo.

No 2º turno os válidos são PT + adversário. No 1º turno também entram os
votos de todos os outros candidatos (`votos_outros`), e o alvo continua sendo
o % de um candidato nos válidos. No 2º turno `votos_outros` é sempre zero
(o ingest confere), então a mesma conta serve aos dois turnos.
"""

from __future__ import annotations

import pandas as pd


def validos(secoes: pd.DataFrame) -> pd.Series:
    """Votos válidos por seção: PT + adversário + outros candidatos."""
    total = secoes["votos_pt"] + secoes["votos_adversario"]
    return total + secoes["votos_outros"] if "votos_outros" in secoes else total


def trocar_alvo(secoes: pd.DataFrame) -> pd.DataFrame:
    """Troca PT e adversário, para projetar o % do adversário com os mesmos modelos."""
    return secoes.rename(columns={"votos_pt": "votos_adversario", "votos_adversario": "votos_pt"})
