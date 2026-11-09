# Fontes operacionais: comunicados, estágio do COP e histórico de eventos de chuva

Data da pesquisa: 2026-11-06. Chamadas reais, só GET públicos, sem autenticação. Complementa
`estagio-oficial-cop.md` (não repete os testes de lá), `dicionario-dados/alertas-oficiais.md`,
`dicionario-dados/recife-alagamento.md` e `apis-e-etl.md`. Abrigos estão fora do escopo (ADR 0016).
Nada foi implementado; é pesquisa para decisão (RF-19, RN-01, RN-13).

## Respostas curtas

1. **Comunicados e estágio do COP têm feed/API/RSS?** Não. Reconfirmado: nenhum serviço ArcGIS, CKAN ou RSS
   publica o estágio vigente nem os comunicados do COP/Defesa Civil do Recife. O estágio só existe como texto em
   notícia e rede social. O caminho continua sendo o **registro assistido da equipe** (fonte "Registro manual da
   equipe (COP)", hora, autor). Os avisos meteorológicos oficiais (APAC, INMET, Cemaden, IDAP) já têm API e já
   entram pelo `alertas-oficiais`; o que falta é **guardá-los como histórico** (o IDAP só mantém ~12 h).
2. **Base histórica de eventos de chuva do Recife?** Existem três camadas reais e complementares:
   - **Atlas Digital de Desastres (S2iD)**: eventos de gravidade municipal, com danos humanos e materiais (16 registros
     do Recife, 1991–2022). É a única fonte oficial de "dano" por evento.
   - **Atendimentos da Defesa Civil (CKAN)**: quase diário, por bairro, 2014–2024 (já na silver como
     alagamento/deslizamento). Dá a "extensão" do evento em bairros, não o dano.
   - **Chuva observada**: APAC diária por estação desde 2022 (já na gold) e ERA5 desde 2021. Dá a "intensidade".
   Não existe tabela pronta de "eventos" com início, fim, estágio e comunicados. Ela precisa ser **montada** por
   cruzamento (seção 3).
3. **Como estruturar sem inventar?** Evento = janela detectada por regra sobre dado medido, mais campos que só a
   equipe ou uma fonte oficial citada preenche. Cada campo leva fonte e hora; o que não tem fonte fica "Dados
   insuficientes". Detalhes na seção 3.

## 1. Fontes testadas

### 1.1 Atlas Digital de Desastres no Brasil (Sedec/MIDR + Ceped/UFSC): recomendada para danos

- **URL:** página `https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml`; CSV
  `https://atlasdigital.mdr.gov.br/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv` (também XLSX,
  manual PDF `/arquivos/Atlas_Digital_Desastres_Manual_Aplicacao.pdf` e log de correções `/arquivos/2026/2026.08-logs-correcoes.xlsx`).
- **Autenticação:** nenhuma. **Formato:** CSV `;`, ~74 MB, 70 colunas, 70.163 registros do país, **latin-1** (não UTF-8).
- **Frequência:** consolidação anual (versão de 06/08/2026 cobre até 2025). **Cobertura:** nacional, por município,
  1991–2025; os dados vêm do S2iD, informados pelo município (subnotificação possível).
- **Licença:** a página não declara. Dado oficial federal; tratar como atribuição obrigatória "Sedec/MIDR, Atlas
  Digital" e perguntar ao MIDR se precisar redistribuir (risco baixo para uso interno).
- **Campos úteis:** `Protocolo_S2iD`, `Data_Evento`, `Data_Registro`, `Cod_Cobrade`, `descricao_tipologia`, `Status`
  (Registro / Reconhecido), `DH_MORTOS`, `DH_FERIDOS`, `DH_DESABRIGADOS`, `DH_DESALOJADOS`, `DH_OUTROS AFETADOS`,
  `DM_total_danos_materiais`, `PEPL_total_publico`, `PEPR_total_privado`. Filtro: `Cod_IBGE_Mun = 2611606`.
- **Exemplo real (todos os 16 registros do Recife foram lidos; os de chuva):**

  | Data do evento | Tipologia | Status | Mortos | Desabrigados | Desalojados | Outros afetados | Danos materiais (R$) |
  |---|---|---|---|---|---|---|---|
  | 03/08/2000 | Enxurradas | Registro | 8 | 2.000 | 1.600 | 0 | 72.843.368,02 |
  | 02/06/2005 | Movimento de massa | Registro | 1 | 63 | 543 | 628 | 11.226.606,91 |
  | 20/04/2010 | Enxurradas | Registro | 6 | 200 | 0 | 0 | 0,00 |
  | 13/06/2012 | Alagamentos | Registro | 0 | 0 | 10 | 0 | 0,00 |
  | 29/05/2022 | Chuvas intensas | Reconhecido | 43 | 3.874 | 831 | 1.532.177 | 61.664.230,93 |

  Também há enxurradas em 1991, 1994, 1996, 1997, movimento de massa em 1997 e 2007, inundação em 2008 (e estiagem
  1999 e doenças infecciosas 2015, que não são chuva). Atenção: `0` no Atlas nem sempre é "zero medido"; o
  município pode não ter preenchido (ver Riscos).
- **Limite:** cobre só eventos que viraram registro/decreto. **Não traz o evento de abril/maio de 2026** (a
  consolidação vai até 2025). Não tem bairros nem horário. Granularidade de dia e município.
- **Esforço:** baixo (um download anual, filtro por IBGE, tabela `silver.eventos_oficiais` pequena). **Riscos:**
  encoding latin-1; colunas com caracteres quebrados; versionamento do nome do arquivo muda a cada consolidação
  (precisa descobrir o link na página); sem licença explícita; sem API.

### 1.2 S2iD (Sistema Integrado de Informações sobre Desastres): não usar como fonte direta

- **URL:** `https://s2id.mi.gov.br/` (relatórios em `https://s2id.mi.gov.br/paginas/relatorios/`). Responde 200.
- **Achado:** só há "Relatório Gerencial – Reconhecimentos Realizados/Vigentes" em tela JSF/PrimeFaces, sem API e sem
  CSV público; busca por conjunto no dados.gov.br não encontrou. Consultar exigiria raspar formulário JSF.
- **Decisão:** o Atlas (1.1) é a versão aberta dos mesmos registros. Não raspar o S2iD. Os reconhecimentos de 2026
  (decretos municipais/estadual de maio) só aparecem em portarias do Diário Oficial e notícias; vão para o
  registro manual, com a URL da portaria.

### 1.3 Atendimentos da Defesa Civil do Recife (Dados Abertos): já integrada; falta explorar para "evento"

- **URL:** CKAN `https://dados.recife.pe.gov.br/api/3/action/package_show?id=registro-de-atendimentos-da-defesa-civil`
  (um CSV por ano, 2014–2025; o portal republica recursos, fica o mais recente por `last_modified`; metadado do
  conjunto alterado em 19/10/2026).
- **Autenticação:** nenhuma. **Licença:** ODbL (`odc-odbl`). **Formato:** CSV `;`, ~890 mil linhas.
- **Cobertura útil para eventos:** 1.722 atendimentos de alagamento (16/01/2014 a 25/06/2024, 71 bairros, 461
  bairro-dias) e 3.266 de deslizamento (29 bairros). **2025 sem linhas de alagamento**, então o histórico termina em
  junho/2024 e **o evento de abril–maio de 2026 não está nele**.
- **Uso para o histórico de eventos:** agrupar dias consecutivos (ou com janela de tolerância) em "episódio" e listar
  bairros e contagem por dia. É dado real de resposta (atendimento), não de dano. Já existe
  `gold.alagamento_bairro_dia` e `gold.ocorrencias_bairro`.
- **Esforço:** baixo (reaproveitar). **Riscos:** data é a da solicitação/vistoria, pode vir dias depois; ausência de
  registro não prova ausência de alagamento (rótulo fraco já documentado).
- **Outros conjuntos do mesmo dataset-pai `defesa-civil` (mesma licença):** `efetivo-da-defesa-civil` (CSV 2023, só
  efetivo; não é "equipe mobilizada por evento"), áreas de risco regionais (já usadas). Não há conjunto de
  "equipes mobilizadas" nem "ações por evento". Busca CKAN por `comunicado` = 0; `chuva` só devolve o conjunto de
  abrigos (fora de escopo).

### 1.4 ArcGIS do Recife (esigportal2): mapas pós-evento de 2026, úteis como contexto, com ressalvas

- **URL base:** `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted/<serviço>/FeatureServer/0`
  (GET `.../query?where=1=1&outFields=*&f=json`, ou `f=geojson`). Sem autenticação nas camadas abaixo; o servidor aceita
  consultas públicas. `maxRecordCount` 2000.
- **Camadas de alagamento de 2026 (todas respondem 200):**

  | Serviço | Geometria | Registros | Campos relevantes | Observação |
  |---|---|---|---|---|
  | `Alaamentos_2026` | polígono | 218 | `nome`, `ano` | áreas alagadas 2026; `nome` vazio nos exemplos |
  | `Poligonos_Alagamentos_2026_5` | polígono | 78 | `comunidade`, `rpa`, `qtd_registros` | comunidades com contagem de registros (ex.: Comunidade Padre Henrique, RPA 4, 73) |
  | `Logradouros_Alagamentos_2026_V1` | linha | 552 | `nlgpavresu`, `indpav`, `ttrechosul` | ruas afetadas (ex.: Av. Professor Artur Coutinho) |
  | `Centroide_Logradouros_Alagamentos_2026_V1` | ponto | 1.177 | `endereco`, `bairro`, `cep` | **tem endereço e CEP; só agregar por bairro** |
  | `Lotes_Areas_Alagadas_2026_V1` / `Lotes_Alagamentos_2026` | polígono | 5.761 / 5.964 | tipo e uso do imóvel, `endnumero`, `nmendcomp` | **nível de lote com endereço; só contagem agregada por bairro** |
  | `pontos_alagamento_arcgis` | ponto | 54 | `bairro`, `logradouro`, `prioridade_emlurb`, `classe_risco` | cadastro de pontos críticos (EMLURB), maioria dos critérios nulos |
  | `Eventos_SESuite_Ponto` e variantes | ponto | 0 | só campos de edição | vazias |

  **Não usar:** `Base_Celpe_032026_Alagamento_2026_V1` (30.045 pontos com `nomecliente`, endereço e medidor de
  clientes da Celpe): dado pessoal, viola RN-13/RNF-03; não ler, não armazenar. `pontos_Ativações_Balanço` exige token
  (499) e trata de balanço de gestão, não de estágio.
- **Sem data de evento nas camadas** (só `ano` ou `ttrechosul` de atualização), então não dizem "quando alagou". Servem
  como "extensão territorial do evento de 2026" para o relatório, sem linha do tempo.
- **Licença:** não declarada nas camadas (`copyrightText` vazio). Fonte oficial da Prefeitura; confirmar com o cliente.
- **Esforço:** médio (agregar por bairro com interseção espacial). **Riscos:** serviços "Hosted" podem ser trocados ou
  removidos sem aviso (versões `_V1`, `_V2`, `_5`); dado de lote/endereço exige agregação antes de gravar.

### 1.5 APAC: avisos sim, comunicados institucionais não

- **URL:** `https://api.apac.pe.gov.br/api.php/alertas` (já usada). Lista ~14 avisos recentes (ids 112–119, nº
  `91/2026`), com `tipo`, `nivel_aviso`, `numero_aviso_meteorologico`, `data_envio`, `data_validade_aviso`,
  `regioes_afetadas`, `url_aviso`. Exemplo real: aviso `91/2026`, UMIDADE, VERMELHO, enviado 04/11/2026, válido até
  09/11/2026, Sertão e São Francisco (não Recife). `/boletins` e `/noticias` devolvem "Método não encontrado".
  `www.apac.pe.gov.br/rss`, `/feed` e `/avisos-meteorologicos` respondem 404.
- **Para histórico:** o endpoint só traz os avisos mais recentes (~14). Para saber "quais avisos valeram durante o
  evento" é preciso **guardar o que o ETL já coleta**. `silver.alertas_oficiais` já faz upsert com `primeira_vez_em` e
  `visto_em`; basta **parar de tratar como efêmero** e expor consulta histórica por janela.
- **Esforço:** baixo (consulta sobre tabela existente). **Risco:** o link `url_aviso` aponta para `dados.apac.pe.gov.br:41120`
  (porta não padrão, HTTP), instável. Guardar o texto e o hash.

### 1.6 Defesa Civil Alerta / IDAP (CAP), INMET, Cemaden

- Já documentados em `alertas-oficiais.md`. Complementos desta pesquisa:
  - O IDAP guarda ~12 h; **não há histórico público**. Só o que o ETL guardou existe.
  - Cemaden `https://painelalertas.cemaden.gov.br/wsAlertas2` devolve os alertas nacionais ativos (ex. 05/11/2026,
    Risco Hidrológico Moderado, RS). Sem arquivo histórico; é lista "ativa agora". `dadosabertos.cemaden.gov.br` não
    conectou (sem resposta) neste teste.
  - Defesa Civil Alerta (alerta por celular, cell broadcast, em operação no Recife desde 2025; cadastro por WhatsApp
    no canal nacional) é **canal de disparo**, não fonte consultável. Dados dos disparos não são públicos.
  - Não há registro de desastres em API pública do Cemaden nem do INMET (INMET `apitempo` segue sem token
    respondendo sem dados neste teste).
- **EM-DAT** (`https://www.emdat.be/`, UCLouvain/CRED): exige cadastro e aceite de termos (uso não comercial). Base
  internacional só de desastres grandes, que o Atlas já cobre melhor para o Recife. **Não recomendada** (não testado
  além da página inicial, 200).

### 1.7 Comunicados e estágio do COP: só texto em notícia e rede social

- **Portais testados:** `https://cop.recife.pe.gov.br/` redireciona para `https://esigportal2.recife.pe.gov.br/portal/home/`
  (portal ArcGIS genérico, sem estágio). `www.recife.pe.gov.br/rss` 404. `www2.recife.pe.gov.br` sem resposta (falha
  de conexão), então não há RSS verificável. O CKAN não tem conjunto de comunicados.
- **Redes sociais oficiais:** não foi possível confirmar o usuário oficial do COP nem de Telegram da Defesa Civil do
  Recife (a busca não retornou perfil confirmado). Telefones públicos: Defesa Civil do Recife 0800 081 3400
  (24 h), 199 (Defesa Civil), 193 (Bombeiros). Raspagem de Instagram/X violaria termos das plataformas e é frágil;
  **não propor**.
- **Imprensa como evidência (não como fonte do sistema):** os estágios aparecem datados e com hora em notícias
  (Folha de Pernambuco, Diario de Pernambuco). Exemplo real da Folha PE, 01/05/2026: às 8h "estágio de atenção", às
  10h elevado a "alerta", 111,3 mm em 12 h (APAC, 10h24), 28 pessoas ilhadas resgatadas pelo CBMPE em Cajueiro,
  aviso vermelho APAC para a RMR até 02/05, e a nota "estágio pode ser atualizado a qualquer momento". Outra
  matéria do Diario de Pernambuco no mesmo dia titula "alerta máximo". As matérias citam de 4 a 5 níveis (Mobilização,
  Atenção, Alerta, Alerta Máximo), e **não concordam entre si** sobre o número. Servem como referência para a
  equipe conferir ao registrar, não para ingestão automática: texto livre, datas de cabeçalho incoerentes
  (republicação), números que mudam durante o dia (óbitos entre 4 e 6 conforme o critério de contagem).
- **Conclusão:** registro assistido. Guardar `url` da notícia/postagem como evidência opcional digitada pela equipe.

## 2. Ranking e adequação

| Fonte | Responde | Real e aberta | Esforço | Risco |
|---|---|---|---|---|
| Atlas Digital (CSV) | dano por evento grave (mortos, desabrigados, R$) | sim | baixo | licença não explícita; subnotificação |
| Atendimentos Defesa Civil (CKAN, já integrado) | extensão por bairro e dia | sim (ODbL) | baixo | termina em 06/2024; rótulo fraco |
| APAC/INMET/Cemaden/IDAP (já integrado) | avisos vigentes e, a partir de agora, histórico | sim | baixo | só vale a partir do início da coleta |
| APAC chuva diária + ERA5 (já integrado) | intensidade e duração da chuva | sim | nulo | estação com falha marcada |
| ArcGIS alagamento 2026 (agregar por bairro) | extensão territorial do evento 2026 | sim, licença a confirmar | médio | camada pode mudar; LGPD em lote/endereço |
| Registro manual da equipe | estágio do COP, ações, equipes, situação final, comunicados | sim, é da equipe | médio (tela) | depende de disciplina |
| S2iD direto, EM-DAT, redes sociais | — | restrito/raspagem | alto | termos, fragilidade |

## 3. Como estruturar o histórico de eventos sem inventar

**Princípio:** o sistema só escreve o que veio de medição ou de fonte oficial citada. Todo o resto é registro da
equipe, com autor e hora (RN-05, RF-19). Campo sem fonte mostra "Dados insuficientes" e qual fonte falta (RN-01).
Zero medido difere de ausente (RN-02).

**Entidade `evento_chuva`** (sugestão para um ADR 0015, ainda sem decisão do arquiteto):

| Campo | Origem | Regra |
|---|---|---|
| `id`, `nome` | sistema | nome automático "Evento de 01/05/2026"; equipe pode renomear |
| `inicio`, `fim` | **sistema, regra sobre chuva medida** | início quando o acumulado medido cruza limiar; fim após período sem chuva significativa. Limiar e janela precisam de decisão do cliente (P-xx). Antes do ETL: `inicio`/`fim` ficam vazios |
| `chuva_pico` | APAC (`gold.chuva_apac_*`) | máx. 1 h/12 h/24 h/72 h por distrito e bairro, com fonte e hora; estação falha fica fora (RN-07) |
| `avisos_oficiais` | `silver.alertas_oficiais` | lista de avisos vigentes na janela (origem, nível, `primeira_vez_em`, `expira_em`, link) |
| `estagios` | **registro manual** | linha do tempo de mudanças (estágio, hora, autor, evidência opcional). Sem registro: "Dados insuficientes" |
| `distritos_bairros_afetados` | atendimentos CKAN (até 06/2024) e, para 2026, camadas ArcGIS agregadas por bairro | separar "com atendimento registrado" de "com mancha mapeada"; não inferir bairro sem fonte |
| `acoes` | tela de Ações da equipe (existente) | cada ação com autor e hora; sem ação registrada não é "nenhuma ação" |
| `equipes_mobilizadas` | registro manual | só número agregado e função; nada que identifique pessoa (RN-13) |
| `consequencias` | Atlas/S2iD (oficial, com protocolo) ou registro manual com a fonte (ex.: boletim da Defesa Civil estadual) | mortos, desabrigados, desalojados, afetados, danos; guardar `fonte`, `consolidado_em` e se há divergência entre fontes |
| `situacao_final` | registro manual, aprovado por segunda pessoa (RN-05) | "encerrado", hora e responsável |
| `comunicados` | registro manual: título, órgão, data/hora, URL ou anexo | texto copiado pela equipe, com origem; nunca texto gerado |

**Eventos históricos (pré-sistema):** carregar como eventos "retrospectivos" com `origem_dado = oficial_historico`:
- grave (com dano): linhas do Atlas do Recife (protocolo S2iD como `codigo_fonte`), com data de evento e danos;
  sem estágio, sem comunicados, sem linha do tempo horária (mostrar "não disponível nesta fonte");
- por episódio: agrupar atendimentos CKAN por janela de dias para dar bairros e volume;
- chuva: cruzar com APAC diária (desde 2022) ou ERA5 (desde 2021); eventos anteriores a 2021 ficam sem chuva medida.

**Comparação entre eventos:** só comparar o que existe nos dois eventos; para o resto exibir "sem dado" em vez de
zero. Mostrar uma coluna por evento e uma linha por indicador, cada célula com fonte e hora.

**Relatório executivo:** gerado só com os campos acima; linha do tempo = união ordenada por hora de (avisos
oficiais com `primeira_vez_em`, mudanças de estágio registradas, ações registradas, comunicados registrados).
Cada item da linha do tempo mostra sua fonte. Nenhum texto narrativo inventado; frases fixas de gabarito apenas.

**Lacunas assumidas:** o evento de abril–maio de 2026 (1 a 4 de maio) não está no CKAN (termina em 06/2024) nem no
Atlas (até 2025). Para ele, só existem: chuva APAC/ERA5 (se carregadas), avisos que a coleta pegou desde que
estiver rodando (verificar `silver.alertas_oficiais`), camadas ArcGIS 2026 e o que a equipe registrar. Não preencher
com números de reportagem sem a equipe registrar a fonte (números de óbitos e desabrigados variam entre
fontes: por exemplo, 4 a 6 óbitos no estado e 671 desabrigados no Recife em atualização de 2 de maio).

## 4. Recomendação priorizada

1. **Agora, esforço baixo (entra em RF de histórico):** habilitar leitura histórica de `silver.alertas_oficiais`
   por janela. É o único jeito de ter "avisos durante o evento"; quanto antes a coleta de 10–15 min estiver agendada,
   mais histórico existe. Confirmar que o agendamento está ativo em produção.
2. **Conector `atlas-desastres`:** CSV anual, filtro `2611606`, latin-1, tabela `silver.eventos_oficiais`
   (protocolo, data, tipologia, status, danos). Cobre os 16 registros e os graves de 2000, 2005, 2010 e 2022 para
   comparação. Atualização manual ou anual (nome do arquivo muda).
3. **Registro assistido de evento:** tela simples para a equipe registrar estágio do COP (hora, estágio, evidência
   opcional), comunicados (órgão, texto, URL), equipes (número agregado), consequências (com fonte) e situação final.
   Reusa a lógica de estágio manual já pesquisada em `estagio-oficial-cop.md`. Segunda pessoa aprova a situação final.
4. **Episódios a partir dos atendimentos CKAN e da chuva APAC:** montar eventos retrospectivos (2014–2024) com
   bairros e intensidade, marcando que não têm dano nem estágio.
5. **Camadas ArcGIS de 2026 agregadas por bairro**, só para o evento de maio de 2026 e só após o cliente confirmar
   licença e fonte (quem produziu a mancha, em que data). Nunca gravar lote, endereço ou dado da Celpe.
6. **Não fazer:** raspar S2iD, redes sociais, portais institucionais sem RSS; usar EM-DAT; ingerir notícia como dado.

## 5. Perguntas ao cliente (registrar em `docs/perguntas-abertas.md`)

1. O COP/Defesa Civil mantém, internamente, um registro dos estágios de abril–maio de 2026 e de eventos anteriores
   (nome do estágio, hora de início e fim)? Podem enviar uma planilha para carga retrospectiva, com fonte?
2. Quantos e quais são os estágios oficiais do COP hoje (a imprensa cita 4 ou 5 níveis, e há divergência: Mobilização,
   Atenção, Alerta, Alerta Máximo)? Qual documento define os critérios (Plano de Contingência, versão e data)?
3. O que define "início" e "fim" de um evento para a equipe: estágio do COP, limiar de chuva (qual), ou decisão da
   chefia? Aceitam que o sistema sugira e a equipe confirme?
4. Quem registra comunicados, estágios, equipes e consequências durante o evento, em qual horário, e quem aprova o
   encerramento (RN-05)?
5. As camadas ArcGIS de alagamento de 2026 (`Poligonos_Alagamentos_2026_5`, `Logradouros_Alagamentos_2026_V1` etc.)
   são da Prefeitura e podem ser usadas no relatório? Qual a data e o método de levantamento? A base Celpe
   (com nome de cliente) foi compartilhada indevidamente? Sugerir ao cliente tratar como dado pessoal.
6. Há fonte oficial dos balanços de consequências do Recife (Defesa Civil municipal, SEPDEC estadual) que possamos
   citar com link e hora, já que os números variam entre notícias?
7. O atendimento da Defesa Civil de 2025 em diante será publicado no CKAN (2025 vem sem alagamento e o histórico
   termina em 06/2024)? Existe extração interna que o Vigidesastres possa compartilhar, agregada por bairro e dia?
8. Qual a política de uso e licença que a Sedec/MIDR aplica ao Atlas Digital para redistribuição em painel interno
   e em relatório?
9. Existe canal fixo oficial (e-mail, grupo) em que o COP envia comunicados e mudança de estágio, para a equipe
   registrar a partir dele?

## Fontes consultadas

- Atlas Digital: `https://atlasdigital.mdr.gov.br/` e `/paginas/downloads.xhtml`, CSV 1991–2025 (baixado e filtrado por IBGE 2611606).
- CKAN Recife: `registro-de-atendimentos-da-defesa-civil`, `defesa-civil`, `efetivo-da-defesa-civil`.
- ArcGIS Recife: pasta `Hosted` (camadas listadas na seção 1.4).
- APAC `api.apac.pe.gov.br/api.php/alertas`; Cemaden `painelalertas.cemaden.gov.br/wsAlertas2`.
- Imprensa (apenas contexto, não ingestão): Folha de Pernambuco, matéria "COP renova estágio de alerta no Recife;
  volume supera 100 mm nas últimas 12 horas" (01/05/2026); Diario de Pernambuco, matérias de maio de 2026 sobre os
  estágios; agregadores de Defesa Civil sobre os balanços de 2 a 5 de maio de 2026.
