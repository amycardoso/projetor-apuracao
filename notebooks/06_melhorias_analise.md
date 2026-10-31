# 06 — 1º turno e erro comum das pendentes

Esta fase faz duas coisas. Leva o projetor ao 1º turno de 2018 e 2022, o que dobra o número de noites de teste. E acrescenta ao modelo hierárquico um erro comum a todas as seções pendentes, para ver se assim a faixa posterior passa a cobrir o que promete sem uma recalibração externa.

Gerado por `notebooks/06a_primeiro_turno.py` (backtest, ~1 h) e `notebooks/06_melhorias.py` (tabelas).

## Os dados do 1º turno batem com o oficial

Os BUs do 1º turno foram baixados com o mesmo pipeline, só com as linhas de Presidente. Seções: {{SECOES}}. No 1º turno, os válidos incluem todos os candidatos, e o alvo continua sendo o % de um candidato nos válidos.

{{TOTAIS}}

PT e principal adversário batem voto a voto nos três anos. Os válidos de 2018 ficam 746 votos acima da totalização do TSE (0,0007%), e a diferença está toda nos demais candidatos. O efeito no % de qualquer candidato é menor que 0,001 ponto.

Dois CSVs de 2018 têm aspas sem escape no nome de candidatos a deputado estadual, o que quebrava o parser. A extração agora guarda só as linhas de Presidente. Reprocessado com essa regra, o 2º turno de 2022 saiu idêntico ao parquet anterior.

Resultado final de cada alvo (% nos válidos):

{{FINAIS}}

As noites são 2022 1T ← 2018 1T e 2018 1T ← 2014 1T. A ordem de chegada de 2022 é a observada (`DT_BU_RECEBIDO`). A de 2018 é simulada a partir do 1º turno de 2022, como no 2º turno. O alvo "adversário" é Bolsonaro nos dois anos. Em 2018, o histórico dele é o voto de Aécio (PSDB) em 2014, a única referência anti-PT disponível. É uma referência fraca.

## Erro dos modelos no 1º turno

Erro absoluto em pontos percentuais nos 22 pontos da grade (0,5% a 95% das seções). "Tempo até cravar" é o % de seções a partir do qual o erro fica abaixo de 0,5 ponto até o fim.

### % do PT

{{ERROS_PT}}

### % do principal adversário

{{ERROS_ADV}}

Em 2022, o hierárquico-t continua o melhor nos dois alvos. Com 2,5% das seções, ele já erra menos de 0,5 ponto para Lula e não sai mais disso. Em 2018 a ordem se inverte. Para Haddad, o swing por UF simples erra 0,25 em média e o hierárquico 0,51, sobretudo no começo (1,5 ponto até 2,5% das seções). A troca de Dilma por Haddad e a entrada de Bolsonaro mudaram o voto do PT de um jeito pouco ligado às covariáveis do modelo (voto anterior, porte, capital). Com poucos locais, o modelo mais flexível acompanha o ruído das primeiras seções. Para Bolsonaro em 2018, as camadas ganham, e o swing por UF sofre com a referência fraca de Aécio.

Nenhum modelo vence em todas as noites. Contando o 2º turno, o hierárquico tem o menor erro nas duas noites de 2022. Nas de 2018, perde para modelos mais simples: as camadas no 2º turno (0,22 contra 0,37) e o swing por UF no 1º. São as noites com ordem simulada e com a eleição anterior menos parecida.

## Erro comum às pendentes

O hierárquico trata o erro de cada local pendente como independente. Com milhares de locais, esse erro some na soma, e a faixa do total fica estreita demais. Na noite real, o que falta difere do que já chegou de um jeito que as covariáveis não capturam, e esse erro é comum a todas as pendentes. O modelo ganhou um termo

    delta ~ Normal(0, c × h),   somado ao swing de todos os locais pendentes,

que desloca o % final em `fração pendente × delta`. Foram testadas duas escalas: h = 1, em que o efeito cresce só com a fração que falta, e h = distância de variação total entre a composição UF × capital/interior dos válidos esperados divulgados e a dos pendentes.

O swing das pendentes não é observado durante a noite, então `c` não pode ser aprendido nela. Ele é calibrado por máxima verossimilhança nos erros de outras noites: erro ~ Normal(0, variância posterior + (fração · c · h)²). A avaliação é leave-one-night-out nas quatro noites do PT. Cada noite usa `c`, ou o multiplicador de (e), calibrado nas outras três. Para o adversário, a calibração usa as noites do PT de outras eleições.

Métodos comparados:

- (c) posterior do hierárquico-t, como sai do modelo;
- (c) + δ, com as duas escalas;
- (e) posterior recalibrada: desvio multiplicado pelo quantil conformal de |erro|/desvio das outras noites (o método adotado na fase 4).

### Quatro noites do PT juntas

{{FAIXAS_GERAL}}

### Por noite

{{FAIXAS_NOITE}}

### Parâmetro calibrado em cada noite

`c` em pontos de swing; para (e), o multiplicador do desvio a 90%.

{{PARAMS}}

Com as quatro noites, `c` = {{C_FRACAO}} ponto de swing na escala de fração e {{C_DISTANCIA}} na de distância. Na escala de fração, isso dá um desvio de cerca de 0,5 ponto no total com 5% das seções divulgadas e de 0,28 ponto na metade da apuração.

![Faixas de 2022, 1º turno](figures/06_faixa_1t_2022.png)

### Alvo adversário

{{FAIXAS_ADV}}

## O que mudou

- **O δ ajuda, mas não basta.** A cobertura de 90% da posterior sobe de 41% para 75% nas quatro noites, e o interval score cai de 2,50 para 2,20, o melhor entre os métodos. Em três das quatro noites, (c) + δ cobre entre 86% e 100%. A resposta à pergunta da fase é não: a faixa ainda não chega perto do nominal em toda noite.
- **A falha é uma noite só.** Em 2018 1T, a cobertura fica em 14%. As outras três noites ensinam um `c` pequeno (0,26), porque nelas o hierárquico errou pouco. Nenhum método calibrado em outras noites cobre bem uma noite fora do padrão. A recalibração (e) também cai para 27% ali.
- **A distância de composição não acrescenta.** Ela dá cobertura parecida com faixas mais largas. A fração que falta já carrega o que importa. O que distingue as noites difíceis não é a composição UF × capital das pendentes, que o modelo já vê.
- **(e) cobre mais no agregado (82%), mas a um custo alto.** Suas faixas são quase o dobro das de (c) + δ, com interval score pior. Em 2022 2T, (e) e (c) + δ cobrem 100%; a faixa de (c) + δ é mais estreita (1,34 contra 1,43 ponto).

Na prática, (c) + δ na escala de fração substitui bem a recalibração (e). Ela é parte do modelo, cresce e encolhe com a fração que falta e precisa de um parâmetro só. O replay continua com (e), calibrada no 2º turno. Trocar exige reexportar `docs/data`.

## Limites

- **Poucas noites.** São quatro noites, e os 22 pontos de uma noite são muito correlacionados. A calibração de `c` se apoia em quatro observações quase independentes. Uma noite como 2018 1T pesa muito.
- **Ordem simulada em 2018.** A ordem de 2018 é a de 2022 transposta, e o erro do começo da noite depende dela.
- **Histórico fraco do adversário em 2018.** O histórico do adversário em 2018 é o voto de Aécio, e as faixas desse alvo herdam essa fraqueza.
