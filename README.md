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

O catálogo de conectores implementados e planejados está em [`docs/apis-e-etl.md`](docs/apis-e-etl.md), com detalhes em
[`docs/dicionario-dados/`](docs/dicionario-dados/). Conector implementado não comprova carga bem-sucedida no banco.

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
.\.venv\Scripts\python.exe scripts/testar_backend_local.py -q -m "not atlas and not integracao"
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
cd frontend
npm test
npm run lint
npm run build
cd ..
```

O executor isolado remove URLs de bancos e não lê `.env`. Testes de integração
exigem um Postgres **descartável**: suas fixtures apagam e recriam esquemas.
Não aponte `DATABASE_URL_TESTE` para bancos compartilhados ou com dados a preservar.

## Estudo de ML: risco de alagamento

**Atualização meteorológica:** diagnóstico, correções do ETL, validação isolada e plano de implantação
em [`docs/operacao-etl.md`](docs/operacao-etl.md). Iniciar `dev.ps1` não atualiza as fontes.
O perfil `etl operacional` e os scripts de agendamento estão preparados; a atualização dos bancos
compartilhados e o registro da tarefa dependem de autorização e da verificação de capacidade.

**Integração territorial:** no Simulador, “Cenário hipotético” mantém as premissas manuais e “Previsão por distrito”
analisa as emissões armazenadas de cada distrito, sem copiar o máximo municipal para todos. O ML é um resultado
paralelo, somente quando publicável; sua ausência não interrompe as regras. O modelo escolhido é o
`0.2.0`, **não validado para uso operacional**. Operação, testes isolados, migração opcional de persistência e
limitações estão em [`docs/ml/integracao-territorial.md`](docs/ml/integracao-territorial.md).

Árvore de decisão com avaliação temporal retrospectiva por bairro-dia, a partir dos atendimentos da
Defesa Civil e da chuva e maré da Open-Meteo. Recall de 80,06% **não é acurácia**:
a precisão observada foi 3,38%, com 7.696 falsos positivos. A AUC-PR foi 0,045971,
abaixo da referência simples de chuva (0,049624). Os experimentos de distrito, SGB
e picos horários não trouxeram melhoria relevante; 2024 já não é holdout independente.
Métodos, números verificáveis, reprodução e limitações:
[`docs/ml/risco-alagamento.md`](docs/ml/risco-alagamento.md).

**Demonstração acadêmica automática:** no `.env` do backend, configure
`AMBIENTE=desenvolvimento` e `ML_PREVIA_EXPERIMENTAL_LOCAL=true`. Copie
`frontend/.env.example` para `frontend/.env.local`, ligue `VITE_ML_DEMO_ACADEMICA=true`
e reinicie o Vite. Ao abrir o Simulador como administrador, a camada ML mostra a
prévia local com o aviso **não validada para uso operacional**. A rota exige
ambiente + configuração + permissão; o bloqueio científico das rotas normais permanece.

```powershell
cd backend
..\.venv\Scripts\python -m climasense.ml alagamento-previa-local --sem-banco  # configuração fixa; só se faltar o artefato local
..\.venv\Scripts\python -m pytest tests/unit/ml        # testes (dados sintéticos, sem banco)
cd ..
```

O treinamento completo continua disponível em `python -m climasense.ml alagamento`;
escolha `--saida` e `--modelo` para não sobrescrever as evidências desta entrega.
A [revisão da consolidação](docs/ml/consolidacao-academica.md) registra patches,
arquivos locais preservados e validações executadas.

## Situação atual

| Marco | Situação |
|---|---|
| M0 Fundação do repositório | Concluído |
| M1 Identidade visual e design system | Concluído |
| M2 Backend base e arquitetura | Concluído |
| M3 Autenticação e papéis | Concluído |
| M4 Território (Atlas, GeoJSON, mapa portátil) | Concluído |
| M5 ETL em POO e fontes reais (Open-Meteo) | Concluído |
| M6 em diante (séries, cenários, avaliações, telas da equipe) | Implementações presentes; análise territorial integrada ao Simulador. Aceite e limitações em [`docs/ml/integracao-territorial.md`](docs/ml/integracao-territorial.md); o plano histórico está em [`specs/tasks.md`](specs/tasks.md) |

## Origem do código

O ClimaSense une o que já existia nos projetos da disciplina, **sem alterar as pastas originais** e usando **somente dados reais**: o ETL (`Projeto-ETL_AVD`), a visualização territorial com MongoDB Atlas (`Desktop/AVD`, Aula 07) e os métodos estatísticos das Atividades 3 e 4. A tabela completa de origem está no [`design.md` §4.1](specs/design.md).

## Equipe

Grupo 3, AVD 2026.2, CESAR School.
