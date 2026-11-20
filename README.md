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

- **Git**, **Python 3.12+** e **Node.js 22** com npm no `PATH`. O backend declara Python `>=3.12` em [`backend/pyproject.toml`](backend/pyproject.toml); a CI usa Python 3.12 e Node 22.
- **Windows com PowerShell** para os comandos e scripts deste guia. Em outros sistemas, use os equivalentes de `.venv/bin/python` e inicie API e Vite em terminais separados.
- Acesso autorizado ao **Postgres/Neon** (aplicação, Silver e Gold) e ao **MongoDB Atlas** (Bronze e território), com rede liberada para o seu computador.
- Internet para instalar dependências e consultar fontes públicas. **Docker é opcional** para bancos isolados: os scripts locais usam Postgres **16** e MongoDB **7**.

## Clonar e selecionar a branch

```powershell
git clone --branch feat/ml-comparacao-alertas https://github.com/Rafaellc-DEV/ClimaSense.git
cd ClimaSense
git branch --show-current
```

O último comando deve mostrar `feat/ml-comparacao-alertas`. Em um clone existente e sem alterações pendentes, use `git fetch origin` e `git switch feat/ml-comparacao-alertas`. Os comandos a seguir partem da **raiz do repositório**, salvo indicação explícita.

## Configurar o ambiente

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
```

Faça as cópias apenas se os arquivos de destino ainda não existirem, para preservar configurações locais. O backend lê o `.env` da raiz (e também um `.env` no diretório de execução, se houver); variáveis exportadas no terminal têm prioridade. Evite arquivos duplicados em `backend/`.

Preencha no `.env`:

| Variável | Configuração local |
|---|---|
| `AMBIENTE` | `desenvolvimento` |
| `ML_PREVIA_EXPERIMENTAL_LOCAL` | `true` exclusivamente para desenvolvimento e demonstração acadêmica; não gera o modelo nem o valida para operação |
| `DATABASE_URL` | URL Postgres/Neon autorizada; formato `postgresql://USUARIO:SENHA@SEU-HOST.neon.tech/climasense?sslmode=require`. `NEON_URL` é um alias, mas prefira só `DATABASE_URL` |
| `DATABASE_URL_MIGRACOES` | **Mantenha comentada** quando a URL principal tiver as permissões necessárias. Se precisar de papel distinto para Alembic/ETL/administração, forneça uma URL válida autorizada. Nunca deixe `DATABASE_URL_MIGRACOES=` ativa e vazia |
| `MONGO_URI` | URI Atlas autorizada, como `mongodb+srv://USUARIO:SENHA@SEU-CLUSTER.mongodb.net/?retryWrites=true&w=majority` |
| `MONGO_DB_TERRITORIO` | `Recife` por padrão; a Bronze usa o banco `bronze` |
| `SESSION_SECRET` | Segredo aleatório gerado localmente após instalar as dependências, conforme abaixo |
| `ADMIN_EMAIL` / `ADMIN_SENHA_INICIAL` | E-mail válido e senha com pelo menos 10 caracteres, sem conter o e-mail ou o nome do usuário; usados por `criar-admin` |
| `CORS_ORIGINS` | `http://localhost:5173`; se houver várias origens, separe por vírgulas |

Os demais padrões estão comentados no [`.env.example`](.env.example): duração de sessão, proxies, supressão, retenção, tiles e funcionalidades opcionais. Não são necessárias chaves de API para Open-Meteo ou APAC. `ANA_USUARIO` e `ANA_SENHA` são reservadas a conectores futuros.

Para a demonstração automática do ML, altere **`frontend/.env.local`** para `VITE_ML_DEMO_ACADEMICA=true`. O Vite lê esse arquivo, não o `.env` da raiz. Todas as variáveis `VITE_*` são públicas no navegador: nunca coloque segredos nelas.

## Instalar as dependências

Na raiz, o script cria `.venv`, instala backend/ETL/testes e frontend e instala os hooks de proteção do Git:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

O script preserva um `.env` existente. Como o arquivo foi copiado no passo anterior, gere o segredo e cole o resultado em `SESSION_SECRET` no `.env`:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Para instalar manualmente, em vez de executar `setup.ps1`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e backend --no-deps
cd frontend
npm ci
cd ..
.\.venv\Scripts\pre-commit.exe install
```

As versões estão fixadas em [`backend/requirements.txt`](backend/requirements.txt), [`backend/requirements-dev.txt`](backend/requirements-dev.txt) e [`frontend/package-lock.json`](frontend/package-lock.json). No VS Code, selecione `.venv\Scripts\python.exe` em **Python: Select Interpreter**. Não é necessário ativar a `.venv` para usar os comandos deste guia.

O `.env`, `frontend/.env.local`, `.venv`, `tmp/` e arquivos `.joblib` ficam fora do Git. Os hooks executam gitleaks para detectar credenciais.

## Configurar e verificar Neon e MongoDB Atlas

No Neon, use a conexão do banco/branch destinado ao desenvolvimento, com `sslmode=require`. No Atlas, confirme usuário de banco, permissões para `bronze` e `MONGO_DB_TERRITORIO` e liberação do seu IP em **Network Access**. Preencha as URLs localmente, sem publicá-las em logs ou commits.

Antes de migrar ou carregar dados, é possível testar as conexões **sem gravações**, usando as funções existentes. Execute em `backend`; ambos devem imprimir `True`:

```powershell
cd backend
..\.venv\Scripts\python.exe -c "from climasense.infra.postgres import engine_da_configuracao, verificar; print(verificar(engine_da_configuracao()))"
..\.venv\Scripts\python.exe -c "from climasense.infra.mongo import conectar, verificar; c = conectar(); print(verificar(c)); c.close()"
cd ..
```

Esses testes fazem `SELECT 1` no Postgres e `ping` no Mongo; não verificam a existência dos esquemas nem a autorização para gravar. Depois de iniciar a API, `GET http://localhost:8000/api/v1/health` também consulta as conexões; em desenvolvimento, confira `bancos.postgres=ok` e `bancos.mongo=ok`.

**Bancos compartilhados:** obtenha autorização do responsável antes de migrações, criação de contas/papéis, cargas, atualizações de fontes ou uso da aplicação que grave sessões e auditoria. Iniciar a API também ativa rotinas de manutenção; não equivale a uma verificação somente de leitura. Se o ambiente compartilhado já estiver preparado, reutilize uma conta autorizada e pule a preparação abaixo.

### Preparar um banco novo e o primeiro acesso (gravações)

Execute somente em bancos próprios de desenvolvimento ou destinos cuja alteração foi autorizada. Os comandos abaixo aplicam migrações, criam a conta administrativa e gravam território no Atlas e no Postgres:

```powershell
cd backend
..\.venv\Scripts\alembic.exe upgrade head
..\.venv\Scripts\python.exe -m climasense.admin criar-admin
..\.venv\Scripts\python.exe -m climasense.territorio carregar
cd ..
```

No primeiro login, troque a senha. As demais contas são criadas pelo administrador. A separação entre o papel `climasense_app` e o dono está na [ADR 0014](docs/adr/0014-papel-de-banco-da-aplicacao.md). O comando `python -m climasense.admin criar-papel-app` altera a senha do papel e reescreve as URLs no `.env`; não é obrigatório para verificar conexão e não deve ser executado sem autorização em banco compartilhado.

Para isolar tudo com Docker, o script existente `powershell -ExecutionPolicy Bypass -File .\dev-local.ps1 -Preparar` cria Postgres na porta `55433` e Mongo na `27018`, aplica migrações, carrega território, executa o ETL completo e inicia a aplicação. Ele substitui as URLs **somente no próprio processo** e não cria o administrador. Para usar os comandos manuais acima nesses contêineres, exporte no terminal as URLs locais definidas em [`dev-local.ps1`](dev-local.ps1), incluindo `DATABASE_URL_MIGRACOES`; terminais novos não herdam essas substituições. Sem `-Preparar`, o script apenas inicia os contêineres e a aplicação.

## Iniciar backend e frontend

Com os bancos preparados e o acesso autorizado, na raiz:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

O script inicia API e Vite. Para encerrar ambos, pressione **Ctrl+C**. Alternativamente, execute cada serviço em um terminal na raiz:

```powershell
# Terminal 1: backend
.\.venv\Scripts\python.exe -m uvicorn climasense.api.main:app --reload --reload-dir backend/climasense --port 8000 --app-dir backend
```

```powershell
# Terminal 2: frontend
cd frontend
npm run dev
```

- Frontend: http://localhost:5173
- Login: http://localhost:5173/entrar
- API: http://localhost:8000/api/v1 · documentação interativa: http://localhost:8000/api/docs
- Vitrine da identidade visual (só em desenvolvimento): http://localhost:5173/_vitrine

O Vite encaminha `/api` para `localhost:8000`; não há variável de URL da API a preencher. Reinicie backend e Vite após alterar configurações. **Iniciar `dev.ps1` não atualiza fontes nem gera o modelo.**

## Carregar e atualizar as fontes reais

Dentro de `backend`, estes comandos são **somente consulta**: `listar` mostra o catálogo implementado/planejado sem conectar aos bancos; `verificar-gold` lê Silver e Gold e compara os agregados sem gravar:

```powershell
cd backend
..\.venv\Scripts\python.exe -m climasense.etl listar
..\.venv\Scripts\python.exe -m climasense.etl verificar-gold
cd ..
```

Para uma primeira carga completa em bancos próprios ou com autorização, execute `..\.venv\Scripts\python.exe -m climasense.etl atualizar` **dentro de `backend`**. Esse pipeline grava território e todas as fontes reais na ordem prevista; pode demorar. Fontes planejadas não são carregadas. O catálogo não comprova que uma carga foi bem-sucedida.

Para atualizar apenas clima e APAC, execute em `backend` os comandos abaixo. **Todos gravam** Bronze no Mongo e Silver/Gold/metadados no Postgres e exigem permissões de escrita e autorização para o destino:

```powershell
cd backend
..\.venv\Scripts\python.exe -m climasense.etl run open-meteo-historico
..\.venv\Scripts\python.exe -m climasense.etl run open-meteo-previsao
..\.venv\Scripts\python.exe -m climasense.etl run open-meteo-mare
..\.venv\Scripts\python.exe -m climasense.etl run apac-chuva --modo tempo-real
..\.venv\Scripts\python.exe -m climasense.etl run apac-previsao
cd ..
```

A chuva observada APAC é distinta da previsão APAC. Para o histórico diário, existe `etl run apac-chuva --modo historico --limite 1` (um mês, também grava). O perfil `etl operacional` reúne fontes meteorológicas com cadência por fonte; destinos remotos exigem aprovação prévia e `--permitir-remoto`. Não é necessário agendar tarefas para executar a aplicação.

Na tela **Fontes**, consulte última tentativa, último sucesso e cobertura. O botão de atualizar também grava nos bancos. Comandos completos, agendamento e diagnóstico: [APIs e ETL](docs/apis-e-etl.md), [operação do ETL](docs/operacao-etl.md) e [dicionário de dados](docs/dicionario-dados/).

## Estudo de ML: risco de alagamento

### Ativar a prévia experimental 0.2.0 e gerar o artefato

A prévia é **exclusiva de desenvolvimento local e demonstração acadêmica**, com o aviso **não validada para uso operacional**. No `.env` da raiz, confirme `AMBIENTE=desenvolvimento` e `ML_PREVIA_EXPERIMENTAL_LOCAL=true`. Em `frontend/.env.local`, `VITE_ML_DEMO_ACADEMICA=true` abre a prévia automaticamente no Simulador; com a flag do frontend desligada, um administrador pode abri-la manualmente. Reinicie a aplicação após configurar.

Em um dispositivo novo, gere o artefato com o comando abaixo, executado **na pasta `backend`**:

```powershell
cd backend
..\.venv\Scripts\python.exe -m climasense.ml alagamento-previa-local
cd ..
```

Ele usa a configuração fixa da prévia e dados históricos reais, consulta o Postgres em modo de leitura quando disponível e busca dados públicos/cache local para completar o estudo. **Pode demorar na primeira execução**, devido aos downloads e ao treinamento. Grava apenas arquivos locais em `tmp/`, incluindo **`tmp/modelos/risco-alagamento-v0.2.0.joblib`**, sem gravar em Neon/Atlas nem reescrever os relatórios científicos. A opção `--sem-banco` permite executar esse treino sem consultar o Postgres, mantendo a necessidade de internet/cache.

**O modelo não é versionado no Git. Sua ausência impede a visualização experimental.** Não é preciso repetir o comando se já houver um artefato compatível em `tmp/modelos/`. A compatibilidade inclui versão do modelo, contrato dos atributos e versão do scikit-learn; mantenha as dependências fixadas. A API apenas lê o arquivo, nunca treina ao abrir a tela. O caminho alternativo `CLIMASENSE_MODELO_ALAGAMENTO` é lido do ambiente do processo, conforme o [`.env.example`](.env.example).

### Acessar mapa, comparação e sinalizações preventivas

1. Entre como **administrador** em http://localhost:5173/entrar e conclua a troca de senha inicial.
2. Abra **Simulador → Previsão por distrito** em http://localhost:5173/app/simulador. Com a demonstração automática desligada, clique em **Ver prévia de pesquisa do ML**. Selecione **ML de alagamento** para ver a camada experimental; a rota `/api/v1/risco-alagamento/previa-local` exige desenvolvimento, flag do backend e permissão `administrar`.
3. Escolha uma data das próximas **72 horas** no calendário. **Atenção preventiva** mostra os bairros dos distritos sinalizados pela chuva; **Estágio** mostra a classificação territorial por regras. O ML diário só avalia **hoje ou amanhã**, no fuso do Recife, com dia local completo e janela de sete dias de chuva horária completa por distrito. Dias parciais, posteriores ou sem insumos ficam indisponíveis, sem representar risco baixo.
4. Consulte o quadro de comparação **Open-Meteo × ClimaSense** e expanda **APAC observada × previsão arquivada na mesma hora**. Open-Meteo é o insumo do ClimaSense, não uma previsão independente. APAC só é pareada quando distrito, período observado e previsão arquivada são compatíveis.

Também há acesso por **Chuva → Ver dias de chuva intensa…** em http://localhost:5173/app/chuva. **Cenário hipotético** mantém a simulação manual. A sinalização preventiva é interna, não um alerta oficial, e funciona independentemente da aprovação do ML. As rotas normais mantêm o bloqueio científico de modelos não publicáveis; ativar a prévia não altera esse critério nem persiste resultados na Gold operacional.

Detalhes e limites: [comparação e prevenção](docs/comparacao-e-prevencao.md), [prévia local](docs/ml/previa-local-e-comparacao.md) e [integração territorial](docs/ml/integracao-territorial.md).

### Evidências científicas

Árvore de decisão com avaliação temporal retrospectiva por bairro-dia, a partir dos atendimentos da
Defesa Civil e da chuva e maré da Open-Meteo. Recall de 80,06% **não é acurácia**:
a precisão observada foi 3,38%, com 7.696 falsos positivos. A AUC-PR foi 0,045971,
abaixo da referência simples de chuva (0,049624). Os experimentos de distrito, SGB
e picos horários não trouxeram melhoria relevante; 2024 já não é holdout independente.
Métodos, números verificáveis, reprodução e limitações:
[`docs/ml/risco-alagamento.md`](docs/ml/risco-alagamento.md).

O treinamento completo continua disponível em `python -m climasense.ml alagamento`;
escolha `--saida` e `--modelo` para não sobrescrever as evidências desta entrega.
A [revisão da consolidação](docs/ml/consolidacao-academica.md) registra patches,
arquivos locais preservados e validações executadas.

## Funcionalidades opcionais

As telas de mapa/situação, Chuva, Simulador, Ações, Saúde, Fontes e administração ficam na área autenticada, conforme as permissões da conta. As flags abaixo preservam os padrões desligados da [ADR 0011](docs/adr/0011-chave-funcionalidade-landing-comunicados.md). Não são necessárias para mapa ML, comparação ou prevenção. Para habilitar uma funcionalidade opcional, use `true` no backend e `1` na variável correspondente do frontend e reinicie os serviços:

| Backend (`.env` da raiz) | Frontend (`frontend/.env.local`) |
|---|---|
| `FUNC_LANDING_PUBLICA` | `VITE_FUNC_LANDING_PUBLICA` |
| `FUNC_COMUNICADOS` | `VITE_FUNC_COMUNICADOS` |
| `FUNC_AVALIACOES` | `VITE_FUNC_AVALIACOES` |
| `FUNC_MAPA_PORTATIL` | `VITE_FUNC_MAPA_PORTATIL` |
| `FUNC_ESTATISTICAS_SERIES` | `VITE_FUNC_ESTATISTICAS_SERIES` |

As flags não substituem as permissões nem garantem uma tela dedicada para cada endpoint. `VITE_AMBIENTE=demonstracao` apenas exibe a faixa de demonstração; `VITE_VITRINE=1` habilita a vitrine fora do Vite dev. O inventário e os critérios de acesso estão em [funcionalidades da equipe](docs/funcionalidades-equipe.md) e [API de gestão](docs/api-gestao.md).

## Solução de problemas

| Sintoma | Como resolver |
|---|---|
| Erro de URL do SQLAlchemy com `DATABASE_URL_MIGRACOES` vazia | Comente ou remova a linha `DATABASE_URL_MIGRACOES=` do `.env` e de eventual `backend/.env`. Se exportada vazia no PowerShell, remova com `Remove-Item Env:DATABASE_URL_MIGRACOES -ErrorAction SilentlyContinue`. Ausente, usa `DATABASE_URL`; quando necessária, informe uma URL válida com permissões autorizadas. Reinicie o backend |
| Modelo ausente ou incompatível | Confira `tmp/modelos/risco-alagamento-v0.2.0.joblib` e eventual `CLIMASENSE_MODELO_ALAGAMENTO` exportada. Instale as dependências fixadas e execute `alagamento-previa-local` em `backend` se faltar artefato compatível. Preserve artefatos de pesquisa existentes antes de substituir; não altere o modelo ou o critério de publicação |
| Prévia experimental desativada / 404 | Confirme `AMBIENTE=desenvolvimento`, `ML_PREVIA_EXPERIMENTAL_LOCAL=true`, Vite em modo dev (`npm run dev`) e login administrativo. Reinicie os serviços. Abra manualmente a prévia ou use `VITE_ML_DEMO_ACADEMICA=true` em `frontend/.env.local`; build de produção não a consulta |
| Dados meteorológicos desatualizados | Verifique **Fontes**, última tentativa/sucesso, horários e cobertura. `dev.ps1` não coleta dados. Execute as atualizações Open-Meteo e APAC acima apenas em banco próprio ou autorizado. Previsão Open-Meteo capturada há mais de 6 h não gera sinalização atual; sucesso da fonte não garante cobertura completa |
| APAC sem observações recentes ou compatíveis | Atualize `apac-chuva --modo tempo-real` no destino autorizado e confira leituras/coletas do próprio distrito nas últimas 2 h. O pareamento exige fim de janela em hora exata e previsão da mesma hora arquivada antes do início observado. Novas coletas podem formar esse histórico; não recuperam previsões arquivadas nem observações horárias perdidas. Sem correspondência, a comparação fica indisponível |
| ML indisponível em dia parcial ou fora do alcance | Selecione um dia local completo de hoje/amanhã, com sete dias de chuva horária completos. A janela meteorológica de 72 h pode incluir datas adicionais e fatias de dias que o ML 0.2.0 não aceita. Atualizar fontes pode suprir lacunas, mas não amplia o alcance do modelo; use a sinalização meteorológica/regras quando houver dados suficientes |

Mais detalhes de diagnóstico e cobertura em [operação do ETL](docs/operacao-etl.md) e [comparação e prevenção](docs/comparacao-e-prevencao.md).

## Testes

Na raiz, para verificações locais sem acessar bancos compartilhados:

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
