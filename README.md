<p align="center"><img src="docs/brand/climasense-logo.png" alt="ClimaSense" width="360"></p>

> **Antecipar riscos. Orientar decisões. Cuidar do território.**

O ClimaSense reúne dados de clima, território e saúde do Recife para ajudar a Vigilância em Saúde a decidir **quais territórios precisam de atenção primeiro, por quais motivos e com qual nível de confiança**. Ele também comunica à população os avisos que já foram revisados pela equipe.

Projeto acadêmico da disciplina de Análise e Visualização de Dados (AVD), CESAR School. O ClimaSense **não substitui** os alertas oficiais da Defesa Civil.

---

## Como o projeto é organizado

O projeto segue **Spec-Driven Development**: especificação → design → tarefas → execução.

| Documento | Para quê |
|---|---|
| [`specs/requirements.md`](specs/requirements.md) | O que deve ser feito: jornadas, regras de negócio e critérios de aceite |
| [`specs/design.md`](specs/design.md) | Como será feito: arquitetura, dados, API, identidade visual e telas |
| [`specs/tasks.md`](specs/tasks.md) | Passos pequenos e verificáveis, com o estado de cada um |
| [`docs/arquitetura.md`](docs/arquitetura.md) | Visão da arquitetura do sistema e das camadas |
| [`docs/adr/`](docs/adr/) | Registros das decisões de arquitetura |
| [`docs/brand/guia-de-marca.md`](docs/brand/guia-de-marca.md) | Identidade visual: logo, cores, tipografia e a régua de maré |

```text
ClimaSense/
├── specs/            requisitos, design e tarefas
├── docs/             arquitetura, ADRs, marca, dicionário de dados, qualidade
├── data/territorio/  arquivos oficiais do Recife (cópia íntegra + MANIFEST.sha256)
├── backend/          API FastAPI + ETL + território (Python)
├── frontend/         landing pública + área da equipe (React + TypeScript)
└── scripts/          utilitários (ex.: gerar o traço cartográfico)
```

## Pré-requisitos

- Python **3.12** ou mais novo
- Node.js **22**
- Acesso ao **MongoDB Atlas** (bronze e território) e a um **Postgres** (Neon na nuvem ou o `docker-compose.yml` local)

## Primeira configuração

O ambiente virtual **`.venv`** fica dentro da pasta `ClimaSense` e é criado no seu computador (ele não vai para o Git). Um único script cria a `.venv`, instala todas as bibliotecas Python e do frontend e prepara o `.env`.

No terminal do VS Code, dentro da pasta ClimaSense (só uma vez):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Depois, preencha no `.env` as mesmas `MONGO_URI` e `DATABASE_URL` (Neon) usadas no ETL anterior. Com o banco migrado, `python -m climasense.admin criar-papel-app` cria o papel `climasense_app` e passa a URL do dono para `DATABASE_URL_MIGRACOES` (ADR 0014). No VS Code, escolha o interpretador `.venv\Scripts\python.exe` (Ctrl+Shift+P → *Python: Select Interpreter*).

As bibliotecas estão fixadas em [`backend/requirements.txt`](backend/requirements.txt) (aplicação e ETL) e [`backend/requirements-dev.txt`](backend/requirements-dev.txt) (testes e qualidade). O frontend usa o `frontend/package-lock.json`.

> O arquivo `.env` **nunca** vai para o Git. O `pre-commit` roda o gitleaks e bloqueia commits que contenham credenciais.

## Banco de dados e primeiro acesso

No `.env`, além de `MONGO_URI` e `DATABASE_URL`, preencha `ADMIN_EMAIL` e `ADMIN_SENHA_INICIAL` (pelo menos 10 caracteres; uma frase curta funciona bem). Se o `SESSION_SECRET` estiver vazio, o `setup.ps1` gera um, ou gere com `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

```powershell
cd backend
..\.venv\Scripts\alembic upgrade head                    # cria os esquemas app, silver e gold
..\.venv\Scripts\python -m climasense.admin criar-admin   # cria o primeiro administrador
cd ..
```

> **Neon com o ETL antigo:** se já existir a tabela `public.silver_vacinados` criada pelo `Projeto-ETL_AVD`, a migração a preserva com o nome `silver_vacinados_legado_etl_avd` (nenhum dado é apagado). O nome antigo passa a ser uma view sobre `silver.vacinados`. Ambas ficam como legado do projeto antigo: a vacinação saiu do ClimaSense (o produto foca chuva, alagamento e deslizamento) e nada no sistema as lê.

No primeiro acesso, o ClimaSense pede a troca da senha. As demais contas da equipe são criadas pelo administrador; cada pessoa recebe uma senha temporária, que precisa trocar ao entrar.

## Carregar os dados reais

Com o `.env` preenchido, dentro de `backend` (cada comando busca a fonte real pela internet):

```powershell
..\.venv\Scripts\python -m climasense.territorio carregar      # distritos, bairros e faixas hídricas → Atlas + app.territorios (103 linhas)
..\.venv\Scripts\python -m climasense.etl listar                # fontes e situação
..\.venv\Scripts\python -m climasense.etl atualizar                  # pipeline completo, em ordem, com resumo e verificação da gold
```

Ou fonte a fonte: `etl run open-meteo-historico`, `etl run open-meteo-previsao`, `etl run open-meteo-mare` e `etl verificar-gold` (também `python scripts/verificar_gold.py`). Mapa das APIs, fluxo bronze → silver → gold e agendamento: [`docs/apis-e-etl.md`](docs/apis-e-etl.md).

As fontes planejadas (ANA, APAC, INMET, Cemaden, alagamentos, tábua da Marinha) estão descritas em [`docs/dicionario-dados/`](docs/dicionario-dados/) e não geram dados até terem conector.

## Rodar em desenvolvimento

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

Para desligar, aperte **Ctrl+C** no terminal.

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1 · documentação interativa em http://localhost:8000/api/docs
- Vitrine da identidade visual (só em desenvolvimento): http://localhost:5173/_vitrine

## Testes

```powershell
cd backend;  ..\.venv\Scripts\pytest            # unidade; integração com Postgres real se DATABASE_URL_TESTE estiver definido
#   Ex.: $env:DATABASE_URL_TESTE="postgresql://climasense:climasense@localhost:5432/climasense"  (docker compose up -d)
cd frontend; npm test; npm run lint
```

## Estudo de ML: risco de alagamento

Árvore de decisão com validação temporal que estima o risco de alagamento por bairro e dia, a partir dos atendimentos da Defesa Civil e da chuva e maré da Open-Meteo. Método, resultado e por que o modelo ainda não é exibido no produto: [`docs/ml/risco-alagamento.md`](docs/ml/risco-alagamento.md).

```powershell
cd backend
..\.venv\Scripts\python -m climasense.ml alagamento   # treina, valida no tempo, salva o modelo e grava o relatório em docs/ml
..\.venv\Scripts\python -m pytest tests/unit/ml        # testes (dados sintéticos, sem banco)
```

## Situação atual

| Marco | Situação |
|---|---|
| M0 Fundação do repositório | Concluído |
| M1 Identidade visual e design system | Concluído |
| M2 Backend base e arquitetura | Concluído |
| M3 Autenticação e papéis | Concluído |
| M4 Território (Atlas, GeoJSON, mapa portátil) | Concluído |
| M5 ETL em POO e fontes reais (Open-Meteo) | Concluído |
| M6 em diante (séries, cenários, avaliações, telas da equipe) | Planejado — ver [`specs/tasks.md`](specs/tasks.md) |

## Origem do código

O ClimaSense une o que já existia nos projetos da disciplina, **sem alterar as pastas originais** e usando **somente dados reais**: o ETL (`Projeto-ETL_AVD`), a visualização territorial com MongoDB Atlas (`Desktop/AVD`, Aula 07) e os métodos estatísticos das Atividades 3 e 4. A tabela completa de origem está no [`design.md` §4.1](specs/design.md).

## Equipe

Grupo 3, AVD 2026.2, CESAR School.
