# Experimento local — suscetibilidade à inundação do SGB (Recife)

**Propósito:** criar atributos físicos dos 94 bairros do Recife e comparar, em pesquisa, a árvore de decisão de alagamento do ClimaSense com uma alternativa que utiliza esses atributos. **Não** cria novos alertas oficiais, não altera banco ou artefato operacional, não modifica o front-end. Continua sendo um estudo **não validado**.

## Fonte e semântica

- Serviço público ArcGIS do SGB, camada **Inundação Área**: <https://geoportal.sgb.gov.br/server/rest/services/gestaoterritorial/inundacao/FeatureServer/0>. Filtra `uf = 'PE' AND municipio = 'RECIFE'` e `processo` contendo `inundação`; não mistura deslizamento/enxurrada.
- Produto oficial do Recife: *Carta de suscetibilidade a movimentos gravitacionais de massa e inundação*, CPRM, 2015, escala 1:45.000: <https://rigeo.sgb.gov.br/items/427bc1cc-aff4-4c94-b4cb-24f43bf4eca7>.
- A camada ArcGIS é uma compilação nacional. Antes de interpretar resultados, confira no relatório `anos_informados` e `fontes_declaradas_na_camada` se o subconjunto retornado é coerente com a carta municipal.
- Suscetibilidade física **não** é ocorrência observada, probabilidade de inundação, estágio do COP ou previsão. A base de rótulos do ML contém *atendimentos registrados* pela Defesa Civil, não todo alagamento ocorrido.

## Execução no Windows

Com o projeto atual **já** contendo a integração ML versão 0.2.0, abra um terminal na pasta `backend` e execute:

```powershell
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.sgb_inundacao
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.comparar_sgb
```

A primeira linha busca **somente Recife** no serviço oficial, valida os polígonos, cruza com a malha oficial local dos 94 bairros e gera arquivos ignorados pelo Git:

- `tmp/experimentos/sgb_inundacao_recife.geojson` — cache da consulta filtrada;
- `tmp/experimentos/sgb_inundacao_por_bairro.csv` — uma linha por bairro;
- `tmp/experimentos/sgb_inundacao_qualidade.json` — cobertura, descartes, conflitos de classes e proveniência.

Para refazer a consulta com dados novos:

```powershell
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.sgb_inundacao --atualizar-fonte
```

Para usar um GeoJSON previamente obtido do mesmo serviço:

```powershell
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.sgb_inundacao --fonte-geojson "C:\caminho\sgb_recife.geojson"
```

A segunda linha usa a tabela local gerada, reconstrói a base de pesquisa existente e grava `tmp/experimentos/comparacao_sgb.json` com AUC-PR fora da amostra da validação temporal, métricas de teste, recall, precisão, falsos positivos, importância das features e referência de chuva. Não salva `.joblib` e não treina por requisição HTTP.

## Variáveis e cruzamento espacial

Com Shapely e projeção métrica **EPSG:31985**, para cada bairro:

- `sgb_frac_alta`: fração da área total do bairro coberta pela classe **Alta**;
- `sgb_frac_media`: fração da área total do bairro coberta pela classe **Média**, desconsiderando sobreposição com **Alta**;
- `sgb_cobertura`: fração do bairro coberta por **qualquer classe**;
- `sgb_sem_carta`: indicador de **ausência de cobertura** (1 = sem carta). Nas frações não cobertas, a informação é `NaN`, **nunca zero**.

Também é calculada `sgb_frac_baixa` para auditoria, mas ela não entra no primeiro experimento por redundância com cobertura e demais classes. Polígonos sobrepostos da mesma classe são unidos e, entre classes, têm prioridade Alta > Média > Baixa; a área de conflito é registrada no relatório.

## Comparação justa e limitações

- **Mesmas linhas, separação temporal e parâmetros** nos modelos A (seis features) e B (seis features + quatro atributos do SGB).
- Pesquisa a partir de **2016**, para não retroagir a informação cartográfica publicada em 2015.
- `SimpleImputer` ajustado separadamente em cada **fold de treinamento**; sem ver dados do período de validação/teste para imputar.
- Parâmetros fixos da experiência anterior: `max_depth=4`, `min_samples_leaf=20`, `class_weight='balanced'`, `random_state=42`.
- A medida principal para escolher novas features deve ser a AUC-PR **out-of-fold no treinamento**, não o teste 2024 já consultado repetidamente. **Os resultados no teste 2024 são exploratórios**, não um novo holdout independente.
- Mesmo que o B tenha AUC-PR maior, **não** promover diretamente o modelo a operacional. Validar em outro período independente, idealmente com previsões meteorológicas históricas emitidas antes dos eventos, e manter o gate científico.
- A informação SGB é estática; não transforma automaticamente previsões atuais por distrito em valores meteorológicos medidos em cada bairro.

## Resultado preservado

Os [resultados existentes](resultados/comparacao_sgb.json) usam 274.386 linhas
de treino desde 2016 e 34.122 de teste, com 1.064 e 336 positivos.
A [auditoria espacial](resultados/sgb_inundacao_qualidade.json) registra
90/94 bairros com carta, ano declarado 2014 e campo entre 2012 e 2014;
2015 refere-se à publicação da carta. Ausência de carta nos outros quatro
bairros permanece desconhecida.

Na mesma amostra SGB, AUC-PR original **0,043979** e enriquecida **0,044027**;
AUC-PR fora da amostra no treino **0,039276** e **0,041055**. O ganho de teste
é mínimo e ambas ficam abaixo da chuva simples (**0,049624**).
No limiar calibrado, recall 100% nas duas variantes, precisão 1,62%/1,65%
e FP 20.413/19.986: esses números não descrevem o artefato original 0.2.0
treinado desde 2014. Não houve melhoria relevante para a entrega nem
validação operacional. O modelo 0.2.0 foi mantido sem incorporar SGB.

## Testes locais

```powershell
..\.venv\Scripts\python.exe -m pytest tests/unit/ml/test_sgb_inundacao.py
```

Os testes utilizam polígonos inventados **somente para testes**, não alimentam os dados da aplicação. Sem alterações no Neon, MongoDB ou Alembic.
