"""Fusos horários dos campos de data do BU.

Conclusão da verificação no 2º turno de 2022 (bu_2022_2t.parquet):

- DT_ENCERRAMENTO está em hora LOCAL. Mediana por UF: 15:01 no AC, 16:01 em
  MS/MT/RO/RR, 16:02 no AM, 17:01 nas UFs de Brasília e 18:02 em Fernando de
  Noronha. No AM há 11 municípios (Tabatinga, Eirunepé, Benjamin Constant…)
  com mediana de 15:01, porque seguem o fuso do Acre. No exterior (ZZ) a
  mediana é 17:0x em cada cidade, na hora do país: o exterior votou no
  horário local, então ali o encerramento não revela o fuso.
- DT_BU_RECEBIDO já está em hora de BRASÍLIA. Em todas as UFs o primeiro
  recebimento é 17:01 ou mais tarde, inclusive AC, AM, MT, RO e RR, que
  encerraram às 15h/16h locais. Nenhuma seção dessas UFs foi recebida antes do
  próprio encerramento. No exterior, a conta só fecha em Brasília: Wellington
  encerrou às 17h locais (01h de Brasília) e o primeiro BU chegou às 01:20,
  Sydney às 03:24 e Tóquio às 07:20.
- Em 2018 cada UF votou das 8h às 17h no horário local (o DT_ENCERRAMENTO
  tem mediana 17:0x em todas as UFs). Assim, o AC encerrou às 19h de Brasília.
  Como 2018 não tem DT_BU_RECEBIDO, a hora local de encerramento é convertida
  com o deslocamento de cada município medido em 2022.

Não houve horário de verão em nenhum dos pleitos (7 e 28/10/2018, 2 e
30/10/2022), então Brasília é UTC-3 nos dois. No exterior o deslocamento de
2022 pode errar por 1h em 2018 nos países que mudaram de horário de verão
entre as duas datas.
"""

from __future__ import annotations

import pandas as pd

FUSO_BRASILIA = "America/Sao_Paulo"

# Horário de encerramento oficial, em hora de Brasília (2022) ou local (2018).
HORA_ENCERRAMENTO = 17

# A divulgação começou às 17h de Brasília em 2022 (horário unificado) e às 19h
# em 2018, quando o Acre fechou as urnas (hora de 2018 ainda a confirmar em
# fonte do TSE). BUs recebidos antes disso, como os do
# exterior, só entram no resultado público nesse instante.
# Chave: (ano, turno). O 1º turno seguiu as mesmas regras de horário.
INICIO_DIVULGACAO = {
    (2018, 1): pd.Timestamp("2018-10-07 19:00", tz=FUSO_BRASILIA),
    (2018, 2): pd.Timestamp("2018-10-28 19:00", tz=FUSO_BRASILIA),
    (2022, 1): pd.Timestamp("2022-10-02 17:00", tz=FUSO_BRASILIA),
    (2022, 2): pd.Timestamp("2022-10-30 17:00", tz=FUSO_BRASILIA),
}


def deslocamento_por_municipio(secoes_2022: pd.DataFrame) -> pd.Series:
    """Horas a somar à hora local de cada município para obter hora de Brasília.

    Calculado em 2022, quando o encerramento foi às 17h de Brasília em todo o
    país: um município cuja mediana de encerramento é 15h local está 2h atrás.
    O exterior fica de fora, porque votou no horário local.
    """
    brasil = secoes_2022[secoes_2022["uf"] != "ZZ"]
    hora_local = brasil["dt_encerramento"].dt.hour + brasil["dt_encerramento"].dt.minute / 60
    mediana = hora_local.groupby(brasil["cd_municipio"]).median().dropna()
    return (HORA_ENCERRAMENTO - mediana).round().astype(int).rename("deslocamento_h")


def recebido_em_brasilia(secoes: pd.DataFrame) -> pd.Series:
    """DT_BU_RECEBIDO com fuso explícito. O campo já vem em hora de Brasília."""
    return secoes["dt_bu_recebido"].dt.tz_localize(FUSO_BRASILIA)


def encerramento_em_brasilia(secoes: pd.DataFrame, deslocamento: pd.Series) -> pd.Series:
    """Converte DT_ENCERRAMENTO (hora local) para hora de Brasília.

    Fica NaT no exterior, cujo fuso não é conhecido.
    """
    horas = secoes["cd_municipio"].map(deslocamento)
    sem_par = secoes.loc[horas.isna() & (secoes["uf"] != "ZZ") & secoes["dt_encerramento"].notna(), "cd_municipio"].unique()
    if len(sem_par):
        raise ValueError(f"{len(sem_par)} municípios sem deslocamento calculado, ex.: {sem_par[:5].tolist()}")
    return (secoes["dt_encerramento"] + pd.to_timedelta(horas, unit="h")).dt.tz_localize(FUSO_BRASILIA)


def momento_divulgacao(recebido: pd.Series, ano: int, turno: int = 2) -> pd.Series:
    """Instante em que a seção passa a contar no resultado público."""
    return recebido.clip(lower=INICIO_DIVULGACAO[(ano, turno)])
