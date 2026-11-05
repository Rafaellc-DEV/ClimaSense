# Risco de alagamento por bairro e dia (F6), estudo de ML

> **EXPERIMENTAL (RN-11).** Classe de risco, nunca probabilidade (RN-06). Gerado por
> `python -m climasense.ml alagamento` em 2026-11-04; modelo `v0.1.0` treinado em
> 2026-11-04T21:06:01+00:00. Não edite à mão: rode o comando de novo.

## Decisão

**Não publicar no produto** (`disponivel: false`). Motivo: O modelo não supera com folga a referência 'limiar_chuva' no período de teste (AUC-PR 0.046 contra 0.050); a regra simples é preferível.

Critérios (todos precisam valer): pelo menos 100 bairro-dias positivos no treino e
30 no teste; recall da classe "alagou" no teste ≥ 0.60; AUC-PR
no teste ≥ 1.10 × a melhor referência simples. Sem isso, a API devolve
`disponivel: false` com o motivo e o gatilho de estágio ignora este insumo; nenhum dado simulado é exibido
(RF-12.10).

## Dados

- **Rótulo** (real): conjunto `registro-de-atendimentos-da-defesa-civil` dos Dados Abertos do Recife (ODbL),
  https://dados.recife.pe.gov.br/dataset/registro-de-atendimentos-da-defesa-civil. O conector `recife-alagamento` do ETL ainda não existe e `silver.ocorrencias` está
  vazia; o estudo baixa os CSVs para `tmp/alagamento/` (fora do Git), sem tocar no ETL nem no banco.
- 881,160 registros lidos (2014 em diante); 1,724 são de
  alagamento pelo critério `evento` (ocorrência `Alagamentos`/`Imóveis Alagados`, ou solicitação
  `Vistoria Alagado`/`Vistoria Setor Alagado`/`Monitoramento Setor Alagado`). Registros cujo bairro não
  existe na base oficial (descartados): Ur 05 (1), Iraque (1).
- **461 bairro-dias com atendimento real**, de 2014-01-16 a
  2024-06-25, em 139 dias distintos.
- A data da fonte é a da solicitação/vistoria, não a do alagamento. O rótulo do dia D é "houve atendimento
  no bairro entre D e D + 3". Por isso o relatório mede também **atendimentos avisados**
  (houve aviso para o bairro em algum dia da janela antes do atendimento?), que não sofre essa inflação.
- **Chuva**: ERA5 horária por distrito; origem: silver.observacoes (open-meteo-historico, somente leitura) + API de arquivo Open-Meteo para os anos que o banco não tem. Somas diárias em hora do Recife; dia
  sem as 24 horas fica nulo (RN-01). O bairro herda a chuva do seu distrito (RN-07).
- **Maré**: o histórico do Open-Meteo Marine começa no fim de 2022. Ajuste harmônico (15
  componentes) na série real de 2023-01-01 a 2026-11-04: R² = 0.993,
  RMSE = 0.050 m. A maré de cada dia é a maré astronômica calculada (sem efeito de vento).
- Área e faixa hídrica por bairro **não entram**: a base territorial só tem geometria de distrito.

### Desequilíbrio de classes

| Período | Bairro-dias | Positivos | Taxa | Negativos por positivo | Dias com positivo | Bairros com positivo |
|---|---:|---:|---:|---:|---:|---:|
| Total ['2014-01-01', '2024-12-31'] | 377,692 | 1683 | 0.446% | 223.4 | 398 | 71 |
| Treino ['2014-01-01', '2023-12-31'] | 343,288 | 1347 | 0.392% | 253.9 | 366 | 65 |
| Teste ['2024-01-01', '2024-12-31'] | 34,404 | 336 | 0.977% | 101.4 | 32 | 28 |

Com menos de 1 positivo a cada centenas de linhas, acurácia não diz nada (prever "nunca alaga" acerta
mais de 99%). Usamos **recall** da classe "alagou" (o cliente prefere alerta falso a evento não avisado),
**precisão** e **AUC-PR** (área sob a curva precisão × recall; a de um classificador aleatório é a própria
taxa de positivos).

## Método

1. Atributos por bairro e dia: `chuva_1d` (chuva do dia), `chuva_3d` (chuva acumulada em 3 dias), `chuva_7d` (chuva acumulada em 7 dias), `mare_max_m` (maré máxima do dia), `mes` (mês), `hist_dias_ano` (histórico de alagamento do bairro). O histórico usa só dias
   anteriores ao dia avaliado.
2. **Validação temporal**: treino até 2023, teste em 2024 (nunca visto até o fim).
   Dentro do treino, janela crescente: para cada um dos últimos 5 anos, treina nos anteriores e
   valida nele. Nota = AUC-PR das pontuações fora da amostra de todos esses anos juntos.
3. Busca: 3 conjuntos de atributos × grade {'max_depth': [3, 4, 5, 6, 8], 'min_samples_leaf': [20, 100, 400], 'class_weight': ['balanced', None]} = 90 tentativas.
4. Limiares das classes, fixados nas pontuações fora da amostra do treino: `moderado` mantém recall
   80%, `alto` mantém 40%. A referência "limiar de chuva" usa o mesmo
   recall-alvo no treino (2.0 mm no dia).
5. `EstimadorReferencia` aplicado a cada distrito e dia do teste com a chuva REAL do dia como se fosse a
   previsão (vantagem para a regra), a maré calculada e o histórico de chuva anterior.

### Tentativas (15 melhores pela validação temporal)

| # | Conjunto | Hiperparâmetros | AUC-PR fora da amostra | Desvio entre anos | AUC-PR no treino |
|--:|---|---|---:|---:|---:|
| 67 | completo **(escolhida)** | max_depth=4, min_samples_leaf=20, class_weight=balanced | 0.0485 | 0.0335 | 0.0286 |
| 69 | completo | max_depth=4, min_samples_leaf=100, class_weight=balanced | 0.0485 | 0.0335 | 0.0286 |
| 71 | completo | max_depth=4, min_samples_leaf=400, class_weight=balanced | 0.0475 | 0.0335 | 0.0286 |
| 73 | completo | max_depth=5, min_samples_leaf=20, class_weight=balanced | 0.0469 | 0.0343 | 0.0372 |
| 75 | completo | max_depth=5, min_samples_leaf=100, class_weight=balanced | 0.0469 | 0.0345 | 0.0371 |
| 88 | completo | max_depth=8, min_samples_leaf=100, class_weight=None | 0.0459 | 0.0457 | 0.1324 |
| 81 | completo | max_depth=6, min_samples_leaf=100, class_weight=balanced | 0.0435 | 0.0318 | 0.0465 |
| 79 | completo | max_depth=6, min_samples_leaf=20, class_weight=balanced | 0.0426 | 0.0319 | 0.0474 |
| 87 | completo | max_depth=8, min_samples_leaf=100, class_weight=balanced | 0.0422 | 0.0383 | 0.0869 |
| 89 | completo | max_depth=8, min_samples_leaf=400, class_weight=balanced | 0.0418 | 0.0410 | 0.0834 |
| 77 | completo | max_depth=5, min_samples_leaf=400, class_weight=balanced | 0.0402 | 0.0347 | 0.0370 |
| 83 | completo | max_depth=6, min_samples_leaf=400, class_weight=balanced | 0.0394 | 0.0342 | 0.0460 |
| 68 | completo | max_depth=4, min_samples_leaf=20, class_weight=None | 0.0385 | 0.0337 | 0.0803 |
| 78 | completo | max_depth=5, min_samples_leaf=400, class_weight=None | 0.0384 | 0.0354 | 0.0534 |
| 72 | completo | max_depth=4, min_samples_leaf=400, class_weight=None | 0.0376 | 0.0329 | 0.0459 |

Referências de uma coluna nos mesmos anos de validação (AUC-PR): chuva_1d = 0.0311, chuva_3d = 0.0398.

## Resultado no período de teste (2024-01-01 a 2024-12-31)

Modelo escolhido: conjunto `completo`, max_depth=4, min_samples_leaf=20, class_weight=balanced.

| Abordagem | Recall | Precisão | AUC-PR | Alertas (% bairro-dias) | VP | FP | FN | Atendimentos avisados | Dias com atendimento avisados |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Árvore: classe moderado ou alto | 0.801 | 0.034 | 0.046 | 23.2 | 269 | 7720 | 67 | 80/84 | 7/8 |
| Árvore: só classe alto | 0.545 | 0.050 | — | 10.6 | 183 | 3470 | 153 | 57/84 | 7/8 |
| Referência: limiar de chuva do dia | 0.893 | 0.017 | 0.050 | 52.7 | 300 | 17835 | 36 | 84/84 | 8/8 |
| Referência: EstimadorReferencia (regra dos cenários) | 0.250 | 0.050 | 0.019 | 4.9 | 84 | 1589 | 252 | 58/84 | 6/8 |

**Leitura.** Com recall 0.80, a árvore marca 23.2% dos bairro-dias; o limiar de chuva, com recall 0.89, marca 52.7% (praticamente todo dia com alguma chuva). A árvore concentra melhor os avisos, mas o critério combinado antes de abrir o teste é a AUC-PR, e por ele a árvore não supera a referência com folga. Nos diagnósticos, passaria em: teste desde 2022, rótulo amplo (inclui monitoramento de rotina); não passaria em: rótulo sem janela (só o dia do atendimento). Uma conclusão que muda com o período ou com o rótulo indica sinal instável; por isso vale a configuração principal, decidida antes de ver o teste.

Importância dos atributos: chuva acumulada em 7 dias 0.46, histórico de alagamento do bairro 0.33, mês 0.13, chuva acumulada em 3 dias 0.06, maré máxima do dia 0.01, chuva do dia 0.01.

### Regras da árvore (até a profundidade 4)

```
|--- chuva_7d <= 36.1
|   |--- hist_dias_ano <= 0.8
|   |   |--- mes <= 7.5
|   |   |   |--- chuva_3d <= 7.8
|   |   |   |   |--- weights: [37678.8, 11086.1] class: 0
|   |   |   |--- chuva_3d >  7.8
|   |   |   |   |--- weights: [27141.5, 19368.9] class: 0
|   |   |--- mes >  7.5
|   |   |   |--- chuva_1d <= 15.3
|   |   |   |   |--- weights: [60005.5, 3058.2] class: 0
|   |   |   |--- chuva_1d >  15.3
|   |   |   |   |--- weights: [104.4, 382.3] class: 1
|   |--- hist_dias_ano >  0.8
|   |   |--- mes <= 7.5
|   |   |   |--- hist_dias_ano <= 2.0
|   |   |   |   |--- weights: [4715.0, 9684.4] class: 1
|   |   |   |--- hist_dias_ano >  2.0
|   |   |   |   |--- weights: [2893.4, 16055.8] class: 1
|   |   |--- mes >  7.5
|   |   |   |--- hist_dias_ano <= 1.4
|   |   |   |   |--- weights: [3363.2, 509.7] class: 0
|   |   |   |--- hist_dias_ano >  1.4
|   |   |   |   |--- weights: [4701.9, 5989.1] class: 1
|--- chuva_7d >  36.1
|   |--- hist_dias_ano <= 0.2
|   |   |--- chuva_3d <= 24.8
|   |   |   |--- mes <= 2.5
|   |   |   |   |--- weights: [1205.2, 2548.5] class: 1
|   |   |   |--- mes >  2.5
|   |   |   |   |--- weights: [10843.0, 3313.1] class: 0
|   |   |--- chuva_3d >  24.8
|   |   |   |--- chuva_7d <= 129.0
|   |   |   |   |--- weights: [7426.6, 9429.6] class: 1
|   |   |   |--- chuva_7d >  129.0
|   |   |   |   |--- weights: [921.1, 5861.6] class: 1
|   |--- hist_dias_ano >  0.2
|   |   |--- mes <= 7.5
|   |   |   |--- chuva_3d <= 29.6
|   |   |   |   |--- weights: [6152.1, 28543.6] class: 1
|   |   |   |--- chuva_3d >  29.6
|   |   |   |   |--- weights: [3027.4, 55175.8] class: 1
|   |   |--- mes >  7.5
|   |   |   |--- mare_max_m <= 1.4
|   |   |   |   |--- weights: [1367.4, 0.0] class: 0
|   |   |   |--- mare_max_m >  1.4
|   |   |   |   |--- weights: [97.4, 637.1] class: 1

```

## Diagnósticos (não mudam a escolha; só mostram a robustez da conclusão)

### teste desde 2022

Treino ['2014-01-01', '2021-12-31'] (736 positivos), teste ['2022-01-01', '2024-12-31'] (947 positivos). Escolhida pela validação: `completo`, max_depth=4, min_samples_leaf=20, class_weight=None. Publicável: sim.

| Abordagem | Recall | Precisão | AUC-PR | Alertas (% bairro-dias) | VP | FP | FN | Atendimentos avisados | Dias com atendimento avisados |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Árvore: classe moderado ou alto | 0.836 | 0.030 | 0.060 | 25.8 | 792 | 25740 | 155 | 259/262 | 41/43 |
| Árvore: só classe alto | 0.698 | 0.044 | — | 14.6 | 661 | 14377 | 286 | 205/262 | 38/43 |
| Referência: limiar de chuva do dia | 0.930 | 0.013 | 0.051 | 66.1 | 881 | 67189 | 66 | 262/262 | 43/43 |
| Referência: EstimadorReferencia (regra dos cenários) | 0.428 | 0.051 | 0.033 | 7.6 | 405 | 7474 | 542 | 221/262 | 30/43 |

### rótulo sem janela (só o dia do atendimento)

Treino ['2014-01-01', '2023-12-31'] (377 positivos), teste ['2024-01-01', '2024-12-31'] (84 positivos). Escolhida pela validação: `completo`, max_depth=5, min_samples_leaf=400, class_weight=None. Publicável: não (O modelo não supera com folga a referência 'limiar_chuva' no período de teste (AUC-PR 0.059 contra 0.071); a regra simples é preferível.).

| Abordagem | Recall | Precisão | AUC-PR | Alertas (% bairro-dias) | VP | FP | FN | Atendimentos avisados | Dias com atendimento avisados |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Árvore: classe moderado ou alto | 0.869 | 0.018 | 0.059 | 11.9 | 73 | 4031 | 11 | 73/84 | 7/8 |
| Árvore: só classe alto | 0.345 | 0.048 | — | 1.8 | 29 | 580 | 55 | 29/84 | 6/8 |
| Referência: limiar de chuva do dia | 0.988 | 0.006 | 0.071 | 42.3 | 83 | 14456 | 1 | 83/84 | 7/8 |
| Referência: EstimadorReferencia (regra dos cenários) | 0.524 | 0.026 | 0.015 | 4.9 | 44 | 1629 | 40 | 44/84 | 5/8 |

### rótulo amplo (inclui monitoramento de rotina)

Treino ['2014-01-01', '2023-12-31'] (1680 positivos), teste ['2024-01-01', '2024-12-31'] (344 positivos). Escolhida pela validação: `completo`, max_depth=6, min_samples_leaf=20, class_weight=balanced. Publicável: sim.

| Abordagem | Recall | Precisão | AUC-PR | Alertas (% bairro-dias) | VP | FP | FN | Atendimentos avisados | Dias com atendimento avisados |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Árvore: classe moderado ou alto | 1.000 | 0.010 | 0.061 | 100.0 | 344 | 34060 | 0 | 86/86 | 8/8 |
| Árvore: só classe alto | 0.442 | 0.072 | — | 6.1 | 152 | 1956 | 192 | 52/86 | 7/8 |
| Referência: limiar de chuva do dia | 0.930 | 0.016 | 0.054 | 57.8 | 320 | 19578 | 24 | 86/86 | 8/8 |
| Referência: EstimadorReferencia (regra dos cenários) | 0.256 | 0.053 | 0.020 | 4.9 | 88 | 1585 | 256 | 60/86 | 6/8 |


## Saída no produto

`GET /api/v1/risco-alagamento?nivel=bairro` e `climasense.ml.alagamento.risco_por_territorio(db, agora)`:
classe `baixo`/`moderado`/`alto` por bairro para hoje e amanhã (vale a maior), ou `sem_dados` quando falta
chuva completa de algum dia da janela de 7 dias. Fatores em português: chuva do distrito, regras da árvore
que levaram à classe e histórico do bairro. Selo experimental sempre. Sem modelo publicado: `disponivel:
false`, motivo e lista vazia.

## Limitações

- O rótulo é um indicador indireto: atendimento da Defesa Civil não é medição de alagamento, e a
  intensidade do registro muda com a gestão e as campanhas (bairro-dias por ano: 2014: 35, 2015: 41, 2016: 30, 2017: 10, 2018: 53, 2019: 21, 2020: 6, 2021: 3, 2022: 111, 2023: 67, 2024: 84). Ausência
  de registro não prova que não alagou.
- Chuva de reanálise (ERA5, grade de ~25 km) num ponto por distrito: subestima chuva convectiva local.
- No produto, os últimos dias vêm da previsão quando a reanálise ainda não chegou (atraso de ~7 dias);
  o modelo foi treinado com reanálise.
- O modelo salvo é exatamente o validado (treinado até 2023); não foi re-treinado com o teste.

## Pendências

- Conector `recife-alagamento` no ETL (com a regra de critério deste estudo) e carga em `silver.ocorrencias`.
- Pluviômetros APAC/Cemaden (2022+) como atributo de chuva observada; tábua de maré da APAC/Marinha.
- Geometria de bairro para área e faixa hídrica; chamados de drenagem da EMLURB (156) como vulnerabilidade.
- Validar as classes com a equipe do Vigidesastres antes de qualquer uso operacional.
