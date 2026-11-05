# Funcionalidades da área da equipe, o problema do cliente e a origem dos dados

Escrito em 05/11/2026 a partir do código e dos bancos em uso. Serve de ponte entre a entrevista com o
Vigidesastres (23/10/2026) e o que o sistema entrega hoje. Onde algo **não** está pronto, o texto diz.

## 1. As dores do cliente (entrevista com a equipe do Vigidesastres)

| # | Dor, nas palavras do cliente |
|---|---|
| D1 | O COP declara estágio para a **cidade inteira**; a equipe precisa saber o impacto **por bairro**. |
| D2 | A mudança de estágio vai para os distritos **à mão, por grupos de WhatsApp**. |
| D3 | **Não dá para acompanhar as ações** feitas em campo durante o evento; as lições aprendidas ficam em planilha. |
| D4 | No pico, as primeiras métricas são **abrigos abertos e desabrigados**, e hoje não estão integradas. |
| D5 | Desconfiança de alerta automático (localização errada): conferem **à mão na APAC e no Cemaden**. |
| D6 | **Segurança de dados e integração** são o critério de adoção (uma falha de PHP já deixou todos sem acesso). |

Preferência declarada: alerta não confirmado é melhor que evento não avisado.

## 2. Funcionalidades da equipe

Menu: Painel · Estágios · Abrigos · Ações · Boletim · Territórios · Comunicados · Análise (Cenários, Séries,
Avaliações, Fontes) · Administração. Papéis: analista (consulta e edita), revisor (+ revisa), coordenação (+ publica
e ajusta limiares) e administrador (tudo).

| Funcionalidade | O que faz | Dor | Dados e API |
|---|---|---|---|
| **Painel** | Primeira tela: estágio declarado por distrito, chuva prevista em 24 h, maré alta, abrigos abertos e desabrigados, “Onde agir”, ações em andamento e pendências (revisões, avisos vencendo, fontes atrasadas). | D1, D3, D4 | Rotas `/painel/resumo`, `/painel/situacao`, `/painel/acoes`, `/estagios`, `/abrigos`, `/acoes`. Fontes: Open-Meteo (previsão e maré), APAC (chuva medida), registros da equipe. |
| **Estágios** | Sugere o estágio por distrito (e por bairro, herdando a chuva do distrito) a partir de limiares; a equipe **declara** com justificativa, **retira** a declaração, vê o histórico, ajusta os limiares (coordenação) e gera a mensagem pronta de WhatsApp. Nunca muda o estágio sozinho. | D1, D2, D5 | Rotas `/estagios`, `/estagios/historico`, `/estagios/parametros`, `/estagios/mensagem`. Chuva medida: `api.apac.pe.gov.br/api.php/precipitacao_acumulada` (19 pluviômetros do Recife, APAC e Cemaden). Chuva prevista: `api.open-meteo.com/v1/forecast`. Maré: `marine-api.open-meteo.com/v1/marine`. Ocorrências de alagamento: Dados Abertos do Recife, `registro-de-atendimentos-da-defesa-civil`. Alertas oficiais: APAC `/alertas`, INMET `apiprevmet3.inmet.gov.br/avisos/ativos`, Cemaden `painelalertas.cemaden.gov.br/wsAlertas2`, IDAP `idapfile.mdr.gov.br/idap/api/rss/cap`. |
| **Abrigos** | Lista de 199 locais com situação (aberto, fechado, **sem informação**), pessoas abrigadas e desabrigados atendidos; atualização rápida, cadastro e histórico de cada alteração. | D4 | Rota `/abrigos`. Locais: Dados Abertos do Recife (`abrigos-temporarios-disponiveis`), camada ArcGIS ABRIGOS_2023 da Prefeitura, Censo SUAS (CRAS) e Plano de Contingência 2026 (arquivo curado `data/abrigos/`). **Abertos agora:** feed do COP, `esigportal2.recife.pe.gov.br/arcgis/rest/services/COP/Abrigos_Ativos/FeatureServer/0`. **Ocupação e desabrigados: não existe API**, é registro da equipe. |
| **Ações** | Registra ação de resposta por território (tipo, responsável, situação, horários), linha do tempo e “lição aprendida” ao concluir. | D3 | Rota `/acoes`. Dado: registro da equipe (sem fonte externa). |
| **Boletim** | Página de uma folha, imprimível em PDF, e resumo em texto para WhatsApp: estágio por distrito, chuva, maré, abrigos, ações em andamento e fontes com hora. | D2, D3, D4 | Rotas `/boletim`, `/boletim/texto`. Compõe os dados das funcionalidades acima. |
| **Saúde depois da chuva** | Janela de vigilância de leptospirose (30 dias após estágio Alerta/Crítico, alagamento registrado ou chuva medida acima do limiar de Alerta), série semanal de dengue, chikungunya e leptospirose no Recife com a chuva ao lado e as semanas incompletas marcadas, nível de alerta do InfoDengue, retrato anual de dengue e chikungunya por bairro e "onde já aconteceu" (alagamento e deslizamento por bairro). Só contagens: nenhum dado pessoal. | D1, D3 | Rotas `/saude/resumo`, `/saude/semanal`, `/saude/bairros`, `/ocorrencias/historico` (contrato em `specs/foco-chuvas.md` §9). InfoDengue `info.dengue.mat.br/api/alertcity` (geocode 2611606); SINAN `ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/{FINAIS,PRELIM}/LEPTBR*.dbc`; Dados Abertos do Recife `casos-de-dengue-zika-e-chikungunya` e `registro-de-atendimentos-da-defesa-civil`; chuva semanal da reanálise ERA5. |
| **Territórios** | Mapa dos 8 distritos e 94 bairros, colorido por estágio, com cartão do território e faixas dos rios. | D1 | Rotas `/territorios`, `/territorios/distritos.geojson`, `/territorios/hidrografia.geojson`, `/territorios/indicadores`. Arquivos oficiais do Recife (distritos sanitários, bairros, faixas hídricas) em `data/territorio`, carregados no Atlas. |
| **Comunicados** | Rascunho, **revisão por outra pessoa**, aprovação e publicação pela coordenação; o publicado aparece na landing com o que fazer e até quando vale. Prévia idêntica à da landing. | D2, D5 | Rotas `/comunicados`; público em `/publico/avisos`. Dado: texto da equipe (regra: ninguém aprova o próprio conteúdo). |
| **Avaliações** | Avaliação do território com evidências (mapa, série, cenário ou fonte, cada uma com data de captura), revisada por outra pessoa. Base para os comunicados. | D1, D5 | Rotas `/avaliacoes`. Evidências apontam para fontes cadastradas em `/fontes`. |
| **Cenários** | “E se chover X”: previsão de chuva e maré por distrito e um estimador de referência **experimental** (não é probabilidade de alagar). | D1 | Rota `/cenarios`. Open-Meteo (previsão e maré) e ocorrências da Defesa Civil. |
| **Séries** | Chuva histórica por distrito, sazonalidade e lacunas visíveis (falta de dado nunca vira zero). | D1, D3 | Rotas `/series`. Open-Meteo Archive (reanálise ERA5), `archive-api.open-meteo.com/v1/archive`, desde 2021. |
| **Fontes** | Status de cada fonte (última carga, atrasada ou em dia) e histórico das cargas. | D5, D6 | Rotas `/fontes`, `/etl/execucoes`. Tabela `app.fontes`. |
| **Administração** | Contas e papéis, auditoria das ações, limites e execução das cargas de dados. | D6 | Rotas `/admin/usuarios`, `/admin/auditoria`, `/admin/fontes`. |
| **Segurança (transversal)** | Login com bloqueio de 15 min após 5 falhas, troca de senha obrigatória no primeiro acesso, sessão com expiração por inatividade, proteção CSRF, e histórico de estágios, abrigos, ações e auditoria **somente de inclusão** (nada é alterado nem apagado). | D6 | Rotas `/auth/*`. Tabelas `app.usuarios`, `app.sessoes`, `app.auditoria`. |

## 3. Como o conjunto responde à dor

- **D1 (cidade × bairro):** sugestão por distrito e por bairro, com a chuva medida nos pluviômetros dentro dos
  bairros; o bairro **herda a chuva do distrito** quando não há estação, e a tela diz isso (não finge precisão).
- **D2 (WhatsApp manual):** mensagem de mudança de estágio e boletim já escritos, prontos para copiar ou abrir no
  WhatsApp. Nada é enviado sozinho.
- **D3 (ações em campo):** registro com situação e linha do tempo, e “lição aprendida” que substitui a planilha.
- **D4 (abrigos e desabrigados):** os dois números abrem o painel; locais e abertos agora vêm de fontes públicas.
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
- **Ocupação de abrigos e desabrigados em tempo real:** não há API pública; depende do registro da equipe ou de um
  acordo com a SEDEC e a Assistência Social.
- **Modelo de risco de alagamento (ML):** desligado. Na validação não superou um limiar simples de chuva, e o rótulo
  disponível (vistorias da Defesa Civil) é fraco. Ver `docs/ml/risco-alagamento.md`.
- **Envio automático por WhatsApp:** fora do escopo; a equipe copia e envia.
- **Limiares dos estágios e nomes dos níveis:** são proposta, ainda sem validação com a Vigilância e a Defesa Civil.
- **Telefone 0800 081 3400 e WhatsApp da Defesa Civil** na landing: confirmados na página da Prefeitura e em
  jornais; vale a Defesa Civil confirmar antes de publicar.
