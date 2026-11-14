# Recuperação operacional do ETL — diagnóstico e entrega

> Registro da investigação anterior. As contagens de testes e falhas abaixo pertencem
> àquela etapa; as quatro falhas foram corrigidas na consolidação acadêmica.
> Consulte o [registro atual](ml/consolidacao-academica.md) para validações e commit.

Auditoria de 13/11/2026, 23:16–23:44 UTC (20:16–20:44 no Recife). Esta entrega altera código local;
**não executou escrita, migração, recuperação de status ou carga no Neon/Atlas compartilhados**.
Não foram criados commits, pushes ou tarefas agendadas. Os valores do `.env` não são reproduzidos aqui.

## A. Causa-raiz e investigação inicial

| Componente | Situação encontrada | Causa identificada | Evidência | Correção necessária |
|---|---|---|---|---|
| Inicialização | `dev.ps1` sobe Uvicorn e Vite | Iniciar a aplicação não executa o ETL | Leitura do script | Manter desenvolvimento separado da coleta e preparar agendamento explícito |
| Agendamento | Nenhuma tarefa local relacionada ao projeto | Não há atualização periódica configurada nesta máquina | Inventário de 202 tarefas, nenhuma correspondente; repositório só tem CI | Um responsável e uma rotina operacional |
| Execuções | 207 registros abertos: nove em cada uma de 23 fontes | Não há exclusão de disparos; falhas na criação dos clientes ficam fora do tratamento; encerramento do processo também abandona tarefas | Registros de 23:01:18–23:01:45 UTC, todos sem fim; nenhuma conexão trabalhadora ativa no diagnóstico | Reserva por fonte, trava entre processos, tratamento da inicialização e recuperação explícita dos registros antigos |
| Previsão | Último snapshot em 07/11; último dado em 09/11 às 23h UTC | Ausência de carga concluída desde então | Silver: zero horas atuais nas janelas de 24/72 h, apesar de existirem os oito distritos | Atualizar a fonte após aprovação |
| Cobertura futura | `forecast_days=3` também limita a maré | São dias de calendário, não 72 h contadas da coleta | Às 23h UTC, GETs reais retornaram só 49 horas futuras; quatro dias retornaram 73 | Solicitar quatro dias e validar cada hora necessária |
| APAC | Última leitura compartilhada em 06/11 às 16:20 UTC | Coletas recentes não terminaram; falhas antigas sem rastreamento suficiente | Último sucesso em 06/11; última falha em 07/11; API pública disponível agora | Coletar sem trocar ausência por zero; manter filtros de idade |
| Neon/Atlas | Ambos acessíveis | Não há evidência de impedimento atual por autenticação/rede | PostgreSQL em transação `READ ONLY`; ping e metadados Atlas; permissões necessárias de INSERT/UPDATE presentes no executor atual | Validar também DDL antes da implantação; não mudar papéis nesta etapa |
| Configuração | API e ETL apontam para o mesmo destino remoto; URL específica de migração ausente | `engine_do_dono` usa a URL da aplicação como alternativa | Configuração comparada internamente, sem expor host/credenciais | Separar privilégios numa implantação administrada; corrigir isolamento de `dev-local.ps1` |
| Ambiente local | `dev-local.ps1` não sobrepunha `DATABASE_URL_MIGRACOES` | Uma URL de dono herdada poderia enviar migração/ETL ao remoto | Leitura do script e da resolução de configuração | Sobrepor ambas as URLs PostgreSQL e restaurar o ambiente ao sair |
| Gold | Objetos existem, mas contêm dados antigos | `n_atualizadas` da Gold APAC é relativo à última coleta armazenada | Gold diária até 05/11; Gold atual referenciada em 06/11 | Atualizar Silver e recalcular somente as Gold correspondentes; consumidores continuam verificando a idade real |
| Cache | TTL climático de 60 s | Não explica uma semana sem dados novos | Código de cache e ausência de novas cargas na Silver | Invalidar no processo executor após o ETL; outras instâncias renovam por TTL |
| Migração | Remoto em `0024` | `0025` não foi implantada | Tabela de inferências e view ausentes | Aplicar somente com aprovação; a leitura meteorológica funciona sem essa migração |
| Interface | Disparava todas as fontes em paralelo, antes de bloquear o botão | Cliques repetidos podiam multiplicar tarefas; acompanhamento sem prazo | `Promise.all` e polling sem encerramento | Sequenciar fontes, bloquear imediatamente e limitar acompanhamento |
| ML | Nenhum artefato compatível carregado no teste operacional | Versão corrigida ainda depende de avaliação científica | API informa indisponibilidade; treinamento não executado nesta entrega | Manter bloqueio de publicação |

Não há log local do servidor que identifique a exceção ou o encerramento responsável pelas 207 tarefas.
Os defeitos de controle acima foram reproduzidos/cobertos localmente; não se atribui retrospectivamente uma
exceção específica àqueles registros. Também não se conclui ausência de agendamento em outra máquina do grupo.
Os filtros temporais do simulador não foram afrouxados. A migração pendente não é a causa do clima vencido.

O Git já continha a integração territorial/ML da etapa anterior. `.env.example` tinha alteração preexistente,
preservada. Nenhuma dessas alterações foi descartada ou sobrescrita.

## B. Estado das fontes e do ETL

Últimas cargas compartilhadas concluídas; horários UTC:

| Fonte | Último sucesso | Lidos / gravados | Última falha conhecida | Situação na auditoria |
|---|---|---|---|---|
| Open-Meteo previsão | 07/11 02:03:44 | 1.920 / 1.920 | Nenhuma encontrada | Snapshot de 07/11, sem cobertura atual |
| Open-Meteo maré | 07/11 02:03:52 | 72 / 72 | Nenhuma encontrada | Sem maré no horizonte atual |
| Open-Meteo histórico | 05/11 02:33:47 | 8.832 / 2.304 | Nenhuma encontrada | 408.576 linhas; último dado em 29/10 23h UTC |
| APAC chuva | 06/11 16:28:01 | 18 / 162 | 07/11 02:05:24 | Leitura mais recente em 06/11 16:20 UTC |
| APAC previsão | Nunca | — | Nenhuma conclusão encontrada | Bronze ausente; nove execuções abertas |
| Alertas oficiais | 07/11 02:06:01 | 21 / 0 | Nenhuma encontrada | Zero gravados pode significar ausência de alerta elegível |

Cada fonte acima tinha nove novas execuções abertas em 13/11, todas com contadores zero, sem `fim`.
As mensagens antigas de erro foram examinadas somente de forma redigida; não permitem atribuir a falha
da APAC a um HTTP/status específico. Não foram publicadas mensagens arbitrárias do banco ou do provedor.

Coletas públicas reais no ambiente isolado:

| Fonte | Bronze | Silver | Resultado |
|---|---:|---:|---|
| Previsão Open-Meteo | 2.112 documentos | 2.112 horas por rodada | Oito distritos; 264 h por ponto, incluindo sete dias passados e quatro dias de calendário |
| Maré Open-Meteo | 96 documentos | 96 horas | Recife; variável `sea_level_height_msl`; cobre 72 h futuras |
| APAC chuva | 68 documentos | Até 171 acumulados válidos na primeira carga | 19 estações com data; um registro sem hora descartado; cadastro também preservado na Bronze |
| APAC previsão | 165 documentos | 135 registros | Previsão municipal, tendência e radar; nenhuma rota indisponível nessa coleta |
| Alertas oficiais | 19 documentos | 0 avisos elegíveis | Quatro origens consultadas; 2 avisos APAC vencidos, 12 fora do Recife e 1 aviso INMET fora do Recife |

Nas repetições locais da APAC, os mesmos registros já existentes geraram 0, 9 ou 18 inserções novas,
sem inventar nova medição. O cadastro e `visto_em` são atualizados segundo o contrato existente.
Uma resposta vazia/inútil de chuva ou previsão agora falha; dados válidos já carregados podem continuar
produzindo zero novas linhas. Ausência de alertas elegíveis continua sendo um resultado legítimo.

O novo `etl operacional` roda sequencialmente previsão, maré, fontes rápidas e ERA5 em janela móvel de 45 dias.
A cada chamada, só coleta o que está fora da cadência: previsão 60 min, maré 180 min, chuva/rios/alertas 15 min,
previsão APAC 60 min e ERA5 1.440 min. Essas cadências não alteram `frescor.toml`.
Rios e ERA5 permanecem implementados, mas não receberam nova coleta real nesta validação; há regressão com dublês.
As quatro fontes planejadas continuam planejadas. O estágio COP não foi preenchido.

## C. Estado dos bancos e persistência

Remoto, somente leitura:

- Neon: versão `0024`, oito distritos e 94 bairros. `silver.observacoes`: 97 MB com índices; banco: 148 MB no diagnóstico.
- Atlas Bronze: estimativas de 7.488 documentos de previsão, 720 de maré, 169 de chuva APAC e 63 de alertas.
  Coleção `apac_previsao` ainda ausente. Território: oito distritos e 81 faixas hídricas.
- `gold.chuva_apac_diaria`: 182.310 linhas, último dia 05/11. `gold.chuva_apac_agora`: referência antiga,
  inclusive herança municipal no distrito 8. Os consumidores atuais não a tratam como medição recente própria.
- Índices de busca meteorológica e por emissão presentes. Consultas agregadas foram limitadas por timeout de 12 s;
  o plano de consulta foi examinado antes da agregação da Silver.

Isolado: PostgreSQL 16 em `127.0.0.1:55432`, banco `climasense_operacao_teste`, sem leitura de `.env`.
Bronze e território Mongo usam **mongomock em memória**. Isso valida transformação e leitura de volta do lote,
mas não comprova persistência, índices ou transações do Atlas. A Silver PostgreSQL é real.
Todos os 18 agregados de `gold.verificar` apresentaram zero diferenças na captura local.
Migração `0025` aplicada localmente; 188 inferências de regras inseridas, repetição com zero novas linhas,
188 linhas consultáveis pela view numa nova sessão. Tabela e índices: 768 kB na captura.
Os testes também verificam proibição de UPDATE/DELETE/TRUNCATE e permissões mínimas dessa tabela.

## D. Arquivos desta entrega

As alterações anteriores de ML/integração permanecem; seu inventário está em
[`ml/integracao-territorial.md`](ml/integracao-territorial.md). Esta continuação acrescenta/altera:

| Arquivo (relativo à raiz) | Finalidade |
|---|---|
| `backend/climasense/etl/execucao.py` | Reserva por fonte; exclusão transacional entre processos/trabalhos; repetição do mesmo trabalho sem duplicação; captura de falhas de inicialização; mensagens sem URI; contadores parciais e invalidação de cache |
| `backend/climasense/etl/orquestrador.py` | Perfil operacional com cadências e continuidade após falha de uma fonte |
| `backend/climasense/etl/__main__.py` | Comando operacional, proteção explícita de destino remoto e saída segura de erros |
| `backend/climasense/etl/conectores/base.py` | Hook de validação antes da Silver e progresso parcial da execução |
| `backend/climasense/etl/conectores/comum.py` | Até duas novas tentativas somente de GET; backoff limitado; Retry-After limitado a 15 s |
| `backend/climasense/etl/conectores/open_meteo.py` | Quatro dias; validação de estrutura/cobertura; valores finitos; cliente HTTP comum |
| `backend/climasense/etl/conectores/apac.py` | Rejeição de resposta vazia, totalmente nula ou sem leitura atual utilizável; corpo arbitrário não vira erro público |
| `backend/climasense/etl/conectores/apac_previsao.py` | Resposta sem informação utilizável para Recife não conta como sucesso |
| `backend/climasense/api/routers/fontes.py` | HTTP 409 para fonte já em execução, executor protegido e metadados da última tentativa |
| `backend/climasense/servicos/fontes.py` | Consulta da última tentativa, separada do último sucesso |
| `dev-local.ps1` | Isola URL do dono e da API; restaura variáveis; interrompe preparação local após falha |
| `scripts/atualizar-operacional.ps1` | Executa uma rodada; não agenda automaticamente |
| `scripts/preparar-agendamento.ps1` | Definição única Windows a cada 15 min, `IgnoreNew`; só registra com `-Registrar` |
| `scripts/validar_operacao_local.py` | GETs reais, PostgreSQL fixo local, Bronze em memória, APIs, persistência e captura de evidências |
| `backend/tests/unit/etl/test_operacao_etl.py` | Cobertura de 72 h, entradas inválidas, política HTTP e bloqueio de destino remoto |
| `backend/tests/integration/test_etl_controle.py` | Concorrência real entre conexões, repetição e falhas de construtor/Mongo |
| `backend/tests/unit/etl/test_orquestrador.py`, `backend/tests/integration/test_fontes_api.py` | Cadências independentes e HTTP 409 antes de criar outra execução |
| `frontend/src/features/fontes/acompanhar.ts` | Acompanhamento com prazo de 30 min, timeout por HTTP, limite de falhas e cancelamento ao sair da tela |
| `frontend/src/features/fontes/TelaFontes.tsx` | Atualização sequencial, bloqueio imediato e contadores de pendências/zero novos registros |
| `frontend/src/features/fontes/DetalheFonte.tsx` | Mesmo acompanhamento limitado na atualização individual |
| `frontend/src/features/fontes/Fontes.module.css` | Apresentação da tentativa em andamento |
| `frontend/src/features/fontes/acompanhar.test.ts` | Prazo máximo, falha da fonte, rede e autorização |
| `frontend/src/features/fontes/TelaFontes.test.tsx` | Sequenciamento, cliques repetidos e ausência de falsa mensagem de atualização |
| `frontend/tests/e2e/operacao-local.spec.ts` | Reprodução das respostas reais locais em desktop/celular, mapa, insumos e acessibilidade |
| `frontend/src/features/simulador/EvidenciasImpacto.tsx` | Uma casa decimal nos acumulados, para não mostrar 0,1 mm como zero |
| `docs/api/openapi.json`, `frontend/src/lib/api-tipos.ts` | Contratos atualizados; tipos das funcionalidades opcionais preservados |
| `README.md`, `docs/apis-e-etl.md`, `docs/operacao-etl.md` | Diagnóstico, comandos, limitações e implantação condicionada à autorização |

Nenhum código de treinamento ou regra de classificação foi redesenhado nesta continuação. Migrações antigas
e `0025` não foram reescritas para corrigir a coleta. `.env` e a alteração preexistente de `.env.example` foram preservados.

## E. Verificação HTTP

GETs públicos: Forecast HTTP 200 nos oito pontos oficiais, Marine HTTP 200, APAC acumulada e previsão municipal
HTTP 200. UTC/GMT interpretado como UTC; horários locais APAC convertidos de UTC−3. Validação usa valores reais,
não substituições por números de teste. Na captura final, a APAC tinha leitura até 23:40 UTC e 16 estações recentes.

API ASGI local autenticada: HTTP 200 em `/auth/eu`, `/fontes`, `/situacao/chuva`, `/estagios?nivel=distrito`,
`/estagios/oficial`, `/estagios/parametros`, `/cenarios`, `/cenarios/premissas-atuais`,
`/cenarios/estimativa?territorio_id=recife&horizonte_h=72`, `/cenarios/impacto-previsto` com horizontes 24 e 72,
GeoJSON de bairros/distritos e POST `/cenarios/simular` com cenário explicitamente hipotético.
GET de impacto não grava inferência. A persistência foi chamada separadamente, somente no banco local.

Não foi iniciada a aplicação contra os bancos compartilhados: login, renovação de sessão, lifespan e algumas
rotas existentes podem gravar. Os resultados HTTP acima não são testes HTTP do ambiente compartilhado.

## F. Validação territorial e limitações

Os oito distritos receberam séries completas e maré nas próximas 72 h; o serviço mantém a chuva de cada distrito.
Na captura de 23:44 UTC, chuva prevista de 72 h: DS1 4,8; DS2 5,1; DS3/DS4 4,8; DS5/DS6/DS8 5,9; DS7 5,8 mm.
DS8 não tem observação APAC própria válida no teste e mantém `null`, sem substituir pelo Recife inteiro.

O banco operacional de teste contém somente território e coletas meteorológicas desta validação.
**Não carrega histórico de ocorrências, IBGE, CNES, carta SGB ou saúde do banco do grupo.** Por isso as classes
de impacto continuam `sem_dados`, e a exposição permanece ausente; não foi inventado histórico zero.
Os testes de regras/integração exercitam classificação com contexto de teste e regressão de cenários manuais.
Isso demonstra consumo correto do clima e comportamento perante lacunas; não demonstra uma classificação
territorial completa com os dados históricos reais do grupo. Essa verificação está no aceite pós-carga remota.

A série horária observada APAC nasce das coletas e não pode recuperar retroativamente 72 h de coletas perdidas.
Acumulado móvel de 72 h vindo da APAC é diferente da soma de três dias locais usada em outra resposta da Situação.
O histórico diário pode exigir atualização específica; lacunas permanecem explícitas.

Frontend: 250 testes aprovados; desktop e celular com reprodução da captura real e ensaio sintético aprovados.
Sem transbordamento horizontal da página e sem violações graves/críticas do axe no recorte testado.
O mapa vetorial e a lista funcionaram; os tiles externos do mapa de ruas não carregaram no ensaio e o aviso
de indisponibilidade apareceu. Isso não foi contado como validação do provedor externo de tiles.
Captura de teste é reprodução, não uma conexão do navegador ao backend compartilhado.

## G. Machine Learning

Nenhum retreinamento real foi executado. Na cadeia operacional local, o carregamento retornou `None` e a API
publicou `disponivel=false`, sem inferência de ML nem linha `ml_temporal` na tabela.
Os testes com artefato sintético verificaram salvamento/carregamento, igualdade de pontuações, inferência
sem `fit`, território desconhecido e rejeição de artefato legado/incompatível. Não equivalem à validação científica
de um modelo operacional. O bloqueio de publicação da versão corrigida permanece intacto.

## H. Testes e reprodução

Executados na raiz, com Python 3.12, salvo comandos frontend:

```powershell
.\.venv\Scripts\python scripts/testar_backend_local.py --postgres-local -q
.\.venv\Scripts\python scripts/validar_operacao_local.py
# Dentro de frontend:
npm test
npm run build
npm run e2e -- operacao-local.spec.ts impacto-territorial.spec.ts
```

- Backend completo: **1.331 aprovados, quatro falhas preexistentes**, 150,33 s. Log local: `tmp/testes-backend-operacao.log`.
- Recorte final de ETL, ML, impacto, migração/persistência: **56 aprovados**.
- Frontend: **250 aprovados**, 29 arquivos; build aprovado (aviso existente de chunks grandes).
- E2E: dois cenários em desktop/celular, total de quatro casos aprovados após corrigir o seletor do teste novo.
- Ruff: análise do backend aprovada; formatação verificada. OpenAPI atualizado sem iniciar servidor.
- Definição Windows testada sem `-Registrar`: `registrada=false`, cadência 15 min e `IgnoreNew`.

Falhas já conhecidas, mantidas sem refatoração fora do escopo:
1. `test_validacao_em_portugues`: dependência de banco ausente responde 503 antes da validação esperada 422.
2. `test_conectores_saude_historico`: fixture CSV usa LF, enquanto o teste separa o cabeçalho apenas por CRLF.
3. Dois testes de `test_admin_papel_app`: `Path.read_text(newline=...)` não é aceito pelo Python 3.12.

O roteiro de dados reais exige banco local previamente criado em `127.0.0.1:55432`, nome
`climasense_operacao_teste`; só migra esse destino literal. A suíte usa outro banco: `climasense_teste`.
Ambos são descartáveis. Evidências em `tmp/operacao-local.json`; imagens `tmp/operacao-desktop.png` e
`tmp/operacao-celular.png`. O teste novo de navegador é ignorado se a captura local não existir.
Docker não está disponível nesta máquina; o PostgreSQL portátil forneceu o isolamento.

## I. Plano remoto — NÃO executado

### Escopo da primeira autorização

1. Confirmar que nenhum trabalhador antigo está ativo, escolher um único responsável e identificar outros agendadores do grupo.
2. Confirmar backup/restore point do Neon e mecanismo de backup do Atlas. Preservar a versão `0024`, metadados das
   execuções afetadas e tabelas APAC/Gold que sofrem upsert/recálculo. Não prosseguir sem recuperação viável.
3. Verificar DDL como dono e ACLs existentes; `SELECT`, `INSERT` e `UPDATE` do executor foram verificados, mas DDL
   e recuperação de backup não foram exercitados remotamente. Não alterar papéis/permissões fora de `0025`.
4. Aplicar **somente `0025`, após `0024`**, com o procedimento Alembic existente. Cria tabela, sequência, índice,
   triggers e view; a própria migração aplica ACLs específicas se `climasense_app` existir. Nenhuma carga de treino.
5. Em transação, salvar os valores anteriores e encerrar como falha **somente as 207 execuções abandonadas
   da janela `2026-11-13 23:01:00Z` a `23:02:00Z`**, ainda `em_andamento`, após reconfirmar contagem/IDs.
   Mensagem fixa: “Execução interrompida; encerrada durante recuperação autorizada.” Não excluir registros.
6. Executar uma carga por vez: previsão Open-Meteo, maré, chuva APAC, previsão APAC e alertas. Conferir cada etapa.
   Não usar `etl atualizar` integral, não recarregar território e não tocar COP/usuários.
7. Validar cobertura atual de 24/72 h, horários, IDs e Gold; só depois executar persistência explícita das regras,
   caso incluída na autorização: **188 linhas por snapshot** (94 bairros × dois impactos), sem ML reprovado.
8. Reiniciar a aplicação com o código atualizado para invalidar caches de todas as instâncias, ou respeitar TTLs:
   clima 60 s, contexto estático do simulador 300 s, outras cargas até 600 s. Conferir HTTP autenticado real com o operador.

### Tabelas, coleções e volumes estimados de uma rodada

| Destino | Operação / estimativa | Finalidade |
|---|---|---|
| `alembic_version`, novos objetos de `0025` | Uma migração aditiva; tabela inicialmente vazia | Persistência rastreável |
| `app.etl_execucoes` | Até 207 UPDATEs delimitados; cinco INSERTs de novas cargas e cinco conclusões | Recuperação e rastreamento |
| `bronze.open_meteo_previsao`, `bronze.open_meteo_mare` | Aproximadamente 2.112 + 96 documentos novos | Snapshots brutos acumulativos |
| `silver.observacoes` | Aproximadamente 2.208 INSERTs | Chuva e maré atuais |
| `bronze.apac_chuva` | Aproximadamente 68 documentos | Acumulados e cadastro recebidos |
| `silver.estacoes`, `silver.apac_estacoes_cadastro` | Dezenas de upserts | Localização e saúde das estações |
| `silver.apac_chuva_leituras`, `silver.apac_chuva_passos` | Até cerca de 171 acumulados + 19 passos; upserts de `visto_em` nas repetições | Chuva observada atual |
| `bronze.apac_previsao` e tabelas `silver.apac_previsao_horaria`, `silver.apac_tendencia_chuva`, `silver.apac_radar` | Aproximadamente 165 documentos / 135 registros | Contexto meteorológico APAC |
| `bronze.alertas_oficiais`, `silver.alertas_oficiais` | Aproximadamente 19 documentos; 0 a N avisos, conforme feed atual | Avisos oficiais elegíveis |
| `gold.chuva_apac_agora`, `gold.chuva_obs_hora_distrito`, `gold.chuva_obs_72h_distrito`, `gold.estacoes_chuva_status` | DELETE/INSERT transacional somente desses agregados, derivados da Silver | Painéis de chuva e situação |
| `silver.inferencias_impacto`, `gold.previsoes_impacto` | 188 INSERTs opcionais; view sem escrita própria | Guardar análise horária por regras |

Nomes, quantidades e frescor precisam ser reconfirmados no momento autorizado; APIs podem mudar.
Primeira rodada meteorológica: ordem de poucos MB, não uma reserva medida no Atlas. No ensaio local, 188 inferências
ocuparam 768 kB com índices. Medir crescimento real antes da automação: previsão horária significa **50.688 documentos
e linhas de previsão/dia**, mais 768 de maré/dia e coletas APAC/alertas. Bronze acumulativa não tem descarte automático.
O plano gratuito pode atingir seu limite rapidamente; medir capacidade/custos e definir cadência/arquivamento
com o grupo, sem apagar dados nem ampliar limites de frescor para esconder atraso.

### Histórico e backfill

Não é necessário recarregar todos os anos para recuperar as previsões. ERA5 está atrasada desde 29/10: se o grupo
aprovar atualizar também a série histórica, usar a janela móvel existente de 45 dias (cerca de 8.832 documentos;
só horas/valores ainda ausentes entram na Silver). Isso não treina o modelo.
Para os três dias locais da chuva APAC, avaliar carga histórica restrita ao mês atual (`--modo historico --limite 1`)
se a API disponibilizar os dias faltantes. Esse endpoint histórico não recebeu GET real nesta validação.
Backfill APAC não reconstitui os passos sub-horários perdidos; não fabricar uma série horária completa.
Essas duas cargas adicionais devem ser autorizadas separadamente se forem necessárias ao aceite.

### Agendamento preparado, ainda desativado

`scripts/preparar-agendamento.ps1` sem parâmetros apenas valida a definição. Após aprovação da cadência/capacidade,
um único responsável pode registrar `ClimaSense-ETL-Operacional` usando `-Registrar -PermitirRemoto`.
Sua ação chama `scripts/atualizar-operacional.ps1 -PermitirRemoto`; a CLI também exige `--permitir-remoto` para
o perfil novo quando o destino não for local. Isso não muda a semântica dos comandos ETL antigos.
Tarefa a cada 15 min, uma instância (`IgnoreNew`), limite de três horas, sem privilégios elevados.
O modelo preparado exige usuário conectado e máquina ligada; não oferece disponibilidade contínua com o PC desligado.
Não registrar simultaneamente os exemplos antigos de tarefas diárias/tempo-real/cron.

As travas do ETL são transacionais, com conexão dedicada durante a coleta; não se usam travas de sessão num
pooler transacional. Exigem uma conexão adicional. Uma fonte com execução abandonada recebe 409 e exige inspeção;
não há expiração automática que poderia permitir duas cargas simultâneas. Morte do processo/indisponibilidade
do banco ainda pode deixar execução aberta; recuperar somente após confirmar que o trabalhador parou.
Falhas independentes são registradas e as demais fontes continuam no orquestrador; retorno não zero sinaliza pendência.

### Verificação e recuperação após autorização

Reexecutar SELECTs de versão/objetos, última execução por fonte, máximos de coleta/leitura, horas válidas por
distrito, última maré, Gold APAC e comparação `gold.verificar` (implementação inspecionada: somente SELECT).
Exigir 72 timestamps distintos e não nulos por distrito e na maré; contagem de linhas sem validade não basta.
Validar `/situacao/chuva`, `/estagios`, `/cenarios/premissas-atuais` e `/cenarios/impacto-previsto` com o operador.
Conferir contexto histórico real, exposição, ausência de herança municipal indevida e bloqueio do ML.

Risco principal: carga parcial entre camadas e crescimento de armazenamento. Não existe transação distribuída
Mongo/Postgres; uma falha pode conservar Bronze e parte da Silver já gravada. Não se promete rollback global.
O mesmo ID de trabalho encerrado não é reexecutado; nova tentativa gera outro lote rastreável e snapshots de
previsão distintos. APAC usa suas chaves naturais e inferências usam hash. Não criar duplicação de agendadores.
Para erro de implantação, parar o agendador, voltar o código e manter o esquema aditivo; conservar evidências e
usar backup/restore se necessário. Downgrade de `0025` apaga inferências e **não** é o rollback padrão remoto.
Os DELETEs usados para recompor Gold ficam em transações do conector; não apagar Bronze para “desfazer” uma carga.

## J. Checklist de conclusão

| Requisito | Situação | Evidência |
|---|---|---|
| Previsão Open-Meteo atual | Verificada localmente; remoto pendente | GET 200, oito pontos, 2.112 horas; cobertura futura completa |
| Previsão de maré atual | Verificada localmente; remoto pendente | GET 200, 96 horas, horizonte completo de 72 h |
| Chuva observada APAC | Verificada, com cobertura parcial | 16 estações recentes na captura; DS8 sem observação própria |
| Cobertura dos oito distritos | Verificada para previsão | Oito IDs oficiais; chuva prevista própria, sem replicar máximo municipal |
| Silver atualizada | Somente ambiente isolado | PostgreSQL real local; compartilhada permanece vencida |
| Gold consistente | Verificada localmente | 18 comparações sem diferenças; remoto não recalculado |
| API situação funcionando | Verificada localmente, com lacunas explícitas | HTTP 200; sem reconstrução fictícia das horas/dias observados ausentes |
| API impacto-previsto funcionando | Verificada localmente | HTTP 200 em 24/72 h, séries atuais e oito distritos |
| Simulador por regras funcionando | Regressão aprovada; aceite com contexto real pendente | Dados climáticos reais consumidos; classes locais sem dados por falta de histórico |
| ML experimental integrado | Integração testada; publicação bloqueada | Inferência sintética sem fit; artefato operacional compatível ausente |
| Frontend funcionando | Verificado no recorte testado | 250 testes; desktop/celular com captura real e acessibilidade; tiles externos indisponíveis |
| Atualização automatizada preparada | Preparada, não registrada | Definição única validada; capacidade/cadência e host dependem do grupo |
| Testes de regressão | Aprovados no recorte, quatro falhas anteriores na suíte completa | Backend 1.331 + 56 no recorte final; frontend 250; quatro casos de navegador |
