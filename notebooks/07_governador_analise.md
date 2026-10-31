# 07 — Governador: mais noites para calibrar o erro comum

Na fase 6, o erro comum às pendentes levou a cobertura de 90% de 41% para 75%, mas o `c` vinha de só quatro noites e falhava em 2018 1T. Aqui entram {{N_GOV}} noites de 2º turno de governador como calibração extra. Também testo se o erro comum deve crescer quando o histórico explica pouco do swing já divulgado.

Gerado por `notebooks/07b_governador.py` (backtest) e `notebooks/07_governador.py` (tabelas).

## As noites de governador

Cada UF com 2º turno de governador vira uma noite. São {{UFS_2018}} em 2018 e {{UFS_2022}} em 2022. O alvo é o % do candidato de menor número entre os dois finalistas. O histórico é o 1º turno de governador do mesmo ano, nas mesmas seções, com o % desse candidato entre os dois. O 1º turno é público três semanas antes, então não vaza nada da noite. A ordem de chegada é a da noite presidencial do mesmo dia, restrita à UF; em 2018 ela é simulada. Os totais conferem com os resultados conhecidos, por exemplo Tarcísio com 55,27% em SP (2022) e Doria com 51,75% em SP (2018).

Essas noites são mais difíceis que as presidenciais. Do 1º para o 2º turno, os votos dos eliminados se redistribuem de forma desigual pelo estado. O erro de nível do swing é maior e muda de uma UF para outra.

Erro absoluto médio (p.p.) nos 22 pontos da grade. "Cravar" é o % de seções a partir do qual o hierárquico fica abaixo de 0,5 ponto até o fim. "Sigma médio" é o desvio posterior do swing de um local em torno do que o modelo explica.

{{GOV}}

O hierárquico tem o menor erro em 15 das 26 noites, o swing uniforme da UF em 9 e o próprio apurado em 2. Os piores casos (AM e RO em 2018, MG em 2018) são noites em que o swing do 1º para o 2º turno variou muito entre regiões do estado.

## Faixas, deixando uma data inteira de fora

Ao avaliar uma noite, o treino exclui todas as disputas do mesmo dia: a presidencial e as de governador de 30/10/2022, por exemplo. Elas compartilham a ordem de chegada e o mesmo clima político, e mantê-las no treino seria vazamento.

Três escalas para o erro comum δ:

- **fração**: δ ~ Normal(0, c); o efeito no total cresce com a fração que falta;
- **ruído**: δ ~ Normal(0, c · sigma / 10), maior quando o swing já divulgado é mal explicado pelo histórico;
- **(e) recalibrada**: o desvio posterior multiplicado pelo quantil conformal das outras noites, como na fase 4.

### Cobertura de 90%

"Noites ≥ 80%" conta as noites em que a faixa cobriu o final em pelo menos 80% dos instantes.

{{FAIXAS90}}

### Cobertura de 95%

{{FAIXAS95}}

### Noites presidenciais, cobertura de 90%

{{PRES}}

### Parâmetros calibrados, por data deixada de fora

{{PARAMS}}

## O erro comum cresce quando o histórico explica pouco

Nas 30 noites, a correlação de Spearman entre o |erro| médio do hierárquico (5% a 95% das seções) e o sigma médio no mesmo trecho é {{SPEARMAN}}. Onde o swing dos locais já divulgados é mais disperso em torno do modelo, o erro de nível das pendentes também é maior. A escala de ruído aproveita isso. Ela tem o melhor interval score nos dois tipos de noite: 4,96 contra 5,50 da fração no governador e 2,22 contra 2,43 no presidente.

## O que mudou em relação à fase 6

- **2018 1T passa a ser coberta.** Com as noites de governador no treino, o `c` aprendido é maior, e a faixa com erro comum cobre essa noite em 100% dos instantes na escala de ruído (91% na de fração), contra 14% na fase 6. Nenhuma noite presidencial fica abaixo de 90%.
- **O preço é largura nas noites presidenciais.** Elas passam a cobrir de 97% a 100%, acima do nominal, com faixas de 2,2 a 2,3 pontos em média. As noites de governador, com histórico de 1º turno, são mais difíceis e puxam o `c` para cima. Uma faixa calibrada em noites mais difíceis erra para o lado seguro.
- **Nas noites de governador, (c) + δ ruído cobre 82% na faixa de 90% e 89% na de 95%**, com o melhor interval score. A recalibração (e) cobre mais (93%), mas com faixas quase duas vezes mais largas.
- **(e) segue falhando em 2018 1T (27%).** Um multiplicador fixo não distingue uma noite difícil de uma fácil; o termo de ruído distingue, porque mede o sigma da própria noite.

Valores calibrados com as 30 noites, usados no teste de 2026: `c` = {{C_FRACAO}} na escala de fração e {{C_RUIDO}} na de ruído; multiplicador de (e) a 90% = {{MULT90}}.

## Limites

- **As noites não são independentes.** Governadores do mesmo dia compartilham a ordem e o clima nacional; deixar a data inteira de fora protege a avaliação, mas a calibração final continua apoiada em quatro datas.
- **O histórico do governador é de outro tipo.** É o 1º turno do mesmo ano, e não a eleição anterior. Por isso o `c` calibrado nessas noites tende a ser conservador para a noite presidencial.
- **A ordem de 2018 é simulada.**
