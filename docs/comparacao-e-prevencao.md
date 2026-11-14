# Comparação meteorológica e sinalizações preventivas

O Simulador conserva a inserção manual e oferece **Previsão por distrito** com
calendário das próximas 72 horas. A tela Chuva tem um link direto para essa análise.
O calendário permite escolher uma data, ver a chuva distrital em milímetros e
destacar seus bairros no mapa. São indicações internas de atenção, não alertas
oficiais da Defesa Civil, confirmação de ocorrência ou estimativa de pessoas atingidas.

## Fluxo e fontes

O fluxo reutiliza `GET /api/v1/cenarios/impacto-previsto`, a série Open-Meteo
armazenada, os parâmetros de estágio, o domínio do simulador e o mapa existente.
O parâmetro opcional `dia=AAAA-MM-DD` escolhe um dia do calendário retornado.
Sem ele, `horizonte_h=6|12|24|72` mantém a análise contínua anterior.
Uma data fora da janela retorna 422; ao expirar a data selecionada, a interface
volta à análise contínua. Formato de data inválido também retorna 422.

A API retorna `dias`, `dia_selecionado`, `sinalizacao_preventiva` nos territórios e
`comparacoes_recentes`, além dos campos anteriores. Datas, cobertura, critérios,
emissão/captura, validade e metadados acompanham os resultados. Nenhum endpoint,
tabela, dependência, migração ou agendamento novo foi criado. A leitura das
previsões é agrupada por distrito; os bairros herdam o ponto representativo do
seu próprio distrito. A seleção não recarrega a malha territorial em cada consulta.

O frontend usa a consulta viva existente: renova a cada minuto enquanto aberto,
com pausa de atualizações em segundo plano e revalidação ao voltar à aba.
Selecionar uma data troca a consulta e atualiza classes, legenda e lista do mapa.
Não há notificações externas, WhatsApp, SMS ou execução de ETL por esse fluxo.

## Dias e limites meteorológicos

São considerados 72 intervalos horários completos a partir da hora atual, quando
exata, ou da próxima hora cheia. A fração já iniciada da hora corrente não é
apresentada como uma hora inteiramente futura. Os intervalos são divididos pelo
calendário de **Recife, UTC−3**. Dependendo do horário, aparecem três ou quatro
datas; o primeiro e o último dia podem representar somente parte do dia local.
O início, fim e número de horas deixam essa diferença explícita.

Usam-se os parâmetros existentes `chuva_prev_24h_{atencao,alerta,critico}_mm`,
carregados do serviço de estágios. Os padrões atuais são 25/50/90 mm e não foram
alterados. Valores exatamente no limiar já o atingem; não se arredonda a soma
antes de decidir. A configuração vigente aparece na tela e na resposta.

- **Período completo e recente:** soma as horas esperadas daquela fatia do dia,
  sem multiplicar a soma parcial para simular 24 h. A comparação com limites
  de 24 h sobre uma fatia menor é uma indicação conservadora de ultrapassagem.
- **Lacunas, duplicatas ou horas inválidas:** não viram zero. `chuva_prevista_mm`
  fica nula, e `chuva_disponivel_mm` mostra somente o subtotal conhecido.
  Se esse subtotal já atingiu atenção, pode sinalizar **pelo menos** o nível
  observado; caso contrário retorna `sem_dados`, nunca ausência de risco.
- **Sem emissão ou emissão vencida:** não produz sinalização atual. Uma captura
  Open-Meteo com mais de 6 h, ou futura em relação à consulta, é recusada.
  Os valores arquivados podem aparecer com a marca de desatualização.

A sinalização meteorológica não depende de histórico carregado, maré ou ML.
Todos os bairros dos distritos sinalizados podem ser vistos em **Atenção
preventiva**. A classificação territorial por regras continua separada: aplica
`classificar_bairro` à chuva daquele período, ao histórico do bairro e à maré
completa e recente quando disponível. Pode continuar `sem_dados` se faltar o
histórico; isso não apaga a ultrapassagem meteorológica conhecida.

Observação APAC atual de 72 h não é usada como se fosse a chuva antecedente de um
dia futuro. Maré ausente ou incompleta não bloqueia a sinalização de chuva;
seus efeitos territoriais ficam sem avaliação. O horizonte contínuo preserva
os gatilhos acumulados de 24/72 h anteriores, sem alterar a simulação manual.

## Open-Meteo × ClimaSense e APAC

**Open-Meteo alimenta o ClimaSense.** O quadro por data compara o insumo de chuva
e sua interpretação territorial: chuva, sinalização meteorológica, regras e ML
quando o período for compatível. Não são duas previsões independentes de chuva.
Para a janela futura selecionada ainda não há medição APAC correspondente;
a interface informa isso, sem usar acumulados passados como confirmação futura.

O quadro recolhido **APAC observada × previsão arquivada na mesma hora** permite
conferir a última leitura de 1 h do distrito quando houver dados armazenados:

1. Só usa leituras do próprio distrito, com leitura e coleta anteriores à consulta,
   nas últimas 2 h (mesma tolerância de medições APAC usada no serviço existente).
   Em empate de horário, conserva o maior valor das estações, com nome informado.
2. O fim da janela deve ser uma hora exata. Não arredonda nem rateia uma janela
   móvel de estação terminada, por exemplo, às 12:10 para compará-la a 11–12 h.
3. A previsão deve cobrir exatamente aquela hora no mesmo distrito, com emissão
   e coleta já disponíveis antes do começo do intervalo observado. Uma previsão
   atual com horas passadas incluídas não vale como previsão arquivada anterior.
4. Sem correspondência, mostra a medição com o motivo e mantém a previsão
   comparável nula. Sem leitura recente, informa indisponibilidade.

O ponto distrital previsto e o pluviômetro têm representatividade espacial
diferente. Essa conferência não calcula acurácia, habilidade preditiva ou métricas
de validação; seria necessário um histórico pareado e protocolo independente.

Os metadados mostram a última atualização da fonte e seu frescor. A leitura APAC
tem também o horário de medição/coleta; a previsão mostra sua captura. Na
integração atual, `emitido_em` da Open-Meteo é a captura pelo ETL, não o horário
de inicialização do modelo meteorológico. Atualização da fonte não garante
completude de cada território ou período.

## ML 0.2.0 e segurança

O artefato, seus pesos, métricas e experimentos foram preservados. Não houve
treinamento ou otimização. Recall de aproximadamente 80% não é acurácia nem
precisão; a versão segue sem validação operacional. Consulte o
[estudo científico](ml/risco-alagamento.md).

O serviço pode avaliar separadamente um dia local completo de hoje ou amanhã,
sem combinar máximos de dias diferentes na comparação. O modelo não classifica
dias posteriores ou fatias parciais como se fossem o mesmo período. A interface
não consulta a prévia para recortes parciais. O modo agregado anterior de
hoje/amanhã continua disponível no horizonte contínuo, com seu significado indicado.

A rota `/risco-alagamento/previa-local` aceita `dia` opcional e conserva os três
bloqueios: desenvolvimento, flag local e permissão administrativa. O frontend
também exige desenvolvimento e permissão; build de produção não consulta a prévia.
O parâmetro de data não relaxa publicação, autorização ou critérios científicos.

## Revisão e simplificação do incremento anterior

A base foi `71c9255`, comparada com `main`, sem alterar ou sincronizar `main`.

- Removidos o estado redundante de acompanhamento e as duas consultas periódicas
  paralelas no detalhe da fonte. Um único acompanhador já monitora a execução;
  os metadados e o histórico são renovados ao concluir. O botão continua impedindo
  disparos duplicados e as falhas mantêm feedback.
- Preparação de dias e bloqueio de inferência foram separados em funções menores,
  sem calcular o horizonte contínuo para depois sobrescrever seus insumos diários.
  A sinalização e a classificação territorial compartilham a série lida uma vez.
- Mantidos os scripts opcionais de operação/agendamento e os ETLs existentes:
  podem ter referências em instalações externas. Eles não são necessários para a
  nova interface e não foram executados, ativados ou substituídos por infraestrutura nova.
- Mantidas a migração `0025`, a CLI e a persistência explícita por compatibilidade,
  pois não se presume que a migração nunca foi aplicada. A nova interface é só
  leitura e não depende da tabela de inferências. O gravador rejeita recortes diários.
- Preservados os documentos e JSON científicos como histórico. Este documento
  descreve o fluxo atual; OpenAPI e tipos TypeScript foram sincronizados a partir
  do contrato real, sem criar um segundo contrato manual para os dados novos.

## Iniciar e verificar

Com dependências e `.env` já configurados conforme o [README](../README.md):

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

Entre na área da equipe e abra **Chuva → Ver dias de chuva intensa…**, ou
**Simulador → Previsão por distrito**. Escolha uma data no calendário acima do
mapa. Confira a legenda **Atenção preventiva**, a lista de bairros, o quadro de
comparação e seus horários. Alterne para **Estágio** para ver a classificação
territorial e para **Cenário hipotético** para continuar inserindo premissas manuais.

As fontes precisam já ter dados disponíveis no banco. Iniciar `dev.ps1` não
executa ETL. Sem dados, aparecem datas com dados insuficientes; não são inventadas
previsões. A configuração da prévia acadêmica continua no
[guia de ML](ml/risco-alagamento.md#execução-e-demonstração-local).

## Validação e limites

Os testes usam fixtures, mocks e API ASGI local; os testes de navegador interceptam
as respostas. A captura `tmp/operacao-local.json`, quando disponível, é somente
reproduzida, sem repetir o ETL que a produziu. As geometrias artificiais do teste
de seleção servem apenas à regressão do mapa, sem alimentar dados reais.

Validações executadas nesta branch:

| Verificação | Resultado |
|---|---|
| Backend isolado, incluindo contrato HTTP e ML | 1.184 testes passaram; 216 testes de Atlas/integração excluídos |
| Frontend Vitest | 261 testes passaram em 29 arquivos |
| Ruff lint e format | Aprovados |
| ESLint e Prettier | Aprovados |
| TypeScript e build Vite | Aprovados, incluindo o build usado no Playwright |
| OpenAPI | Exportação verificada; tipos TypeScript sincronizados |
| Playwright desktop e celular | 4 testes passaram, incluindo seleção de dias, mudança de cores, comparação, acessibilidade e retorno manual |
| Evidências científicas | Hash do artefato e conteúdo dos relatórios preservados |
| Diff | `git diff --check` sem erros |

Na raiz, sem URLs de bancos de teste:

```powershell
.\.venv\Scripts\python.exe scripts/testar_backend_local.py -q -m "not atlas and not integracao"
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
.\.venv\Scripts\python.exe scripts/exportar_openapi.py --verificar
cd frontend
npm test
npm run lint
npm run build
npm run e2e -- --grep "previsão por distrito preserva|apresenta previsão real dos oito"
cd ..
git diff --check
```

O segundo cenário de navegador é ignorado se faltar a captura local preexistente.
Nesta execução a captura estava disponível; os quatro casos passaram. Foram
inspecionadas imagens de desktop e celular. O teste usa geometria artificial
para isolar as cores e a seleção; tiles de rua externos não foram validados.
Avisos existentes de Canvas/jsdom, React Router, TestClient/httpx, Node e tamanho
de chunks do Vite não impediram as verificações.

Não foram
executados testes que recriam esquemas PostgreSQL ou acessam Atlas, nem migrações,
ETLs, persistência ou tarefas agendadas. A consulta SQL nova tem cobertura isolada
e de contrato HTTP, mas não foi exercitada contra PostgreSQL nesta tarefa.
Não houve validação científica de previsões futuras ou pareamentos meteorológicos
com provedores ao vivo. Limites de cobertura espacial, rótulos e desbalanceamento
do ML continuam valendo.
