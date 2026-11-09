# Funcionalidades da área da equipe, o problema do cliente e a origem dos dados

Escrito em 05/11/2026 a partir do código e dos bancos em uso. Serve de ponte entre a entrevista com o
Vigidesastres (23/10/2026) e o que o sistema entrega hoje. Onde algo **não** está pronto, o texto diz.

> **Mudança de escopo de 06/11/2026 (PRD v3, ADR 0016):** abrigos saíram do produto (tela, rotas, ETL e tabelas).
> O foco passa a ser chuva, maré, o cenário em que as áreas são mais afetadas e, com o aumento das chuvas, qual
> distrito é mais impactado e com quais arboviroses. As ações podem ser excluídas e registradas por cidade, distrito
> ou bairro. O menu atual tem as cinco telas do PRD (ver `docs/progresso-onda-1.md`, Etapa 5); as linhas abaixo
> descrevem as funcionalidades, não o menu.

## 1. As dores do cliente (entrevista com a equipe do Vigidesastres)

| # | Dor, nas palavras do cliente |
|---|---|
| D1 | O COP declara estágio para a **cidade inteira**; a equipe precisa saber o impacto **por bairro**. |
| D2 | A mudança de estágio vai para os distritos **à mão, por grupos de WhatsApp**. |
| D3 | **Não dá para acompanhar as ações** feitas em campo durante o evento; as lições aprendidas ficam em planilha. |
| D4 | No pico, as primeiras métricas são **abrigos abertos e desabrigados**, e hoje não estão integradas. (Fora do escopo desde 06/11/2026; o dono do projeto reorientou para chuva, maré, cenário e arboviroses, ADR 0016.) |
| D7 | Com o aumento das chuvas, saber **qual distrito é mais impactado e com quais arboviroses** (dengue, chikungunya, zika). (Pedido de 06/11/2026.) |
| D5 | Desconfiança de alerta automático (localização errada): conferem **à mão na APAC e no Cemaden**. |
| D6 | **Segurança de dados e integração** são o critério de adoção (uma falha de PHP já deixou todos sem acesso). |

Preferência declarada: alerta não confirmado é melhor que evento não avisado.

## 2. Funcionalidades da equipe

Menu: Painel · Estágios · Abrigos · Ações · Boletim · Territórios · Comunicados · Análise (Cenários, Séries,
Avaliações, Fontes) · Administração. Papéis: analista (consulta e edita), revisor (+ revisa), coordenação (+ publica
e ajusta limiares) e administrador (tudo).

| Funcionalidade | O que faz | Dor | Dados e API |
|---|---|---|---|
| **Situação do evento** (antigo Painel) | Estágio oficial da cidade dado pelo COP, chuva medida em 24 h, chuva prevista em 24 h e nível da maré, cada número com fonte e hora; atualiza sozinha. | D1 | Rotas `/estagios/oficial`, `/boletim`. Fontes: registro da equipe (estágio do COP), APAC (chuva medida), Open-Meteo (previsão e maré). O painel antigo (`/painel/situacao`, `/painel/acoes`) saiu na Onda 1. |
| **Estágios** | Sugere o estágio por distrito (e por bairro, herdando a chuva do distrito) a partir de limiares; a equipe **declara** com justificativa, **retira** a declaração, vê o histórico, ajusta os limiares (coordenação) e gera a mensagem pronta de WhatsApp. Nunca muda o estágio sozinho. | D1, D2, D5 | Rotas `/estagios`, `/estagios/historico`, `/estagios/parametros`, `/estagios/mensagem`. Chuva medida: `api.apac.pe.gov.br/api.php/precipitacao_acumulada` (19 pluviômetros do Recife, APAC e Cemaden). Chuva prevista: `api.open-meteo.com/v1/forecast`. Maré: `marine-api.open-meteo.com/v1/marine`. Ocorrências de alagamento: Dados Abertos do Recife, `registro-de-atendimentos-da-defesa-civil`. Alertas oficiais: APAC `/alertas`, INMET `apiprevmet3.inmet.gov.br/avisos/ativos`, Cemaden `painelalertas.cemaden.gov.br/wsAlertas2`, IDAP `idapfile.mdr.gov.br/idap/api/rss/cap`. |
| ~~**Abrigos**~~ | **Removida em 06/11/2026** (ADR 0016): lista de locais, abertos, ocupação e desabrigados, cadastro e histórico, rota `/abrigos`, conector `recife-abrigos` e feed de abrigos ativos do COP. | — | — |
| **Ações** | Registra ação de resposta na cidade toda, num distrito ou num bairro (responsável, situação, horários), com linha do tempo; **excluir** em qualquer situação, com confirmação. A exclusão é auditada (quem, quando, território, tipo e situação) e a linha do tempo fica guardada. “Lição aprendida” saiu da tela na Onda 1. | D3 | Rotas `/acoes`, `DELETE /acoes/{acao_id}`. Dado: registro da equipe (sem fonte externa). |
| **Boletim** (Relatório executivo) | Página de uma folha, imprimível em PDF, e resumo em texto para WhatsApp: estágio por distrito, chuva, maré, ações em andamento e fontes com hora. | D2, D3 | Rotas `/boletim`, `/boletim/texto`. Compõe os dados das funcionalidades acima. |
| **Arboviroses no simulador** | Para cada distrito, dengue, chikungunya e zika como **contexto** do cenário: série semanal recente do município, total anual de confirmados do distrito e classe relativa (baixa, média, alta); ordem de atenção dos distritos pela chuva simulada e, no empate, pelas arboviroses. Zika: "Dados insuficientes". Selo "Experimental"; não é previsão de casos. | D1, D7 | `POST /cenarios/simular` (`arboviroses`, `ordem_de_atencao_distritos`). InfoDengue (semanal, município) e Dados Abertos do Recife `casos-de-dengue-zika-e-chikungunya` (anual, por bairro, somado por distrito). A tela do Simulador ainda não mostra o bloco (06/11/2026). |
| **Saúde depois da chuva** | Janela de vigilância de leptospirose (30 dias após estágio Alerta/Crítico, alagamento registrado ou chuva medida acima do limiar de Alerta), série semanal de dengue, chikungunya e leptospirose no Recife com a chuva ao lado e as semanas incompletas marcadas, nível de alerta do InfoDengue, retrato anual de dengue e chikungunya por bairro e "onde já aconteceu" (alagamento e deslizamento por bairro). Só contagens: nenhum dado pessoal. | D1, D3 | Rotas `/saude/resumo`, `/saude/semanal`, `/saude/bairros`, `/ocorrencias/historico` (contrato em `specs/foco-chuvas.md` §9). InfoDengue `info.dengue.mat.br/api/alertcity` (geocode 2611606); SINAN `ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/{FINAIS,PRELIM}/LEPTBR*.dbc`; Dados Abertos do Recife `casos-de-dengue-zika-e-chikungunya` e `registro-de-atendimentos-da-defesa-civil`; chuva semanal da reanálise ERA5. |
| **Territórios** | Mapa dos 8 distritos e 94 bairros, colorido por estágio, com cartão do território e faixas dos rios. | D1 | Rotas `/territorios`, `/territorios/distritos.geojson`, `/territorios/hidrografia.geojson`, `/territorios/indicadores`. Arquivos oficiais do Recife (distritos sanitários, bairros, faixas hídricas) em `data/territorio`, carregados no Atlas. |
| **Comunicados** | Rascunho, **revisão por outra pessoa**, aprovação e publicação pela coordenação; o publicado aparece na landing com o que fazer e até quando vale. Prévia idêntica à da landing. | D2, D5 | Rotas `/comunicados`; público em `/publico/avisos`. Dado: texto da equipe (regra: ninguém aprova o próprio conteúdo). |
| **Avaliações** | Avaliação do território com evidências (mapa, série, cenário ou fonte, cada uma com data de captura), revisada por outra pessoa. Base para os comunicados. | D1, D5 | Rotas `/avaliacoes`. Evidências apontam para fontes cadastradas em `/fontes`. |
| **Cenários** | “E se chover X”: previsão de chuva e maré por distrito e um estimador de referência **experimental** (não é probabilidade de alagar). | D1 | Rota `/cenarios`. Open-Meteo (previsão e maré) e ocorrências da Defesa Civil. |
| **Séries** | Chuva histórica por distrito, sazonalidade e lacunas visíveis (falta de dado nunca vira zero). | D1, D3 | Rotas `/series`. Open-Meteo Archive (reanálise ERA5), `archive-api.open-meteo.com/v1/archive`, desde 2021. |
| **Fontes** | Status de cada fonte (última carga, atrasada ou em dia) e histórico das cargas. | D5, D6 | Rotas `/fontes`, `/etl/execucoes`. Tabela `app.fontes`. |
| **Administração** | Contas e papéis, auditoria das ações, limites e execução das cargas de dados. | D6 | Rotas `/admin/usuarios`, `/admin/auditoria`, `/admin/fontes`. |
| **Segurança (transversal)** | Login com bloqueio de 15 min após 5 falhas, troca de senha obrigatória no primeiro acesso, sessão com expiração por inatividade, proteção CSRF, e histórico de estágios, eventos das ações e auditoria **somente de inclusão** (nada é alterado nem apagado). A ação em si pode ser excluída (06/11/2026); o histórico dela fica. | D6 | Rotas `/auth/*`. Tabelas `app.usuarios`, `app.sessoes`, `app.auditoria`. |

## 3. Como o conjunto responde à dor

- **D1 (cidade × bairro):** sugestão por distrito e por bairro, com a chuva medida nos pluviômetros dentro dos
  bairros; o bairro **herda a chuva do distrito** quando não há estação, e a tela diz isso (não finge precisão).
- **D2 (WhatsApp manual):** mensagem de mudança de estágio e boletim já escritos, prontos para copiar ou abrir no
  WhatsApp. Nada é enviado sozinho.
- **D3 (ações em campo):** registro com situação e linha do tempo, e “lição aprendida” que substitui a planilha.
- **D4 (abrigos e desabrigados):** fora do escopo desde 06/11/2026 (ADR 0016).
- **D7 (distrito mais impactado e arboviroses):** o simulador ordena os distritos pela chuva simulada e mostra as
  arboviroses de cada um como contexto, com a fonte e o ano; sem série, "Dados insuficientes".
- **D5 (confiança no alerta):** toda sugestão mostra fonte e hora, com o lembrete de conferir APAC e Cemaden; alertas
  oficiais entram filtrados para o Recife (código IBGE, polígono ou mesorregião), o que evita o caso do alerta de
  outra cidade.
- **D6 (segurança):** ver a linha “Segurança” acima.

## 4. O que ainda não existe ou depende de terceiros

- **Saúde por bairro em tempo útil:** leptospirose e arboviroses semanais só existem por **município** nas fontes
  públicas (SINAN com ~2 semanas de atraso; InfoDengue com ~1 semana); por bairro só há o retrato anual de dengue e
  chikungunya (2026 ainda não publicado). O caminho continua sendo o extrato agregado do SINAN local da Vigilância.
- **Animais peçonhentos e diarreias (MDDA):** não carregados (peçonhentos sem relação clara com a chuva; MDDA sem
  download público).
- **Telas de saúde:** as rotas existem (05/11/2026); a interface é do frontend.
- **Camadas de pessoas com deficiência e população vulnerável:** o Censo 2022 não traz deficiência por bairro.
- **Estágio com chuva própria por bairro:** a previsão é por distrito; a APAC dá medida por estação.
- **Arboviroses semanais por distrito e zika:** por distrito só há o total anual; zika não tem série integrada
  (P-27, P-28).
- **Modelo de risco de alagamento (ML):** desligado. Na validação não superou um limiar simples de chuva, e o rótulo
  disponível (vistorias da Defesa Civil) é fraco. Ver `docs/ml/risco-alagamento.md`.
- **Envio automático por WhatsApp:** fora do escopo; a equipe copia e envia.
- **Limiares dos estágios e nomes dos níveis:** são proposta, ainda sem validação com a Vigilância e a Defesa Civil.
- **Telefone 0800 081 3400 e WhatsApp da Defesa Civil** na landing: confirmados na página da Prefeitura e em
  jornais; vale a Defesa Civil confirmar antes de publicar.
