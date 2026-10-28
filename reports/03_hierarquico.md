# 03 — Modelo hierárquico bayesiano no 2º turno

Pergunta: o pooling aprendido supera os pesos escolhidos à mão?

`SwingHierarquico`: swing por local ~ Normal(mu, sigma/sqrt(peso)), com mu = alpha + beta·X + a_ufcap e a_regiao ~ N(0, tau_regiao), a_uf ~ N(a_regiao, tau_uf), a_ufcap ~ N(a_uf, tau_ufcap) (UF × capital). PyMC, ADVI (30 mil iterações), 1.000 amostras. Detalhes no docstring de `projetor.models.hierarquico`. `SwingCamadasInterceptoPorte` usa k = 30 e min_locais = 1000, escolhidos em 2018 na fase 2.

![|erro| x % apurado](figures/03_erro_vs_apurado.png)


## 2022 — ordem observada, histórico de 2018

|                                 |   SwingUniforme |   SwingUniformeUF |   SwingCamadasInterceptoPorte |   SwingHierarquico |
|:--------------------------------|----------------:|------------------:|------------------------------:|-------------------:|
| 0.5%                            |            4.91 |              4.03 |                          4.91 |               1.6  |
| 1%                              |            3.23 |              2.66 |                          0.42 |               0.17 |
| 2.5%                            |            1.52 |              0.86 |                          0.1  |               0.13 |
| 5%                              |            0.21 |              0.22 |                          0.02 |               0.06 |
| 10%                             |            0.58 |              0.03 |                          0.21 |               0.21 |
| 15%                             |            0.69 |              0.05 |                          0.25 |               0.2  |
| 20%                             |            0.74 |              0.02 |                          0.2  |               0.14 |
| 25%                             |            0.73 |              0.04 |                          0.19 |               0.13 |
| 30%                             |            0.7  |              0.05 |                          0.14 |               0.08 |
| 35%                             |            0.67 |              0.08 |                          0.14 |               0.09 |
| 40%                             |            0.59 |              0.09 |                          0.12 |               0.08 |
| 45%                             |            0.54 |              0.09 |                          0.1  |               0.06 |
| 50%                             |            0.47 |              0.09 |                          0.07 |               0.05 |
| 55%                             |            0.39 |              0.1  |                          0.06 |               0.05 |
| 60%                             |            0.31 |              0.11 |                          0.05 |               0.04 |
| 65%                             |            0.23 |              0.11 |                          0.04 |               0.03 |
| 70%                             |            0.17 |              0.11 |                          0.02 |               0.03 |
| 75%                             |            0.13 |              0.09 |                          0.01 |               0.02 |
| 80%                             |            0.08 |              0.08 |                          0    |               0.01 |
| 85%                             |            0.05 |              0.06 |                          0.01 |               0.01 |
| 90%                             |            0.02 |              0.05 |                          0.01 |               0    |
| 95%                             |            0    |              0.02 |                          0.02 |               0.01 |
| média                           |            0.77 |              0.41 |                          0.32 |               0.15 |
| tempo até cravar (|erro| < 0,5) |           50    |              5    |                          1    |               1    |
| segundos por ponto              |            0.03 |              0.09 |                          0.52 |              14.59 |


## 2018 — ordem simulada a partir de 2022, histórico de 2014

|                                 |   SwingUniforme |   SwingUniformeUF |   SwingCamadasInterceptoPorte |   SwingHierarquico |
|:--------------------------------|----------------:|------------------:|------------------------------:|-------------------:|
| 0.5%                            |            0.49 |              0.61 |                          0.49 |               3    |
| 1%                              |            0.88 |              0.86 |                          0.17 |               1.37 |
| 2.5%                            |            0.75 |              1.85 |                          1.1  |               0.69 |
| 5%                              |            0.39 |              1.23 |                          0.12 |               0.35 |
| 10%                             |            0.08 |              1.21 |                          0.43 |               0.36 |
| 15%                             |            0.36 |              1.15 |                          0.53 |               0.19 |
| 20%                             |            0.36 |              1.03 |                          0.52 |               0.1  |
| 25%                             |            0.38 |              0.81 |                          0.4  |               0.08 |
| 30%                             |            0.38 |              0.63 |                          0.26 |               0.18 |
| 35%                             |            0.37 |              0.51 |                          0.19 |               0.2  |
| 40%                             |            0.34 |              0.38 |                          0.11 |               0.2  |
| 45%                             |            0.26 |              0.22 |                          0.02 |               0.22 |
| 50%                             |            0.18 |              0.11 |                          0.02 |               0.25 |
| 55%                             |            0.12 |              0.04 |                          0.02 |               0.26 |
| 60%                             |            0.05 |              0.01 |                          0.05 |               0.26 |
| 65%                             |            0    |              0.03 |                          0.05 |               0.24 |
| 70%                             |            0.05 |              0.07 |                          0.07 |               0.24 |
| 75%                             |            0.08 |              0.08 |                          0.06 |               0.21 |
| 80%                             |            0.11 |              0.08 |                          0.05 |               0.18 |
| 85%                             |            0.13 |              0.08 |                          0.06 |               0.15 |
| 90%                             |            0.14 |              0.09 |                          0.06 |               0.13 |
| 95%                             |            0.12 |              0.09 |                          0.05 |               0.09 |
| média                           |            0.27 |              0.51 |                          0.22 |               0.41 |
| tempo até cravar (|erro| < 0,5) |            5    |             40    |                         25    |               5    |
| segundos por ponto              |            0.03 |              0.08 |                          0.56 |              14.47 |


## Pooling aprendido (média posterior, p.p. de swing)

tau = desvio entre grupos de cada nível; sigma = ruído de um local de peso médio.

|               |   locais |   tau_regiao |   tau_uf |   tau_ufcap |   sigma |
|:--------------|---------:|-------------:|---------:|------------:|--------:|
| (2022, '5%')  |     5634 |         2.61 |     1.64 |        1.13 |    4.1  |
| (2022, '25%') |    24183 |         1.88 |     1.57 |        1.35 |    3.66 |
| (2022, '50%') |    46675 |         1.92 |     1.59 |        1.47 |    3.54 |
| (2018, '5%')  |     5208 |         2.62 |     1.52 |        5.36 |    7.27 |
| (2018, '25%') |    24107 |         2.46 |     1.78 |        4.88 |    7.08 |
| (2018, '50%') |    46889 |         2.44 |     2.01 |        4.91 |    7.24 |


## ADVI x NUTS (2022)

NUTS via nutpie, 4 cadeias × 250 amostras após 500 de aquecimento.

| seções   |   advi erro | advi IC 90%    |   advi tau_uf |   advi seg |   nuts erro | nuts IC 90%    |   nuts tau_uf |   nuts seg |
|:---------|------------:|:---------------|--------------:|-----------:|------------:|:---------------|--------------:|-----------:|
| 2.5%     |      -0.133 | [50.04, 51.56] |         1.855 |      5.93  |      -0.003 | [50.31, 51.48] |         2.371 |     13.672 |
| 10%      |       0.213 | [50.88, 51.36] |         1.598 |      7.278 |       0.21  | [50.99, 51.23] |         2.147 |     18.714 |
| 50%      |       0.046 | [50.88, 51.01] |         1.588 |     16.24  |       0.046 | [50.93, 50.97] |         2.32  |    136.427 |


## Prévia dos intervalos (para a fase 4)


|   ano |   largura média do IC 90% (p.p.) | pontos com o final dentro do IC 90%   |
|------:|---------------------------------:|:--------------------------------------|
|  2018 |                         0.830564 | 7/22                                  |
|  2022 |                         0.584186 | 18/22                                 |


## Conclusão

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
