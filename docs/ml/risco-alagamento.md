# ML acadêmico de alagamento — versão 0.2.0

O ClimaSense estuda a classificação de alagamento por bairro do Recife, com árvore
de decisão e avaliação temporal. **O modelo escolhido permanece o 0.2.0 e não está
validado para uso operacional.** A demonstração acadêmica não equivale a alerta
oficial da Defesa Civil e não autoriza publicação ou mudança do estágio do COP.

## Arquitetura e funcionamento

O módulo `backend/climasense/ml/alagamento/` reúne coleta histórica, construção dos
atributos, avaliação, armazenamento e inferência. O ETL organiza bronze → silver →
gold; o estudo lê a silver ou APIs públicas e grava somente arquivos locais.
A API FastAPI lê o artefato compatível em cache, sem treinar durante requisições.
O frontend React apresenta classes e fatores em português, em uma camada separada
das regras de cenário e da suscetibilidade física do território.

Cada linha de pesquisa é um bairro-dia. As seis variáveis são chuva diária e
acumulada em 3/7 dias, maré máxima astronômica, mês e taxa de dias com atendimento
real anterior ao dia avaliado. O bairro herda a chuva do ponto representativo do
distrito sanitário; isso não mede a chuva em cada rua. Dias incompletos ou com
horas inválidas não viram zero. As classes são baixo, moderado, alto e sem dados;
não são probabilidades nem os estágios oficiais do COP.

O rótulo positivo significa atendimento registrado pela Defesa Civil no bairro
entre D e D+3. A data da vistoria/solicitação pode diferir da data do evento.
Ausência de registro não comprova ausência de alagamento. Os atributos de chuva
realizada até o fim de D tornam a avaliação **retrospectiva**, sem demonstração
de antecedência operacional. Maré é uma aproximação harmônica, sem efeitos de
vento; os primeiros folds ainda têm limitações de disponibilidade temporal.

## Método e preservação científica

A árvore escolhida tem `max_depth=4`, `min_samples_leaf=20`,
`class_weight="balanced"` e `random_state=42`. O treino termina em 2023; o teste
exploratório usa 2024. Há cinco folds de janela temporal crescente, com limiares
ajustados nas pontuações fora da amostra do treino: recall alvo de 80% para a classe
moderado ou alto e de 40% para alto. Esses alvos não são desempenho garantido.
Os cortes excluem rótulos que atravessariam a fronteira entre treino e teste ou
o fim da observação. O histórico do artefato usa registros reais do treino,
sem incorporar os dias positivos expandidos ou os atendimentos do teste.

O bloqueio estatístico exige pelo menos 100 positivos no treino, 30 no teste,
recall de teste ≥ 60% e AUC-PR ≥ 1,10 × a melhor referência simples, com métricas
finitas. Além disso, o artefato retrospectivo permanece `publicavel=false`, com
`avaliacao_operacional=false`: cumprir apenas métricas retrospectivas não basta.
O carregamento verifica versão, contrato de atributos, classes, limiares,
biblioteca e validação. Não houve redução desses critérios nesta entrega.

**2024 já foi consultado várias vezes e não constitui mais um holdout independente
para seleção de modelos.** Nenhum resultado abaixo autoriza ajuste de parâmetros
no teste ou promoção operacional.

## Resultados conferidos

Os [metadados do artefato 0.2.0](resultados/modelo-0.2.0.json) foram extraídos do
arquivo local existente, sem treinamento. O teste abrange 01/01 a 28/12/2024,
34.122 bairro-dias, dos quais 336 positivos. Treino: 1.347 positivos até
28/12/2023. Na classe moderado ou alto: VP=269, FP=7.696, FN=67 e VN=26.090.

| Medida | Definição | Resultado do modelo |
|---|---|---:|
| Recall | VP / (VP + FN): positivos recuperados | 80,06% |
| Precisão | VP / (VP + FP): positivos entre sinalizações | 3,38% |
| Acurácia | (VP + VN) / total: acertos nas duas classes | 77,25% |
| AUC-PR | `average_precision_score`: resumo da relação precisão–recall ao variar o limiar | 0,045971 |

**Recall não é precisão nem acurácia.** A acurácia acima é calculada da matriz de
confusão, não uma evidência de aprovação. Com prevalência de apenas 0,98%, prever
sempre negativo teria aproximadamente 99,02% de acurácia e recall zero. O recall
de bairro-dias com rótulo expandido também não equivale ao recall de eventos
físicos independentes. A referência de chuva tem AUC-PR 0,049624, maior que a árvore.

| Experimento controlado | Original na amostra do experimento | Enriquecido | Conclusão |
|---|---:|---:|---|
| Distrito sanitário como categoria | 0,045971 | 0,045255 | Sem ganho; mesmos recall, precisão e FP |
| Suscetibilidade à inundação SGB, desde 2016 | 0,043979 | 0,044027 | Ganho mínimo, abaixo da referência; sem melhora relevante |
| Picos de chuva em 1h/3h/6h | 0,045971 | 0,045720 | Sem ganho; mesmos recall, precisão e FP |

As colunas são AUC-PR exploratória de teste. Compare apenas as duas variantes
dentro de cada linha: a análise SGB restringe o período de treino a partir de
2016 e não é diretamente equivalente à análise desde 2014, mesmo com o mesmo
ano de teste. A referência de chuva é 0,049624 nas amostras registradas, mas os
limiares e as matrizes de confusão das referências podem diferir entre estudos.
Não se demonstrou significância estatística ou melhoria operacional.

No treino, AUC-PR fora da amostra com distrito foi 0,048270; com SGB passou de
0,039276 para 0,041055; com picos, de 0,048433 para 0,048430. Esses diagnósticos
também não dispensam validação futura. Consulte os [JSON preservados](resultados/README.md)
e os métodos de [distrito](previa-local-e-comparacao.md),
[SGB](experimento-sgb-inundacao.md) e [picos](experimento-chuva-intensa.md).

## Execução e demonstração local

Instale as dependências pelas instruções do [README](../../README.md). Configure
o backend com `AMBIENTE=desenvolvimento` e `ML_PREVIA_EXPERIMENTAL_LOCAL=true`
no `.env` local. Nunca versione esse arquivo. O caminho padrão do modelo é
`tmp/modelos/risco-alagamento-v0.2.0.joblib`; `CLIMASENSE_MODELO_ALAGAMENTO`
permite escolher outro caminho de **arquivo local confiável**. O formato joblib
executa desserialização Python, portanto não aceite artefatos de terceiros.

Para demonstração automática, copie `frontend/.env.example` para
`frontend/.env.local` e defina `VITE_ML_DEMO_ACADEMICA=true`. Reinicie o Vite,
entre como administrador e abra **Simulador**: a tela seleciona Previsão por
distrito, consulta a prévia e abre a camada ML. A chave desligada mantém o fluxo
manual e o botão de prévia local. O frontend também exige ambiente de backend
de desenvolvimento. Build de produção e usuários sem permissão não consultam
a prévia; o backend exige desenvolvimento + flag + permissão `administrar`.

As rotas normais `/api/v1/risco-alagamento` e
`/api/v1/cenarios/impacto-previsto` mantêm o bloqueio científico. Somente
`/api/v1/risco-alagamento/previa-local` pode calcular classes com o artefato
reprovado, com avisos de pesquisa e sem gravar inferências. Em produção, mesmo
com a flag ligada, essa consulta não retorna a prévia (404 para administrador).
Falta de artefato, insumos incompletos e falhas são informadas, sem inventar classes.

Para reproduzir a configuração fixa, se o artefato local estiver ausente, partindo
da raiz e com as dependências instaladas:

```powershell
cd backend
..\.venv\Scripts\python.exe -m climasense.ml alagamento-previa-local --sem-banco
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.comparar_territorio --sem-banco
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.sgb_inundacao
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.comparar_sgb --sem-banco
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.comparar_chuva_intensa --sem-banco
cd ..
```

Esses comandos acessam fontes públicas/cache, gravam arquivos locais e podem
levar tempo; não foram reexecutados na consolidação. `--sem-banco` desativa a
leitura do Postgres, não o acesso à rede. O comando completo
`python -m climasense.ml alagamento` preserva a busca histórica e a geração de
relatórios; use `--saida` e `--modelo` para destinos próprios, pois os padrões
reescrevem o relatório e o artefato locais. Reexecutar fontes atualizadas pode
mudar os resultados; preserve cache, versões de dependências e relatórios para
comparação auditável. Nenhum modelo novo é necessário para esta entrega.

## Limitações e próximos estudos

Desbalanceamento extremo, poucos dias/eventos registrados, cobertura espacial
desigual, chuva distrital e definição dos rótulos limitam o significado dos
resultados. A prévia de hoje/amanhã aplica o artefato aos insumos disponíveis;
o teste retrospectivo não comprova desempenho de previsões emitidas antecipadamente.

Hipóteses futuras: auditar rótulos e datas dos eventos; melhorar resolução e
cobertura espacial; arquivar previsões com instante de emissão; definir alvos
inteiramente futuros; validar em período temporal independente; investigar
outros algoritmos com protocolo pré-definido. São propostas, não implementações
ou resultados obtidos nesta entrega.

O [relatório histórico 0.1.0](risco-alagamento-v0.1.0.md) e
`risco-alagamento-metricas.json` permanecem como evidência antiga, com outra
implementação e amostra. Não representam a versão escolhida nesta consolidação.
