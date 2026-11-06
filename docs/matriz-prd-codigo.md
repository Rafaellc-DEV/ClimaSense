# Matriz PRD × código atual

Onda 0, agente `arquiteto`, 06/11/2026. Base: `docs/PRD.md` v2 e o código no commit `1431fdb`, mais as alterações
locais do frontend ainda não commitadas (`features/situacao`, `saude`, `registro`, `abrigos`, `boletim`). Rotas
relativas a `/api/v1`; contrato exportado em `docs/api/openapi.json` (`scripts/exportar_openapi.py`).

- **Veredito:** **manter** (o código atende; só conferir), **adaptar** (existe em parte ou não existe; vira tarefa),
  **remover** (existe e sai do produto; para landing e comunicados, "desligar por chave", ADR 0011).
- **Hoje:** A = atende, P = parcial, N = não existe.

## 1. Resumo

| | Manter | Adaptar | Remover | Total |
|---|---|---|---|---|
| RF (01–32) | 6 | 26 | 0 | 32 |
| RNF (01–12) | 2 | 10 | 0 | 12 |

| Hoje | RF | RNF |
|---|---|---|
| Atende (A) | 6 | 2 |
| Parcial (P) | 17 | 9 |
| Não existe (N) | 9 | 1 |

Nenhum requisito do PRD pede remoção. O que sai do produto são **funcionalidades existentes fora do escopo** (§4):
landing pública, comunicados e avaliações (desligar por chave), painel antigo, módulo de registro do evento e lições
aprendidas, mapa portátil e estatísticas de séries.

## 2. Requisitos funcionais

| ID | Fase | Veredito | Hoje | Onde está | Evidência | O que falta |
|---|---|---|---|---|---|---|
| RF-01 | 1 | adaptar | P | `dominio/estagio.py`, `servicos/estagios.py`, `api/routers/estagios.py`, `frontend/src/features/situacao/TelaSituacao.tsx`, `features/territorio/MapaSituacao.tsx` | `GET /estagios?nivel=distrito\|bairro` devolve `sugerido` e `declarado`; mapa da Situação colore por estágio; `tests/unit/dominio/test_estagio.py` | **Estágio oficial da cidade dado pelo COP** não existe: falta registro (manual ou feed) com fonte e hora, mostrado ao lado do sugerido/declarado. |
| RF-02 | 1 | adaptar | P | `api/routers/abrigos.py`, `api/routers/territorios.py` (`/territorios/hidrografia.geojson`), `api/routers/saude_agravos.py` (`/ocorrencias/historico`) | Abrigos com coordenadas; faixas hídricas; ocorrências por bairro | Camadas de **áreas de risco**, **população vulnerável** e **equipamentos de saúde**; controle liga/desliga no mapa da equipe. Fontes: `docs/pesquisa/fontes-vulneraveis-equipamentos-risco.md`. |
| RF-03 | 1 | adaptar | N | — | `docs/funcionalidades-equipe.md` §4 registra a lacuna | Agregado por bairro de idosos e crianças (IBGE 2022); deficiência sem fonte por bairro (P-12). "Dados insuficientes" até lá. |
| RF-04 | 1 | adaptar | N | — | — | Cruzamento equipamento × vulneráveis do bairro (depende de RF-02 e RF-03). |
| RF-05 | 1 | adaptar | P | `etl/conectores/alertas.py`, `silver.alertas_oficiais` (migração 0008), `servicos/estagios.py::_alertas_vigentes`, `features/situacao/CartaoDistrito.tsx` | APAC, INMET, Cemaden e IDAP filtrados para o Recife, com `emitido_em` e `expira_em` | Alertas do **COP** e da **Defesa Civil do Recife** fora do IDAP (registro manual com hora); lista própria de alertas. |
| RF-06 | 1 | adaptar | P | `dominio/prioridades.py`, `GET /territorios/prioridades` (sem uso no frontend) | Prioridade por estágio e evidências | Índice de vulnerabilidade (vulneráveis + áreas de risco + histórico) e destaque visual (ex.: DS VII). |
| RF-07 | 1 | adaptar | P | `features/situacao/CartaoDistrito.tsx` | Cartão mostra estágio, motivos e alertas | População vulnerável, equipamentos de saúde e abrigos próximos no cartão do bairro. |
| RF-08 | 1 | manter, com ressalva | A | `api/routers/abrigos.py`, `servicos/abrigos.py`, `app.abrigos` + `app.abrigo_atualizacoes` (0007), feed do COP em `etl/conectores/abrigos.py`, `features/situacao/ResumoTopo.tsx` | `GET /abrigos` → `totais.abrigos_abertos`, `totais.desabrigados`, `atualizado_em`; `tests/integration/test_evento_chuva.py` | Desabrigados só por registro da equipe (P-02). **Ressalva (Gate 0, 06/11/2026):** o feed do COP de abrigos ativos está vazio hoje; abrigos abertos dependem de o COP publicar e, até lá, valem pelo registro manual da equipe. |
| RF-09 | 1 | adaptar | P | `GET /abrigos?distrito_id=` | Totais do recorte pedido | Os dois números **por distrito e da cidade** numa só resposta e na tela. |
| RF-10 | 1 | adaptar | P | `frontend/src/lib/api.ts` (`staleTime 60s`, `refetchOnWindowFocus: false`), `features/landing/useEstado.ts` (`refetchInterval 120s`) | Hora exibida nas respostas | Telas da equipe não se atualizam sozinhas: definir `refetchInterval` por tela (ex.: 60 s na Situação). |
| RF-11 | 2 | adaptar | P | `etl/conectores/infodengue.py`, `etl/conectores/leptospirose.py`, `GET /saude/resumo`, `features/saude/TelaSaude.tsx` | Séries semanais com semana incompleta marcada | Fonte mais atual da vigilância (P-01); hoje 1 a 3 semanas de atraso, mostrado com a hora. |
| RF-12 | 2 | adaptar | P | `dominio/janela_leptospirose.py`, `GET /saude/semanal`, `GET /saude/bairros` | Leptospirose semanal e janela de 30 dias; arboviroses por bairro e ano | **Peçonhentos** (SINAN `ANIMBR`, só município, testado em `docs/pesquisa/saude-e-chuva.md`); recorte **por território** semanal (depende da vigilância). |
| RF-13 | 2 | adaptar | N | — (vacinação COVID removida pela migração 0009) | — | Consultas, vacinas e medicamentos nos abrigos: sem fonte; "Dados insuficientes" até haver fonte ou registro da equipe (P-03). Não é a vacinação COVID antiga. |
| RF-14 | 2 | adaptar | N | — | — | Situação de unidades de saúde (fechada, danificada) com fonte e hora; cadastro pelo CNES. |
| RF-15 | 1 | manter | A | `app.acoes_resposta` (0007), `api/routers/acoes.py`, `servicos/acoes.py`, `features/registro/TelaRegistro.tsx` | Território, `tipo`, `responsavel`, `situacao`, `inicio_em`, `fim_em`; `tests/integration/test_evento_chuva.py` | Conferir: por distrito já é possível (território pode ser distrito). Tirar "lição aprendida" da tela (§4). |
| RF-16 | 1 | adaptar | P | `GET /acoes?situacao=em_andamento`, `TelaRegistro.tsx`, `TelaBoletim.tsx` | Lista filtrável | Andamento resumido por distrito (contagem por situação) na tela Ações. |
| RF-17 | 1 | adaptar | P | `api/routers/boletim.py`, `servicos/boletim.py`, `features/boletim/TelaBoletim.tsx` | `GET /boletim`: estágio, chuva, maré, abrigos, ações e fontes, imprimível | Relatório **executivo** a partir do Boletim: período, ações por distrito e situação, saúde, cenário salvo; modelo do cliente (P-08). |
| RF-18 | 3 | adaptar | N | — | — | Consolidado pós-evento (fase 3). |
| RF-19 | 1 | adaptar | P | `api/envelope.py` (`meta.fontes[].atualizado_em`, `status`), `app.fontes.limite_desatualizacao_h`, `api/routers/fontes.py`, `features/fontes/` | Status `atualizada/desatualizada/com_falha/planejada` por fonte | `/abrigos`, `/acoes`, `/estagios/historico` não usam o envelope; limite **por tipo de dado** (PRD §9); selo de desatualizado em todo indicador da equipe. |
| RF-20 | 1 | adaptar | P | `frontend/src/app/AppShell.tsx` (menu) | Menu: Situação, Chuva, Registro do evento, Abrigos, Saúde, Comunicados, Boletim, Fontes, Administração | Reorganizar nas 5 telas do PRD (Mapa, Situação, Saúde, Ações, Simulador); tirar Comunicados do menu (ADR 0011); checagem de simplicidade do `qa-ux`. |
| RF-21 | 1 | manter | A | `frontend/playwright.config.ts` (projeto `celular`, Pixel 7), CSS Modules responsivos | Testes e2e em desktop e celular | Rodar o projeto `celular` também no CI (hoje o CI roda só vitest e build). |
| RF-22 | 1 | adaptar | P | `features/situacao/resumo.ts`, `TelaSituacao.tsx` (quem pede decisão sobe) | Ordenação por estágio | Ordenar por vulnerabilidade (depende de RF-06). |
| RF-23 | 1 | adaptar | P | `api/routers/cenarios.py` (`GET /cenarios?horizonte_h=`), `dominio/cenario.py`, `features/chuva/ProximosDias.tsx` | Chuva prevista e maré por distrito com prioridade experimental | Classe de risco por bairro com legenda e **nível de confiança**, alagamento e deslizamento. |
| RF-24 | 1 | adaptar | N | — | `GET /cenarios` não recebe premissas da usuária | Premissas editáveis (§8.1) e recálculo sem recarregar. |
| RF-25 | 1 | adaptar | P | `sugerido.motivos` em `GET /estagios` | Motivos por território | Explicação por bairro no simulador + população vulnerável exposta. |
| RF-26 | 1 | adaptar | N | — | — | Mesmas camadas do mapa principal no simulador. |
| RF-27 | 1 | adaptar | N | `silver.previsoes_emitidas` (0002) guarda previsões do sistema, não cenários | — | Salvar cenário (premissas + resultado + autor + hora) e usar no relatório. |
| RF-28 | 1 | adaptar | N | Índice `observacoes_emissao` (0006), cache de 60 s nos estágios | Preocupação com tempo, sem simulador | Medir: recálculo por regras para 94 bairros em segundos. |
| RF-29 | 1 | manter | A | `dominio/estagio.py` (`Estagio = sem_dados, observacao, atencao, alerta, critico`), `app.estagio_parametros` (0007), `PUT /estagios/parametros` | Gatilhos de chuva 24 h, prevista 24 h e 72 h, maré junto do pico e histórico de alagamento; faltando previsão ou maré → `sem_dados`; `tests/unit/dominio/test_estagio.py` | Limiares ainda sem validação do cliente (P-06). |
| RF-30 | 1 | manter | A | `POST /estagios` (permissão `editar`, analista ou acima), `app.estagio_declaracoes` somente inclusão (0007, 0010), auditoria em `servicos/estagios.py`, `features/situacao/Declarar.tsx` | Justificativa obrigatória, autor e hora; encerrar é nova linha | — |
| RF-31 | 1 | manter | A | `POST /estagios/mensagem`, `POST /estagios/mensagem/uso`, `dominio/mensagem.py`, `features/evento/Evento.tsx` (`MensagemPronta`) | Texto padronizado + `wa_me_url`; nada é enviado; `TelaSituacao.test.tsx` | Conferir que o texto traz estágio, territórios, motivo, hora e fonte. `GET /boletim/texto` (resumo do boletim) não é pedido pelo RF-31: ver §4. |
| RF-32 | 1 | adaptar | P | `silver.alertas_oficiais.criterio_geo` e `territorio_id` (0008), `ConfiraOficial` em `features/evento/Evento.tsx` | Fonte, hora, filtro geográfico e link para APAC/Cemaden na Situação | Território **exato** do alerta na tela (hoje o território gravado é `recife` por padrão; `area` só em texto) e a orientação "confira na APAC ou no Cemaden" em todo alerta, não só no topo. |

## 3. Requisitos não funcionais

| ID | Veredito | Hoje | Onde está | Evidência | O que falta |
|---|---|---|---|---|---|
| RNF-01 | adaptar | P | `auth/`, `api/autorizacao.py`, `dominio/papeis.py`, `app.auditoria` somente inclusão (0003) | Sessão no servidor, CSRF, Argon2id, bloqueio, 4 papéis; `tests/integration/test_matriz_autorizacao.py`, `test_auditoria.py` | "Quem **acessou** o quê": hoje só login e alterações são auditados; registrar leitura de dados restritos (vulneráveis). |
| RNF-02 | adaptar | P | `api/seguranca.py` (CSP, HSTS, `X-Frame-Options`), Gitleaks no pre-commit e no CI | Sem PHP; independente dos sistemas da prefeitura | Rotas públicas (`/publico/*`) ainda ativas: desligar (ADR 0011); hospedagem (ADR 0013). |
| RNF-03 | adaptar | P | Conectores descartam campos pessoais (`etl/conectores/abrigos.py`, `arboviroses.py`), `config.supressao_minima = 5` | Só contagens na API | Legado `silver.vacinados` e `public.silver_vacinados_legado_etl_avd` com microdados individuais no Neon (D-05); acesso restrito à camada de vulneráveis. |
| RNF-04 | adaptar | P | 12 conectores em `etl/conectores/`; formulários de abrigo e ação | APAC, INMET, Cemaden, IDAP, CKAN, COP (abrigos ativos), InfoDengue, SINAN | COP (estágio, ocupação), Assistência Social, vigilância; **importação manual por arquivo** com hora. |
| RNF-05 | adaptar | P | `GET /fontes` | Status de frescor por fonte | Mesmo que RF-10 e RF-19. |
| RNF-06 | adaptar | P | Índices e cache | Sem orçamento medido | Medir carga da tela principal e do simulador. |
| RNF-07 | adaptar | N | `GET /health` | — | Meta de disponibilidade (P-14), hospedagem e monitor (ADR 0013). |
| RNF-08 | adaptar | P | Fonte Atkinson Hyperlegible, axe no Playwright | — | Reduzir às 5 telas; validar com as duas usuárias. |
| RNF-09 | adaptar | P | `sugerido.motivos`; `GET /risco-alagamento` com `disponivel: false` | Modelo não publicado por não superar a regra (`docs/ml/risco-alagamento.md`) | Nível de confiança por bairro nas regras; ML só pelos critérios do PRD §8.4. |
| RNF-10 | manter | A | ADR 0008, `features/vitrine/dadosReais.ts` (dados oficiais), fixtures só em `backend/tests/**/fixtures/` e `frontend/tests/e2e/` | Nenhum seed no produto; vitrine só em desenvolvimento (`VITE_VITRINE`) | Política escrita no ADR 0010. |
| RNF-11 | manter | A | `.github/workflows/ci.yml` | Jobs: gitleaks; backend `ruff check`, `ruff format --check`, `pytest` com Postgres 16; frontend `npm run lint`, `npm test`, `npm run build` | Propostas (não aplicadas): rodar Playwright `celular`; `scripts/exportar_openapi.py --verificar` para o contrato não ficar velho. |
| RNF-12 | adaptar | P | Atlas e Neon só com dados públicos e registros da equipe | — | Hospedagem definitiva antes de dado não público (ADR 0013, P-07); legado de vacinação (D-05). |

## 4. Funcionalidades existentes fora do PRD ou que mudam

| Funcionalidade | Onde | Veredito | Motivo |
|---|---|---|---|
| Landing pública (busca, avisos, abrigos para a população) | `frontend/src/features/landing/`, `GET /publico/*` | **remover** do produto por chave (`FUNC_LANDING_PUBLICA`), sem apagar | PRD §5 e §12; ADR 0011 |
| Comunicados com revisão e publicação | `features/comunicados/`, `/comunicados/*`, `app.comunicados*`, `app.revisoes` | **remover** por chave (`FUNC_COMUNICADOS`), sem apagar | PRD §5; ADR 0011 |
| Avaliações territoriais | `/avaliacoes/*`, `app.avaliacoes*` (sem tela) | **remover** por chave (`FUNC_COMUNICADOS`) | Só existem para os comunicados |
| Painel antigo | `api/routers/painel.py` (`/painel/resumo`, `/painel/situacao`, `/painel/acoes`) | **remover** depois de a Situação cobrir RF-08..10 | Duplica a Situação; `/painel/acoes` é fila de revisões de comunicados. `AppShell.tsx` ainda usa `/painel` para o contador. |
| Registro do evento (linha do tempo de estágios e ações, lição aprendida) | `features/registro/`, `licao_aprendida` em `app.acoes_resposta`, `app.acao_eventos` | **adaptar** para a tela **Ações** | PRD §5 tira o módulo separado de registro e lições; `acao_eventos` continua como histórico auditável, sem tela própria |
| Mensagem pronta de WhatsApp da mudança de estágio | `POST /estagios/mensagem` | **manter** | RF-31 |
| Resumo do boletim em texto para WhatsApp | `GET /boletim/texto` | **decisão do dono** (D-07) | Não é pedido pelo RF-31 (que cobre a mudança de estágio); nada é enviado, então não fere o §5 |
| Chuva (próximos dias e histórico) | `features/chuva/`, `GET /cenarios`, `GET /series` | **adaptar** | Vira premissas do Simulador (§8.1) e camada do Mapa; sai do menu como tela própria (RF-20) |
| Séries: sazonalidade, referência e estatística descritiva | `/series/sazonalidade`, `/series/referencia`, `/series/estatisticas` | **remover** do menu (rotas sem uso no frontend) | Não pedidas |
| Mapa portátil (HTML offline da Aula 07) | `GET /territorios/mapa-portatil` | **remover** do produto | Não pedido; legado acadêmico |
| Indicadores por distrito para colorir o mapa | `GET /territorios/indicadores` | **adaptar** | Sem uso no frontend; reaproveitar para as camadas |
| Abrigos | `features/abrigos/`, `/abrigos/*` | **manter** | RF-08, RF-09 |
| Saúde depois da chuva | `features/saude/`, `/saude/*`, `/ocorrencias/historico` | **manter** e completar | RF-11, RF-12 |
| Boletim | `features/boletim/`, `GET /boletim` | **adaptar** | Ponto de partida do relatório executivo (RF-17) |
| Fontes | `features/fontes/`, `/fontes`, `/etl/*` | **manter** | Sustenta RF-19 |
| Administração e segurança | `features/admin/`, `/admin/*`, `/auth/*` | **manter** | RNF-01 |
| Modelo de ML de alagamento | `backend/climasense/ml/`, `GET /risco-alagamento` (`disponivel: false`) | **manter desligado** | PRD §8.4: só publica se cumprir os critérios |
| Vitrine de componentes | `features/vitrine/`, `/_vitrine` | **manter** só em desenvolvimento | Usa dados oficiais; já atrás de `VITE_VITRINE` |

## 5. Conflitos com decisões anteriores

1. **Vacinação.** Removida em 04/11/2026 (migração 0009, `specs/foco-chuvas.md` §2). O PRD pede vacinas e medicamentos
   **nos abrigos** (RF-13), quando houver fonte. Não é a vacinação COVID antiga, que continua fora.
2. **Estágio declarado × oficial.** O código trata o declarado pela equipe como o estágio vigente; o PRD (RF-01) pede
   também o **oficial do COP** ao lado. As duas coisas coexistem.
3. **Lições aprendidas** (`specs/foco-chuvas.md` F4, métrica 7) saem do escopo (PRD §5).
4. **Deslizamento** aparece no PRD no mesmo nível do alagamento (RF-02, §8.2); o código e o estudo de ML só tratam
   alagamento (deslizamento só em `gold.ocorrencias_bairro`).
5. **Base territorial.** O PRD diz que "a base territorial só tem geometria de distrito". O repositório já tem a malha
   dos 94 bairros (`data/territorio/bairros-do-recife.geojson`, lida em `territorio/geometria.py` para localizar
   pontos), mas a API não a serve como GeoJSON. Corrigir o PRD ou servir a malha.
6. **`specs/foco-chuvas.md` §5** (quem mexe em quê) foi superada pelo ADR 0012.
