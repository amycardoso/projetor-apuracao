# projetor-apuracao

Projeta o resultado final da eleição presidencial brasileira a partir da apuração parcial divulgada pelo TSE.

A cada instante da apuração, o modelo usa as seções já totalizadas para estimar o placar final e um intervalo de confiança para cada candidato. As seções que ainda faltam diferem das já apuradas (região, porte do município, horário de envio), e o modelo precisa corrigir esse viés.

## Objetivos

- Projetar o percentual final de votos válidos de cada candidato durante a apuração.
- Fazer backtest nas eleições de 2018 e 2022, reconstruindo a ordem de chegada das seções a partir dos boletins de urna.
- Entregar intervalos calibrados: um intervalo de 90% deve conter o resultado final em cerca de 90% dos instantes testados.

## Status

- **Fase 1 (baselines, 2º turno):** com histórico de 2018, o swing uniforme por UF erra 0,41 p.p. em média em 2022 e fica abaixo de 0,5 p.p. a partir de 5% das seções. Em 2018 (ordem simulada, histórico de 2014), o melhor baseline é o swing nacional: 0,27 p.p. em média. Ver `reports/01_baselines.md`.
- **Fase 2 (regressões de swing, 2º turno):** a regressão nacional com deslocamentos encolhidos por região, UF e UF × capital/interior (`SwingCamadasInterceptoPorte`, k escolhido em 2018) erra 0,32 p.p. em média em 2022 e fica abaixo de 0,5 p.p. a partir de 1% das seções. Em 2018, erra 0,22. Ver `reports/02_ols.md`.
- **Fase 3 (hierárquico bayesiano, 2º turno):** com o pooling aprendido em PyMC (`SwingHierarquico`), o erro médio de 2022 cai para 0,15 p.p. (contra 0,32 dos pesos à mão), mas 2018 piora para 0,41 (contra 0,22), e os intervalos de 90% ainda ficam estreitos demais. Ver `reports/03_hierarquico.md`.
- **Fase 4 (faixas, 2º turno):** a verossimilhança Student-t melhora o hierárquico nos dois anos (2022: 0,14 p.p.; 2018: 0,37). As faixas só do modelo (analítica, bootstrap e posterior) cobrem só 18–45% e estão estreitas demais. A posterior recalibrada pelo conformal do outro ano cobre 100% em 2022 e 86% em 2018, com o melhor interval score. Ver `reports/04_intervalos.md`.

## Dados

Os dados vêm do portal de dados abertos do TSE (`dadosabertos.tse.jus.br`). Tudo fica em `data/`, que não é versionado.

### Fontes

| Ano | Dataset CKAN | Arquivos |
|-----|--------------|----------|
| 2018 | `resultados-2018-boletim-de-urna` | `BWEB_{1,2}t_{UF}_*.zip` |
| 2022 | `resultados-2022-boletim-de-urna` | `bweb_{1,2}t_{UF}_*.zip` |

São 27 UFs mais `ZZ` (exterior), com um `.sha512` ao lado de cada zip. Cada zip traz um CSV em latin-1, separado por `;`, com uma linha por seção × cargo × votável.

O tamanho compactado de todas as UFs é:

| Ano | 1º turno | 2º turno |
|-----|----------|----------|
| 2018 | 1.333 MiB | 71 MiB |
| 2022 | 1.390 MiB | 66 MiB |

Descompactado, o CSV ocupa cerca de 20 vezes o zip (só o de SP no 2º turno tem 380 MB). Por isso a ingestão extrai um CSV por vez e apaga cada um depois de processar.

### Pipeline

```bash
python -m projetor.ingest --anos 2018 2022 --turno 2
```

- Baixa os zips para `data/raw/`, com cache e verificação do sha512.
- Corrige o cabeçalho, que muda entre anos: `SG_ UF` e `CD_FLASCARD_URNA_EFETIVADA` em 2018.
- Grava `data/interim/bu_{ano}_{turno}t.parquet` só com Presidente, uma linha por seção.
- Os votos ficam em formato largo: `votos_pt` (NR 13), `votos_adversario` (NR 17 em 2018, 22 em 2022), `votos_branco` e `votos_nulo`.

### Ordem de chegada das seções

O projetor precisa saber em que ordem as seções entraram na totalização.

**2022.** A ordem vem de `DT_BU_RECEBIDO`, que já está em hora de Brasília em todas as UFs. `DT_ENCERRAMENTO` está em hora local. O exterior recebe BUs desde a madrugada, mas o resultado só foi divulgado a partir das 17h de Brasília. Os detalhes estão em `src/projetor/tempo.py`.

**2018.** O BU de 2018 não tem `DT_BU_RECEBIDO` nem `DT_EMISSAO_BU`. A regra planejada é herdar a ordem de 2022 por local de votação:

1. Cada seção de 2018 recebe a posição relativa (percentil de chegada) do mesmo local de votação (município + zona + local) em 2022.
2. Se o local não tiver par em 2022, usa a zona.
3. Se a zona também não tiver par, usa o município.

Em 2018 cada UF votou no horário local. Assim, AC e o oeste do AM fecharam às 19h de Brasília, e a curva de chegada precisa levar isso em conta.
