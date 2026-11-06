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
