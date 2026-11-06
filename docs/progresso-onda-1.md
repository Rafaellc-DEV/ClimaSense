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
