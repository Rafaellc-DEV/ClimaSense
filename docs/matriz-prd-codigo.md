# Matriz PRD × código atual

Onda 0, agente `arquiteto`, 06/11/2026. Base: `docs/PRD.md` v2 e o código no commit `1431fdb`, mais as alterações
locais do frontend ainda não commitadas (`features/situacao`, `saude`, `registro`, `abrigos`, `boletim`). Rotas
relativas a `/api/v1`; contrato exportado em `docs/api/openapi.json` (`scripts/exportar_openapi.py`).

> **Atualização de 06/11/2026 (PRD v3, ADR 0016):** abrigos saíram do produto. As linhas RF-02, RF-07, RF-08,
> RF-09, RF-13, RF-15, RF-17, RF-33, RF-34, RNF-03 e RNF-04 e as §4 e §5 foram revistas contra a árvore de trabalho
> da branch `evolucao-prd-v2` (alterações ainda não commitadas). As demais linhas continuam com o retrato do Gate 0;
> o avanço da Onda 1 está em `docs/progresso-onda-1.md`.
>
> **Atualização de 06/11/2026 (PRD v4, ADR 0017):** entram RF-35 a RF-42 (§2.1), todos **em construção** e com
> veredito **adaptar**. Abrigos continuam fora (ADR 0016).

- **Veredito:** **manter** (o código atende; só conferir), **adaptar** (existe em parte ou não existe; vira tarefa),
  **remover** (existe e sai do produto; para landing e comunicados, "desligar por chave", ADR 0011).
- **Hoje:** A = atende, P = parcial, N = não existe.

## 1. Resumo

| | Manter | Adaptar | Remover | Total |
|---|---|---|---|---|
| RF (01–34) | 6 | 27 | 1 | 34 |
| RF (35–42, v4) | 0 | 8 | 0 | 8 |
| RNF (01–12) | 2 | 10 | 0 | 12 |

| Hoje | RF | RNF |
|---|---|---|
| Atende (A) | 6 | 2 |
| Parcial (P) | 18 | 9 |
| Não existe (N) | 9 | 1 |
| Em construção (v4) | 8 (RF-35 a RF-42) | 0 |
| Removido do PRD | 1 (RF-08) | 0 |

Na v3 do PRD, RF-08 (abrigos abertos e desabrigados) foi removido e o código correspondente já saiu (ADR 0016). A
contagem do Gate 0 foi ajustada só nas linhas revistas pela v3. Além disso, saem do produto **funcionalidades existentes fora do escopo** (§4):
landing pública, comunicados e avaliações (desligar por chave), painel antigo, módulo de registro do evento e lições
aprendidas, mapa portátil e estatísticas de séries.

## 2. Requisitos funcionais

| ID | Fase | Veredito | Hoje | Onde está | Evidência | O que falta |
|---|---|---|---|---|---|---|
| RF-01 | 1 | adaptar | P | `dominio/estagio.py`, `servicos/estagios.py`, `api/routers/estagios.py`, `frontend/src/features/situacao/TelaSituacao.tsx`, `features/territorio/MapaSituacao.tsx` | `GET /estagios?nivel=distrito\|bairro` devolve `sugerido` e `declarado`; mapa da Situação colore por estágio; `tests/unit/dominio/test_estagio.py` | **Estágio oficial da cidade dado pelo COP** não existe: falta registro (manual ou feed) com fonte e hora, mostrado ao lado do sugerido/declarado. |
| RF-02 | 1 | adaptar | P | `api/routers/territorios.py` (`/territorios/camadas/areas-risco`, `/camadas/vulneraveis`, `/camadas/equipamentos-saude`, `/hidrografia.geojson`), `frontend/src/features/mapa/PainelCamadas.tsx`, `usarCamadas.tsx` | Controle "Camadas do mapa" no Mapa e no Simulador (Onda 1, Etapa 6); `features/mapa/Camadas.test.tsx` | Áreas de risco com cobertura parcial e sem tipo de perigo (P-25); deficiência sem fonte (P-23). **v3:** a camada de abrigos saiu (ADR 0016). |
| RF-03 | 1 | adaptar | N | — | `docs/funcionalidades-equipe.md` §4 registra a lacuna | Agregado por bairro de idosos e crianças (IBGE 2022); deficiência sem fonte por bairro (P-12). "Dados insuficientes" até lá. |
| RF-04 | 1 | adaptar | N | — | — | Cruzamento equipamento × vulneráveis do bairro (depende de RF-02 e RF-03). |
| RF-05 | 1 | adaptar | P | `etl/conectores/alertas.py`, `silver.alertas_oficiais` (migração 0008), `servicos/estagios.py::_alertas_vigentes`, `features/situacao/CartaoDistrito.tsx` | APAC, INMET, Cemaden e IDAP filtrados para o Recife, com `emitido_em` e `expira_em` | Alertas do **COP** e da **Defesa Civil do Recife** fora do IDAP (registro manual com hora); lista própria de alertas. |
| RF-06 | 1 | adaptar | P | `dominio/prioridades.py`, `GET /territorios/prioridades` (sem uso no frontend) | Prioridade por estágio e evidências | Índice de vulnerabilidade (vulneráveis + áreas de risco + histórico) e destaque visual (ex.: DS VII). |
| RF-07 | 1 | adaptar | P | `features/mapa/PainelTerritorio.tsx`, `features/mapa/ResumoBairro.tsx`, `GET /territorios/{territorio_id}/resumo-vulnerabilidade` | Painel do bairro com estágio, alertas, residentes vulneráveis e equipamentos (em área de risco); `features/mapa/TelaMapa.test.tsx` | Deficiência sem fonte (P-23). **v3:** "abrigos próximos" saiu do painel e da rota (ADR 0016). |
| RF-08 | — | **remover** (feito) | — | Apagados: `api/routers/abrigos.py`, `dominio/abrigos.py`, `servicos/abrigos.py`, `etl/conectores/abrigos.py`, `features/abrigos/`, `data/abrigos/`; migração `0019_remove_abrigos_exclusao_acao.py` apaga `app.abrigos`, `app.abrigo_atualizacoes` e a fonte `recife-abrigos` | `tests/integration/test_migracao_0019.py`; `TelaSituacao.test.tsx` e `TelaBoletim.test.tsx` conferem que "desabrigados" não aparece | Removido no PRD v3 (ADR 0016). **Pendente (dono):** aplicar a 0019 no Neon e decidir as coleções bronze órfãs no Atlas (P-31). |
| RF-09 | 1 | manter | A | `frontend/src/features/situacao/TelaSituacao.tsx` (`GET /estagios/oficial`, `GET /boletim`) | Estágio oficial do COP, chuva medida em 24 h, chuva prevista em 24 h e nível da maré, cada um com fonte e hora; "Dados insuficientes" sem registro; `TelaSituacao.test.tsx` | Estágio oficial depende de registro da equipe (P-21). Na cidade, a chuva é o maior valor entre os distritos. |
| RF-10 | 1 | adaptar | P | `frontend/src/lib/api.ts` (`staleTime 60s`, `refetchOnWindowFocus: false`), `features/landing/useEstado.ts` (`refetchInterval 120s`) | Hora exibida nas respostas | Telas da equipe não se atualizam sozinhas: definir `refetchInterval` por tela (ex.: 60 s na Situação). |
| RF-11 | 2 | adaptar | P | `etl/conectores/infodengue.py`, `etl/conectores/leptospirose.py`, `GET /saude/resumo`, `features/saude/TelaSaude.tsx` | Séries semanais com semana incompleta marcada | Fonte mais atual da vigilância (P-01); hoje 1 a 3 semanas de atraso, mostrado com a hora. |
| RF-12 | 2 | adaptar | P | `dominio/janela_leptospirose.py`, `GET /saude/semanal`, `GET /saude/bairros` | Leptospirose semanal e janela de 30 dias; arboviroses por bairro e ano | **Peçonhentos** (SINAN `ANIMBR`, só município, testado em `docs/pesquisa/saude-e-chuva.md`); recorte **por território** semanal (depende da vigilância). |
| RF-13 | 2 | adaptar | N | — (vacinação COVID removida pela migração 0009) | — | Consultas, vacinas e medicamentos em eventos de chuva: sem fonte; "Dados insuficientes" até haver fonte ou registro da equipe (P-03). **v3:** a parte "nos abrigos" saiu (ADR 0016). Não é a vacinação COVID antiga. |
| RF-14 | 2 | adaptar | N | — | — | Situação de unidades de saúde (fechada, danificada) com fonte e hora; cadastro pelo CNES. |
| RF-15 | 1 | manter | A | `app.acoes_resposta` (0007), `api/routers/acoes.py` (`DELETE /acoes/{acao_id}`), `servicos/acoes.py::excluir`, `features/acoes/TelaAcoes.tsx`; migração 0019 (sem chave estrangeira em `app.acao_eventos`) | Território `municipio`, `distrito` ou `bairro`; exclusão em qualquer situação, com auditoria `acao_resposta_excluida` (sem descrição nem responsável) e linha do tempo guardada; `tests/integration/test_evento_chuva.py::test_acao_em_municipio_distrito_ou_bairro_e_exclusao_em_qualquer_situacao`; `TelaAcoes.test.tsx` ("Excluir esta ação?") | Confirmar com o cliente a guarda da linha do tempo da ação excluída (P-30). Ações ainda gravam `tipo: "outro"`. |
| RF-16 | 1 | adaptar | P | `GET /acoes?situacao=em_andamento`, `TelaRegistro.tsx`, `TelaBoletim.tsx` | Lista filtrável | Andamento resumido por distrito (contagem por situação) na tela Ações. |
| RF-17 | 1 | adaptar | P | `api/routers/boletim.py`, `servicos/boletim.py`, `features/boletim/TelaBoletim.tsx` | `GET /boletim`: estágio, chuva, maré, ações e fontes, imprimível (abrigos saíram na v3; `TelaBoletim.test.tsx`) | Relatório **executivo** a partir do Boletim: período, ações por distrito e situação, saúde, cenário salvo; modelo do cliente (P-08). |
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
| RF-33 | 1 | adaptar | P | `servicos/arboviroses_cenario.py`, `servicos/simulador.py` (`itens[].arboviroses` por distrito, `resumo.arboviroses`) | `POST /cenarios/simular`: dengue e chikungunya com série semanal do município (InfoDengue) e total anual por distrito (Prefeitura); zika "Dados insuficientes"; classe por terços; supressão de 1 a 4; aviso de contexto e selo experimental; `tests/unit/test_arboviroses_cenario.py`, `tests/integration/test_onda1_etapa3.py::test_arboviroses_*` | **Tela:** o Simulador ainda não exibe o bloco (conferido em 06/11/2026; tarefa do `frontend-equipe`). Validar o critério (P-29); zika (P-27); fonte semanal por distrito (P-28). |
| RF-34 | 1 | adaptar | P | `servicos/simulador.py::_ordem_distritos` | `resumo.ordem_de_atencao_distritos`: estágio sugerido pela chuva simulada, depois classe de arboviroses, depois nome; `agravos_em_destaque` | Mostrar na tela; validar a ordem com o cliente (P-29). |
| RF-32 | 1 | adaptar | P | `silver.alertas_oficiais.criterio_geo` e `territorio_id` (0008), `ConfiraOficial` em `features/evento/Evento.tsx` | Fonte, hora, filtro geográfico e link para APAC/Cemaden na Situação | Território **exato** do alerta na tela (hoje o território gravado é `recife` por padrão; `area` só em texto) e a orientação "confira na APAC ou no Cemaden" em todo alerta, não só no topo. |

### 2.1 Requisitos da ampliação de escopo (PRD v4, ADR 0017)

Conferido na árvore de trabalho em 06/11/2026. "Reaproveita" diz o que já existe e serve de base; nenhum conector,
rota ou tela própria destes requisitos existe ainda. Fontes, cadência e limites em `docs/pesquisa/api-*.md`.

| ID | Fase | Veredito | Hoje | Reaproveita (onde está) | Evidência | O que falta |
|---|---|---|---|---|---|---|
| RF-35 | 1 (inundação: 2) | adaptar | em construção | `etl/conectores/planejados.py::ConectorAnaTelemetria` (planejado, falha com "Conector planejado"); padrão de `etl/conectores/apac.py` (mesmo host da APAC); `alertas-oficiais` traz "Risco Hidrológico" do Cemaden | `docs/pesquisa/api-hidrologia.md` (estação `39187800` testada na APAC e na ANA) | Conector `apac-rios` (rios e reservatórios, limiares guardados com a leitura); ANA legado como segunda fonte; classe pelos limiares oficiais; bloco na Situação e camada no Mapa; texto "estação a montante do Recife" e "Dados insuficientes" para Beberibe, Tejipió, Jordão e Pina; verbetes e `frescor.toml`. Inundação por território (Experimental) depende de P-49. Licença P-33; sensores do COP P-35. |
| RF-36 | 1 | adaptar | em construção | `etl/conectores/apac.py` (`JANELAS` de 1 h a 120 h, `silver.apac_chuva_leituras`); `servicos/situacao_chuva.py` e `GET /situacao/chuva` (medida em 24 h e 72 h por distrito, estações sem leitura; distrito sem pluviômetro não mostra chuva medida); `etl/conectores/open_meteo.py` | Docstring de `servicos/situacao_chuva.py`; `docs/pesquisa/api-meteorologia.md` | Conferir se a tela Situação usa `GET /situacao/chuva` (não achei chamada no frontend em 06/11/2026); número de estações válidas por distrito; série horária a partir da coleta (gold nova) com o aviso na tela; temperatura como previsão/modelo; umidade do solo como modelo com selo Experimental. Token INMET P-36; Open-Meteo P-46; código de município da APAC P-33. |
| RF-37 | 1 (alagamento 2026: depois de P-32) | adaptar | em construção | `etl/conectores/areas_risco.py` (mesmo servidor ArcGIS, setores Sedec, 24 de 94 bairros); `etl/conectores/alagamento.py` (atendimentos 2014 a 2024); `etl/conectores/ibge_censo.py` | `docs/pesquisa/api-territorial.md` (489 polígonos SGB; 86 bairros com R3/R4) | Conector da suscetibilidade do SGB; contagem de atendimentos com grau R3/R4 por bairro (ler `Grau_de_Risco`); agregado de alagamento de 2026 por bairro sem lote nem endereço; cobertura "x de 94" por camada; deficiência: total municipal e "Dados insuficientes" (P-41). Licença P-32; 2025 e 2026 P-42. |
| RF-38 | 1 | adaptar | em construção | `GET /territorios/{territorio_id}/resumo-vulnerabilidade`, `features/mapa/ResumoBairro.tsx`, `features/mapa/PainelCamadas.tsx`, `servicos/vulnerabilidade.py`, `servicos/prioridade_vulnerabilidade.py` | Painel do bairro com vulneráveis e equipamentos (Etapa 6) | Juntar no painel do bairro chuva prevista, suscetibilidade e ocorrências, lado a lado, com data de referência e cobertura; sem índice composto (P-22). |
| RF-39 | 2 | adaptar | em construção | `etl/conectores/infodengue.py`, `etl/conectores/leptospirose.py`, `dominio/janela_leptospirose.py`, `GET /saude/semanal`, `features/saude/TelaSaude.tsx` | `docs/pesquisa/api-epidemiologia.md` (SAMU 2026 e SISAGUA 2026 testados) | Conectores `samu-recife` (agregar na leitura; descartar endereço, sexo, idade, hora) e `sisagua`; comparativo por semana epidemiológica ligado ao evento do RF-41; data de corte por fonte; texto "Coincidência temporal, não prova de causa"; selo Experimental. Convênio P-38 a P-40; janelas P-50; termos P-51. |
| RF-40 | 1 | adaptar | em construção | `etl/conectores/alertas.py` (`silver.alertas_oficiais` com `primeira_vez_em` e `visto_em`), `features/evento/Evento.tsx` (`ConfiraOficial`), `GET/POST /estagios/oficial` | `docs/pesquisa/api-operacional.md` §1.5 | Consulta histórica de alertas por janela; lista organizada por origem, nível e validade; sinalizações internas com fonte, hora, confiança e justificativa, separadas dos oficiais (P-53); registro de alertas do COP e da Defesa Civil do Recife pela equipe. |
| RF-41 | 2 | adaptar | em construção | `servicos/boletim.py`, `features/boletim/TelaBoletim.tsx` (Relatório executivo), `app.acoes_resposta`, `app.acao_eventos`, `app.estagio_oficial`, `app.cenarios` | Relatório executivo a partir do Boletim (Etapa 5) | Entidade de evento (início, fim, comunicados, distritos afetados, situação final, pendências) com linha do tempo; aprovação por outra pessoa (RN-05); conector `atlas-desastres` (retrospectivos) e episódios dos atendimentos. Regras e papéis P-43, P-44; termos do Atlas P-34; estágios retrospectivos P-47. |
| RF-42 | 1 | adaptar | em construção | `api/envelope.py` (`meta.fontes[].atualizado_em`, `status`, `limite_frescor_h`, `desatualizado`), `etl/frescor.toml`, `GET /fontes`, `features/fontes/` | Fonte e "atualizado há" em todo indicador (Etapa 1) | Acrescentar data de referência, frequência da fonte, situação da integração (incluir "registro manual" e "sem fonte") e confiabilidade (medido, previsão, modelo, oficial; estações válidas). |

## 3. Requisitos não funcionais

| ID | Veredito | Hoje | Onde está | Evidência | O que falta |
|---|---|---|---|---|---|
| RNF-01 | adaptar | P | `auth/`, `api/autorizacao.py`, `dominio/papeis.py`, `app.auditoria` somente inclusão (0003) | Sessão no servidor, CSRF, Argon2id, bloqueio, 4 papéis; `tests/integration/test_matriz_autorizacao.py`, `test_auditoria.py` | "Quem **acessou** o quê": hoje só login e alterações são auditados; registrar leitura de dados restritos (vulneráveis). |
| RNF-02 | adaptar | P | `api/seguranca.py` (CSP, HSTS, `X-Frame-Options`), Gitleaks no pre-commit e no CI | Sem PHP; independente dos sistemas da prefeitura | Rotas públicas (`/publico/*`) ainda ativas: desligar (ADR 0011); hospedagem (ADR 0013). |
| RNF-03 | adaptar | P | Conectores descartam campos pessoais (`etl/conectores/arboviroses.py`, CNES; o conector de abrigos saiu na v3), `config.supressao_minima = 5` | Só contagens na API | Legado `silver.vacinados` e `public.silver_vacinados_legado_etl_avd` com microdados individuais no Neon (D-05); acesso restrito à camada de vulneráveis. |
| RNF-04 | adaptar | P | Conectores em `etl/conectores/`; formulários de ação e de estágio oficial | APAC, INMET, Cemaden, IDAP, CKAN, InfoDengue, SINAN, CNES, IBGE, Sedec (o feed de abrigos ativos do COP saiu na v3) | COP (estágio oficial, P-21), vigilância (saúde por território, P-01, P-28), Assistência Social (vulneráveis, P-12); **importação manual por arquivo** com hora. |
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
| Landing pública (busca e avisos; os abrigos para a população saíram na v3) | `frontend/src/features/landing/`, `GET /publico/*` | **remover** do produto por chave (`FUNC_LANDING_PUBLICA`), sem apagar | PRD §5 e §12; ADR 0011 |
| Comunicados com revisão e publicação | `features/comunicados/`, `/comunicados/*`, `app.comunicados*`, `app.revisoes` | **remover** por chave (`FUNC_COMUNICADOS`), sem apagar | PRD §5; ADR 0011 |
| Avaliações territoriais | `/avaliacoes/*`, `app.avaliacoes*` (sem tela) | **remover** por chave (`FUNC_COMUNICADOS`) | Só existem para os comunicados |
| Painel antigo | `api/routers/painel.py` (`/painel/resumo`, `/painel/situacao`, `/painel/acoes`) | **remover** depois de a Situação cobrir RF-09 e RF-10 | Duplica a Situação; `/painel/acoes` é fila de revisões de comunicados. `AppShell.tsx` ainda usa `/painel` para o contador. |
| Registro do evento (linha do tempo de estágios e ações, lição aprendida) | `features/registro/`, `licao_aprendida` em `app.acoes_resposta`, `app.acao_eventos` | **adaptar** para a tela **Ações** | PRD §5 tira o módulo separado de registro e lições; `acao_eventos` continua como histórico auditável, sem tela própria |
| Mensagem pronta de WhatsApp da mudança de estágio | `POST /estagios/mensagem` | **manter** | RF-31 |
| Resumo do boletim em texto para WhatsApp | `GET /boletim/texto` | **decisão do dono** (D-07) | Não é pedido pelo RF-31 (que cobre a mudança de estágio); nada é enviado, então não fere o §5 |
| Chuva (próximos dias e histórico) | `features/chuva/`, `GET /cenarios`, `GET /series` | **adaptar** | Vira premissas do Simulador (§8.1) e camada do Mapa; sai do menu como tela própria (RF-20) |
| Séries: sazonalidade, referência e estatística descritiva | `/series/sazonalidade`, `/series/referencia`, `/series/estatisticas` | **remover** do menu (rotas sem uso no frontend) | Não pedidas |
| Mapa portátil (HTML offline da Aula 07) | `GET /territorios/mapa-portatil` | **remover** do produto | Não pedido; legado acadêmico |
| Indicadores por distrito para colorir o mapa | `GET /territorios/indicadores` | **adaptar** | Sem uso no frontend; reaproveitar para as camadas |
| Abrigos | `features/abrigos/`, `/abrigos/*`, `/publico/abrigos`, conector `recife-abrigos` | **removido** (feito; migração 0019 ainda não aplicada no Neon) | PRD v3, ADR 0016 |
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
7. **Abrigos** (`specs/foco-chuvas.md` F3 e métricas 3, 4 e 6; `specs/requirements.md` RF-15.1) saem do escopo
   (PRD v3, ADR 0016).
8. **Histórico somente de inclusão × exclusão de ação.** `docs/funcionalidades-equipe.md` dizia que nada é apagado.
   Na v3 a ação (`app.acoes_resposta`) pode ser excluída; o histórico (`app.acao_eventos`, `app.auditoria`) continua
   somente de inclusão. A guarda do histórico da ação excluída precisa de confirmação do cliente (P-30).
9. **Arboviroses no simulador** (RF-33, RF-34) são contexto, não previsão: a classe é ordinal e relativa, sem
   percentual (RN-06), e leva o selo "Experimental" (RN-11).
10. **Registro do evento** (§4, "Registro do evento ... adaptar para a tela Ações"; PRD v3 §5 "módulo separado de
    registro do evento"). Na v4 o histórico de eventos entra como RF-41, dentro da tela Ações; lições aprendidas
    continuam fora. O campo `licao_aprendida` de `app.acoes_resposta` segue obsoleto.
11. **Comunicados** (ADR 0011, desligados por chave) **×** comunicados do RF-41. Os do RF-41 são registros da equipe
    sobre comunicados de outros órgãos (órgão, hora, link), sem revisão nem publicação à população; não religam
    `FUNC_COMUNICADOS`.
12. **`ana-telemetria` "exige cadastro"** (`docs/dicionario-dados/ana-telemetria.md`) vale só para o HidroWebService
    novo; o serviço legado `ServiceANA.asmx` responde sem token (RF-35).
