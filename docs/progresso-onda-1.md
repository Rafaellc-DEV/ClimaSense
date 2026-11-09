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

## Etapa 6 — Camadas com o dado que existe (06/11/2026)

**O que mudou**
- RF-02, RF-04: `cnes-equipamentos` — 271 unidades públicas e SUS do CNES (sem consultórios de pessoa física, CNPJ,
  telefone, e-mail ou endereço), bairro por ponto-em-polígono; 263 com coordenada no mapa.
- RF-03: `ibge-censo-2022-bairro` — 94 de 94 bairros, faixas 0-4, 0-14, 60+, 70+ e total (1.482.654 moradores). O
  IBGE não publica 80+ por bairro: a faixa é 70+ (migração 0018) e nada é estimado. Deficiência: "Dados insuficientes"
  (não há dado público por bairro).
- RF-02: `recife-areas-risco` — 677 setores R1–R4 da camada `Setores_Risco_SEDEC`, cobrindo 24 de 94 bairros
  (regionais Nordeste, Noroeste, Norte, Oeste e Sul): rotulado "cobertura parcial"; a camada não informa o tipo de
  perigo.
- Backend: tabelas silver (migração 0017), rotas das camadas, `resumo-vulnerabilidade` por território (equipamentos
  em área de risco) e população vulnerável exposta no simulador (contagem de residentes, nunca percentual).
- Frontend: controle "Camadas do mapa" no Mapa e no Simulador; painel do bairro com residentes vulneráveis,
  equipamentos (em área de risco) e áreas mapeadas, cada número com a fonte.

**Testes**: backend 1078 passed, ruff limpo; frontend lint, tsc, 226 testes e build verdes. Cargas reais no Neon e
conferência na tela com dados reais (Edge, 1440 e 375 px).

**Pendências**
- P-22 (como combinar histórico e população na ordem dos prioritários), P-23 (deficiência), P-24 (80+), P-25
  (cobertura e tipo de perigo das áreas de risco), P-26 (rede municipal sem CNES).
- Para a Etapa 5: lista de abrigos longa no painel do bairro; Mapa estoura 3 px a 375 px; rótulo "102 bairros" no
  Simulador mistura distritos.

## Etapa 5 — Menu nas cinco telas (06/11/2026)

**O que mudou**
- RF-20: menu com as cinco telas do PRD — Mapa (`/app`), Situação do evento, Saúde, Ações e Simulador; Fontes e
  Administração no rodapé. Saíram do menu (com redirecionamento, sem 404): Registro do evento → Ações, Abrigos →
  Situação do evento, Boletim → Ações > Relatório executivo, painel antigo → Situação; Chuva segue acessível pelo
  Simulador ("Previsão e histórico de chuva").
- RF-08, RF-09, RF-10: `GET /abrigos/situacao` com abrigos abertos, pessoas abrigadas e desabrigados da cidade e dos 8
  distritos (vulneráveis primeiro). Ocupação e desabrigados voltam como registro manual da equipe (PRD v2 §9), com
  hora e autor; vazio = "Dados insuficientes", soma com abrigo aberto sem contagem = "soma parcial".
- RF-15, RF-16, RF-17: Ações com distrito, responsável, status e horário; em andamento pelos territórios mais
  vulneráveis; "Encerrar evento e lição aprendida" saiu (fora do escopo; dados preservados, campo obsoleto).
  Relatório executivo a partir do Boletim, com período, estágio oficial do COP, abrigos por distrito, ações e saúde.
- `/painel/situacao` e `/painel/acoes` removidas; o frontend não usa mais `/painel/` (fontes via `GET /fontes`).
- Ajustes da revisão: 3 abrigos à vista no painel do bairro, Mapa sem estouro a 375 px, "Territórios" no Simulador.

**Testes**: backend 1080 passed, ruff limpo; frontend lint, tsc, 218 testes e build verdes. Conferido com dados
reais, sem interceptar rotas: as cinco telas e o relatório a 1440 e 375 px, sem erro de JavaScript, sem resposta de
erro da API e sem rolagem horizontal.

**Pendências**
- `GET /painel/resumo` ainda existe no backend, sem uso no frontend: pode ser removida.
- O feed do COP está vazio hoje: "Abrigos abertos" é 0 pelo feed e desabrigados dependem do registro da equipe.
- Ações gravam `tipo: "outro"` porque a API ainda exige o campo; registros antigos "Boletim emitido: ..." aparecem em
  "Concluídas e canceladas".
- `docs/matriz-prd-codigo.md` e `docs/funcionalidades-equipe.md` ainda citam rotas do painel antigo.

## Fechamento da Onda 1 — revisões (06/11/2026)

**qa-ux**: nenhum P0. Fase 1: RF 20 atendidos e 9 parciais (Gate 0: 6 atendidos); RNF 8 atendidos, 3 parciais e 1 não
atendido (RNF-07, disponibilidade). E2E contra a API real 14/14 (escritas interceptadas). Backend 1080, frontend 218.
P1 abertos:
1. "Pessoas abrigadas 0" e "abrigos abertos 0" por ausência de registro (Situação, Relatório, Simulador): deve ser
   "Dados insuficientes" (RN-02) — backend-api e frontend-equipe.
2. A Saúde abre a janela de leptospirose pela declaração de teste "Crítico" do DS I (04/11), que foi retirada; a
   janela precisa ignorar declarações encerradas — backend-api.
3. `/boletim` leva mais de 5 s (RNF-06) — backend-api.
4. Estágio oficial do COP sempre "Dados insuficientes" até alguém informar (P-21).

**seguranca-lgpd**: nenhum crítico; os achados do Gate 0 foram corrigidos (vacinação fora dos bancos, papel da
aplicação sem posse nem DDL, somente-inclusão com gatilho, supressão, docs e health em produção, chaves FUNC_*,
login por IP, gitleaks, auditoria de leitura, prazo de guarda). Abertos:
- Alto: P-20 (a API ainda carrega a URL do dono para disparar o ETL, `api/routers/fontes.py:113`) e P-19 (senha do
  `neondb_owner` exposta numa sessão).
- Médio: `climasense_app` tem UPDATE/DELETE em `app.revisoes`, `app.tentativas_login` e `app.territorios` sem uso;
  a senha do arquivo cifrado da vacinação está em texto puro na mesma pasta do arquivo.
- Baixo: limite de tentativas por conta independente de IP; `SUPRESSAO_MINIMA` aceita 1; total em `/saude/bairros`
  com um só bairro suprimido; fixture do CNES com códigos reais de consultórios de pessoa física; entradas sem limite
  (`resultado` em `POST /cenarios`, corpo da requisição, datas do boletim, paginação, cache do `/health`); leitura
  das camadas de vulneráveis sem auditoria; texto livre sem checagem no servidor; 2 moderadas do react-router.
- Não rodou no Neon: `sincronizar-frescor` (limites em `app.fontes` divergem do TOML) e `limpar-retencao` (hoje não
  há o que apagar).

## Mudança de escopo de 06/11/2026

Pedido direto do dono do projeto, registrado no ADR 0016 (proposta; aprovação em D-13) e no `docs/PRD.md` v3.

**O que mudou**
- Sai tudo de abrigos: abrigos abertos, ocupação, pessoas abrigadas, desabrigados, capacidade, camada do mapa, ETL
  (`recife-abrigos`, cadastro e feed de ativos do COP), situação de abrigos e pressão nos abrigos do simulador. Código
  removido do backend e do frontend; `data/abrigos/` e o verbete do dicionário apagados. RF-08 removido; a parte de
  abrigos de RF-02, RF-07 e RF-13 saiu; P-02 encerrada.
- Migração 0019: apaga `app.abrigos`, `app.abrigo_atualizacoes` e a fonte `recife-abrigos`; tira a chave estrangeira
  de `app.acao_eventos` para permitir excluir a ação. Testada só no Postgres local (`test_migracao_0019.py`).
- RF-09: a Situação do evento mostra o estágio oficial do COP, a chuva (24 h medida e prevista) e o nível da maré.
- RF-15: ação na cidade, no distrito ou no bairro; `DELETE /acoes/{acao_id}` em qualquer situação, auditado como
  `acao_resposta_excluida` (sem descrição nem responsável); a linha do tempo fica guardada.
- RF-33, RF-34 (novos): `POST /cenarios/simular` devolve por distrito o bloco `arboviroses` (série semanal do
  município pelo InfoDengue; total anual de confirmados por distrito pela Prefeitura; zika "Dados insuficientes";
  classe baixa/média/alta em terços entre distritos, relativa e provisória) e `ordem_de_atencao_distritos` (estágio
  sugerido pela chuva simulada, depois arboviroses). Contexto, não previsão causal; selo "Experimental".
- Documentação: PRD v3, matriz, perguntas P-27 a P-31 e D-13 a D-15, avisos nas `specs/`, `apis-e-etl.md`,
  dicionário de dados, `funcionalidades-equipe.md`, `ESTRATEGIA-AGENTES.md`, notas nos ADRs 0010, 0014 e 0015 e nas
  pesquisas; `docs/api-gestao.md` regenerado por `scripts/gerar_mapa_api.py`.

**Pendências**
- **Para o dono:** aplicar a 0019 no Neon (antes, decidir se exporta os registros de abrigo) e depois rodar
  `sincronizar-frescor`; decidir o destino das coleções bronze `recife_abrigos` e `recife_abrigos_ativos` no Atlas,
  que ficam órfãs (P-31).
- `CLAUDE.md` ainda diz "próximo número: 0015" (o próximo livre é 0017) e `.claude/agents/backend-api.md` e
  `qa-ux.md` ainda citam abrigos (D-14, D-15).
- A tela do Simulador ainda não mostra as arboviroses nem a ordem de atenção (só a API devolve).
- Perguntas ao cliente: zika sem série (P-27), arboviroses por distrito só anuais (P-28), critério de classe e ordem
  de atenção (P-29), guarda do histórico de ação excluída (P-30).

## Ampliação de escopo e pesquisas de 06/11/2026

Pedido direto do dono do projeto: foco em funcionalidades novas, a partir de cinco dores do cliente e de cinco
pesquisas de fontes reais (só GET públicos, sem criar conta). Registrado no ADR 0017 (proposta; aprovação em D-16) e
no `docs/PRD.md` v4. Só documentação mudou; nenhum código, banco ou contrato de API.

**Pesquisas** (`docs/pesquisa/`)
- `api-hidrologia.md`: a API da APAC expõe nível de rios e reservatórios com limiares oficiais; o serviço legado da
  ANA responde sem token. Só uma estação de nível tem o Recife no cadastro (Capibaribe, São Lourenço da Mata, a
  montante). Não há estação de nível dentro da cidade, nem SACE do SGB para o Capibaribe, nem sensor de canal aberto.
- `api-meteorologia.md`: a chuva de 24 h e 72 h por estação já chega pelo `apac-chuva`; não há série horária histórica
  medida para o Recife; temperatura medida só com token do INMET; umidade do solo só como modelo (Open-Meteo, cujo
  plano gratuito é para uso não comercial).
- `api-territorial.md`: a suscetibilidade a deslizamento do SGB cobre os 94 bairros; os atendimentos da Defesa Civil
  trazem grau R1 a R4 (86 bairros com R3 ou R4); há camadas de alagamento de 2026; deficiência por bairro não existe;
  os atendimentos de 2025 e 2026 não estão no portal.
- `api-epidemiologia.md`: nenhuma fonte pública mostra casos de doença nos dias do evento; SAMU (mensal) e SISAGUA
  (cerca de 1 semana) são as mais rápidas, como demanda de urgência e qualidade da água; o resto só com convênio.
- `api-operacional.md`: estágio e comunicados do COP só por registro da equipe; Atlas Digital de Desastres para
  eventos antigos com danos; histórico de alertas só o que o ETL guardar.

**O que mudou**
- ADR 0017: entram RF-35 a RF-42, por fonte real; não entram raspagem de rede social, S2iD direto, EM-DAT, microdados
  individuais, base da Celpe com nome de cliente, CadÚnico individual e a API `/arboviroses` do Ministério da Saúde.
  Abrigos continuam fora: o texto do pedido citava abrigos, e o ADR 0016 prevalece.
- PRD v4: §5 (o histórico de eventos entra; lições aprendidas continuam fora), §7.8 (RF-35 a RF-42 com fase e tela),
  §9 (fontes novas com cadência real e o que não existe), RNF-03, §11, §12, §13 e §14. Nenhuma tela nova (D-17).
- Matriz: §2.1 com RF-35 a RF-42 (todos "em construção", veredito "adaptar") e o que cada um reaproveita; conflitos
  10 a 12 na §5.
- Perguntas P-32 a P-54 e decisões D-16 a D-21 em `docs/perguntas-abertas.md`; avisos das `specs/` atualizados.

**Pendências**
- **Para o dono:** aprovar o ADR 0017 e o PRD v4 (D-16), o encaixe nas cinco telas (D-17), a ordem de construção
  (D-18) e a regra para fontes sem termos (D-19).
- **Para o dono (LGPD):** o arquivo `cad.csv` (cerca de 72 MB, microdado do Cadastro Único) está na raiz do
  repositório, fora do Git mas sem regra no `.gitignore` (D-20).
- **Para o cliente:** licenças e termos (P-32 a P-34, P-46, P-51), acessos (P-35 a P-37), extratos de saúde (P-38 a
  P-40), regras do evento (P-43, P-44) e o aviso sobre a base da Celpe (P-45).
- `CLAUDE.md` deve dizer "próximo número: 0018" (D-21); sugestões para `.claude/agents/` no relatório do arquiteto.
- Nenhum conector novo foi escrito: `apac-rios`, `sgb-suscetibilidade`, `samu-recife`, `sisagua` e `atlas-desastres`
  ficam para o `etl-dados` depois da aprovação.
