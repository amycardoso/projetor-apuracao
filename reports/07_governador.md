# 07 — Governador: mais noites para calibrar o erro comum

Na fase 6, o erro comum às pendentes levou a cobertura de 90% de 41% para 75%, mas o `c` vinha de só quatro noites e falhava em 2018 1T. Aqui entram 26 noites de 2º turno de governador como calibração extra. Também testo se o erro comum deve crescer quando o histórico explica pouco do swing já divulgado.

Gerado por `notebooks/07b_governador.py` (backtest) e `notebooks/07_governador.py` (tabelas).

## As noites de governador

Cada UF com 2º turno de governador vira uma noite. São AM, AP, DF, MG, MS, PA, RJ, RN, RO, RR, RS, SC, SE, SP em 2018 e AL, AM, BA, ES, MS, PB, PE, RO, RS, SC, SE, SP em 2022. O alvo é o % do candidato de menor número entre os dois finalistas. O histórico é o 1º turno de governador do mesmo ano, nas mesmas seções, com o % desse candidato entre os dois. O 1º turno é público três semanas antes, então não vaza nada da noite. A ordem de chegada é a da noite presidencial do mesmo dia, restrita à UF; em 2018 ela é simulada. Os totais conferem com os resultados conhecidos, por exemplo Tarcísio com 55,27% em SP (2022) e Doria com 51,75% em SP (2018).

Essas noites são mais difíceis que as presidenciais. Do 1º para o 2º turno, os votos dos eliminados se redistribuem de forma desigual pelo estado. O erro de nível do swing é maior e muda de uma UF para outra.

Erro absoluto médio (p.p.) nos 22 pontos da grade. "Cravar" é o % de seções a partir do qual o hierárquico fica abaixo de 0,5 ponto até o fim. "Sigma médio" é o desvio posterior do swing de um local em torno do que o modelo explica.

|   ano | UF   |   final A |   Apurado |   SwingUniforme |   SwingHierarquico-t |   cravar (hier.) |   sigma médio |
|------:|:-----|----------:|----------:|----------------:|---------------------:|-----------------:|--------------:|
|  2018 | AM   |     41.5  |     3.2   |           4.441 |                2.207 |             80   |         4.981 |
|  2018 | AP   |     52.35 |     0.863 |           0.622 |                0.339 |             35   |         3.554 |
|  2018 | DF   |     69.79 |     1.686 |           0.159 |                0.294 |             10   |         2.291 |
|  2018 | MG   |     71.8  |     1.058 |           0.449 |                1.764 |             75   |         6.166 |
|  2018 | MS   |     47.65 |     0.212 |           1.032 |                0.585 |             25   |         4.343 |
|  2018 | PA   |     55.43 |     0.302 |           0.288 |                0.192 |             10   |         3.276 |
|  2018 | RJ   |     59.87 |     0.645 |           0.763 |                0.307 |             20   |         5.251 |
|  2018 | RN   |     42.4  |     1.536 |           0.453 |                0.78  |             75   |         3.61  |
|  2018 | RO   |     66.34 |     0.586 |           3.272 |                1.991 |             25   |         3.389 |
|  2018 | RR   |     53.34 |     2.791 |           0.848 |                0.468 |             40   |         5.306 |
|  2018 | RS   |     46.38 |     2.085 |           0.572 |                0.518 |             45   |         4.546 |
|  2018 | SC   |     71.09 |     1.151 |           1.859 |                0.842 |             75   |         5.566 |
|  2018 | SE   |     35.28 |     5.258 |           2.719 |                0.62  |             20   |         5.477 |
|  2018 | SP   |     48.25 |     1.606 |           1.099 |                1.388 |             80   |         5.88  |
|  2022 | AL   |     52.33 |     3.089 |           1.104 |                1.089 |             70   |         6.523 |
|  2022 | AM   |     43.35 |     2.36  |           0.902 |                0.966 |             45   |         3.34  |
|  2022 | BA   |     52.79 |     2.431 |           0.157 |                0.432 |             25   |         2.98  |
|  2022 | ES   |     46.2  |     0.446 |           0.151 |                0.317 |              2.5 |         2.192 |
|  2022 | MS   |     43.1  |     0.932 |           1.272 |                0.558 |             55   |         3.746 |
|  2022 | PB   |     52.51 |     1.54  |           0.594 |                1.127 |             75   |         4.894 |
|  2022 | PE   |     58.7  |     1.984 |           1.373 |                0.577 |             20   |         6.202 |
|  2022 | RO   |     47.53 |     3.347 |           1.201 |                0.651 |             55   |         2.959 |
|  2022 | RS   |     42.88 |     2.148 |           0.668 |                0.846 |             55   |         4.393 |
|  2022 | SC   |     29.31 |     0.934 |           0.439 |                0.27  |              5   |         2.521 |
|  2022 | SE   |     48.3  |     4.086 |           5.088 |                0.931 |             20   |         5.878 |
|  2022 | SP   |     55.27 |     1.836 |           0.326 |                0.098 |              0.5 |         1.295 |

O hierárquico tem o menor erro em 15 das 26 noites, o swing uniforme da UF em 9 e o próprio apurado em 2. Os piores casos (AM e RO em 2018, MG em 2018) são noites em que o swing do 1º para o 2º turno variou muito entre regiões do estado.

## Faixas, deixando uma data inteira de fora

Ao avaliar uma noite, o treino exclui todas as disputas do mesmo dia: a presidencial e as de governador de 30/10/2022, por exemplo. Elas compartilham a ordem de chegada e o mesmo clima político, e mantê-las no treino seria vazamento.

Três escalas para o erro comum δ:

- **fração**: δ ~ Normal(0, c); o efeito no total cresce com a fração que falta;
- **ruído**: δ ~ Normal(0, c · sigma / 10), maior quando o swing já divulgado é mal explicado pelo histórico;
- **(e) recalibrada**: o desvio posterior multiplicado pelo quantil conformal das outras noites, como na fase 4.

### Cobertura de 90%

"Noites ≥ 80%" conta as noites em que a faixa cobriu o final em pelo menos 80% dos instantes.

| tipo       | metodo          | cobertura   | noites ≥ 80%   |   largura |   winkler |
|:-----------|:----------------|:------------|:---------------|----------:|----------:|
| governador | (c) + δ fração  | 82%         | 20/26          |      3.41 |      5.5  |
| governador | (c) + δ ruído   | 82%         | 19/26          |      3.45 |      4.96 |
| governador | (c) posterior   | 65%         | 10/26          |      2.63 |      6.19 |
| governador | (e) recalibrada | 93%         | 23/26          |      6.26 |      6.6  |
| presidente | (c) + δ fração  | 97%         | 4/4            |      2.3  |      2.43 |
| presidente | (c) + δ ruído   | 99%         | 4/4            |      2.2  |      2.22 |
| presidente | (c) posterior   | 41%         | 1/4            |      0.62 |      2.5  |
| presidente | (e) recalibrada | 80%         | 3/4            |      1.53 |      1.93 |

### Cobertura de 95%

| tipo       | metodo          | cobertura   | noites ≥ 80%   |   largura |   winkler |
|:-----------|:----------------|:------------|:---------------|----------:|----------:|
| governador | (c) + δ fração  | 87%         | 21/26          |      4.17 |      6.63 |
| governador | (c) + δ ruído   | 89%         | 20/26          |      4.21 |      5.62 |
| governador | (c) posterior   | 71%         | 13/26          |      3.27 |      8.28 |
| governador | (e) recalibrada | 98%         | 25/26          |      8.09 |      8.3  |
| presidente | (c) + δ fração  | 100%        | 4/4            |      2.72 |      2.72 |
| presidente | (c) + δ ruído   | 100%        | 4/4            |      2.6  |      2.6  |
| presidente | (c) posterior   | 42%         | 1/4            |      0.73 |      3.62 |
| presidente | (e) recalibrada | 83%         | 3/4            |      1.94 |      2.41 |

### Noites presidenciais, cobertura de 90%

| noite      | (c) posterior   | (c) + δ fração   | (c) + δ ruído   | (e) recalibrada   |
|:-----------|:----------------|:-----------------|:----------------|:------------------|
| 2018 1T PT | 9%              | 91%              | 100%            | 27%               |
| 2018 2T PT | 45%             | 95%              | 95%             | 91%               |
| 2022 1T PT | 91%             | 100%             | 100%            | 100%              |
| 2022 2T PT | 18%             | 100%             | 100%            | 100%              |

### Parâmetros calibrados, por data deixada de fora

| data    |   (c) + δ fração |   (c) + δ ruído |   (e) recalibrada |
|:--------|-----------------:|----------------:|------------------:|
| 2018 1T |             1.18 |            2.93 |              3.24 |
| 2018 2T |             0.83 |            2.58 |              3.6  |
| 2022 1T |             1.22 |            3    |              3.48 |
| 2022 2T |             1.34 |            2.87 |              3.7  |

## O erro comum cresce quando o histórico explica pouco

Nas 30 noites, a correlação de Spearman entre o |erro| médio do hierárquico (5% a 95% das seções) e o sigma médio no mesmo trecho é 0,57. Onde o swing dos locais já divulgados é mais disperso em torno do modelo, o erro de nível das pendentes também é maior. A escala de ruído aproveita isso. Ela tem o melhor interval score nos dois tipos de noite: 4,96 contra 5,50 da fração no governador e 2,22 contra 2,43 no presidente.

## O que mudou em relação à fase 6

- **2018 1T passa a ser coberta.** Com as noites de governador no treino, o `c` aprendido é maior, e a faixa com erro comum cobre essa noite em 100% dos instantes na escala de ruído (91% na de fração), contra 14% na fase 6. Nenhuma noite presidencial fica abaixo de 90%.
- **O preço é largura nas noites presidenciais.** Elas passam a cobrir de 97% a 100%, acima do nominal, com faixas de 2,2 a 2,3 pontos em média. As noites de governador, com histórico de 1º turno, são mais difíceis e puxam o `c` para cima. Uma faixa calibrada em noites mais difíceis erra para o lado seguro.
- **Nas noites de governador, (c) + δ ruído cobre 82% na faixa de 90% e 89% na de 95%**, com o melhor interval score. A recalibração (e) cobre mais (93%), mas com faixas quase duas vezes mais largas.
- **(e) segue falhando em 2018 1T (27%).** Um multiplicador fixo não distingue uma noite difícil de uma fácil; o termo de ruído distingue, porque mede o sigma da própria noite.

Valores calibrados com as 30 noites, usados no teste de 2026: `c` = 1,17 na escala de fração e 2,88 na de ruído; multiplicador de (e) a 90% = 3,46.

## Limites

- **As noites não são independentes.** Governadores do mesmo dia compartilham a ordem e o clima nacional; deixar a data inteira de fora protege a avaliação, mas a calibração final continua apoiada em quatro datas.
- **O histórico do governador é de outro tipo.** É o 1º turno do mesmo ano, e não a eleição anterior. Por isso o `c` calibrado nessas noites tende a ser conservador para a noite presidencial.
- **A ordem de 2018 é simulada.**
