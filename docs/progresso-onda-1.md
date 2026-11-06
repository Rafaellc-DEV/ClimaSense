# Progresso da Onda 1

Branch `evolucao-prd-v2`, commits locais no nome do dono, sem push. Cada etapa termina com os checks da área verdes.

## Etapa 0 — Segurança urgente (06/11/2026)

**O que mudou**
- Base: rodada anterior e Onda 0 commitadas; hooks bloqueiam commit na `main` e todo push; o hook do Prettier usa a
  versão do projeto (3.3.3), que antes brigava com a 3.1.0 do mirror.
- RNF-02 (ADR 0011): chaves `FUNC_*` / `VITE_FUNC_*` desligadas por padrão (landing e `/publico/*`, inclusive a busca
  pública de territórios; comunicados; avaliações; mapa portátil; estatísticas de séries). Rota não registrada,
  item fora do menu, `/` abre o login. Em produção, `/api/docs`, `/api/redoc` e `/api/openapi.json` dão 404 e
  `/health` responde só o status.
- RNF-01: login com limite por IP (20 falhas/15 min), bloqueio por e-mail contado só no mesmo IP, atraso progressivo
  (2^k s, teto 30 s), desbloqueio pelo administrador (`POST /admin/login/liberar`, auditado) e IP real atrás de proxy
  confiável (`PROXIES_CONFIAVEIS`). Migração 0012.
- RNF-03, RNF-12 (ADR 0010): legado de vacinação exportado para `C:\Users\rlc3\vacinacao-climasense-2026-11-06.tar.gpg`
  (AES-256; senha em `C:\Users\rlc3\chave-vacinacao.txt`, nunca impressa), validado decifrando uma cópia (36.064,
  4.716, 25 e 60.000 registros), e depois apagado do Atlas (coleção e banco `vacinacao`) e do Neon (migração 0013).
- RNF-01, RNF-12 (ADR 0014): papel `climasense_app` para a API, sem DDL e sem posse; auditoria e históricos só
  SELECT/INSERT. O dono (`DATABASE_URL_MIGRACOES`) fica para migrações e ETL. Migração 0014.
- Neon na versão 0014. Verificado: API conecta como `climasense_app`; `UPDATE app.auditoria` e `CREATE TABLE` negados.
- RNF-02: react-router 6.30.6 e echarts 6.1.0 (adiantado da Etapa 4); `npm audit --omit=dev` sem alta nem crítica.
- `.gitleaks.toml` passa a pegar `postgresql+driver://`.

**Testes**: backend 946 passed (unit + integration, Postgres local), ruff limpo; frontend lint, tsc, 176 testes e build verdes.

**Pendências**
- Sem branch do Neon (sem `neonctl` nem chave de API): migrações testadas no Postgres local antes do Neon.
- Restam 2 vulnerabilidades moderadas do react-router que só a v7 corrige (sem SSR, links internos).
- Suíte de integração inteira como `climasense_app`: 11 testes semeiam silver/gold e precisam do dono (esperado).
- P-19 (trocar a senha do `neondb_owner`) e P-20 (ETL disparado pela API usa a URL do dono) em `docs/perguntas-abertas.md`.
- Login de verificação na API com o papel novo não foi testado pelo agente (senha do gestor não está no repositório).

## Etapa 1 — Frescor e supressão (06/11/2026)

**O que mudou**
- RF-19, RNF-05: limites de frescor por fonte em `backend/climasense/etl/frescor.toml` (fonte única), com
  `esta_desatualizado` que devolve `None` sem dado (nunca "em dia" por falta de dado). Seção "Frescor" no
  dicionário de dados de cada fonte.
- RF-19, RF-10: `meta.fontes` com `limite_frescor_h` e `desatualizado` em toda rota de indicador; `GET /abrigos`
  ganhou `meta` sem quebrar `itens` e `totais`.
- RNF-03, RN-13: contagens de 1 a 4 em `/saude/bairros` saem como `null` com `suprimido: true`; totais que
  revelariam a célula saem nulos (ADR 0015). Única rota com agravo por território hoje.
- RNF-01: leitura de `/saude/*` e `/boletim*` auditada (`leitura_dados_saude`, `leitura_boletim`), sem o corpo.
- RNF-03: limites de valor e mensagens 422 em português; prazo de guarda (90 dias para tentativas de login, 30 dias
  após expirar para sessões) no comando `python -m climasense.admin limpar-retencao` (ADR 0015).
- Frontend: fonte e "atualizado há" em todo indicador, selo "Desatualizado", "Dados insuficientes: falta a fonte X";
  atualização automática (60 s; saúde 10 min; pausa com a aba oculta); "< 5" para valores suprimidos; aviso
  "Não escreva nome, CPF ou dado de saúde de pessoas" nos textos livres.

**Testes**: backend 968 passed (unit + integration), ruff limpo; frontend lint, tsc, 188 testes e build verdes.

**Pendências**
- **Para o dono:** `python -m climasense.admin sincronizar-frescor` e `limpar-retencao` NÃO rodaram no Neon: o
  classificador de permissões negou a execução ao agente. Até rodar, a tela de Fontes usa os limites antigos de
  `app.fontes`, enquanto `meta.fontes` já usa o TOML. Rodar com o `.env` (sem `DATABASE_URL`, `MONGO_URI` e
  `DATABASE_URL_MIGRACOES` exportados no shell).
- A limpeza do prazo de guarda é manual ou por agendador (não roda no ETL).
- Revisão visual em celular e desktop pendente (fica para o `qa-ux`).

## Etapa 2 — Estágio oficial do COP e mapa por bairro (06/11/2026)

**O que mudou**
- RF-01, RNF-04: não há fonte pública legível do estágio oficial da cidade (busca em `docs/pesquisa/estagio-oficial-cop.md`;
  pergunta P-21 ao COP). O estágio oficial entra por registro auditado da equipe: `GET/POST /estagios/oficial`,
  histórico somente-inclusão (`app.estagio_oficial`, migração 0015, aplicada no Neon). Sem registro: "Dados insuficientes".
- RF-01, RF-07: `GET /territorios/bairros.geojson` com os 94 bairros (simplificado, ~96 KB, ETag).
- RF-06, RF-22, RN-06: `GET /territorios/prioridade` ordena distritos e bairros pelo histórico de atendimentos da Defesa
  Civil, com o critério escrito e sem percentual.
- Frontend: a tela **Mapa** passa a ser a principal (`/app`); Situação em `/app/situacao`. Bairros coloridos pelo
  estágio (declarado cheio, sugerido listrado, sem dado em hachura cinza), faixa do estágio do COP com "Informar",
  painel do bairro (estágio, alertas com fonte/hora/território e APAC/Cemaden, abrigos, Declarar), prioritários e
  lista de bairros como alternativa por teclado.

**Testes**: backend 981 passed (unit + integration no Postgres local), ruff limpo; frontend lint, tsc, 204 testes e
build verdes. Rotas novas conferidas na API real contra o Neon (94 bairros; prioridade com dados).

**Pendências**
- O Neon tem só ocorrências de alagamento (1.722 bairro-dia): foi carregado antes de o conector ler deslizamentos.
  Sem deslizamento, a prioridade não reflete o DS VII (vulnerável a deslizamentos, segundo o cliente). A recarga de
  `recife-alagamento` foi interrompida por um reinício de sessão (nada gravado) e foi relançada.
- Duas execuções antigas de `recife-alagamento` ficaram como "em_andamento" em `app.etl_execucoes`.
- Alertas oficiais são municipais (sem área própria): o painel diz "alerta do município do Recife".
- `/estagios?nivel=bairro` leva ~4 s na API local; a previsão estava com 25 h (ETL de tempo real não rodou).

## Etapa 3 — Simulador de cenário (06/11/2026)

**O que mudou**
- RF-23, RF-24, RF-25, RF-28, RN-01, RN-06, RN-11: `GET /cenarios/premissas-atuais` (valores das fontes reais, com
  `meta.fonte_por_premissa`) e `POST /cenarios/simular`: classes ordinais por bairro e distrito (alagamento,
  deslizamento, estágio sugerido) pelos gatilhos de estágio + histórico da Defesa Civil, confiança (nunca "alta" antes
  da validação), 1 a 3 motivos, limiar sensível, selo experimental e `tempo_calculo_ms`. Premissa desconhecida (null)
  não vira zero: o gatilho não é avaliado e a confiança cai.
- RF-27: cenários salvos (`app.cenarios`, somente-inclusão, migração 0016 aplicada no Neon).
- A antiga estimativa "e se chover X" passou para `GET /cenarios/estimativa` (Chuva > Próximos dias atualizado).
- Frontend: tela **Simulador** com premissas pré-preenchidas (uma linha de fonte por campo), mapa que recalcula sozinho,
  alternância Alagamento/Deslizamento/Situação sugerida, motivos ao clicar, salvar e abrir cenários; cabe em 375 px.
- Dados: recarga de `recife-alagamento` com deslizamentos (Neon: 1.722 alagamentos e 3.266 deslizamentos por
  bairro-dia). O DS VII passa a liderar os prioritários (1.237 deslizamentos), como o cliente descreveu. Previsão, maré,
  APAC, alertas e abrigos ativos atualizados; quatro execuções interrompidas fechadas como falha.

**Testes**: backend 1039 passed, ruff limpo; frontend lint, tsc, 212 testes e build verdes. Conferido com a API real
(Edge, 1440 e 375 px, sem rolagem horizontal; cálculo em 1,3 s).

**Pendências**
- Queda de rede (DNS do Neon) travou dois agentes e uma carga; tudo foi retomado e refeito.
- A lista "Bairros, do mais exposto ao menos" do Simulador mistura bairros e distritos ("102 bairros"): ajustar o
  rótulo na Etapa 5.
- `impacto_pessoas` segue nulo até a Etapa 6 (população vulnerável).
