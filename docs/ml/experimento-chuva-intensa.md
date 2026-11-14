# Experimento controlado: chuva máxima em janelas de 1h, 3h e 6h

## Pergunta

Na mesma amostra de bairros/dias e mantendo os hiperparâmetros da árvore, o acréscimo de **picos de precipitação de curta duração** melhora a AUC-PR ou reduz falsos alertas em comparação ao modelo de seis atributos?

## Contexto

- **Fonte**: chuva horária histórica de Open-Meteo ERA5, reaproveitando `climasense.ml.alagamento.clima.chuva_horaria`; leitura opcional da `silver` e complementação por cache/API, sem escrever em bancos.
- **Motivação local**: a APAC publica mapas de chuva em intervalos de 1h, 3h, 6h etc. A escolha das janelas é meteorologicamente plausível, não comprova eficácia preditiva.
- **Unidade**: distrito sanitário, cujo valor é herdado pelos bairros correspondentes conforme o contrato atual do estudo.
- **Definição**: `chuva_pico_1h`, `chuva_pico_3h` e `chuva_pico_6h` = **maior soma em mm de uma janela móvel contínua de 1, 3 ou 6 horas que TERMINE durante o dia local D**. É uma soma acumulada, não taxa em mm/h. As janelas podem atravessar meia-noite.
- **Disponibilidade temporal**: as 24 horas de D e as cinco horas imediatamente anteriores precisam estar presentes e válidas. Ausência de hora não vira 0; o dia completo é excluído da comparação.

## Segurança e limites

1. A implementação é pesquisa local: não altera `.env`, o artefato de inferência 0.2.0, o frontend, o gate científico ou bancos remotos.
2. Teste com ano de 2024 é EXPLORATÓRIO, pois já foi consultado. Não constitui holdout novo; avaliar em período posterior independente antes de afirmar generalização.
3. O estudo atual utiliza atributos de chuva REALIZADA até o FIM de D e rótulos de atendimentos entre D e D+3. Portanto, é **um diagnóstico retrospectivo, não uma previsão antecipada**. Para previsão operacional é necessário alinhar data/hora de emissão, leads, previsão arquivada e rótulo inteiramente futuro.
4. `hist_dias_ano` herda as limitações do registro de atendimento e da taxa histórica anterior; positivo = atendimento registrado, não alagamento físico confirmado.
5. Os picos representam chuvas espaciais em escala de distrito, não pluviômetros de cada rua ou bairro; eventos localizados podem não ser capturados.
6. Mantém `max_depth=4`, `min_samples_leaf=20`, `class_weight="balanced"` e `random_state=42`, com folds temporais e limiares calibrados nos folds do treino. O ano de teste nunca participa de treinamento nem ajuste de limiar.
7. Sem ganho contra referência não promover o modelo. O gate operacional segue intacto.

## Como executar

O experimento já está integrado ao código. Partindo da raiz:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/unit/ml/test_chuva_intensa.py -q
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.comparar_chuva_intensa
```

Alternativa para fonte de chuva sem consultar o Postgres:

```powershell
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.comparar_chuva_intensa --sem-banco
```

Esse comando ainda acessa os dados públicos, se não houver cache local, e pode realizar processamento extenso na primeira execução.

O relatório é criado em `tmp/experimentos/comparacao_chuva_intensa.json`.

## Resultado preservado

A [execução existente](resultados/comparacao_chuva_intensa.json) comparou as mesmas
377.692 linhas completas, sem exclusões por picos ausentes (100% de cobertura).
Após cortes temporais: 343.006 linhas de treino e 34.122 de teste, com 1.347 e
336 positivos. AUC-PR de teste: original **0,045971**, picos **0,045720**;
fora da amostra no treino: **0,048433** e **0,048430**. Ambos tiveram recall
80,06%, precisão 3,38% e 7.696 FP no limiar moderado ou alto. A referência de
chuva diária atingiu AUC-PR **0,049624**. Não houve melhoria relevante e o
modelo 0.2.0 foi mantido. Não foi repetido treinamento nesta consolidação.

## Como interpretar

- `qualidade_dados.cobertura_pct_dentre_originais`: se muito abaixo de 100%, investigar horas ausentes antes de interpretar a comparação.
- `modelo_original_mesma_amostra` e `modelo_com_picos_mesma_amostra`: comparação justa por mesma amostra e rótulos.
- `auc_pr_oof_treino`: evidência exploratória preferível para comparar intervenções sem olhar o teste.
- `metricas_teste_exploratorio`: 2024 já consultado várias vezes; use apenas como diagnóstico, não para selecionar parâmetros.
- `topk_exploratorio`: fração de **bairro-dias rotulados positivos** recuperados entre 10 ou 20 bairros por dia. Não confundir com recall de eventos reais e não utilizar para liberar produção.
- `referencia_chuva_1d_mesma_amostra`: chuva diária simples, na mesma amostra. É uma comparação parcial; o gate oficial considera outras referências também.

## Fontes de documentação pública

- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo Previous Runs API: https://open-meteo.com/en/docs/previous-runs-api
- APAC — chuva em janelas 1/3/6 horas: https://geoportal.apac.pe.gov.br/server/rest/services/met_monitoramento_chuvas_pe/MapServer
- *Rainfall thresholds model for predicting urban local pluvial flooding* (2025): https://www.sciencedirect.com/science/article/pii/S221458182500480X
