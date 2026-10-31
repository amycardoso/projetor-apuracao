# 07 — Eleição de 2026, fora da amostra

Até aqui, todo resultado vinha de eleições em que os modelos foram desenvolvidos. Em 2026, nada foi reescolhido olhando a noite. Os modelos e hiperparâmetros são os das fases 2 a 4. O `c` do erro comum e o multiplicador da faixa (e) foram calibrados nas noites de 2018 e 2022 (fases 6 e 7). É o teste mais limpo do projeto.

Gerado por `notebooks/07a_eleicao_2026.py` (backtest, ~1 h) e `notebooks/07_eleicao_2026.py` (tabelas).

## Os dados de 2026

Os boletins de urna estão no Portal de Dados Abertos do TSE (`resultados-2026-boletim-de-urna`). O pacote CKAN lista 27 UFs no 2º turno. O zip de Roraima falta na lista, mas está no CDN com o mesmo carimbo de geração e com `.sha512`. O ingest agora completa UFs nessa situação. O formato mudou: as datas vêm em ISO (`2026-10-25 19:42:19`) e vários números vêm sem aspas.

{{TOTAIS}}

Os percentuais do 1º turno batem com o resultado final publicado (Lula 45,16%, Flávio Bolsonaro 47,03%). O adversário é o número 22 (PL) nos dois turnos.

`DT_BU_RECEBIDO` existe em todas as seções ({{SEM_RECEBIDO}} sem valor) e está em hora de Brasília. No 2º turno, o Acre encerrou às 15:01 locais (17:01 de Brasília) e o primeiro BU chegou às 17:05. Primeiro recebimento por UF: {{RECEBIDO}}.

A ordem de 2026 foi bem mais enviesada que a de 2022. São Paulo e Rio só começam a chegar às 19:03, e as primeiras seções vêm sobretudo do Paraná, do Pará e do Distrito Federal. Com 0,5% das seções no 2º turno, o apurado dava 54,7% a Lula, que terminou com 51,8%.

## Erro dos modelos congelados

Erro absoluto (p.p.) nos 22 pontos da grade, de 0,5% a 95% das seções.

{{ERROS}}

Entre 19h44 e 20h23 do 2º turno, de 14% a 47% das seções, o apurado mostrou Flávio na frente; o mínimo de Lula foi 49,5%. Na noite inteira, a projeção do hierárquico ficou entre 51,6% e 51,8%, e o limite inferior da faixa de 90% nunca desceu de 50,3%. No 2º turno, o hierárquico-t erra 0,07 ponto em média e fica abaixo de 0,5 ponto desde 0,5% das seções. É o melhor resultado do projeto em qualquer noite. No 1º turno, hierárquico e camadas empatam no alvo PT (0,17 e 0,18). Para Flávio, as camadas ganham (0,09 contra 0,12). O hierárquico erra mais no começo da noite (0,8 ponto até 2,5% para Lula) e menos depois de 5%.

## Faixas congeladas

Quatro faixas, todas fixadas antes de 2026:

- (c) posterior do hierárquico-t, como sai do modelo;
- (c) + δ fração, com `c` = {{C}} das quatro noites do PT (fase 6);
- (e) recalibrada, com multiplicadores {{MULT90}} (90%) e {{MULT95}} (95%) das mesmas quatro noites;
- (c) + δ ruído, com `c` = {{C_RUIDO}} das 30 noites presidenciais e de governador (fase 7). É a faixa que o replay mostra.

{{FAIXAS}}

A posterior pura volta a cobrir menos que o prometido: 45% a 77% na faixa de 90%. As três faixas corrigidas cobrem de 91% a 100% nas três noites. Entre as faixas corrigidas, a recalibração (e) teve o menor interval score em 2026, com faixas de 0,7 a 0,9 ponto. Em duas noites, a posterior pura pontuou ainda um pouco melhor, porque os erros foram pequenos e ficaram perto da faixa estreita. As faixas com δ cobriram tudo, com 1,1 a 1,4 ponto. Foi uma noite fácil para o modelo, e as faixas calibradas em noites difíceis (2018 1T e os governadores) erraram para o lado seguro.

A escolha do replay continua sendo (c) + δ ruído. Nas 34 noites avaliadas (30 de calibração e as 3 de 2026), ela nunca cobre menos de 90% numa noite presidencial. A (e) cai para 27% em 2018 1T, porque um multiplicador fixo não distingue uma noite difícil de uma fácil. O custo é uma faixa mais larga quando a noite é fácil, como 2026.

## Comparação com o modelo de Rodrigo Mahlmeister

Os números do modelo de Rodrigo são os públicos, como repassados no briefing do projeto. A coluna "este projeto" mostra o hierárquico-t congelado, com a faixa de 95% de (c) + δ ruído. O instante é o mesmo, medido em % das seções divulgadas. Nos dois turnos, o relógio deste projeto chega a esse ponto entre 17h29 (1º turno) e 19h19 (2º turno).

{{RODRIGO}}

- **No 2º turno**, as duas projeções ficam a 0,2 ponto ou menos do final. A deste projeto chega mais perto (51,71 contra 51,6, com final 51,79). As duas faixas cobrem o resultado; a daqui é mais larga.
- **No 1º turno, com 2,2% das seções**, o modelo de Rodrigo acertou melhor: 0,02 ponto de erro em Flávio e 0,34 em Lula, contra 0,52 e 0,74 do hierárquico. O modelo em camadas daqui, mais parecido com o dele, projetava Lula 45,48 e Flávio 46,73 nesse instante. O valor de Lula é praticamente o dele (45,50). A diferença em Flávio é compatível com o ponto de partida do modelo de Rodrigo: segundo a reportagem da NeoFeed, ele partiu da pesquisa Quaest e somou dois pontos a Flávio. Este projeto não usa pesquisa nenhuma.
- **Uma comparação de um instante só diz pouco.** O modelo de Rodrigo não publicou faixas no 1º turno nem um backtest, então a comparação para no ponto. Ao longo da noite inteira, o hierárquico daqui erra 0,05 a 0,06 ponto depois de 5% das seções nos dois turnos.

![2026, 2º turno](figures/07_2026_2t.png)

## Limites

- **Três noites de teste.** São duas datas, com os mesmos dois candidatos, numa eleição polarizada como a de 2022. É o cenário mais favorável ao swing.
- **Números de Rodrigo não auditados.** Os números do modelo de Rodrigo não foram auditados aqui; vêm da reportagem e do briefing.
- **Grade de pontos.** O instante de comparação foi incluído na grade porque era o publicado; a grade em si não foi ajustada a 2026.
