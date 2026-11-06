# ADR 0012 — Pastas de cada agente na estrutura real do repositório

- **Situação:** proposta (Gate 0)
- **Data:** 06/11/2026
- **Base:** `docs/ESTRATEGIA-AGENTES.md` v2, seção 3; `.claude/agents/*.md` (seção 7, copiados sem alteração)

## Contexto

A estratégia v2 dá a cada agente um conjunto de pastas para que agentes em paralelo não editem o mesmo arquivo. Ao
conferir com a árvore real, há quatro diferenças:

1. A estratégia cita `backend/alembic/`, que não existe. As migrações estão em `backend/migrations/` (com
   `backend/alembic.ini`).
2. Pastas sem dono: `backend/climasense/servicos/` (casos de uso de estágios, abrigos, ações, boletim, saúde),
   `backend/climasense/territorio/` (carga oficial e geometria), `backend/climasense/modelos/` (interface do estimador),
   `backend/climasense/{config,admin,__main__}.py`, `backend/pyproject.toml`, `backend/requirements*.txt`, `scripts/`,
   `data/`, a configuração do frontend (`frontend/package.json`, `vite.config.ts`, `playwright*.config.ts`) e a
   infraestrutura (`.github/`, `.pre-commit-config.yaml`, `docker-compose.yml`, `dev*.ps1`, `setup.ps1`).
3. Sobreposição em testes: `qa-ux` é dono de `backend/tests/` e `frontend/tests/`, mas `backend-api`, `etl-dados` e
   `ml-risco` devem entregar "testes novos para o que mudou".
4. O router `backend/climasense/api/routers/risco_alagamento.py` era do ML (`specs/foco-chuvas.md` §5) e agora fica em
   `api/`, do `backend-api`.

## Decisão

| Agente | Pastas (estratégia v2) | Complemento proposto por esta ADR |
|---|---|---|
| `arquiteto` | `docs/`, `.claude/`, `CLAUDE.md` | exceto `docs/dicionario-dados/` (etl-dados) e `docs/ml/` (ml-risco); `docs/api/openapi.json` é gerado, não editado |
| `backend-api` | `backend/climasense/api/`, `dominio/`, `auth/`, `infra/`, `backend/alembic/` | `backend/alembic/` = **`backend/migrations/`** + `backend/alembic.ini`; mais `servicos/`, `config.py`, `admin.py`, `__main__.py`, `backend/pyproject.toml`, `backend/requirements*.txt`, `scripts/` (geradores de documentação a partir da API) |
| `etl-dados` | `backend/climasense/etl/`, `docs/dicionario-dados/` | mais `backend/climasense/territorio/` (carga do território, como diz a estratégia) e `data/` (arquivos oficiais versionados). A importação manual fica em `backend/climasense/etl/importacao/`; a rota de envio do arquivo é do `backend-api` |
| `ml-risco` | `backend/climasense/ml/`, `docs/ml/` | mais `backend/climasense/modelos/` |
| `frontend-equipe` | `frontend/src/` | mais `frontend/package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `eslint.config.js`, `index.html`, `public/`; os testes unitários junto dos componentes (`frontend/src/**/*.test.ts[x]`) |
| `seguranca-lgpd` | nenhuma | — |
| `qa-ux` | `backend/tests/`, `frontend/tests/` | mais `frontend/playwright*.config.ts` |
| sessão principal, com aprovação do usuário | — | `.github/`, `.pre-commit-config.yaml`, `.gitleaks.toml`, `docker-compose.yml`, `dev*.ps1`, `setup.ps1`, `infra/` (quando existir) |

**Testes (resolve a sobreposição):** cada agente que implementa escreve os testes da sua área na subpasta
correspondente, e o `qa-ux` é dono do resto e revisa:

| Subpasta | Quem escreve |
|---|---|
| `backend/tests/unit/{api,dominio}/`, `backend/tests/unit/test_*.py`, `backend/tests/integration/` (exceto `test_etl_*.py`) | `backend-api` |
| `backend/tests/unit/{etl,territorio}/`, `backend/tests/integration/test_etl_*.py`, `backend/tests/unit/etl/fixtures/` | `etl-dados` |
| `backend/tests/unit/ml/` | `ml-risco` |
| `frontend/tests/e2e/`, `backend/tests/conftest.py`, `backend/tests/fixtures/`, `frontend/tests/setup.ts`, `frontend/tests/unit/` e testes de aceite novos por RF | `qa-ux` |

**Regras de fronteira:**

1. Arquivo compartilhado (`backend/climasense/api/main.py` para registrar router, `frontend/src/app/App.tsx` para
   rota, `frontend/src/app/AppShell.tsx` para menu): só o dono edita; os demais pedem pela sessão principal.
2. Tabela nova só por migração do `backend-api`. Quem precisa de tabela (etl-dados, ml-risco) pede.
3. A regra de camadas continua verificada por `backend/tests/unit/test_arquitetura.py`.
4. Nenhum agente faz commit (estratégia v2, princípio 6).

## Alternativas consideradas

- **Corrigir o texto dos agentes direto** (`backend/alembic/` → `backend/migrations/`): a estratégia pede os arquivos
  com o conteúdo exato da seção 7; a correção fica registrada aqui e vira edição dos agentes se o dono aprovar.
- **`qa-ux` como único autor de testes**: atrasaria cada tarefa e contradiz "testes novos para o que mudou" nos agentes
  que implementam.

## Consequências

- `specs/foco-chuvas.md` §5 ("Quem mexe em quê") fica superada por esta ADR.
- Se aprovada, a sessão principal ajusta `.claude/agents/backend-api.md` (`backend/migrations/`) e acrescenta os
  complementos acima aos agentes.
