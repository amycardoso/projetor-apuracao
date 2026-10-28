# Quem chega primeiro engana: projetando o resultado do 2º turno a partir da apuração parcial

Às 18h da noite de 30 de outubro de 2022, com 29% das seções divulgadas, Lula tinha 48,9% dos votos válidos. Às 18h45, com quase 69% das seções, passou de 50%, e terminou com 50,90%. Quem olhava só o apurado viu uma virada. Não houve virada. A vitória já estava nos números desde as primeiras seções, mas as seções não chegam em ordem aleatória, e o apurado é uma média ponderada de quem chegou primeiro.

Este projeto tenta responder a uma pergunta simples: a cada instante da apuração, o que dá para dizer sobre o resultado final, e com que confiança? A resposta vem em duas partes. A primeira é uma projeção pontual do % do PT nos votos válidos. A segunda é uma faixa que promete conter o resultado final 90% ou 95% das vezes e cumpre essa promessa. A segunda foi bem mais difícil que a primeira.

## O problema: a ordem da apuração não é aleatória

Os boletins de urna (BU) de 2022 trazem, para cada seção, o horário em que o boletim chegou ao sistema de totalização (`DT_BU_RECEBIDO`). Com esse campo dá para reconstruir a noite seção por seção. A primeira coisa que aparece é que a ordem tem geografia.

![Composição regional dos válidos já divulgados, 2022](figures/00_composicao_regiao_2022.png)

Até 10% das seções divulgadas, o Centro-Oeste pesava 3,4 vezes mais do que pesa no total, e o Norte 3,0 vezes. O Sudeste, com 42% dos votos válidos do país, era só 10,7% do que tinha sido apurado. As capitais chegaram adiantadas (1,9 vez o seu peso), e o interior atrasado. Como Lula teve 69% dos válidos no Nordeste e 46% no Sudeste, essa ordem decide para onde a parcial pende.

![Parcial do PT contra % apurado](figures/00_parcial_pt_vs_apurado.png)

Com 5% das seções, a parcial de Lula estava 4,3 pontos abaixo do resultado final. Com 50%, ainda 1,2 ponto abaixo. Um bom projetor precisa corrigir esse viés olhando para as seções que faltam, e não só para as que chegaram.

## Inspiração

A forma do modelo e da apresentação vem do modelo de projeção de apuração de Rodrigo Mahlmeister, de 2026. Duas ideias vieram de lá: projetar o swing de cada local de votação contra a eleição anterior e mostrar, para cada candidato, a projeção, a faixa e o apurado lado a lado. O que este repositório acrescenta é um backtest sistemático, sem vazamento, em duas eleições, uma progressão explícita de modelos e uma avaliação séria da calibração das faixas. Os erros e as escolhas daqui são meus, não dele.

## Dados

Tudo vem do portal de dados abertos do TSE: os boletins de urna por seção do 2º turno de 2014, 2018 e 2022, para as 27 UFs e o exterior. São cerca de 180 MB de zips. Depois de agregar só a votação para presidente, sobra uma linha por seção, com município, zona, local de votação, aptos, comparecimento e votos do PT, do adversário, brancos e nulos. Os totais batem voto a voto com o resultado oficial nos três anos: 2014 (Dilma 54.501.118), 2018 (Haddad 47.040.906 e Bolsonaro 57.797.847) e 2022 (Lula 60.345.999 e Bolsonaro 58.206.354).

Há três cuidados que não aparecem à primeira vista.

- **Fusos.** `DT_ENCERRAMENTO` está em hora local; em 2022, Acre fechou às 15h e Fernando de Noronha às 18h. Já `DT_BU_RECEBIDO` vem em hora de Brasília em todas as UFs. O exterior recebe boletins desde a madrugada, mas o resultado só foi divulgado a partir das 17h.
- **2018 não tem horário de recebimento.** O BU de 2018 traz só abertura e encerramento. A ordem de 2018 é, portanto, simulada: cada seção herda a distribuição de chegada do mesmo local de votação em 2022 e, na falta dele, da zona, do município ou da UF. O backtest de 2018 mede o modelo sob a ordem de 2022, não sob a ordem real daquela noite.
- **Locais mudam de número.** Para comparar com a eleição anterior, os locais de votação foram pareados pela chave município + zona + local: 94,3% com par direto de 2018 para 2022, 0,7% por rezoneamento e o resto por zona ou município.

## Um backtest que não deixa o futuro vazar

O simulador percorre uma grade de 22 instantes do relógio (de 0,5% a 95% das seções). Em cada instante, o modelo recebe dois conjuntos.

- As seções **divulgadas**, com tudo, inclusive os votos da noite.
- As seções **pendentes**, só com identificadores, eleitores aptos e o resultado da eleição anterior no local equivalente. Votos, comparecimento, horários e a própria posição no relógio ficam de fora.

Um teste automatizado garante isso para todos os modelos. Ele zera os votos do PT e põe 999 votos no adversário em todas as seções futuras, e a projeção precisa sair idêntica. As métricas são o erro absoluto do % do PT final em cada instante, a média desses erros e o "tempo até cravar": o primeiro instante a partir do qual o erro fica abaixo de 0,5 ponto e não sai mais.

Há dois backtests: 2022 com histórico de 2018 e 2018 com histórico de 2014. Todo hiperparâmetro foi escolhido em 2018 e só depois aplicado em 2022.

## A progressão de modelos

**Baselines.** O primeiro modelo é o próprio apurado. O segundo aplica às pendentes o swing médio das seções divulgadas contra a eleição anterior (swing uniforme). O terceiro faz o mesmo com um swing por UF.

**Regressões.** A fase 2 ajusta, a cada instante, uma regressão ponderada do swing por local contra o voto anterior, o tamanho do município e uma dummy de capital. A regressão nacional sozinha subestimou Lula em cerca de 1 ponto entre 5% e 10% das seções. Com essas covariáveis, ela não enxerga que o swing do Sudeste (+10,8 pontos) foi muito maior que o do Nordeste (−0,3). O que funcionou foi manter a regressão no nível nacional e estimar só deslocamentos por região, UF e UF × capital/interior, cada um encolhido para o nível de cima com peso n/(n + k). O k = 30 foi escolhido em 2018.

**Hierárquico bayesiano.** A fase 3 troca o k escolhido à mão por pooling aprendido. É o mesmo swing por local, com efeitos de região, UF e UF × capital/interior, e desvios entre grupos estimados pelos dados, em PyMC com inferência variacional. A fase 4 trocou a verossimilhança normal por uma Student-t (ν aprendido ≈ 3 a 4), mais robusta a locais com swing extremo.

| Modelo | 2022: erro médio | 2022: fica abaixo de 0,5 a partir de | 2018: erro médio |
|---|---|---|---|
| Apurado | 2,19 | 85% | 2,47 |
| Swing uniforme | 0,77 | 50% | 0,27 |
| Swing por UF | 0,41 | 5% | 0,51 |
| Regressão nacional | 0,70 | 45% | 0,46 |
| Camadas com deslocamentos e UF × capital | 0,32 | 1% | **0,22** |
| Hierárquico (normal) | 0,15 | 1% | 0,41 |
| **Hierárquico (Student-t)** | **0,14** | **0,5%** | 0,37 |

*Erros em pontos percentuais do % do PT nos válidos, médias sobre os 22 instantes.*

![Erro contra % apurado, hierárquico](figures/03_erro_vs_apurado.png)

Em 2022, o hierárquico com verossimilhança normal (o da figura) erra 1,6 ponto com 0,5% das seções e fica em 0,2 ou menos a partir de 1%. Com a Student-t, o erro com 0,5% cai para 0,4 e não passa de 0,3 depois. Os modelos com limiar mínimo de locais ainda estão no swing uniforme nesse ponto e erram 4,9. Em 2018, o modelo em camadas vence. Parte da explicação é honesta e desconfortável: o k dele foi escolhido justamente em 2018. A outra parte está nos dados. O swing de 2014 para 2018 foi muito mais disperso que o de 2018 para 2022, com ruído local de 7,2 pontos contra 3,5. O desvio entre capital e interior dentro da mesma UF foi de 4,9 pontos, contra 1,5. Bolsonaro cresceu muito mais nas cidades grandes, e as cidades grandes chegam cedo.

## As faixas, e por que as de modelo falham

Uma projeção sem faixa convida a uma falsa precisão. A fase 4 comparou cinco formas de construir faixas de 90% e 95%.

- (a) Erro de previsão analítico do modelo em camadas.
- (b) Bootstrap preditivo por local.
- (c) Posterior do hierárquico.
- (d) Conformal: o quantil do erro do modelo pontual na outra eleição, por faixa do relógio.
- (e) Posterior recalibrada: o desvio de (c) multiplicado pelo quantil de |erro|/desvio na outra eleição.

As três primeiras incluem a incerteza do comparecimento de cada local pendente.

| Método | 2022: cobertura 90% | 2022: Winkler | 2018: cobertura 90% | 2018: Winkler |
|---|---|---|---|---|
| (a) analítico | 27% | 5,00 | 36% | 1,93 |
| (b) bootstrap | 18% | 5,34 | 41% | 4,23 |
| (c) posterior | 18% | 1,10 | 45% | 2,81 |
| (d) conformal | 95% | 4,18 | 64% | 2,49 |
| **(e) posterior recalibrada** | **100%** | **1,10** | **86%** | **2,34** |

![Cobertura nominal contra empírica](figures/04_cobertura.png)

As faixas que vêm só do modelo cobrem de 18% a 45% quando prometem 90%. Isso não pede ajuste fino; mostra que falta algo no modelo. O diagnóstico é o mesmo para (a), (b) e (c). Os três tratam o erro de cada local pendente como independente, então a incerteza total encolhe com a raiz do número de locais que faltam. O erro real tem um componente comum: as seções pendentes diferem das divulgadas de um jeito que as covariáveis não capturam, e esse desvio não se dilui. Em 2022, o erro do hierárquico ficou em cerca de três desvios posteriores de 30% a 95% das seções, quase constante. Incluir a incerteza do comparecimento quase não mudou a largura.

O conformal puro (d) resolve 2022, mas falha em 2018. Cada direção é calibrada por uma única noite, e os erros de 2022 foram menores que os de 2018. A posterior recalibrada (e) junta o melhor dos dois. A forma da faixa vem do modelo: larga quando falta muito, estreita no fim. A escala vem da outra eleição. Ela teve o menor interval score nos dois anos e é a faixa que o replay mostra.

![Projeção e faixas ao longo da apuração de 2022](figures/04_faixa_2022.png)

## Duas noites a mais e o erro comum

Para testar o diagnóstico acima, o projetor foi levado ao 1º turno de 2018 e 2022. Não foi preciso um modelo multinomial. O alvo continua sendo o % de um candidato nos válidos, que agora incluem os demais candidatos. Os totais do BU batem voto a voto com o oficial para PT e adversário nos três anos. Em 2022 1T, o hierárquico-t erra 0,18 ponto em média para Lula e 0,14 para Bolsonaro. Em 2018 1T, perde para o swing por UF (0,51 contra 0,25 para Haddad). A troca de Dilma por Haddad mudou o voto do PT de um jeito que a eleição anterior explica mal.

O hierárquico ganhou o termo que faltava: um erro `delta ~ Normal(0, c)` somado ao swing de todas as pendentes, que desloca o total em proporção à fração que falta. Como esse erro não é observável durante a noite, `c` é calibrado nas outras noites, em leave-one-night-out nas quatro noites do PT. Com isso, a cobertura de 90% da posterior subiu de 41% para 75%, e o interval score ficou o melhor entre os métodos, com faixas quase com a metade da largura das de (e). O nominal não foi alcançado. Três noites ficam entre 86% e 100%, mas 2018 1T, a noite fora do padrão, fica em 14%. Nenhuma calibração feita em outras noites resolve isso. O `c` das quatro noites é 0,56 ponto de swing. Medir a distância de composição entre divulgadas e pendentes não ajudou. Os detalhes estão no relatório 06.

## Limitações

- **A ordem de 2018 é simulada a partir da de 2022.** Isso também significa que, ao escolher hiperparâmetros em 2018, o modelo já viu a ordem de chegada de 2022, embora não os votos. O teste de 2022 está fora da amostra de votos, mas não é cego.
- **Há poucas noites.** São quatro noites (1º e 2º turnos de 2018 e 2022), cada uma com 22 instantes fortemente correlacionados. As coberturas têm poucos graus de liberdade efetivos, e uma noite fora do padrão pesa muito na calibração.
- **Um candidato por vez.** No 1º turno, cada candidato é projetado separadamente. Nada garante que as projeções somem 100%.
- **O comparecimento é tratado de forma simples.** Os válidos esperados de uma seção pendente vêm da taxa de válidos da eleição anterior, e a incerteza sobre eles é um ruído independente por local.
- **O exterior é tratado de forma grosseira.** Cidades do exterior entram como municípios, sem fuso próprio no relógio de 2018.

## Próximos passos

1. **Mais noites de calibração.** Os 2º turnos de governador dariam várias noites, e o `c` do erro comum deixaria de depender de quatro observações.
2. **Erro comum que dependa da noite.** Por exemplo, maior quando o histórico explica pouco do swing já divulgado, que é o sinal de 2018 1T.
3. **Ordem real de 2018.** Os arquivos de log das urnas ou snapshots da divulgação daquela noite substituiriam a simulação.
4. **Operação ao vivo.** O hierárquico leva cerca de 15 segundos por atualização com ADVI. Isso cabe numa noite real, com atualizações a cada poucos minutos, consumindo a API de divulgação do TSE em vez dos boletins consolidados.

O código, os relatórios de cada fase (`reports/00` a `reports/06`) e o replay interativo estão no repositório. Os números deste texto saem dos scripts em `notebooks/`, rodados sobre os dados públicos do TSE.
