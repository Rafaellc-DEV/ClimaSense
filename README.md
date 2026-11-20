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

Depois, preencha no `.env` as `MONGO_URI` e `DATABASE_URL` (Neon) autorizadas para desenvolvimento. Mantenha `DATABASE_URL_MIGRACOES` **comentada quando não utilizada**: nesse caso, usa-se `DATABASE_URL`, que precisa ter as permissões necessárias. Não deixe `DATABASE_URL_MIGRACOES=` ativa e vazia, pois isso causa erro de URL no SQLAlchemy. A separação de papéis está na [ADR 0014](docs/adr/0014-papel-de-banco-da-aplicacao.md). No VS Code, escolha o interpretador `.venv\Scripts\python.exe` (Ctrl+Shift+P → *Python: Select Interpreter*).

As bibliotecas estão fixadas em [`backend/requirements.txt`](backend/requirements.txt) (aplicação e ETL) e [`backend/requirements-dev.txt`](backend/requirements-dev.txt) (testes e qualidade). O frontend usa o `frontend/package-lock.json`.

> Os arquivos `.env` e `frontend/.env.local` **nunca** vão para o Git. O `pre-commit` roda o gitleaks e bloqueia commits que contenham credenciais.

## Banco de dados e primeiro acesso

No `.env`, além de `MONGO_URI` e `DATABASE_URL`, preencha `ADMIN_EMAIL` e `ADMIN_SENHA_INICIAL` (pelo menos 10 caracteres; uma frase curta funciona bem). O `setup.ps1` gera `SESSION_SECRET` ao criar o `.env`; se o arquivo já existir e o campo estiver vazio, gere com `.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"` e preencha-o.

> Migrações, criação de contas, cargas e uso da aplicação podem gravar nos bancos. Em bancos compartilhados, prossiga somente com autorização do responsável. Se já estiverem preparados, use uma conta autorizada e pule a preparação abaixo.

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
..\.venv\Scripts\python -m climasense.territorio carregar      # distritos, bairros e faixas hídricas → Atlas + app.territorios
..\.venv\Scripts\python -m climasense.etl listar                # fontes e situação
..\.venv\Scripts\python -m climasense.etl atualizar                  # pipeline completo, em ordem, com resumo e verificação da gold
```

Para atualizar previsão, maré e APAC, execute em `backend` (todos gravam nos bancos):

```powershell
..\.venv\Scripts\python.exe -m climasense.etl run open-meteo-previsao
..\.venv\Scripts\python.exe -m climasense.etl run open-meteo-mare
..\.venv\Scripts\python.exe -m climasense.etl run apac-chuva --modo tempo-real
..\.venv\Scripts\python.exe -m climasense.etl run apac-previsao
```

`etl listar` apenas mostra o catálogo, sem conectar aos bancos; `etl verificar-gold` consulta os agregados sem gravar. Fontes, histórico Open-Meteo e fluxo bronze → silver → gold: [`docs/apis-e-etl.md`](docs/apis-e-etl.md). Diagnóstico e atualização periódica: [`docs/operacao-etl.md`](docs/operacao-etl.md). Os detalhes de cada fonte estão em [`docs/dicionario-dados/`](docs/dicionario-dados/).

## Rodar em desenvolvimento

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

Para desligar, aperte **Ctrl+C** no terminal.

Iniciar `dev.ps1` não atualiza as fontes nem gera o modelo de ML.

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1 · documentação interativa em http://localhost:8000/api/docs
- Vitrine da identidade visual (só em desenvolvimento): http://localhost:5173/_vitrine

## Testes

```powershell
.\.venv\Scripts\python.exe scripts/testar_backend_local.py -q -m "not atlas and not integracao"
cd frontend
npm test
npm run lint
cd ..
```

Execute a partir da raiz. O executor do backend isola as configurações de banco. Testes de integração exigem um Postgres **descartável**: as fixtures apagam e recriam esquemas. Nunca use um banco compartilhado em `DATABASE_URL_TESTE`.

## Estudo de ML: risco de alagamento

Árvore de decisão com validação temporal que estima o risco de alagamento por bairro e dia, a partir dos atendimentos da Defesa Civil e da chuva e maré da Open-Meteo. O modelo **0.2.0 é experimental e não validado para uso operacional**. Método, resultados e limitações: [`docs/ml/risco-alagamento.md`](docs/ml/risco-alagamento.md).

Para a demonstração acadêmica local, configure `AMBIENTE=desenvolvimento` e `ML_PREVIA_EXPERIMENTAL_LOCAL=true` no `.env` da raiz. Copie `frontend/.env.example` para `frontend/.env.local`, se ainda não existir, defina `VITE_ML_DEMO_ACADEMICA=true` e reinicie a aplicação. Essa configuração é exclusiva de desenvolvimento e exige uma conta de administrador.

Em um novo dispositivo, gere o artefato executando **dentro de `backend`**:

```powershell
cd backend
..\.venv\Scripts\python.exe -m climasense.ml alagamento-previa-local
cd ..
```

O comando pode demorar na primeira execução; consulta dados reais e grava o modelo localmente, sem gravar nos bancos. O artefato em `tmp/modelos/` **não é versionado no Git**, e sua ausência impede a visualização experimental. Não é preciso gerá-lo a cada inicialização se já existir um artefato compatível. Preparação e compatibilidade: [`docs/ml/previa-local-e-comparacao.md`](docs/ml/previa-local-e-comparacao.md).

Entre como administrador e abra **Simulador → Previsão por distrito → ML de alagamento**. Sem a abertura automática, use **Ver prévia de pesquisa do ML**. No mesmo mapa, escolha uma data para ver a comparação meteorológica e **Atenção preventiva**; há também acesso pela tela **Chuva**. As sinalizações são internas, não alertas oficiais. O ML diário aceita apenas hoje ou amanhã, com dia completo e dados suficientes. Fluxo e limites: [`docs/comparacao-e-prevencao.md`](docs/comparacao-e-prevencao.md) e [`docs/ml/integracao-territorial.md`](docs/ml/integracao-territorial.md).

## Situação atual

| Marco | Situação |
|---|---|
| M0 Fundação do repositório | Concluído |
| M1 Identidade visual e design system | Concluído |
| M2 Backend base e arquitetura | Concluído |
| M3 Autenticação e papéis | Concluído |
| M4 Território (Atlas, GeoJSON, mapa portátil) | Concluído |
| M5 ETL em POO e fontes reais (Open-Meteo) | Concluído |
| M6 em diante (séries, cenários, avaliações, telas da equipe) | Implementações presentes; análise territorial no Simulador. Estado e limites em [`docs/ml/integracao-territorial.md`](docs/ml/integracao-territorial.md) |

## Origem do código

O ClimaSense une o que já existia nos projetos da disciplina, **sem alterar as pastas originais** e usando **somente dados reais**: o ETL (`Projeto-ETL_AVD`), a visualização territorial com MongoDB Atlas (`Desktop/AVD`, Aula 07) e os métodos estatísticos das Atividades 3 e 4. A tabela completa de origem está no [`design.md` §4.1](specs/design.md).

## Equipe

Grupo 3, AVD 2026.2, CESAR School.
