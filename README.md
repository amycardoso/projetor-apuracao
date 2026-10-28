# projetor-apuracao

Projeta o resultado final da eleição presidencial brasileira a partir da apuração parcial divulgada pelo TSE.

A cada instante da apuração, o modelo usa as seções já totalizadas para estimar o placar final e um intervalo de confiança para cada candidato. As seções que ainda faltam diferem das já apuradas (região, porte do município, horário de envio), e o modelo precisa corrigir esse viés.

## Objetivos

- Projetar o percentual final de votos válidos de cada candidato durante a apuração.
- Fazer backtest nas eleições de 2018 e 2022, reconstruindo a ordem de chegada das seções a partir dos boletins de urna.
- Entregar intervalos calibrados: um intervalo de 90% deve conter o resultado final em cerca de 90% dos instantes testados.

## Dados

Boletins de urna por seção, do portal de dados abertos do TSE (`dadosabertos.tse.jus.br`). Os dados brutos ficam em `data/` e não são versionados.
