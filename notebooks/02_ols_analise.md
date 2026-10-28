**O que funcionou.** O melhor modelo nos dois anos é `SwingCamadasInterceptoPorte`: uma regressão nacional, com deslocamentos encolhidos por região, UF e UF × capital/interior.

- Em 2022 (teste), o erro médio é 0,32 p.p., contra 0,41 do melhor baseline (`SwingUniformeUF`). O |erro| fica abaixo de 0,5 p.p. a partir de 1% das seções e abaixo de 0,25 a partir de 2,5%.
- Em 2018 (treino), o erro médio é 0,22, contra 0,27 do `SwingUniforme`.
- O nível UF × capital/interior melhorou as duas famílias em 2018: 0,220 contra 0,244 no modo intercepto e 0,242 contra 0,253 no modo regressão. Por isso foi mantido. Em 2022 também ajuda: 0,32 contra 0,61 no intercepto e 0,52 contra 0,54 na regressão.
- Em 2022, a regressão nacional mostra que o swing pró-PT foi maior onde o PT tinha menos voto (−0,17 p.p. por ponto de `ant_pct_pt`) e nos municípios maiores.

**O que não funcionou.**

- A WLS nacional sozinha (`SwingOLS`) é pior que o swing por UF em 2022, com média de 0,70. Ela subestima Lula em cerca de 1 p.p. entre 5% e 10% das seções. Com essas três covariáveis, não captura o swing regional (Sudeste +10,8 p.p. contra Nordeste −0,3), e as primeiras seções vêm de regiões com swing menor.
- As regressões completas por região e UF (`SwingCamadas`, `SwingCamadasPorte`) precisaram de k entre 10.000 e 30.000 para não piorar, ou seja, ficaram quase iguais ao nacional. Ajustar 4 parâmetros por UF com poucos locais é ruído demais.
- Com 0,5% das seções e `min_locais = 1000`, todos os modelos em camadas ainda usam o swing uniforme e erram 4,9 p.p. em 2022. Até ~1% das seções, nenhum modelo é confiável.
- O coeficiente de `capital` troca de sinal entre 10% (+0,2) e 50% (−1,6) das seções em 2022. Isso mostra que as primeiras capitais a chegar não representam as que chegam depois.

**Ressalvas honestas.**

1. O par escolhido para `SwingCamadasInterceptoPorte` (k = 30, `min_locais` = 1000) está no limite inferior da grade de k. Um k menor talvez fosse ainda melhor em 2018. Não estendi a grade para não continuar ajustando.
2. Escolher k, `min_locais` e a variante em 2018 não deixa 2022 totalmente independente: a ordem de chegada de 2018 é simulada a partir da de 2022. A ordem de 2022 entrou no treino, embora os votos de 2022 não. O 2022 é um teste "fora da amostra de votos", não um teste cego.
3. O erro de 2018 mede o modelo sob a ordem de 2022, não sob a noite real de 2018.
4. Ainda não há intervalos: estes números são só de erro pontual. A calibração fica para a próxima fase.
