**Student-t (passo 0).** A t ficou: o erro médio melhora nos dois anos (2022: 0,171 → 0,136; 2018: 0,401 → 0,370), com ν aprendido entre 3,3 e 4,3. O ganho está do meio para o fim da noite: em 2018, o erro de 5% a 95% cai de 0,195 para 0,124, e o viés persistente da fase 3 encolhe. Só a ponta de 2018 piora: até 2,5% das seções, 1,93 contra 1,71.

**As faixas baseadas só no modelo — (a) analítica, (b) bootstrap e (c) posterior — têm cobertura muito abaixo da prometida.** Cobrem de 18% a 45% quando prometem 90% ou 95%. Pela regra do projeto, isso é bug, não ajuste fino.

- O diagnóstico é o mesmo nos três métodos. Eles tratam o erro de cada local pendente como independente, então a incerteza encolhe com a raiz do número de locais que faltam.
- O erro real tem um componente comum: as pendentes diferem das divulgadas de um jeito que as covariáveis não explicam, e esse desvio não se dilui. Em 2022, o |erro| do hierárquico fica em ~3 desvios posteriores de 30% a 95% das seções, quase constante.
- A incerteza do comparecimento entrou em (a), (b) e (c), mas muda pouco a largura. O problema não é falta de ruído local; é falta de um termo correlacionado.

**O conformal por faixa de relógio (d)** acerta 2022 (95% de cobertura, calibrado em 2018), mas cobre só 64–68% em 2018, quando calibrado em 2022.

- Em cada direção, um único ano dá os quantis. Os erros de 2022 foram menores que os de 2018, então a calibração de 2022 fica estreita para 2018.
- Na faixa de 10–25%, o conformal erra os 3 pontos de 2018.
- A faixa é larga no meio da noite em 2022: 0,77 p.p. de largura média.

**O melhor resultado foi (e), a posterior recalibrada.** O desvio posterior é multiplicado pelo quantil de |erro|/desvio do outro ano: ~4,2 para a faixa de 90% em 2022 e ~3,2 em 2018.

- Teve o menor interval score nos dois anos: 1,10 contra 4,18 do conformal em 2022, e 2,34 contra 2,49 em 2018.
- A cobertura ficou em 100% em 2022 (conservadora) e em 86% em 2018. Em 2018 ainda fica abaixo dos 90%/95% prometidos, mas dentro da margem de 15 p.p.
- A forma da faixa vem do modelo, larga no início e estreita no fim, e só a escala vem da calibração. Por isso ela é estreita no fim da noite sem perder cobertura.

**Limitações.**

- Cada direção de teste é uma única noite, e os 22 pontos de uma noite são fortemente correlacionados. As coberturas são estimativas com poucos graus de liberdade efetivos.
- Um multiplicador de 3 a 4 sobre a posterior mostra que falta estrutura no modelo. O próximo passo natural é pôr no próprio hierárquico um termo de discrepância comum às pendentes, proporcional à fração que falta, e mais noites de calibração (1º turno, 2014 com ordem simulada).
- Até isso existir, a recomendação é publicar (e) e tratar (a)–(c) como incerteza mínima, não como faixa.
