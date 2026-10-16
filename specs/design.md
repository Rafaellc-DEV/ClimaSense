# ClimaSense — Planejamento de Design (`design.md`)

| Campo | Valor |
|---|---|
| Fase SDD | 2 de 4 — Design (como será feito) |
| Versão | 0.3 — revisada em 15/10/2026: somente dados reais (D8) |
| Data | 15/10/2026 |
| Entrada | `specs/requirements.md` v0.2 (aprovado, com as decisões P1–P3) |
| Saída | Base para o `specs/tasks.md` |

Este documento responde **como** cada requisito será implementado: arquitetura, stack, dados, contratos de API, fluxos, identidade visual, telas, segurança e testes. Cada decisão aponta para os requisitos que atende (`RF-…`, `RN-…`, `RNF-…`).

---

## 1. Decisões principais (resumo)

| # | Decisão | Por quê | Atende |
|---|---|---|---|
| D1 | **Monólito modular em camadas** (API) + **processo ETL separado** (worker/CLI) | O template marca camadas + MVC + microsserviços. Para um MVP acadêmico, dois executáveis independentes (API e ETL) isolam a parte mais instável (fontes externas) sem o custo operacional de vários serviços. Os módulos internos têm fronteiras claras e podem virar serviços depois. | R-08, RNF-MAN-01, RNF-CON-01 |
| D2 | **Backend Python 3.12 + FastAPI** | API REST tipada, OpenAPI gerado automaticamente (contrato vivo), validação com Pydantic e o mesmo ecossistema do ETL (pandas, pymongo). | R-02, contrato de API |
| D3 | **MongoDB Atlas** para a bronze e a base territorial. **Postgres (Neon)** para a silver, a gold e os dados da aplicação. | Decisão P2. Preserva o ETL atual (bronze no Atlas, silver no Neon) e usa um banco relacional para os fluxos com integridade (versões, revisões, auditoria). | R-03, RN-03, RF-14 |
| D4 | **Frontend React 18 + TypeScript + Vite** | Muitas telas, estados de filtro compartilhados e componentes acessíveis reutilizáveis. Streamlit e Dash foram descartados: limitam a identidade visual, o controle de acessibilidade e o fluxo de login com papéis. | R-06, RNF-ACE, RNF-VIS |
| D5 | **Apache ECharts** para os gráficos | Cobre todos os gráficos previstos (linha com faixa de incerteza, calendário-heatmap, barras, séries longas). Tem padrões de textura (`decal`) para daltonismo e descrição ARIA automática. | RF-08, RF-09, RNF-ACE-09, RNF-VIS-05 |
| D6 | **Leaflet 1.9.4** para o mapa, com `model.js` portado para TypeScript | É a mesma biblioteca do mapa atual. A lógica testada (escala, classes, busca sem acento, CSV) é migrada com os testes. | RF-07, RF-13.6 |
| D7 | **Sessão no servidor** (cookie `HttpOnly`) + token CSRF | Permite expirar por inatividade, revogar e registrar a sessão, sem guardar tokens no navegador. | RF-02, RNF-SEG-03 |
| D8 | **Somente dados reais.** O ETL (POO) integra fontes climáticas reais sem cadastro já no MVP (Open-Meteo: histórico, previsão e maré; Dados Abertos do Recife: alagamentos). ANA, APAC, INMET, Cemaden e a Marinha seguem como conectores planejados. | Decisão P3 revisada: nada simulado no produto. Fontes que exigem credencial entram quando o acesso for liberado, sem refazer as telas. | RF-12.4, RF-12.10, RN-19 |
| D9 | **Identidade “Régua de maré”** (seção 8) | O elemento visual central vem do próprio Recife: a régua que mede o nível da água nas pontes do Capibaribe. Ela mostra o nível do aviso, em vez de enfeitar. | RNF-VIS-01, RF-01 |

---

## 2. Arquitetura

### 2.1 Visão de contexto

```mermaid
flowchart LR
  subgraph Externo
    PREF[API CKAN<br/>Dados Abertos Recife]
    OFI[Arquivos oficiais<br/>distritos, bairros, faixas hídricas]
    FUT[ANA · APAC · INMET · Cemaden<br/>maré · previsão numérica<br/><i>evolução</i>]
  end
  subgraph ClimaSense
    ETL[Worker ETL<br/>Python CLI]
    API[API FastAPI<br/>monólito modular]
    WEB[Frontend React<br/>landing + área da equipe]
  end
  ATLAS[(MongoDB Atlas<br/>bronze + território)]
  NEON[(Postgres Neon<br/>silver + gold + app)]
  CID((Cidadão))
  EQ((Equipe))

  PREF --> ETL
  OFI --> ETL
  FUT -.-> ETL
  ETL --> ATLAS
  ETL --> NEON
  ATLAS --> API
  NEON --> API
  API --> WEB
  CID --> WEB
  EQ --> WEB
```

### 2.2 Camadas e componentes (aderência ao template)

| Camada | Pacote | Componente do template | Regras |
|---|---|---|---|
| Apresentação | `frontend/` | Interface Web | Só fala com a API. Não guarda segredos. |
| Controladores REST | `climasense/api/routers/` | Controladores REST | Validam a entrada (Pydantic), aplicam a autorização e chamam um serviço. **Não têm regra de negócio.** |
| Aplicação | `climasense/servicos/` | Serviços (template §5) | Orquestram os casos de uso, as transações e a auditoria. |
| Domínio | `climasense/dominio/` | Núcleo de Domínio | Regras puras (RN-01 a RN-19), máquinas de estado e estatística. Sem I/O. 100% testável sem banco. |
| Infraestrutura | `climasense/infra/` | Persistência + Fontes Externas | Repositórios Mongo e Postgres e clientes HTTP. |
| Autenticação | `climasense/auth/` | Autenticação e Autorização | Sessões, hash de senha, papéis e CSRF. |
| ETL | `climasense/etl/` | Fontes Externas + Validação e Qualidade | Extract, Transform e Load preservados, com conectores e registro de execuções. |
| Território | `climasense/territorio/` | Fontes Externas + Persistência | Carga oficial no Atlas (porte do `load_mongo.py`) e mapa portátil (porte do `gerar_mapa.py`). |
| Modelos | `climasense/modelos/` | (novo) | Interface do estimador de alagamento. No MVP, uma regra de referência simples sobre dados reais, marcada como experimental. |

Regra de dependência: `api → servicos → dominio ← infra`. O domínio não importa nada de fora. Os serviços recebem os repositórios por injeção (`Depends`), o que permite testar com dublês.

### 2.3 Módulos de negócio

| Módulo | Domínio | Serviço | Router |
|---|---|---|---|
| Território | `dominio/territorio.py` (escala, classes, busca, precisão) | `servicos/territorio.py` | `/territorios` |
| Fontes e qualidade | `dominio/qualidade.py` (status, desatualização, lacunas) | `servicos/fontes.py` | `/fontes`, `/etl` |
| Séries | `dominio/estatistica.py` (porte das Atividades 3 e 4), `dominio/series.py` | `servicos/series.py` | `/series` |
| Cenários | `dominio/cenario.py`, `modelos/estimador.py` | `servicos/cenarios.py` | `/cenarios` |
| Saúde agregada | `dominio/saude.py` (supressão < 5, amostra) | `servicos/saude.py` | `/saude` |
| Avaliações | `dominio/fluxo_revisao.py` (máquina de estados) | `servicos/avaliacoes.py` | `/avaliacoes` |
| Comunicados | `dominio/fluxo_revisao.py`, `dominio/comunicado.py` | `servicos/comunicados.py` | `/comunicados`, `/publico` |
| Painel | — | `servicos/painel.py` | `/painel` |
| Administração | `dominio/papeis.py` | `servicos/usuarios.py`, `servicos/auditoria.py` | `/admin` |

---

## 3. Stack tecnológica

### 3.1 Backend e ETL

| Uso | Biblioteca | Observação |
|---|---|---|
| Linguagem | Python 3.12 | Funciona em Windows e Linux. |
| API | FastAPI + Uvicorn | OpenAPI em `/api/docs`. |
| Validação e configuração | Pydantic v2 + pydantic-settings | Lê o `.env`. Aceita `NEON_URL` como sinônimo de `DATABASE_URL` (compatibilidade). |
| Postgres | SQLAlchemy 2 + Alembic + psycopg2-binary | O mesmo driver do ETL atual. Migrações versionadas. |
| MongoDB | pymongo 4 + certifi | O mesmo padrão de conexão do `load_mongo.py` (ServerApi 1, timeouts). |
| ETL | pandas, requests | Preservados do `Projeto-ETL_AVD`. |
| Geo | pyproj (área geodésica), shapely (simplificação para a web), folium (mapa portátil) | Preservados do `Desktop/AVD`. Shapely é novo. |
| Senhas | pwdlib[argon2] | Argon2id. |
| Testes | pytest, mongomock, httpx (TestClient) | Os testes `unittest` existentes rodam sob o pytest. |
| Qualidade | ruff (lint e formatação) | |

### 3.2 Frontend

| Uso | Biblioteca |
|---|---|
| Base | React 18, TypeScript 5, Vite 5 |
| Rotas | React Router 6 |
| Dados do servidor | TanStack Query 5 (cache, estados de carregamento e erro) |
| Gráficos | Apache ECharts 5 (`echarts-for-react`) |
| Mapa | Leaflet 1.9.4 (componente próprio, sem `react-leaflet`, para portar o `app.js` com fidelidade) |
| Componentes acessíveis | Radix UI Primitives (Dialog, Select, Tabs, Toast, Tooltip), sem estilo, vestidos com os tokens do ClimaSense |
| Formulários | react-hook-form + zod |
| Datas | date-fns com locale `ptBR` e fuso `America/Recife` |
| Ícones | Lucide (sempre com rótulo de texto) |
| Fonte | Atkinson Hyperlegible Next, auto-hospedada via Fontsource |
| Estilo | CSS Modules + variáveis CSS (tokens). Sem framework utilitário, para a identidade não herdar a cara de template. |
| Testes | Vitest + Testing Library; Playwright + @axe-core/playwright |

### 3.3 Execução

- **Desenvolvimento:** `uvicorn` (porta 8000) + `vite` (porta 5173, com proxy de `/api`). Script `dev.ps1`.
- **Demonstração e produção:** a API serve o build do frontend (`frontend/dist`) num único processo. O ETL roda como comando agendado (Agendador de Tarefas do Windows, cron ou GitHub Actions).
- **Bancos:** Atlas e Neon na nuvem. Um branch “dev” do Neon é usado no desenvolvimento. O `docker-compose.yml` sobe um Postgres local opcional para os testes de integração.

---

## 4. Estrutura de pastas

```text
ClimaSense/
├── README.md                    # visão geral, como rodar (PowerShell e bash)
├── .env.example                 # todas as variáveis, sem valores reais
├── .gitignore                   # .env, .venv, node_modules, dist, __pycache__, tmp
├── docker-compose.yml           # Postgres local opcional (testes de integração)
├── specs/
│   ├── requirements.md
│   ├── design.md
│   └── tasks.md
├── docs/
│   ├── arquitetura.md           # versão narrativa das seções 2–3 + template preenchido
│   ├── dicionario-dados/        # um arquivo por fonte (estilo CRISP-DM)
│   ├── adr/                     # registros de decisão (D1–D9 e futuras)
│   └── brand/                   # logo original, prévia da identidade
├── data/
│   └── territorio/              # arquivos oficiais + correcoes-bairros.json + metadados
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   ├── climasense/
│   │   ├── config.py
│   │   ├── api/            main.py, deps.py, erros.py, routers/
│   │   ├── auth/           sessoes.py, senhas.py, csrf.py, papeis.py
│   │   ├── dominio/        territorio.py, qualidade.py, estatistica.py, series.py,
│   │   │                   cenario.py, saude.py, fluxo_revisao.py, comunicado.py, papeis.py
│   │   ├── servicos/       (um por módulo da seção 2.3)
│   │   ├── infra/          mongo.py, postgres.py, modelos_sql.py, repositorios/
│   │   ├── etl/            extract.py, transform.py, load.py   ← preservados
│   │   │                   conectores/ (base.py, vacinacao.py, open_meteo.py, recife_alagamento.py,
│   │   │                                ana.py*, apac.py*, inmet.py*, cemaden.py*,
│   │   │                                recife_alagamento.py*, mare.py*)   *esqueleto
│   │   │                   execucao.py, cli.py
│   │   ├── territorio/     carga.py (porte do load_mongo.py), geometria.py,
│   │   │                   mapa_portatil.py (porte do gerar_mapa.py), assets/
│   │   └── modelos/        estimador.py (interface), referencia.py
│   └── tests/
│       ├── unit/           dominio, etl, territorio (inclui test_distritos portado)
│       ├── integration/    api + bancos
│       └── fixtures/
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── public/brand/       logo
    ├── src/
    │   ├── app/            rotas, providers, AppShell, PublicShell
    │   ├── design-system/  tokens.css, tipografia, componentes base
    │   ├── features/       landing, auth, painel, territorio, series, cenarios,
    │   │                   avaliacoes, comunicados, fontes, admin, conta
    │   ├── map/            model.ts (porte do model.js), MapView.tsx
    │   ├── charts/         tema ECharts, ChartFrame, utilitários
    │   ├── lib/            api.ts, formatos pt-BR, filtros na URL
    │   └── textos/         textos da interface centralizados (RNF-MAN-07)
    └── tests/              unit (vitest), e2e (playwright + axe)
```

### 4.1 Origem de cada peça existente

| Arquivo original (não alterado) | Novo local | Adaptação |
|---|---|---|
| `Projeto-ETL_AVD/src/extract.py` | `backend/climasense/etl/extract.py` | Mesma classe `Extract`. Parâmetros vêm do conector. `ler_bronze` filtra pela última execução. |
| `Projeto-ETL_AVD/src/transformer.py` | `backend/climasense/etl/transform.py` | Mesma classe `Transform` e os mesmos métodos. Adiciona a contagem de descartes por motivo. |
| `Projeto-ETL_AVD/src/load.py` | `backend/climasense/etl/load.py` | `salvar_bronze` passa a acrescentar (RN-09). `salvar_silver` grava em `silver.vacinados` e mantém a view `public.silver_vacinados`. |
| `Projeto-ETL_AVD/src/config.py` | `backend/climasense/config.py` + `etl/conectores/vacinacao.py` | URLs e IDs no conector. Segredos no `.env`. |
| `Projeto-ETL_AVD/run_etl.py` | `backend/climasense/etl/cli.py` | `python -m climasense.etl run vacinacao [--limite N] [--etapa bronze|silver|gold]` |
| `Desktop/AVD/load_mongo.py` | `backend/climasense/territorio/carga.py` + `geometria.py` | Mesmas funções (`baixar_dados`, `carregar_arquivos`, `area_km2`, `corrigir_vinculos`, `enriquecer_distritos`, `salvar_atlas`, `ler_atlas`). Grava também as faixas hídricas no Atlas. |
| `Desktop/AVD/gerar_mapa.py` + `mapa_assets/` | `backend/climasense/territorio/mapa_portatil.py` + `assets/` | Mesmo HTML portátil (modos Atlas e `--local`). Exposto em `GET /territorios/mapa-portatil` (RF-07.12). |
| `Desktop/AVD/mapa_assets/model.js` | `frontend/src/map/model.ts` | Porte 1:1 para TS. `tests/model.test.cjs` vira `model.test.ts`. |
| `Desktop/AVD/mapa_assets/app.js` | `frontend/src/features/territorio/` | As funções viram componentes React com o mesmo comportamento (checklist RF-07). |
| `Desktop/AVD/tests/test_distritos.py` | `backend/tests/unit/territorio/test_distritos.py` | Os mesmos 6 testes, mudando só os imports. |
| `Desktop/AVD/tests/browser.cjs` | `frontend/tests/e2e/mapa.spec.ts` | As mesmas asserções (8 distritos, 94 bairros, 81 faixas, busca, CSV). |
| `Desktop/AVD/dados/*` | `data/territorio/` | Cópia byte a byte. O bruto é preservado (RN-12). |
| `Atividade3/main.py`, `Atividade4/main.py` | `backend/climasense/dominio/estatistica.py` | Funções puras: média, mediana, moda, variância, desvio, amplitude, assimetria, curtose e `classificar_curtose`. **Sem** o `'...' → 0` (RN-02). |

---

## 5. Dados

### 5.1 Fluxo e camadas

```mermaid
flowchart LR
  F[Fonte] -->|Extract| B[(Bronze · Atlas<br/>original + _fonte,<br/>_execucao_id, _data_carga)]
  B -->|Transform| S[(Silver · Postgres<br/>tipado, limpo,<br/>metadados RNF-CON-04)]
  S -->|SQL versionado| G[(Gold · Postgres<br/>agregados prontos<br/>para os painéis)]
  G --> API
  T[Arquivos oficiais] -->|carga território| TA[(Atlas<br/>Recife.DistritosSanitarios<br/>Recife.FaixasHidricas)]
  TA --> API
  TA -->|sincroniza| TR[(Postgres<br/>app.territorios)]
```

### 5.2 MongoDB Atlas

| Banco.Coleção | Conteúdo | Origem |
|---|---|---|
| `Recife.DistritosSanitarios` | 8 features GeoJSON enriquecidas (bairros, área, auditoria). Upsert por `properties.cdistscodi`. | Preservado (`load_mongo.py`) |
| `Recife.FaixasHidricas` | 81 features das faixas marginais, com a geometria original e uma versão `geometry_web` simplificada (tolerância de cerca de 5 m). | Novo. O arquivo original tem 3,4 MB, e a versão simplificada reduz o tráfego da tela (RNF-DES-03). |
| `vacinacao.bronze_vacinados` | Registros originais da API + `_fonte`, `_execucao_id`, `_data_carga`. **Acumulativa.** | Preservado (nome mantido), com a mudança da RN-09 |
| `bronze.<fonte>` | Uma coleção por conector futuro (ex.: `bronze.open_meteo_historico`, `bronze.recife_alagamento`) | Novo |

Índices: `{_execucao_id: 1}` nas coleções bronze e `{"properties.cdistscodi": 1}` (único) nos distritos.

### 5.3 Postgres (Neon): esquemas `silver`, `gold` e `app`

**silver**

| Tabela | Colunas principais |
|---|---|
| `silver.vacinados` | as colunas atuais do `Transform` + `execucao_id`. A view `public.silver_vacinados` mantém a compatibilidade. |
| `silver.estacoes` | `id`, `fonte_id`, `codigo_fonte`, `nome`, `lat`, `lon`, `territorio_id`, `ativa` |
| `silver.observacoes` | `id`, `fonte_id`, `estacao_id` (nulo se for por área), `territorio_id`, `variavel` (`chuva_mm`, `nivel_m`, `mare_m`, `temp_c`), `valor` (**nulo ≠ 0**, RN-02), `unidade`, `tipo` (`observada`, `prevista`, `derivada`), `observado_em` (UTC), `emitido_em`, `horizonte_h`, `coletado_em`, `qualidade` (`ok`, `suspeito`, `ausente`), `execucao_id` |
| `silver.ocorrencias` | `id`, `fonte_id`, `territorio_id`, `ocorrido_em`, `registrado_em`, `tipo`, `confirmada` (bool/nulo), `precisao_espacial` |
| `silver.previsoes_emitidas` | `id`, `territorio_id`, `horizonte_h`, `emitida_em`, `metodo`, `versao_metodo`, `saida` jsonb, `insumos` jsonb (o que se sabia naquele momento, RF-09.8) |

**gold** (gerada por SQL versionado em `backend/climasense/etl/gold/*.sql`, reproduzível, CA-04)

| Tabela | Grão |
|---|---|
| `gold.vacinacao_distrito_mes` | distrito × mês: `doses`, `amostra_n`, `total_fonte`, `suprimido` (RN-13), `execucao_id` |
| `gold.chuva_diaria` | território × dia: `acumulado_mm`, `n_observacoes`, `cobertura_pct`, `tipo` |
| `gold.chuva_mensal` | território × mês: idem |
| `gold.referencia_mensal` | território × mês do ano: `media`, `mediana`, `anos_usados`, `cobertura_pct` |

**app**

| Tabela | Colunas principais | Notas |
|---|---|---|
| `app.usuarios` | `id` uuid, `nome`, `email` (único, minúsculo), `senha_hash`, `papeis` text[], `ativo`, `troca_senha_obrigatoria`, `criado_em` | RF-16.1: sem exclusão |
| `app.sessoes` | `id_hash`, `usuario_id`, `criada_em`, `ultimo_uso`, `expira_em`, `revogada`, `ip`, `user_agent` | RF-02.5 |
| `app.tentativas_login` | `email`, `ip`, `em`, `sucesso` | RF-02.3 |
| `app.territorios` | `id` (`recife`, `ds-4`, `bairro-afogados`), `tipo`, `nome_oficial`, `nome_exibicao`, `pai_id`, `codigo_oficial` | Sincronizada a partir do Atlas |
| `app.fontes` | `id` (slug), `nome`, `orgao`, `url`, `tipo`, `licenca`, `conector`, `limite_desatualizacao_h`, `min_observacoes`, `implementada` bool, `ativa` | RF-06, RF-16.3 |
| `app.etl_execucoes` | `id` uuid, `fonte_id`, `inicio`, `fim`, `status` (`em_andamento`, `sucesso`, `falha`), `lidos`, `gravados`, `descartados`, `motivos_descarte` jsonb, `erro`, `disparado_por` | RF-12.5 |
| `app.avaliacoes` | `id`, `territorio_id`, `periodo_inicio`, `periodo_fim`, `estado`, `versao_atual`, `criado_por`, `criado_em` | |
| `app.avaliacao_versoes` | `id`, `avaliacao_id`, `numero`, `prioridade`, `justificativa`, `limitacoes`, `evidencias` jsonb, `autor_id`, `criado_em` | Imutável (RN-03) |
| `app.comunicados` | `id`, `estado`, `territorios` text[], `publico`, `nivel`, `validade_inicio`, `validade_fim`, `versao_atual`, `versao_aprovada`, `publicado_em`, `publicado_por`, `avaliacao_id` | |
| `app.comunicado_versoes` | `id`, `comunicado_id`, `numero`, `titulo`, `texto`, `orientacoes`, `evidencias` jsonb, `autor_id`, `criado_em`, `hash_conteudo` | O hash prova que o publicado é exatamente o aprovado (RN-04) |
| `app.revisoes` | `id`, `alvo` (`avaliacao`/`comunicado`), `versao_id`, `revisor_id`, `decisao` (`aprovar`, `devolver`), `justificativa`, `em` | RN-05 verificado no serviço **e** por uma constraint |
| `app.auditoria` | `id` bigserial, `em`, `usuario_id`, `acao`, `alvo_tipo`, `alvo_id`, `detalhes` jsonb, `ip` | Somente INSERT: o usuário da aplicação não tem permissão de UPDATE nem DELETE (RF-14.2) |

Convenções: horários em `timestamptz` (UTC), exibidos em `America/Recife` (RN-16). Identificadores de território legíveis e estáveis.

### 5.4 Conectores (interface comum)

```python
# POO, como no ETL da disciplina: as classes Extract, Transform e Load são preservadas,
# e cada fonte é uma subclasse de Conector que as combina.
class Conector(ABC):
    id: str                       # "vacinacao", "open-meteo-historico", "recife-alagamento"
    fonte: FonteInfo              # nome, órgão, url, licença, tipo (observada | prevista | derivada)

    def __init__(self, extract: Extract, transform: Transform, load: Load): ...

    @abstractmethod
    def extrair(self, ctx: ExecucaoCtx) -> list[dict]: ...            # API → registros (bronze)
    @abstractmethod
    def transformar(self, bruto: pd.DataFrame) -> pd.DataFrame: ...    # bronze → silver

    def executar(self, ctx: ExecucaoCtx) -> ResultadoExecucao:        # método-modelo comum a todos
        registros = self.extrair(ctx)
        self.load.salvar_bronze(registros, ctx)
        df = self.transformar(self.extract.ler_bronze(ctx))
        self.load.salvar_silver(df, ctx)
        ...

class ConectorVacinacao(Conector): ...          # porte direto do Projeto-ETL_AVD
class ConectorOpenMeteoHistorico(Conector): ...
```

| Conector | Estado no MVP | Notas |
|---|---|---|
| `vacinacao` | **Implementado** (porte do ETL existente) | API CKAN, paginação de 500, limite configurável. A gold traz `amostra_n`. |
| `territorio-oficial` | **Implementado** (porte do `load_mongo.py`) | Distritos, bairros e faixas hídricas. |
| `open-meteo-historico` · `open-meteo-previsao` · `open-meteo-mare` | **Implementado no MVP** | Open-Meteo (sem cadastro): chuva horária e diária por ponto representativo de cada distrito (reanálise ERA5, `tipo = derivada`), previsão de chuva até 72 h e nível do mar previsto, que inclui a maré (`tipo = prevista`). Termos de uso para projeto acadêmico a confirmar na tarefa. A execução acontece no computador da equipe. |
| `recife-alagamento` | **Implementado no MVP** | Dados Abertos do Recife (conjuntos com a tag alagamento / Defesa Civil). Ocorrências entram como **não confirmadas** por padrão (contexto §14.2). |
| `ana-telemetria` | Esqueleto + documentação | ANA, HidroWebService (chuva e nível de rios em estações telemétricas). Requer cadastro e credenciais (`ANA_USUARIO`, `ANA_SENHA` no `.env`). Endpoints e limites serão confirmados no manual oficial na tarefa do conector. |
| `apac-chuva` | Esqueleto | APAC: monitoramento e serviço de chuva acumulada de 24 h (ArcGIS REST). |
| `inmet` | Esqueleto | Estações automáticas (Recife A301). Acesso e termos a verificar. |
| `cemaden` | Esqueleto | Pluviômetros automáticos. Acesso a verificar. |
| `mare-marinha` | Esqueleto | Tábua de maré oficial da Marinha (Porto do Recife), para comparar com o nível previsto do Open-Meteo. Formato a definir. |

Os esqueletos têm a classe, a documentação no dicionário de dados e um teste marcado `skip`. A tela de Fontes mostra essas fontes como “Planejada”.

### 5.5 Modelo de ML (preparado, não implementado)

```python
class EstimadorAlagamento(Protocol):
    metodo: str; versao: str; experimental: bool
    def estimar(self, territorio_id: str, horizonte_h: int, insumos: Insumos) -> Estimativa: ...
```

`Estimativa` tem `janela_atencao`, `prioridade` (categoria, **nunca porcentagem**, RN-06), `fatores[]`, `faixa_incerteza`, `qualidade` (`completa`, `parcial`, `insuficiente`) e `limitacoes[]`. No MVP existe só o `EstimadorReferencia`, uma regra simples e transparente sobre dados **reais** (chuva prevista, maré prevista e histórico de ocorrências), sempre com `experimental = true`. Toda saída é gravada em `silver.previsoes_emitidas`. O modelo real (referência simples → candidatos → validação temporal, contexto §14.4) entra numa etapa própria.

---

## 6. Contrato da API (`/api/v1`)

O FastAPI gera o OpenAPI completo em `/api/docs` (Swagger) e `/api/openapi.json`. Este é o contrato de referência.

### 6.1 Convenções

- **Envelope de dados analíticos** (atende CA-02, RN-10, RN-19):

```json
{
  "dados": [ ... ],
  "meta": {
    "fontes": [{"id": "open-meteo-historico", "nome": "Open-Meteo (reanálise ERA5)", "tipo": "derivada",
                "atualizado_em": "2026-10-15T20:00:00Z", "status": "atualizada"}],
    "recorte": {"territorio_id": "ds-4", "inicio": "2026-07-01", "fim": "2026-10-15", "granularidade": "distrito"},
    "cobertura_pct": 92.5,
    "amostra": {"n": 5000, "total_fonte": 1400000},
    "avisos": ["Indicador disponível apenas por distrito."],
    "dados_insuficientes": false
  }
}
```

- **Erros:** `application/problem+json` (RFC 9457), com `title` e `detail` em português simples, prontos para a tela. Ex.: `{"title": "Sem permissão", "detail": "Você não tem permissão para esta ação. Fale com a coordenação.", "status": 403}`.
- **Paginação:** `?pagina=1&por_pagina=20`, com a resposta trazendo `total`.
- **Datas:** ISO 8601 em UTC na API. A conversão para `America/Recife` acontece no frontend.
- **Autenticação:** cookie `cs_sessao`. Métodos que alteram dados exigem o cabeçalho `X-CSRF-Token` igual ao cookie `cs_csrf`.

### 6.2 Endpoints

Papéis: **P** público · **A** analista · **R** revisor · **C** coordenação · **ADM** administrador.

| Método e rota | Papel | Descrição | Req. |
|---|---|---|---|
| `GET /health` | P | Status da API e dos bancos (sem detalhes sensíveis) | RNF-CON |
| `GET /publico/avisos?bairro=` | P | Comunicados **publicados e vigentes**, ordenados por nível e data | RF-01, RN-04, RN-14 |
| `GET /publico/avisos/{id}` | P | Detalhe de um aviso publicado | RF-01.3 |
| `GET /publico/estado` | P | `{avisos_ativos, atualizado_em}` para o topo da landing | RF-01.1 |
| `GET /publico/territorios/busca?q=` | P | Busca de bairro sem acento (para o filtro da landing) | RF-01.5 |
| `POST /auth/entrar` | P | `{email, senha}` → cria a sessão e define os cookies | RF-02 |
| `POST /auth/sair` | autenticado | Revoga a sessão | RF-02.6 |
| `GET /auth/eu` | autenticado | Usuário, papéis, `expira_em` e `troca_senha_obrigatoria` | RF-03.3 |
| `POST /auth/renovar` | autenticado | Renova a inatividade (“Continuar conectado”) | RF-02.5 |
| `POST /auth/trocar-senha` | autenticado | `{senha_atual, nova_senha}` | RF-02.7 |
| `GET /painel/resumo` | A | Avisos ativos, aguardando revisão (para o usuário), territórios em atenção e saúde das fontes | RF-04.5 |
| `GET /territorios` | A | Árvore Recife → distritos → bairros | RF-05.1 |
| `GET /territorios/distritos.geojson` | A | FeatureCollection dos 8 distritos (com `ETag`) | RF-07.1 |
| `GET /territorios/hidrografia.geojson` | A | Faixas hídricas (`geometry_web`) | RF-07.7 |
| `GET /territorios/indicadores?indicador=&inicio=&fim=` | A | Valor por distrito para colorir o mapa, no envelope de dados | RF-07.2 |
| `GET /territorios/mapa-portatil` | A | Baixa o HTML portátil (porte do `gerar_mapa.py`) | RF-07.12 |
| `GET /fontes` · `GET /fontes/{id}` | A | Lista e detalhe com status calculado | RF-06 |
| `GET /fontes/{id}/execucoes` | A | Histórico de execuções | RF-12.5 |
| `POST /etl/execucoes` | ADM | `{fonte_id, limite?}` → dispara em segundo plano e retorna o `id` | RF-16.2 |
| `GET /etl/execucoes/{id}` | ADM | Status e registro da execução | RF-12.5 |
| `GET /series?variavel=&territorio_id=&inicio=&fim=&frequencia=` | A | Pontos `{t, valor\|null}`, com lacunas explícitas | RF-08.1–3 |
| `GET /series/referencia?...` | A | Referência histórica e método | RF-08.4 |
| `GET /series/sazonalidade?...` | A | Matriz ano × mês | RF-08.5 |
| `GET /series/estatisticas?...` | A | Estatística descritiva com classificação em texto | RF-08.6, RF-08.7 |
| `GET /cenarios?territorio_id=&horizonte_h=` | A | Observação, previsão, estimativa e prioridade, com `experimental: true` | RF-09 |
| `GET /saude/vacinacao?territorio_id=&inicio=&fim=` | A | Agregado por distrito e mês, com `amostra` e `suprimido` | RF-15 |
| `GET /avaliacoes` · `POST /avaliacoes` | A | Lista com filtros · cria rascunho | RF-10 |
| `GET /avaliacoes/{id}` · `PUT /avaliacoes/{id}` | A | Detalhe com versões · nova versão (só em Rascunho ou Devolvida) | RF-10, RN-03 |
| `POST /avaliacoes/{id}/enviar` | A | Rascunho → Em revisão | RF-10.2 |
| `POST /avaliacoes/{id}/aprovar` · `/devolver` | R | Decisão (justificativa obrigatória ao devolver; o autor não decide) | RN-05 |
| `POST /avaliacoes/{id}/encerrar` | C | → Encerrada | RF-10.2 |
| `GET /comunicados` · `POST /comunicados` | A | Lista · cria rascunho (pode vir de `avaliacao_id`) | RF-11 |
| `GET /comunicados/{id}` · `PUT /comunicados/{id}` | A | Detalhe · nova versão | RF-11.4 |
| `GET /comunicados/{id}/previa` | A | A versão atual renderizada como a landing mostrará | RF-11.3 |
| `GET /comunicados/{id}/versoes` · `/versoes/{a}/diferenca/{b}` | A | Histórico e diferenças entre versões | RF-11.7 |
| `POST /comunicados/{id}/enviar` | A | → Em revisão | RF-11.2 |
| `POST /comunicados/{id}/aprovar` · `/devolver` | R | Decisão sobre a **versão** | RN-04, RN-05 |
| `POST /comunicados/{id}/publicar` | C | Só se `versao_atual == versao_aprovada` e a validade estiver ok (+ RN-19) | RF-11.5 |
| `POST /comunicados/{id}/encerrar` | C | Tira da landing | RF-11.6 |
| `GET /admin/usuarios` · `POST` · `PATCH /admin/usuarios/{id}` | ADM | Gestão de usuários (ativar, desativar, papéis, redefinir senha) | RF-16.1 |
| `GET /admin/auditoria?usuario=&acao=&inicio=&fim=` | ADM | Consulta da auditoria | RF-14.3 |
| `PATCH /admin/fontes/{id}` | ADM | Limites de desatualização e mínimo de observações | RF-16.3 |

### 6.3 Esquemas centrais (trecho OpenAPI)

```yaml
components:
  schemas:
    NivelAviso:
      type: string
      enum: [informativo, atencao, alerta, critico]
    EstadoFluxo:
      type: string
      enum: [rascunho, em_revisao, aprovado, devolvido, publicado, encerrado]
    AvisoPublico:
      type: object
      required: [id, titulo, nivel, territorios, orientacoes, validade_inicio, validade_fim, emitido_por, publicado_em]
      properties:
        id: {type: string, format: uuid}
        titulo: {type: string, maxLength: 120}
        nivel: {$ref: '#/components/schemas/NivelAviso'}
        territorios: {type: array, items: {$ref: '#/components/schemas/TerritorioRef'}}
        texto: {type: string, maxLength: 1200}
        orientacoes: {type: array, items: {type: string}, maxItems: 5}
        validade_inicio: {type: string, format: date-time}
        validade_fim: {type: string, format: date-time}
        emitido_por: {type: string, example: "Vigilância em Saúde do Recife"}
        publicado_em: {type: string, format: date-time}
    TerritorioRef:
      type: object
      properties:
        id: {type: string, example: ds-4}
        tipo: {type: string, enum: [municipio, distrito, bairro]}
        nome_exibicao: {type: string, example: "Distrito Sanitário IV"}
    Ponto:
      type: object
      properties:
        t: {type: string, format: date-time}
        valor: {type: number, nullable: true, description: "null = sem dado (diferente de 0)"}
        tipo: {type: string, enum: [observada, prevista, derivada]}
    Estimativa:
      type: object
      properties:
        experimental: {type: boolean, const: true}
        metodo: {type: string}
        versao_metodo: {type: string}
        emitida_em: {type: string, format: date-time}
        horizonte_h: {type: integer, enum: [24, 48, 72]}
        janela_atencao: {type: object, nullable: true, properties: {inicio: {type: string}, fim: {type: string}}}
        prioridade: {type: string, enum: [sem_indicacao, atencao, alerta, critico, dados_insuficientes]}
        fatores: {type: array, items: {type: object, properties: {nome: {type: string}, descricao: {type: string}}}}
        qualidade: {type: string, enum: [completa, parcial, insuficiente]}
        limitacoes: {type: array, items: {type: string}}
```

---

## 7. Fluxos e regras no código

### 7.1 Máquina de estados de comunicados (avaliações usam o mesmo núcleo, sem “publicado”)

```mermaid
stateDiagram-v2
  [*] --> rascunho: criar (Analista)
  rascunho --> rascunho: editar = nova versão
  rascunho --> em_revisao: enviar (autor)
  em_revisao --> aprovado: aprovar (Revisor ≠ autor)
  em_revisao --> devolvido: devolver + justificativa
  devolvido --> rascunho: editar = nova versão
  aprovado --> em_revisao: editar = nova versão (RN-03)
  aprovado --> publicado: publicar (Coordenação; versão = aprovada)
  publicado --> encerrado: validade expirou / encerrar
  publicado --> em_revisao: editar = nova versão (sai da landing até nova aprovação)
  encerrado --> [*]
```

Implementação: `dominio/fluxo_revisao.py` define a tabela de transições `(estado, acao, papel) → estado` e as guardas (RN-04, RN-05, RN-14, RN-19). O serviço aplica a transição, grava a revisão e a auditoria **na mesma transação**. Uma tarefa periódica (a cada minuto, na API) encerra os comunicados vencidos. A landing também filtra por `validade_fim > agora`, então nunca mostra um aviso vencido, mesmo que a tarefa atrase.

### 7.2 Status das fontes (RF-06)

```text
se não implementada                      → "Planejada"
senão se última execução == falha              → "Com falha"   (mostra o último dado válido)
senão se agora - último sucesso > limite       → "Desatualizada"
senão                                          → "Atualizada"
```

### 7.3 Dados insuficientes (RN-01)

O domínio devolve `dados_insuficientes = true` quando a cobertura do recorte fica abaixo do mínimo da fonte ou quando faltam insumos obrigatórios de um cenário. O frontend tem **um único componente** (`EstadoDados`) para esse estado. Ele nunca é substituído por zero ou por “baixo”.

### 7.4 Sessão (RF-02)

1. `POST /auth/entrar`: verifica o bloqueio (5 falhas em 15 min por e-mail) e o Argon2id, cria a sessão (token aleatório de 32 bytes, guardado só o hash) e define `cs_sessao` (HttpOnly, Secure, SameSite=Lax, Path=/api) e `cs_csrf` (legível pelo JS).
2. Cada requisição atualiza `ultimo_uso`. Se `agora - ultimo_uso > 60 min`, a sessão expira e a API responde 401 com `detail` “Sua sessão terminou por inatividade. Entre novamente.”
3. O frontend tem um temporizador de inatividade. Aos 58 min abre um diálogo grande: “Você continua aí? Por segurança, vamos sair em 2 minutos.” [**Continuar conectado**] [Sair agora].

---

## 8. Identidade visual e design system

### 8.1 O conceito: a régua de maré

O Recife é uma cidade de rios e pontes onde a maré decide boa parte dos alagamentos. Nas pontes do Capibaribe existem **réguas linimétricas**: escalas graduadas que mostram o nível da água. Qualquer pessoa entende uma régua com água subindo, sem precisar ler um gráfico.

O ClimaSense usa essa régua como **seu único elemento memorável**. Ela não é decoração: mostra o nível do aviso mais alto em vigor. Todo o resto da interface fica quieto e disciplinado.

- Na **landing**, a régua aparece grande, ao lado da frase de estado, com quatro segmentos rotulados (1 Fique atento, 2 Atenção, 3 Alerta, 4 Situação crítica). A água preenche até o topo do segmento do nível vigente, na cor do nível, com a linha d’água em amarelo-sol, num único movimento de entrada (desativado com `prefers-reduced-motion`). No celular, a régua grande é substituída pelo selo-régua compacto, para os telefones de emergência continuarem na primeira tela (RF-01.6).
- Na **área da equipe**, a régua vira o **selo de nível** (badge): quatro marcas, com as preenchidas até o nível, sempre acompanhadas do nome do nível em texto (RN-17).
- O fundo da landing usa as **faixas hídricas reais do Recife** (os dados do próprio projeto), desenhadas como traço finíssimo. Fica moderno e específico, sem fotos de banco de imagem nem ondas genéricas.

### 8.2 Revisão do plano contra padrões genéricos

Antes de fixar o plano, comparei-o com o que sairia “no automático” para um painel de clima:

| Primeira ideia (genérica) | Problema | Decisão final |
|---|---|---|
| Hero com número grande + 3 cards de estatística + gradiente azul | É o padrão de qualquer dashboard. Não diz se há aviso. | Hero = **frase de estado** em tipo grande + régua de maré. Os números vão para dentro da área da equipe. |
| Divisores de seção em forma de onda | É o clichê de toda marca ligada à água. Não carrega informação. | Nenhuma onda decorativa. A única água é a linha da régua, que tem um valor. |
| Rótulos em CAIXA ALTA espaçada acima de cada título (como “INTELIGÊNCIA CLIMÁTICA” nos protótipos) | É uma marca de template e é mais difícil de ler para o público idoso. | Tudo em caixa normal. O texto auxiliar da logo vira “Inteligência climática para a saúde”. |
| “Recife • PE”, “Protótipo • Dados fictícios” (meta com pontos) | É uma convenção genérica e pouco legível. | Frases completas: “Recife, Pernambuco”. |
| Painéis todos iguais, com sombra cinza e o mesmo raio | O “kit SaaS”, que achata a hierarquia. | Hierarquia por **peso e espaço**: painéis com borda de 1 px e sem sombra. Sombra só em elementos flutuantes (diálogos, menus). Raios diferentes por função (seção 8.5). |
| Fonte Inter ou Segoe | Escolha neutra, sem relação com o público. | **Atkinson Hyperlegible Next**, criada pelo Braille Institute para leitores com baixa visão. A escolha vem do público (equipes mais velhas). |
| Barra de filtros com 4 selects | Exige leitura técnica. | **Filtro em frase**: “Mostrando **Recife inteiro**, de **1º de julho** a **15 de outubro de 2026**.” Cada parte em destaque é um botão grande que abre a escolha. |

### 8.3 Cores (tokens)

Derivadas da logo enviada: azul “Clima” `#013C69` (amostrado), verde-azulado “Sense” `#006F71`, sol `#EDB105` e a água em degradê azul.

**Base**

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--cs-mare` | `#0F4C75` | `#7FB6E0` | Cor principal da marca, títulos, item ativo, botão principal |
| `--cs-mare-forte` | `#0A3A5C` | `#A9CFEE` | Hover e pressionado do botão principal |
| `--cs-mangue` | `#0B6F6C` | `#4FC1B6` | Ações secundárias, links, foco de seleção |
| `--cs-sol` | `#EDB105` | `#F2C23A` | Só na marca e no destaque da linha d’água. Nunca como texto sobre branco. |
| `--cs-papel` | `#FFFFFF` | `#13222C` | Painéis |
| `--cs-nevoa` | `#F2F6F8` | `#0C1820` | Fundo da página (azul-acinzentado frio, não creme) |
| `--cs-tinta` | `#0E2433` | `#E8F0F5` | Texto principal (contraste 15,9:1 no papel) |
| `--cs-tinta-2` | `#44596A` | `#B4C4CF` | Texto secundário (7,2:1) |
| `--cs-linha` | `#D5E0E7` | `#2A3D4A` | Bordas e divisores |
| `--cs-foco` | `#B35C00` | `#FFB45C` | Anel de foco, 3 px (visível sobre azul e branco) |

**Níveis de aviso (status, reservados — nunca usados como cor de série)**

| Nível | Texto exibido | Marca/borda | Fundo do selo | Texto do selo | Marcas da régua |
|---|---|---|---|---|---|
| Informativo | Fique atento | `#1F6FB2` | `#E6F0F9` | `#0E2433` | 1 de 4 |
| Atenção | Atenção | `#C98A00` | `#FFF4D6` | `#0E2433` | 2 de 4 |
| Alerta | Alerta | `#D2581F` | `#FDE7DA` | `#0E2433` | 3 de 4 |
| Crítico | Situação crítica | `#A41F15` | `#A41F15` | `#FFFFFF` (7,5:1) | 4 de 4 |
| Dados insuficientes | Dados insuficientes | `#6B7A85` + hachura 45° | `#EEF1F3` | `#0E2433` | régua vazia, tracejada |
| Sem aviso | Nenhum aviso ativo | `#0B6F6C` | `#E3F3F1` | `#0E2433` | linha d’água na base |

O texto dos selos é sempre a tinta escura (ou branco no crítico), então o contraste nunca depende da cor de status (RNF-ACE-03, RN-17).

### 8.4 Cores dos gráficos (validadas)

Paleta categórica com ordem fixa, validada com o verificador de daltonismo (protan, deutan, tritan) e contraste. Resultado: **todos os testes passam** nos modos claro e escuro (pares adjacentes: CVD ΔE ≥ 8,3; visão normal ΔE ≥ 22,8; contraste ≥ 3:1). Os 3 primeiros passam também em **todos os pares** (para mapas e dispersão).

| Ordem | Matiz | Claro | Escuro | Uso típico |
|---|---|---|---|---|
| 1 | azul rio | `#1F6FB2` | `#4A93D6` | Série principal (ex.: Recife, ano selecionado) |
| 2 | laranja barro | `#C4612B` | `#D9713A` | Segunda série (ex.: maré prevista) |
| 3 | verde mangue | `#0A8F63` | `#22A874` | Terceira série |
| 4 | violeta | `#7A52C7` | `#9B7CE0` | |
| 5 | oliva | `#5D7F1F` | `#7C9E33` | |
| 6 | magenta | `#B8478F` | `#D465A8` | |

- **Referência histórica:** sempre cinza tracejado `#6B7A85`, nunca uma cor de série.
- **Faixa de incerteza:** a cor da série com 18% de opacidade.
- **Sequencial (mapa e calendário de chuva, uma só matiz azul, do claro ao escuro):** `#E3EEF7 #B9D4EA #86B3D9 #4F8CC2 #1F6FB2 #17558A #0E3A60`. Para as 5 classes do mapa (ordinal), os passos começam em `#86B3D9`, para a classe mais baixa não sumir no fundo.
- **Sequencial de saúde (vacinação):** rampa verde-mangue `#A7DCC6 → #044D36`, outra matiz para não confundir com a chuva.
- **Sem dado:** hachura cinza 45° (nunca a cor do zero).
- **Regras:** um eixo por gráfico (chuva e maré em **dois gráficos alinhados**, como no protótipo 03); legenda sempre com 2+ séries e rótulo direto em até 4; textos e valores na cor da tinta, nunca na cor da série; “Ver como tabela” em todo gráfico; texturas (`decal`) ativáveis.

### 8.5 Tipografia

**Família única: Atkinson Hyperlegible Next** (variável, pesos 300–800). O fallback é `"Atkinson Hyperlegible", system-ui, sans-serif`. Números tabulares (`font-variant-numeric: tabular-nums`) em tabelas e eixos. O destaque tipográfico vem do **peso e do tamanho**, não de troca de fonte, de itálico numa palavra ou de cor numa palavra só.

Escala (razão 1,25, base 18 px):

| Token | Tamanho | Peso | Uso |
|---|---|---|---|
| `--t-estado` | clamp(40px, 6vw, 72px) / 1,05 | 800 | Frase de estado da landing (o tipo como elemento visual) |
| `--t-1` | 44px / 1,1 | 750 | Título da página na landing |
| `--t-2` | 35px / 1,15 | 700 | Título da tela na área da equipe |
| `--t-3` | 28px / 1,2 | 700 | Título de seção |
| `--t-4` | 22px / 1,3 | 650 | Título de painel |
| `--t-corpo` | 18px / 1,55 | 400 | Texto padrão (RNF-ACE-02) |
| `--t-apoio` | 16px / 1,5 | 400 | Fonte, legendas, ajuda (mínimo absoluto) |

O comprimento de linha fica em até 68 caracteres no texto corrido. Tudo é alinhado à esquerda: nada centralizado além do conteúdo de diálogos curtos.

### 8.6 Espaço, forma e elevação

- Espaçamento em base 8: `4, 8, 12, 16, 24, 32, 48, 64, 96`.
- Raios por função: **4 px** em campos, selos e células · **10 px** em painéis · **pílula** só em chips de filtro · **0** na régua (é um instrumento).
- Bordas de 1 px com `--cs-linha`. Sombra só em diálogos, menus suspensos e no aviso de sessão.
- Alvos de clique: altura mínima de **48 px** nos botões (56 px no botão principal da landing) e 44 px nos itens de lista.

### 8.7 Movimento

- **Um momento orquestrado:** a linha d’água da régua sobe até o nível vigente ao carregar a landing (700 ms, `ease-out`). Nada mais se move sozinho.
- Os demais movimentos só respondem a ações: abrir a gaveta do menu, expandir um painel, confirmar com um toast. Sem entradas em cascata por seção e sem hover animado em todo card.
- `prefers-reduced-motion: reduce` desliga tudo isso.

### 8.8 O que torna a identidade moderna e única

Moderno aqui não quer dizer efeito por efeito. São quatro escolhas que nenhum outro produto teria do mesmo jeito, porque saem dos dados e do território do Recife:

1. **Régua de maré como linguagem de nível** (8.1). É o mesmo símbolo na landing, nos selos, no editor de comunicados (escolha do nível em 4 botões-régua) e no ícone do app.
2. **Cartografia viva em traço fino.** As faixas hídricas e os 8 distritos são desenhados como linhas, a partir das geometrias do próprio projeto, sem mapa de fundo. Na landing, o bloco **“Onde há aviso agora”** pinta o distrito afetado na cor do nível, com a nota de que o aviso vale para os bairros citados (RN-07).
3. **Tipografia como elemento visual.** A frase de estado em 72 px e peso 800, com ajuste de espaçamento negativo, ocupa o lugar da imagem de destaque. O peso variável da Atkinson Hyperlegible Next permite transições finas de hierarquia sem trocar de fonte.
4. **Movimento com significado.** No primeiro carregamento, a linha d’água sobe e o distrito afetado ganha cor. Esse é o único momento animado, e ele mostra a informação principal.

Elementos da marca a produzir (tarefas da trilha M1):

| Peça | Descrição |
|---|---|
| Logo limpa | A versão enviada tem halos semitransparentes. Será feita uma versão com alfa limpo (PNG) e uma vetorização do símbolo (SVG) para uso em tamanho pequeno. |
| Ícone do app e favicon | O símbolo da nuvem/sol em quadrado com fundo `--cs-mare`, mais uma versão monocromática. Tamanhos 16, 32, 180 e 512. |
| Imagem de compartilhamento (Open Graph) | Frase de estado + régua + traço dos rios, 1200 × 630. |
| Guia de marca | `docs/brand/guia-de-marca.md`: uso da logo, áreas de proteção, cores, tipografia, régua, tom de voz, o que não fazer. |
| Vitrine do design system | Rota de desenvolvimento `/_vitrine` com todos os componentes e estados (substitui o Storybook, com menos dependências). |

### 8.9 Linguagem da interface

- Caixa de frase, verbos simples e voz ativa. O botão diz o que acontece, e o retorno usa o mesmo verbo: **“Enviar para revisão” → “Enviado para revisão.”**
- Siglas sempre por extenso na primeira vez: “Distrito Sanitário IV (DS IV)”.
- Erros dizem o que fazer: “Não foi possível carregar os dados de chuva. A fonte não respondeu às 14h. Tente de novo em alguns minutos.” Sem pedir desculpas.
- Estados vazios convidam a agir: “Nenhuma avaliação ainda. Comece pelo mapa e registre a primeira.”
- Vocabulário fixo (glossário em `frontend/src/textos/`): aviso (público) × comunicado (interno) · avaliação · revisar · publicar · encerrar · dados insuficientes.

---

## 9. Telas

### 9.1 Landing pública (`/`)

Objetivo: em 3 segundos, a pessoa sabe se existe aviso e o que fazer.

```text
DESKTOP ≥ 1024px
┌──────────────────────────────────────────────────────────────────────────────┐
│ [logo ClimaSense]                       Avisos  Como funciona  Sobre  [Acesso da equipe] │
├──────────────────────────────────────────────────────────────────────────────┤
│ ░ traço fino das faixas hídricas do Recife ao fundo ░                          │
│  ┌──────┐                                                                     │
│  │ ▔▔ 4 │  Nenhum aviso ativo                                                 │
│  │ ▔▔ 3 │  publicado pela equipe.                    ← --t-estado, 800        │
│  │ ▔▔ 2 │                                                                     │
│  │ ▔▔ 1 │  Última verificação: hoje, 18h04.                                   │
│  │≈≈≈≈≈≈│  [ Digite seu bairro ______________ ] [Ver avisos do bairro]        │
│  └──────┘                                                                     │
│  régua de maré                                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│ Em emergência ligue:  199 Defesa Civil   193 Bombeiros   192 SAMU   (tel:)    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Avisos em vigor (quando houver)          │ Onde há aviso agora (mapa em traço,  │
│                                          │ distrito afetado na cor do nível)    │
│  ┌ selo-régua Alerta ─ Alerta de alagamento em Afogados e Mustardinha ───────┐ │
│  │ O que fazer: • Evite atravessar ruas alagadas • ...                         │ │
│  │ Vale até amanhã, 18h. Emitido pela Vigilância em Saúde do Recife, 14h20.   │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ Como um aviso chega até você  (sequência real → numeração justificada)         │
│  1 Dados de chuva, maré e território   2 A equipe avalia   3 Um responsável revisa e publica │
├──────────────────────────────────────────────────────────────────────────────┤
│ Sobre o ClimaSense · o que é e o que não é (não substitui a Defesa Civil)      │
│ De onde vêm os dados (lista de fontes com status) · Equipe                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Rodapé: projeto acadêmico, CESAR School · links oficiais                       │
└──────────────────────────────────────────────────────────────────────────────┘

CELULAR 375px: régua menor à esquerda da frase; telefones de emergência logo abaixo da frase,
em botões de largura total; “Acesso da equipe” no topo como link discreto.
```

O bloco **“Onde há aviso agora”** desenha os 8 distritos em traço e pinta os afetados. Sem aviso, todos ficam neutros e a legenda diz “Nenhum distrito com aviso publicado.”

Com aviso ativo, a frase vira, por exemplo, **“Alerta para 2 bairros até amanhã, 18h.”**, e a régua sobe até a marca 3, na cor do nível. Com vários avisos, a frase cita o mais alto e diz “e mais 1 aviso”.

### 9.2 Entrar (`/entrar`)

Uma coluna estreita centralizada (a exceção ao alinhamento à esquerda, por ser um formulário curto): logo, “Acesso da equipe”, campo **E-mail**, campo **Senha** com o botão “Mostrar senha”, e o botão **Entrar** (56 px). Abaixo, “Esqueceu a senha? Fale com o administrador do ClimaSense.” Erros aparecem acima do botão, com ícone e texto.

### 9.3 Estrutura da área da equipe

```text
┌─────────────────┬────────────────────────────────────────────────────────────┐
│ [logo]          │ Mostrando [Recife inteiro ▾], de [1º jul.] a [15 out. 2026] │
│                 │                                        Rafael Costa  [Sair] │
│ ▌Painel inicial ├────────────────────────────────────────────────────────────┤
│  Mapa do        │ Título da tela (--t-2)                                      │
│  território     │ Uma frase dizendo para que a tela serve                     │
│  Séries e       │                                                             │
│  sazonalidade   │ conteúdo (grade de 12 colunas, até 1440 px)                 │
│  Cenários de    │                                                             │
│  alagamento     │                                                             │
│  Avaliações   3 │  ← contador de itens aguardando                             │
│  Comunicados  1 │                                                             │
│  Fontes de dados│                                                             │
│  Administração  │                                                             │
│                 │                                                             │
│ Recife,         │                                                             │
│ Pernambuco      │                                                             │
└─────────────────┴────────────────────────────────────────────────────────────┘
menu: 296px (cada item cabe em uma linha), fundo papel, itens 52px, ícone + texto 18px; ativo = fundo maré 8% + barra mangue 4px + peso 700
< 1024px: o menu vira gaveta (botão “Menu”), e o filtro em frase quebra em linhas
```

Uma faixa “Ambiente de testes” aparece no topo quando `AMBIENTE` não é `producao`, para ninguém confundir o ambiente. Os dados continuam reais (RN-19).

### 9.4 Painel inicial (`/app`)

Responde “o que precisa de mim agora?” em 4 blocos, sem gráfico protagonista:

1. **Avisos publicados agora**: lista curta com o selo-régua e a validade.
2. **Aguardando sua revisão**: avaliações e comunicados (só para quem revisa), com o botão “Revisar”.
3. **Territórios em atenção**: até 5 linhas, cada uma com território, motivo em uma frase e “Abrir no mapa”.
4. **Saúde das fontes**: uma linha por fonte, com o status em texto e ícone.

### 9.5 Mapa do território (`/app/mapa`) — preserva o mapa atual

```text
┌ Busca e camadas (300px) ─┬─ Mapa (Leaflet) ────────────────────┬─ Detalhe (360px) ───────┐
│ Distrito ou bairro [___] │ [Enquadrar]                          │ Conheça o território    │
│ Colorir por [Bairros ▾]  │                                      │ (ou o distrito selecion.)│
│   bairros · área · vacinação · ocorrências* · prioridade*         │ bairros · área · lista  │
│ Camadas                  │       polígonos + rótulos            │ Fatores (se houver)     │
│  ☑ Distritos  ☑ Faixas   │       faixas hídricas                │ Qualidade dos dados     │
│ Intensidade [====] 72%   │                       ┌ Legenda ─────┐ │ Compare os distritos    │
│ Distritos  8 de 8        │                       │ 5 classes    │ │ (ranking em barras)     │
│  ■ DS I  11 bairros      │                       │ Como ler     │ │ [Registrar avaliação]   │
│  ...                     │                       └──────────────┘ │                         │
│ [Limpar filtros]         │ Fonte: … · atualizado em …           │ [Exportar CSV] [Mapa offline] │
└──────────────────────────┴──────────────────────────────────────┴─────────────────────────┘
* com o estado "dados insuficientes" quando não houver dado
```

Checklist de equivalência RF-07.1–14 nos testes E2E (seção 11). A nota da correção dos distritos VII e VIII fica no painel “Sobre os dados”. O botão “Mapa offline” baixa o HTML portátil.

### 9.6 Séries e sazonalidade (`/app/series`)

- Linha de controles: Variável [Chuva ▾] · Frequência (Diária | Semanal | Mensal, botões segmentados) · Comparar com [Média histórica ▾].
- Gráfico protagonista: “Chuva ao longo do tempo”, com a série azul, a referência cinza tracejada e as lacunas visíveis como faixa hachurada. Acima do gráfico, um **resumo em frase** gerado pela API: “Em setembro choveu 38% abaixo da média de 2021–2025. Faltam dados em 4 dias.”
- Abaixo, dois painéis: **Calendário de chuvas** (ano × mês, rampa azul) e **Estatística descritiva** (tabela simples: medida, valor, o que significa).
- Aviso de série curta (RN-08) e o tipo da fonte (observada, prevista ou derivada) na legenda.

### 9.7 Cenários de alagamento (`/app/cenarios`)

Segue a estrutura do protótipo 03, já aprovado: dois gráficos alinhados pelo eixo do tempo (chuva com faixa de incerteza; maré) e, à direita, o **cartão de decisão** com o selo-régua da prioridade, a janela de atenção, os fatores, a qualidade dos dados e o botão **“Encaminhar para avaliação”**. No topo, uma faixa fixa: **“Experimental: não validado para uso operacional.”** Quando faltam insumos, o cartão mostra o estado “Dados insuficientes para estimar”, com a régua vazia e tracejada.

### 9.8 Avaliações (`/app/avaliacoes`, `/app/avaliacoes/:id`)

Lista com filtros por estado (abas com contagem) e uma tabela: território, prioridade (selo), estado, autor, atualizada em. Detalhe com o formulário (prioridade como 4 botões grandes com a régua, justificativa, limitações e evidências anexadas a partir do mapa, das séries e dos cenários) e a **linha do tempo** das versões e decisões.

### 9.9 Comunicados (`/app/comunicados`, editor `/app/comunicados/:id`)

```text
┌ Etapas do fluxo (sequência real): Rascunho → Em revisão → Aprovado → Publicado ──────────┐
├ Editor (58%) ───────────────────────────────┬ Prévia para a população (38%) ─────────────┤
│ Territórios [Afogados ×] [+ adicionar]      │ ┌ exatamente como na landing ────────────┐ │
│ Público [População ▾]                       │ │ selo-régua  Alerta                     │ │
│ Nível (4 botões com régua)                  │ │ Alerta de alagamento em Afogados       │ │
│ Título [________________] 54/120            │ │ O que fazer: ...                       │ │
│ Texto  [________________] 410/1200          │ │ Vale até ...  Emitido por ...          │ │
│   ⚠ Frase com mais de 25 palavras (linha 2) │ └────────────────────────────────────────┘ │
│ O que fazer (até 5 itens)                   │ Versão 3 · criada por Rafael, 15/10 17h40  │
│ Validade: de [__] até [__]                  │ Revisor: (a definir ao enviar)             │
│ Evidências vinculadas: [Mapa DS V] [Série…] │ Histórico (linha do tempo)                 │
├─────────────────────────────────────────────┴───────────────────────────────────────────┤
│ [Salvar rascunho]        [Enviar para revisão]        (Publicar: só Coordenação, se aprovado) │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

Para o revisor, a mesma tela fica em modo leitura, com uma área de **decisão**: [Aprovar esta versão] [Devolver com justificativa]. Publicar e encerrar pedem confirmação com o texto da consequência (RNF-ACE-11): “Publicar torna o aviso visível para qualquer pessoa na página inicial até 16/10, 18h.”

### 9.10 Fontes de dados (`/app/fontes`)

Tabela com fonte, órgão, tipo, status (texto e ícone), última atualização, cobertura e um link “Ver detalhes”. As fontes “Planejada” (ANA, APAC, INMET…) aparecem num grupo separado, explicando o que trarão. O detalhe mostra os metadados (RNF-CON-04), as execuções do ETL e, para o administrador, o botão **“Atualizar agora”**.

### 9.11 Administração (`/app/admin/...`)

Três abas: **Usuários** (tabela + formulário de papéis com caixas de seleção descritivas; desativar em vez de excluir), **Execuções do ETL** e **Auditoria** (filtros por usuário, ação e período).

### 9.12 Componentes do design system

| Componente | Função | Requisitos |
|---|---|---|
| `ReguaMare` | Régua de nível (landing grande / selo pequeno) | RF-01, RN-17 |
| `SeloNivel` | Régua compacta + nome do nível | RN-17 |
| `FiltroFrase` | Filtro global como frase editável, sincronizado com a URL | RF-05 |
| `QuadroGrafico` | Título, resumo em frase, gráfico ECharts, “Ver como tabela”, legenda de fonte, selos de estado | RF-06.4, RNF-ACE-09 |
| `LegendaFonte` | “Fonte: … · Atualizado em …” | CA-02 |
| `EstadoDados` | Dados insuficientes, desatualizado, com falha | RN-01 |
| `MapaTerritorio` | Leaflet + `model.ts` | RF-07 |
| `EtapasFluxo` | Etapas do fluxo de revisão | RF-11.2 |
| `LinhaDoTempo` | Histórico de versões e decisões | RF-11.7 |
| `Botao`, `Campo`, `Selecao`, `Dialogo`, `Aviso` (toast), `Tabela`, `Abas`, `VazioConvidativo` | Base | RNF-ACE |
| `AvisoSessao` | Diálogo de inatividade | RF-02.5 |

Uma **prévia visual da identidade** (régua, cores, tipografia, hero da landing e estrutura da área da equipe) acompanha este documento em `docs/brand/previa-identidade.html`, para aprovação antes da execução.

---

## 10. Segurança e configuração

### 10.1 `.env.example`

```dotenv
# Ambiente: desenvolvimento | demonstracao | producao
AMBIENTE=desenvolvimento

# MongoDB Atlas (bronze + território) — mesma variável do ETL e do mapa atuais
MONGO_URI=mongodb+srv://USUARIO:SENHA@SEU-CLUSTER.mongodb.net/?appName=ClimaSense
MONGO_DB_TERRITORIO=Recife
MONGO_DB_BRONZE_VACINACAO=vacinacao

# Postgres / Neon (silver + gold + aplicação). NEON_URL também é aceito.
DATABASE_URL=postgresql://USUARIO:SENHA@SEU-HOST.neon.tech/climasense?sslmode=require

# Sessão
SESSION_SECRET=gere-com-python--c-import-secrets-print-secrets.token_urlsafe-48
SESSAO_INATIVIDADE_MIN=60
CORS_ORIGINS=http://localhost:5173

# Primeiro administrador (usado só pelo comando de criação inicial)
ADMIN_EMAIL=
ADMIN_SENHA_INICIAL=

# ETL
ETL_LIMITE_VACINACAO=5000
SUPRESSAO_MINIMA=5

# Mapa
MAP_TILES_URL=https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}

# Conectores futuros (deixe em branco até implementar)
ANA_USUARIO=
ANA_SENHA=
```

### 10.2 Medidas

| Ameaça | Medida | Req. |
|---|---|---|
| Vazamento de segredo | `.env` no `.gitignore`. Varredura de segredos (gitleaks) no CI e num hook de pre-commit. A configuração nunca é logada. | RNF-SEG-01, CA-12 |
| Força bruta | Bloqueio de 15 min após 5 falhas. Tempo de resposta constante. | RF-02.3 |
| Sequestro de sessão | Token de 32 bytes, só o hash no banco. Cookie HttpOnly, Secure e SameSite. Revogação no logout. | RNF-SEG-03 |
| CSRF | Double-submit (`cs_csrf` + cabeçalho `X-CSRF-Token`) | RNF-SEG-04 |
| XSS | React escapa por padrão. O texto do comunicado é texto puro (sem HTML), com quebras de linha convertidas na renderização. CSP restritiva. | RNF-SEG-04 |
| Injeção de fórmula no CSV | `csvCell` portado (prefixo `'` em `= + - @ \t \r`) | RF-07.10 |
| Escalada de privilégio | Papéis verificados no backend em cada rota (dependência `exige_papel`). Testes por papel. | RF-03.1 |
| Reidentificação | Supressão de agregados com contagem menor que 5. Nenhum endpoint devolve registro individual. | RN-13 |
| Exposição de erro | Handler global devolve problem+json sem pilha. Logs sem a URI de conexão (o padrão do `mongo_teste.py`). | RNF-SEG-05 |

Cabeçalhos: `Content-Security-Policy` (permitindo os tiles configurados), `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security` em produção.

---

## 11. Estratégia de testes

| Nível | Ferramenta | O que cobre | Critério |
|---|---|---|---|
| Domínio | pytest | Transições de estado e guardas (RN-03/04/05/14/19), status das fontes, dados insuficientes, estatística (comparada aos valores do `relatorio.md`), supressão | CA-06, CA-07, CA-08 |
| ETL | pytest + mongomock + fixtures CKAN | `Transform` com os mesmos casos do original, bronze acumulativa, registro de execução, falha da fonte | CA-11 |
| Território | pytest | Os 6 testes portados do `test_distritos.py` + simplificação das faixas | RF-13.6 |
| API | pytest + TestClient + Postgres (Docker ou branch Neon) | Contratos, papéis (matriz rota × papel), CSRF, sessão, envelope `meta` | RF-03, CA-02 |
| Frontend unidade | Vitest | `model.ts` (4 testes portados), formatos pt-BR, filtro na URL, CSV | RF-07, RN-16 |
| Ponta a ponta | Playwright | J1 (landing em 375 px e desktop), J2 (login, bloqueio, inatividade), mapa (checklist RF-07), J6 e J7 (rascunho → revisão → publicação → aparece na landing → expira) | CA-01, CA-09, CA-10 |
| Acessibilidade | @axe-core/playwright + checklist manual | Todas as telas, sem violações sérias ou críticas | CA-13 |
| Reprodutibilidade | Script `verificar_gold.py` | Recalcula a gold a partir da silver e compara | CA-04 |

---

## 12. Riscos de implementação

| Risco | Mitigação |
|---|---|
| Rede da faculdade bloqueia o Atlas ou o Neon | `GET /health` mostra qual banco falhou. O mapa tem a opção explícita de dados locais só no modo portátil (RNF-CON-02). |
| GeoJSON das faixas é pesado (3,4 MB) | Geometria simplificada para a web, `ETag` e compressão gzip. |
| Plano gratuito do Neon suspende por inatividade | A primeira requisição pode demorar. O frontend mostra “Conectando aos dados…” em vez de erro imediato. |
| Escopo grande para o semestre | O `tasks.md` vai separar em marcos entregáveis: base → mapa e ETL → séries e cenários → fluxo de comunicados → polimento e acessibilidade. |
| Fontes reais com formatos diferentes entre si | O formato `silver.observacoes` foi pensado a partir dos metadados mínimos do contexto §16.2, e os conectores reais só precisam preenchê-lo. |

---

## 13. Rastreabilidade (resumo)

| Requisito | Seções do design |
|---|---|
| RF-01 Landing | 6.2 `/publico`, 8.1, 9.1 |
| RF-02/03 Login e papéis | 7.4, 6.2 `/auth`, 10.2 |
| RF-04 Menu lateral | 9.3, 9.4 |
| RF-05 Filtros | 8.2 (filtro em frase), 9.12 `FiltroFrase` |
| RF-06 Fontes | 7.2, 9.10 |
| RF-07 Mapa | 4.1, 5.2, 9.5, 11 |
| RF-08 Séries | 5.3 gold, 6.2 `/series`, 9.6 |
| RF-09 Cenários | 5.5, 9.7 |
| RF-10/11 Avaliações e comunicados | 5.3 app, 7.1, 9.8, 9.9 |
| RF-12/13 ETL e território | 4.1, 5.1–5.4 |
| RF-14 Auditoria | 5.3 `app.auditoria` |
| RF-15 Saúde agregada | 5.3 `gold.vacinacao_distrito_mes`, 10.2 |
| RF-16 Administração | 6.2 `/admin`, 9.11 |
| RNF-ACE / RNF-VIS | 8, 9 |
| RNF-SEG | 7.4, 10 |
