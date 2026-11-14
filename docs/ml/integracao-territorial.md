# Integração territorial de ML — diagnóstico e execução

> Registro da etapa anterior de integração, preservado com seu contexto e evidências.
> O diagnóstico de árvore limpa abaixo antecede as alterações recebidas nesta tarefa.
> A entrega atual usa o modelo 0.2.0 não operacional, com prévia acadêmica configurável;
> consulte [o estudo vigente](risco-alagamento.md) e a [consolidação](consolidacao-academica.md).

## Diagnóstico anterior às alterações

Árvore de trabalho limpa em `git status --short` e `git diff --stat`.

| Intervenção | Classificação | Arquivos/componentes | PRD |
|---|---|---|---|
| Preservar autenticação, mapas, ETL, estágios e cenário manual | MANTER | auth, território, conectores, domínio do simulador | RF-20, RF-23–29 |
| Corrigir histórico real, intervalo temporal e contrato do artefato | CORRIGIR | ml/alagamento/base.py, modelo.py, estudo.py, armazenamento.py, servico.py | RN-01, RN-07, RN-11 |
| Consumir previsão por distrito, sem replicar o máximo municipal | INTEGRAR | serviços de cenários/simulador e rota de impacto | RF-23–25, RF-36, RF-38 |
| Mostrar suscetibilidade e exposição separadas do perigo | INTEGRAR | silver existente, simulador e mapa existente | RF-22, RF-25, RF-37–38 |
| Distinguir previsão atual de hipótese manual e explicar indisponibilidade | INTEGRAR | frontend/features/simulador | RF-19, RF-20, RF-42 |
| Registro acumulativo e idempotente, com leitura gold derivada da silver | CRIAR | migração incremental e persistência explícita | RF-19, RF-27, RF-42 |
| Testes de paridade, isolamento, falhas e integração | CRIAR | testes de backend/frontend | RNF-09–11 |

O estudo v0.1.0 (relatórios originais preservados) foi reprovado: AUC-PR 0,046 versus
0,050 da referência. `hist_dias_ano` usa dias reais no treino, mas o artefato conta dias
positivos da janela expandida. Os cortes anuais precisam de intervalo compatível com
essa janela. Reanálise do próprio dia e maré ajustada posteriormente não demonstram
antecedência operacional. A versão corrigida exige nova avaliação e não herda aprovação.

Conectores e tabelas não comprovam carga no banco: nesta implementação não se consultam
Atlas/Neon do grupo. Dados ausentes permanecem ausentes. A malha dos 94 bairros já existe;
o modelo de deslizamento não existe. A análise correspondente será sobreposição explicável.
Arboviroses e população permanecem contexto, sem previsão causal ou índice composto novo.

Não exigem alteração: autenticação, papéis, identidade visual, mapas Leaflet base,
conectores meteorológicos, migrações anteriores, relatórios históricos gerados e bancos remotos.

## Arquitetura implementada

```text
Open-Meteo / APAC → ETL existente → bronze → silver
                                            ↓
                         emissões por distrito disponíveis no instante da análise
                                            ↓
                       janelas horárias completas + histórico territorial
                                            ↓
                      regras existentes + ML condicionado ao gate
                                            ↓
                    GET /cenarios/impacto-previsto → mapa e simulador existentes

CLI explícita prever-impacto --persistir → silver.inferencias_impacto
                                                   ↓
                                      view gold.previsoes_impacto
```

A requisição HTTP não grava inferências nem treina. O endpoint é protegido pela permissão
`consultar`, usa o envelope existente e acrescenta campos opcionais aos itens. As permissões de sessão
e sua renovação permanecem intactas. O cenário manual não consulta ML: sua entrada é uma hipótese
uniforme, identificada na tela. A previsão atual mantém os valores de cada distrito, e cada bairro
herda somente os do distrito correto. As somas são calculadas das horas reais, sem distribuir a
chuva uniformemente. A maré é avaliada perto do pico, e a carta SGB é contexto, sem novo índice ou peso.

São registrados: snapshot da previsão, validade, horizonte, fonte, observação APAC, número de estações, histórico,
parâmetros e séries usadas. Uma janela incompleta, emissão futura ou chuva vencida não vira zero.
Previsão de chuva exige emissão com até 6 h; maré, até 24 h; leitura APAC, até 2 h. Sem estação própria
do distrito, a chuva observada fica ausente. A ausência da tabela opcional SGB é tratada como falta de
dado. Cobertura parcial da carta é informada, não interpretada como terreno seguro.

O motor de regras mantém as classes e a ordenação existentes. ML é avaliação diária paralela de hoje
e amanhã, não equivalente a todos os horizontes horários das regras; não muda estágio declarado nem
emite alertas. Arboviroses continuam contexto. População e equipamentos representam exposição
potencial de residentes/estabelecimentos, nunca quantidade prevista de atingidos.

## Integridade do ML

- Algoritmo preservado: `DecisionTreeClassifier`, `random_state=42`, grade original, sem ajuste pelo teste.
- Mesmas seis features e ordem canônica; matrizes de treino tipadas como float.
- Versão `0.2.0`, contrato de atributos `2-dias-reais-anteriores`. Artefatos `0.1.0` não são aceitos.
- Histórico salvo somente com dias reais de atendimento do treino; a inferência usa somente datas
  anteriores ao dia avaliado. O histórico fica congelado no treino, com limitação explícita.
- Intervalo de segurança igual à janela de rótulo em treino/teste e folds; fim da amostra sem seguimento
  suficiente fica excluído da avaliação. A consulta de inferência exclui coleta/emissão posteriores ao instante.
- `joblib` preserva estimador, atributos, limiares, territórios, histórico, períodos, métricas e versões do ambiente.
  Carregamento rejeita arquivo inválido, contrato incompatível e publicação sem critérios estatísticos ou
  evidência operacional. Apenas arquivos locais confiáveis devem ser carregados.
- Critérios originais mantidos: 100 positivos no treino, 30 no teste, recall ≥ 0,60 e AP ≥ 1,10 × a referência.
  Métricas ausentes/não finitas também reprovam. O gate é conferido ao carregar artefato marcado como publicável.
- Reanálise do próprio dia não prova antecedência operacional. O ajuste da maré foi limitado a antes do teste
  principal, mas ainda é posterior aos primeiros folds. Esse estudo é explicitamente retrospectivo e permanece
  **não publicável**. Não há transferência da aprovação de outro artefato nem opção de forçar publicação na CLI.
- Relatórios novos são gerados em `docs/ml/v0.2.0/`; os relatórios históricos não foram editados manualmente.
  O cache novo dos CSVs conserva somente data, bairro e categorias necessárias, sem endereço/localidade.
  Nenhum cache ou lote remoto antigo foi apagado.

As métricas reais disponíveis continuam sendo as históricas: recall 0,801, precisão 0,034 e AP 0,046
contra AP 0,050 da referência. Não são métricas da versão corrigida. A execução real com
`--sem-banco --sem-diagnosticos` foi tentada, mas o CKAN da Defesa Civil respondeu **HTTP 503** antes do
download. Nenhum novo modelo ou relatório de desempenho real foi produzido. Testes sintéticos de
equivalência são evidência de engenharia, não evidência de qualidade preditiva operacional.

## Banco de dados

A migração incremental **0025**, com predecessor fixo **0024**, cria:

- `silver.inferencias_impacto`: inserções acumulativas de resultados horários das regras.
- `gold.previsoes_impacto`: view sobre a silver, preservando a propriedade de derivação da gold.
- Restrição única por SHA-256 da entrada lógica, método, versão, território, horizonte e resultado.
  A hora de geração é excluída da chave; repetir a mesma avaliação não duplica a inferência.
- Gatilhos impedem UPDATE, DELETE e TRUNCATE; `climasense_app` recebe SELECT/INSERT na silver e SELECT na view.

`data_previsao` é geração; `emitido_em_fonte` conserva o nome do contrato, mas na integração atual Open-Meteo
corresponde à captura pelo ETL (`ctx.agora`), **não** à inicialização do modelo meteorológico do fornecedor.
Essa limitação aparece na API e na tela. `inicio_validade/fim_validade`
delimitam a janela analisada. Os insumos persistidos permitem reconstruir as regras da rodada.
O código não grava cenário manual nem ML reprovado na tabela. O resultado diário do ML também não é
gravado como se fosse uma inferência horária equivalente. Não se reutiliza o esquema legado de vacinação.
O verificador dos agregados gold existentes permanece inalterado.

**Ambiente verificado:** PostgreSQL 16 local descartável em `127.0.0.1:55432`, dentro de `tmp/postgres`.
Foram verificadas subida/descida da migração, leitura pela view, 188 linhas de teste (94 bairros × 2 tipos),
repetição sem novas linhas e bloqueio de alteração/exclusão. As fontes usadas nos testes são artificiais,
restritas ao banco descartável. Nenhuma migração ou carga foi executada no Neon/Atlas do grupo.

Consulta de verificação após aplicação revisada da migração e execução explícita da rotina:

```sql
SELECT territorio_id, distrito_id, tipo_impacto, metodo, versao_modelo,
       classe_resultado, confianca_qualitativa, status_validacao,
       data_previsao, emitido_em_fonte, inicio_validade, fim_validade
FROM gold.previsoes_impacto
ORDER BY data_previsao DESC, id DESC
LIMIT 100;
```

Essa consulta não implica que existam registros no Neon: nesta entrega só o banco local foi usado.

## Comandos de operação e teste

Na raiz, o runner isola as configurações ANTES da importação da API, desabilita `.env` e remove URLs
herdadas. `--postgres-local` aponta exclusivamente para o banco descartável citado; as fixtures o recriam.
Não apontar testes destrutivos de migração para um banco de aplicação.

```powershell
.\.venv\Scripts\python scripts/testar_backend_local.py -q tests/unit/ml
.\.venv\Scripts\python scripts/testar_backend_local.py --postgres-local -q tests/integration/test_impacto_territorial.py
.\.venv\Scripts\python scripts/testar_backend_local.py --postgres-local -q
.\.venv\Scripts\ruff check backend scripts/testar_backend_local.py
.\.venv\Scripts\ruff format --check backend scripts/testar_backend_local.py
```

Dentro de `backend`, com configuração apropriada ao ambiente desejado:

```powershell
# Treino explícito, sem banco; salva via estudo.salvar/armazenamento.salvar, gera relatório versionado.
..\.venv\Scripts\python -m climasense.ml alagamento --sem-banco --sem-diagnosticos
# Somente consulta das previsões já armazenadas. Requer acesso de leitura ao banco configurado.
..\.venv\Scripts\python -m climasense.ml prever-impacto --horizonte 24
# Gravação explícita: requer 0025 aplicada e permissão de inserção. Não foi executado no grupo.
..\.venv\Scripts\python -m climasense.ml prever-impacto --horizonte 24 --persistir
```

Carregamento e equivalência são exercitados pelos testes `tests/unit/ml/test_integridade.py`.
O teste usa arquivo temporário e compara pontuações, classes, métricas e metadados após o carregamento.
Não baixa nem carrega modelos de terceiros.

Atualização das fontes permanece na CLI existente, para execução deliberada pelo responsável:

```powershell
python -m climasense.etl run open-meteo-previsao
python -m climasense.etl run open-meteo-mare
python -m climasense.etl run apac-chuva
```

Esses comandos de ETL escrevem nos bancos configurados e **não foram executados nesta entrega**.

No frontend:

```powershell
npm run lint
npm test
npm run build
npx playwright test tests/e2e/impacto-territorial.spec.ts --reporter=line
```

O teste de navegador intercepta toda a API, roda em desktop/celular, verifica ausência de overflow,
preservação do Leaflet, troca de contexto, retorno ao cenário manual e acessibilidade.
Na máquina desta execução, foi necessário iniciar o preview já compilado com
`node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4173 --strictPort`, pois o iniciador
encadeado do Playwright falhou. O projeto usa Node 22 como referência; nesta máquina foi usado Node 26.13.1.

## Exemplo de contrato e limites

`GET /api/v1/cenarios/impacto-previsto?horizonte_h=24` devolve o envelope existente:

```json
{
  "dados": {
    "contexto": "previsao_atual",
    "experimental": true,
    "ml_alagamento": {
      "disponivel": false,
      "motivo": "Modelo ausente, inválido ou incompatível. É necessária avaliação da versão corrigida.",
      "modelo": null,
      "itens": []
    },
    "itens": [],
    "resumo": {},
    "calculado_em": "<instante UTC>",
    "tempo_calculo_ms": 0
  },
  "meta": { "fontes": ["<metadados das fontes>"], "avisos": ["<limitações>"] }
}
```

O trecho acima é esquemático: listas e metadados foram abreviados, não é resposta de produção.
No teste integrado a API entrega os itens com o formato OpenAPI gerado, dados insuficientes e fontes.
Não há endpoint novo de escrita; salvar cenário manual continua em `POST /cenarios`.

Pendências científicas: reexecutar o estudo quando a fonte responder; obter emissões meteorológicas históricas
para validar antecedência; resolver o ajuste temporal da maré nos primeiros folds; melhorar rótulos e cobertura;
validar gatilhos com o cliente. Suscetibilidade não é modelo supervisionado de deslizamento. Hospedagem,
licenças, mapa bairro–rio e dados não públicos continuam sujeitos às decisões já registradas no PRD.

## Verificações executadas

| Verificação | Evidência |
|---|---|
| Linha de base antes das alterações | Frontend: 241 testes passaram. Backend unitário: 1.076 passaram, quatro falharam. |
| Suíte completa com PostgreSQL local e UTC | 1.319 passaram, quatro falharam; todas as integrações passaram. |
| Última validação focada após endurecimento de artefatos/serialização | 59 testes passaram: ML, API territorial, persistência, migração e permissões. |
| Ruff | `check` e `format --check` passaram; 266 arquivos verificados. |
| Frontend final | Lint passou; 244 testes passaram; TypeScript e build Vite passaram. |
| Playwright | Dois testes passaram, desktop e celular, com acessibilidade e sem overflow. |
| Persistência real em banco descartável | 188 inserções, zero na repetição; leitura por outra sessão confirmou persistência; limpeza exclusiva do banco de teste. |
| Histórico do experimento | Relatórios originais sem diff; nenhuma métrica real nova inventada. |
| Preservação | Nenhuma exclusão de arquivo versionado; nenhuma dependência de projeto alterada; nenhum joblib versionado. |

As quatro falhas reproduzidas desde a linha de base não foram ocultadas nem tiveram suas asserções enfraquecidas:

1. `test_validacao_em_portugues.py::test_resposta_422_traz_mensagem_em_portugues`: a dependência de banco ausente
   responde 503 antes da validação do corpo esperada pelo teste (422).
2. `test_conectores_saude_historico.py::test_atlas_csv_sem_registro_do_recife_ou_sem_coluna_falha_com_mensagem`:
   extração do cabeçalho na fixture pressupõe CRLF neste checkout.
3. `test_admin_papel_app.py::test_gravar_no_env_troca_so_as_variaveis_indicadas` e
   `::test_gravar_no_env_ignora_comentario_com_o_mesmo_nome`: o código anterior usa
   `Path.read_text(newline=...)`, incompatível com o Python 3.12 declarado pelo projeto.

Os dois testes de integração inicialmente sensíveis ao fuso passaram ao configurar o banco descartável em UTC,
como no CI. A fixture da matriz de autorização recebeu o cadastro territorial oficial necessário às rotas que
ela percorre, preservando todas as verificações de papel. A lista de tabelas esperadas inclui a nova tabela real.
O teste de navegador revelou um link de atribuição do Leaflet sem distinção visual: foi corrigido apenas com
sublinhado no mapa do Simulador.

Python 3.12.10 e dependências declaradas foram preparados em `.venv`; `npm ci` preservou o lockfile.
Os binários de PostgreSQL foram obtidos da distribuição [EDB](https://www.enterprisedb.com/download-postgresql-binaries),
indicada pelo [projeto PostgreSQL para Windows](https://www.postgresql.org/download/windows/), sem instalar serviço.
Nenhum arquivo `.env` do projeto foi lido ou modificado. Os testes administrativos usam somente arquivos
temporários artificiais. Os logs de verificação ficam em `tmp/`, ignorado pelo Git.

## Inventário de arquivos para revisão

Os caminhos abaixo são relativos à raiz do ClimaSense. Não houve mudança de stack, branch, commit ou push.

| Arquivo | Tipo de mudança | Justificativa | Funcionalidade afetada | Requisito |
|---|---|---|---|---|
| `README.md` | Documentar | Atualizar integração e limites reais | Operação e descoberta | RF-20, RF-42 |
| `docs/arquitetura.md` | Documentar | Explicar fluxo e persistência | Arquitetura | RF-23, RF-42 |
| `docs/ml/integracao-territorial.md` | Criar | Diagnóstico, comandos e evidências | Manutenção e ciência | RF-19, RNF-09–11 |
| `docs/api/openapi.json` | Gerar | Registrar nova rota e campos opcionais | Contrato HTTP | RF-23, RF-42 |
| `backend/climasense/api/routers/cenarios.py` | Integrar | Nova consulta sem mudar cenário manual | API territorial | RF-23–28, RF-38 |
| `backend/climasense/api/routers/risco_alagamento.py` | Integrar | Confiança qualitativa na resposta | API de ML | RNF-09, RN-06 |
| `backend/climasense/dominio/cenario.py` | Corrigir | Exigir cobertura horária real | Regra de referência | RN-01 |
| `backend/climasense/dominio/simulador.py` | Integrar | Aceitar janelas reais sem uniformizar série atual | Regras preservadas | RF-23, RF-36 |
| `backend/climasense/etl/conectores/alagamento.py` | Corrigir | Descartar endereço antes da bronze | Extração de rótulos | RNF-03, RN-13 |
| `backend/climasense/ml/__main__.py` | Integrar | CLI explícita de inferência e falha controlada | Treino e operação | RNF-09–11 |
| `backend/climasense/ml/alagamento/base.py` | Corrigir | Histórico e contrato compartilhado | Features | RN-01, RN-07 |
| `backend/climasense/ml/alagamento/modelo.py` | Corrigir | Purga temporal, dias reais e metadados | Estudo v0.2.0 | RN-11, RNF-09 |
| `backend/climasense/ml/alagamento/armazenamento.py` | Corrigir | Recusar artefatos/metadados inválidos e rever gate | Carregamento | RN-11 |
| `backend/climasense/ml/alagamento/clima.py` | Corrigir | Não completar dia com duplicatas | Chuva diária | RN-01, RN-02 |
| `backend/climasense/ml/alagamento/estudo.py` | Corrigir | Não ajustar maré com teste principal/futuro | Validação retrospectiva | RN-11 |
| `backend/climasense/ml/alagamento/ocorrencias.py` | Corrigir | Cache sanitizado preservando categorias | Rótulos | RN-13 |
| `backend/climasense/ml/alagamento/relatorio.py` | Corrigir | Versionar saídas e distinguir aprovação estatística/operacional | Relatórios gerados | RF-19, RN-11 |
| `backend/climasense/ml/alagamento/servico.py` | Corrigir | Features compatíveis, as-of e cobertura completa | Inferência | RN-01, RN-07, RN-11 |
| `backend/climasense/ml/alagamento/prever.py` | Criar | Separar inferência e gravação explícita | Persistência idempotente | RF-27, RF-42 |
| `backend/climasense/servicos/cenarios.py` | Integrar | Reutilizar consulta com limite de emissão/coleta | Previsão por distrito | RF-36 |
| `backend/climasense/servicos/impacto_territorial.py` | Criar | Orquestrar regras, dados e ML condicionado | Análise territorial | RF-22–25, RF-36–38 |
| `backend/migrations/versions/0025_inferencias_impacto.py` | Criar | Histórico acumulativo e view derivada | Banco | RF-19, RF-27, RF-42 |
| `backend/tests/unit/ml/test_alagamento.py` | Adaptar teste | Atualizar assinatura e aprovação sintética explícita | Regressão anterior | RNF-11 |
| `backend/tests/unit/ml/test_integridade.py` | Criar teste | Paridade, gate, serialização e falhas | Integridade do ML | RNF-09–11 |
| `backend/tests/unit/test_impacto_territorial.py` | Criar teste | Distritos, janelas, API, idempotência e falta de dados | Serviço territorial | RF-23–28, RF-42 |
| `backend/tests/unit/etl/test_conectores_chuva.py` | Ampliar teste | Provar descarte anterior à bronze | Privacidade | RN-13 |
| `backend/tests/integration/test_impacto_territorial.py` | Criar teste | SQL, durabilidade, migração, view e permissões reais | Integração local | RF-27, RF-42, RNF-01 |
| `backend/tests/integration/test_migracoes.py` | Adaptar teste | Incluir tabela criada na lista esperada | Esquema | RNF-11 |
| `backend/tests/integration/test_matriz_autorizacao.py` | Adaptar fixture | Carregar territórios necessários às rotas analíticas | Permissões | RNF-01 |
| `scripts/testar_backend_local.py` | Criar | Impedir herança de URLs remotas e leitura de .env nos testes | Isolamento | RNF-11–12 |
| `frontend/src/features/simulador/TelaSimulador.tsx` | Integrar | Separar hipótese e previsão por distrito | Tela existente | RF-20, RF-23–28 |
| `frontend/src/features/simulador/tipos.ts` | Integrar | Tipar metadados opcionais | Contrato da tela | RF-42 |
| `frontend/src/features/simulador/MapaDoCenario.tsx` | Integrar | Reutilizar mapa com evidências e rótulo do contexto | Mapa existente | RF-23, RF-25 |
| `frontend/src/features/simulador/EstagioPorDistrito.tsx` | Integrar | Exibir fontes/validade no detalhe | Distritos | RF-19, RF-42 |
| `frontend/src/features/simulador/EvidenciasImpacto.tsx` | Criar | Compartilhar explicações e limites | Detalhes de bairro/distrito | RF-25, RF-38, RF-42 |
| `frontend/src/features/simulador/Simulador.module.css` | Corrigir | Distinguir link de atribuição por sublinhado | Acessibilidade do mapa | RF-20, RF-21 |
| `frontend/src/features/simulador/TelaSimulador.test.tsx` | Ampliar teste | Troca de contexto, falhas e preservação de salvamento | Regressão da tela | RNF-11 |
| `frontend/src/lib/api-tipos.ts` | Gerar | Sincronizar tipos, preservando contratos das flags desligadas | Tipos HTTP | RF-42 |
| `frontend/tests/e2e/impacto-territorial.spec.ts` | Criar teste | Validar desktop/celular e acessibilidade com API interceptada | Fluxo funcional | RF-20, RF-21, RNF-11 |

Os tipos foram gerados de um contrato temporário completo (flags ligadas apenas na geração), porque o contrato
HTTP padrão omite funcionalidades desligadas ainda preservadas no código. Isso não altera as flags da aplicação.

## Estado de entrega

O ML está integrado ao código da análise territorial e realiza inferência sobre entradas novas sem treinamento,
quando recebe artefato compatível e aprovado. **No estado real desta entrega permanece experimental e indisponível
operacionalmente**. A avaliação por regras utiliza previsões meteorológicas existentes por distrito e funciona sem
modelo, desde que haja insumos suficientes. Nenhum modelo de chuva ou de deslizamento foi inventado. Resultados
possuem metadados, e a persistência das regras foi verificada somente no banco local. Nenhum estágio oficial foi
alterado. Restam os dados/validação científicos descritos acima e as quatro falhas anteriores da suíte.
