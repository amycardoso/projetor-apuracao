# projetor-apuracao

**Quão boas são as projeções de apuração em tempo real no Brasil, e as faixas de incerteza delas são honestas?** Este repositório responde com um backtest sem vazamento em seis noites presidenciais (2018 a 2026) e 26 noites de governador, só com os boletins de urna do TSE.

**[Abrir o replay interativo](https://amycardoso.github.io/projetor-apuracao/)**

**[Ler a análise em notebook](notebooks/analise.ipynb)**: o problema, o swing por região, a evolução dos modelos, as faixas e 2026, com os gráficos.

[![Replay da apuração de 2026](reports/figures/05_replay.png)](https://amycardoso.github.io/projetor-apuracao/)

Entre 19h44 e 20h23 de 25/10/2026, depois de uma pausa na divulgação, o apurado do 2º turno mostrou Flávio Bolsonaro na frente. A curva reconstruída dos boletins difere da do TSE publicada pelo g1 em no máximo 0,02 ponto em cada marca de 10% das urnas. O projetor, congelado com o que aprendeu em 2018 e 2022, ficou entre 51,6% e 51,9% para Lula a noite inteira. O final foi 51,79%, e o limite inferior da faixa de 90% nunca desceu de 50,3%.

## O que este projeto acrescenta

O modelo de swing por local de votação em camadas, como o de Rodrigo Mahlmeister em 2026 e os do Washington Post e do NYT, é uma das referências comparadas aqui, não o objetivo. As contribuições próprias:

1. **Backtest sem vazamento** em seis noites presidenciais (1º e 2º turnos de 2018, 2022 e 2026, com históricos desde 2014) e 26 de governador. A ordem de chegada é reconstruída pelo `DT_BU_RECEBIDO`, com tratamento de fuso. As seções pendentes só levam o que se sabe antes da noite.
2. **Pooling aprendido contra pesos escolhidos à mão.** Um hierárquico bayesiano com Student-t contra o modelo em camadas, com as noites em que cada um ganha.
3. **Auditoria das faixas.** As faixas que saem só do modelo cobrem de 18% a 45% quando prometem 90%. Um erro comum às seções pendentes, que cresce quando o histórico explica pouco do swing já divulgado e é calibrado em outras noites, corrige isso.
4. **Nenhuma pesquisa eleitoral.** Só boletins de urna e a eleição anterior.
5. **Teste congelado em 2026**, comparado com os números públicos de Rodrigo.

## Resultados

Erro absoluto médio do % do PT nos válidos (pontos percentuais), em 22 instantes de 0,5% a 95% das seções. As noites de 2026 usam os modelos congelados.

| Noite | Apurado | Swing por UF | Camadas | Hierárquico-t |
|---|---|---|---|---|
| 2018, 2º turno | 2,47 | 0,51 | **0,22** | 0,37 |
| 2022, 2º turno | 2,19 | 0,41 | 0,32 | **0,14** |
| 2018, 1º turno | 4,69 | **0,25** | 0,50 | 0,51 |
| 2022, 1º turno | 4,11 | 0,75 | 0,43 | **0,18** |
| 2026, 1º turno | 2,99 | 0,33 | 0,18 | **0,17** |
| 2026, 2º turno | 1,31 | 0,18 | 0,12 | **0,07** |

Cobertura da faixa de 90%, com a largura média em pontos entre parênteses. As noites de 2018 e 2022 são avaliadas deixando a data de fora da calibração; as de 2026 usam a calibração congelada.

| Faixa | 4 noites presidenciais, 2018–2022 | 26 noites de governador | 3 noites de 2026 |
|---|---|---|---|
| Posterior do hierárquico, como sai do modelo | 41% (0,6) | 65% (2,6) | 62% (0,3) |
| Posterior recalibrada por um multiplicador conformal | 80% (1,5) | 93% (6,3) | 95% (0,8) |
| **Posterior com erro comum na escala de ruído** | **99% (2,2)** | **82% (3,5)** | **100% (1,3)** |

A faixa com erro comum é a única que não falha em nenhuma noite presidencial; a recalibrada cobre 27% em 2018 1T. O custo é largura nas noites fáceis, como 2026.

Comparação com os números públicos de Rodrigo, no mesmo % de seções:

| Instante | Rodrigo | Este projeto (faixa de 95%) | Final |
|---|---|---|---|
| 2026 1T, 2,2%: Flávio | 47,01 | 46,51 (45,1–47,9) | 47,03 |
| 2026 1T, 2,2%: Lula | 45,50 | 45,90 (44,3–47,5) | 45,16 |
| 2026 2T, 2,42%: Lula | 51,6 (50,8–52,2) | 51,71 (50,4–53,1) | 51,79 |

No 1º turno, o modelo de Rodrigo acertou melhor naquele instante. O modelo em camadas daqui dava Lula 45,48, quase o número dele; a vantagem dele em Flávio é compatível com o ponto de partida que veio de uma pesquisa. A discussão completa está no [artigo](reports/artigo.md).

## Inspiração e créditos

- **Rodrigo Mahlmeister** ([@ro_mahl](https://x.com/ro_mahl)) e o modelo de projeção de apuração que ele publicou nas eleições de 2026, descrito pela [reportagem da NeoFeed](https://neofeed.com.br/finde/como-um-pesquisador-brasileiro-criou-um-algoritmo-que-simulou-e-acertou-o-resultado-do-1o-turno/). Vêm dele as ideias de projetar o swing de cada local de votação contra a eleição anterior e de mostrar projeção, faixa e apurado lado a lado. Este projeto é uma reimplementação independente, feita a partir da descrição pública do método; o código de Rodrigo é privado e não foi usado.
- **Referências técnicas:** o modelo de noite eleitoral do Washington Post ([washingtonpost/elex-live-model](https://github.com/washingtonpost/elex-live-model)) e J. J. Cherian, L. Bronner e E. J. Candès, *Election modeling in 2024: a conformal inference approach*, relatório técnico do Washington Post (2024).
- **Dados:** boletins de urna do [Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/), dados públicos.

## Relatórios

| | |
|---|---|
| [Artigo](reports/artigo.md) | O texto completo: problema, dados, backtest, modelos, faixas e limitações |
| [00 — Quem chega primeiro](reports/00_quem_chega_primeiro.md) | Viés da ordem de apuração por região, porte e capital; swing local 2018→2022 |
| [01 — Baselines](reports/01_baselines.md) | Apurado, swing uniforme e swing por UF |
| [02 — Regressões de swing](reports/02_ols.md) | WLS por local e camadas com encolhimento; escolha de k em 2018 |
| [03 — Hierárquico](reports/03_hierarquico.md) | Pooling aprendido em PyMC; ADVI contra NUTS |
| [04 — Faixas](reports/04_intervalos.md) | Cinco métodos de faixa, cobertura e interval score |
| [06 — Melhorias](reports/06_melhorias.md) | 1º turno de 2018 e 2022; erro comum às pendentes, avaliado em leave-one-night-out |
| [07 — Governador](reports/07_governador.md) | 26 noites de governador; erro comum que cresce com o ruído do swing |
| [07 — Eleição de 2026](reports/07_eleicao_2026.md) | Teste congelado em 2026 e comparação com Rodrigo Mahlmeister |

## Replay interativo

`docs/` é uma página estática, sem build, publicada em https://amycardoso.github.io/projetor-apuracao/, que reproduz a noite com um relógio, cartões por candidato e o gráfico do apurado contra a projeção. Ela lê só agregados nacionais (`docs/data/replay_{ano}.json`, alguns KB), nada por seção.

Para abrir localmente:

```bash
python -m http.server 8000 --directory docs
```

Ela também funciona no celular ([screenshot](reports/figures/05_replay_celular.png)). Depois de subir o servidor, abra http://localhost:8000. Um link como http://localhost:8000/#t=10 abre a noite com 10% das seções divulgadas.

## Como reproduzir

Requer Python 3.11 ou mais novo e cerca de 1 GB livre: 180 MB de zips do TSE e a venv com PyMC.

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

```bash
.venv/bin/python -m projetor.ingest --anos 2014 2018 2022 --turno 2
```

```bash
.venv/bin/python -m projetor.locais
```

```bash
.venv/bin/python -m projetor.ordem
```

Para o 1º turno (~1,3 GB de zips por ano, apagados depois de virar parquet):

```bash
.venv/bin/python -m projetor.ingest --anos 2014 2018 2022 --turno 1
```

```bash
.venv/bin/python -m projetor.ordem --turno 1
```

Para 2026 e para as noites de governador:

```bash
.venv/bin/python -m projetor.ingest --anos 2026 --turno 2
```

```bash
.venv/bin/python -m projetor.ordem --ano 2026 --turno 2
```

```bash
.venv/bin/python -m projetor.governador --anos 2018 2022
```

```bash
.venv/bin/pytest
```

Os relatórios saem dos scripts em `notebooks/`, rodados da raiz do repositório, em ordem:

- `00_quem_chega_primeiro.py`
- `01_baselines.py`
- `02_ols.py`
- `03_hierarquico.py`
- `04a_amostras_hierarquico.py` (~30 min)
- `04b_faixas_camadas.py` (~40 min)
- `04_intervalos.py`
- `05_exportar_app.py` (~1 h)
- `06a_primeiro_turno.py` (~1 h)
- `06_melhorias.py`
- `07b_governador.py` (~1 h) e `07_governador.py`
- `07a_eleicao_2026.py` (~1 h) e `07_eleicao_2026.py`

O que é pesado vai para `data/`, que não é versionado.

## Estrutura

```
src/projetor/
  ingest.py        baixa os BUs do TSE (com hash), normaliza e agrega Presidente por seção
  tempo.py         fusos: encerramento em hora local, recebimento em hora de Brasília
  locais.py        pareia locais de votação entre eleições
  ordem.py         relógio de chegada: observado em 2022, simulado em 2018
  historico.py     resultado da eleição anterior por local, com fallback por zona/município/UF
  replay.py        estado da apuração num instante, sem vazamento
  backtest.py      simulador da noite: pendentes só com covariáveis permitidas
  votos.py         válidos (inclui outros candidatos no 1º turno) e troca de alvo
  governador.py    2º turnos de governador como noites extras, com o 1º turno como histórico
  noites.py        noites já rodadas, para calibrar o erro comum e a faixa recalibrada
  intervals.py     faixas analítica, bootstrap, posterior, conformal e recalibrada
  discrepancia.py  erro comum às pendentes: perfil da noite, calibração e aplicação
  models/
    baseline.py    Apurado, SwingUniforme, SwingUniformeUF
    ols.py         SwingOLS
    camadas.py     SwingCamadas e variantes com encolhimento por nível
    hierarquico.py SwingHierarquico (PyMC, normal ou Student-t)
notebooks/         scripts que geram cada relatório
reports/           relatórios, artigo e figuras
docs/              replay interativo estático (publicado pelo GitHub Pages)
tests/             testes, inclusive os de não vazamento
```

## Dados

Boletins de urna do portal de dados abertos do TSE (`dadosabertos.tse.jus.br`), datasets `resultados-{2014,2018,2022,2026}-boletim-de-urna`, 1º e 2º turnos, 27 UFs e exterior. Os votos do PT e do adversário batem voto a voto com o resultado oficial nos seis pleitos. A única diferença está nos válidos do 1º turno de 2018, 746 votos (0,0007%) a mais.

## Licença

O código está sob a [licença MIT](LICENSE). Os dados não são redistribuídos: o repositório só traz agregados nacionais em `docs/data/`, e os boletins de urna são baixados do TSE pelo próprio pipeline.
