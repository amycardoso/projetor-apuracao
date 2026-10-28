**Em 2022, sim: o pooling aprendido supera os pesos escolhidos à mão.**

- O erro médio cai de 0,32 p.p. (`SwingCamadasInterceptoPorte`) para 0,15. O tempo até cravar fica igual, 1% das seções.
- O ganho maior está no início. Com 0,5% das seções, o hierárquico erra 1,60 p.p., contra 4,91 do modelo em camadas, que ainda estava no swing uniforme. Entre 10% e 50%, os dois ficam próximos (0,05 a 0,21).
- Há uma vantagem estrutural: o hierárquico não precisa de um limite para trocar o swing uniforme pela regressão. A pooling resolve isso sozinha com poucos locais.

**Em 2018, não.**

- O hierárquico tem erro médio de 0,41, contra 0,22 do modelo em camadas e 0,27 do swing uniforme. Erra muito no começo: +3,0 p.p. com 0,5% das seções e +1,4 com 1%.
- Depois disso, subestima Haddad de forma persistente, entre −0,1 e −0,26 de 5% a 90% das seções.
- Testei se o viés vinha do corte em 0–100% somado ao ruído local. Sem o ruído, o erro com 50% passa de −0,25 para −0,22, então não é isso.
- Duas explicações prováveis:
  1. O swing 2014→2018 é muito mais disperso (sigma ≈ 7,2 p.p. contra 3,5 em 2022; tau de UF × capital ≈ 4,9 contra 1,5). A verossimilhança normal sem caudas pesadas deixa os locais extremos puxarem a regressão nacional.
  2. Em 2018 a comparação favorece as camadas, porque k e `min_locais` foram escolhidos justamente nesse backtest na fase 2.

**O que os tau mostram.**

- Em 2022, o desvio entre regiões (~1,9–2,6), entre UFs da mesma região (~1,6) e entre capital e interior dentro da UF (~1,1–1,5) tem ordem parecida. A pooling é moderada nos três níveis.
- Em 2018, o nível UF × capital domina (tau ≈ 5). Isso confirma a hipótese da fase 1: entre 2014 e 2018, capitais e interior se moveram de forma diferente.

**ADVI x NUTS.**

- As projeções pontuais praticamente coincidem com 10% e 50% das seções (diferença < 0,01 p.p.). Com 2,5%, o NUTS ficou mais perto do final (−0,003 contra −0,13).
- O ADVI subestima os tau (tau_uf 1,6–1,9 contra 2,1–2,4 no NUTS), como é típico do campo médio. Mesmo assim, deu intervalos mais largos que o NUTS.
- Custo: o ADVI leva 6–16 s por ponto. O NUTS leva 14–19 s com até 10% das seções e 136 s com 50%.

**Custo de execução.** O hierárquico leva ~14,5 s por ponto da grade, contra 0,5 s do modelo em camadas e 0,1 s do swing por UF. Numa noite real, com atualização a cada poucos minutos, ainda é viável.

**Intervalos (prévia para a fase 4).** Os intervalos de 90% ainda subestimam a incerteza. O final caiu dentro do intervalo em 18 de 22 pontos em 2022 e só em 7 de 22 em 2018. A incerteza do comparecimento ainda não está no modelo, e o viés de 2018 não aparece nos intervalos. Calibrar isso é o trabalho da fase 4.
