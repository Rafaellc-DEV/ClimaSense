# ADR 0017 — Ampliação de escopo: hidrologia, território, saúde durante o evento e histórico de eventos

- **Situação:** proposta (pedido do dono do projeto em 06/11/2026; aguarda a aprovação registrada em D-16 e a
  validação com o cliente)
- **Data:** 06/11/2026
- **Base:** `docs/PRD.md` v4 (RF-35 a RF-42); RN-01, RN-02, RN-05, RN-06, RN-11, RN-13; RF-19; ADR 0008, 0010, 0015
  e 0016; pesquisas de 06/11/2026 em `docs/pesquisa/api-hidrologia.md`, `api-meteorologia.md`, `api-territorial.md`,
  `api-epidemiologia.md` e `api-operacional.md`

## Contexto

O dono do projeto pediu, em 06/11/2026, foco em funcionalidades novas a partir de cinco dores do cliente, todas já
registradas no PRD (§2) e nas entrevistas:

1. **Informação urgente indisponível ou espalhada.** A equipe confere à mão na APAC e no Cemaden o nível dos rios, a
   chuva que de fato caiu em cada distrito e os avisos vigentes.
2. **Mapa de risco incompleto.** As áreas de risco da Sedec cobrem só 24 dos 94 bairros (P-25); o resto do território
   aparece sem informação, e a equipe não consegue cruzar risco, vulneráveis e equipamentos de saúde.
3. **Sem dado de saúde durante o evento.** A equipe não vê o que se desenrola durante e depois da chuva (dor do PRD §2).
4. **Desconfiança de alerta automático.** Alertas com localização errada; os avisos oficiais chegam por canais
   diferentes (APAC via COP, Defesa Civil por WhatsApp).
5. **Relatório executivo e memória dos eventos.** Não há registro consolidado de cada evento (início, fim, estágios,
   comunicados, ações, consequências) nem forma de comparar com eventos passados.

Os módulos sugeridos pelo dono foram: hidrologia, meteorologia observada, cobertura territorial dos 94 bairros,
cruzamento de camadas, saúde durante o evento, central de alertas, histórico de eventos com relatório executivo e
metadados de cada dado. **O texto colado pelo dono também cita abrigos; essa parte não vale: a decisão de tirar abrigos
do produto (ADR 0016) prevalece.**

As cinco pesquisas de 06/11/2026 testaram as fontes por GET público, sem criar conta. O que elas confirmaram, e o que
elas mostraram que não existe, é a base desta decisão.

## Decisão

Entram no PRD (v4) os requisitos RF-35 a RF-42, **somente com as fontes reais abaixo**. Tudo segue as regras do
projeto: dado real (ADR 0008), ausência não é zero (RN-01, RN-02), classe e nunca percentual (RN-06), selo
"Experimental" para inferência ainda não validada (RN-11), só agregado (RN-13), fonte e hora em todo indicador (RF-19).
Os novos requisitos entram nas cinco telas que já existem, sem tela nova (proposta, D-17).

### 1. Hidrologia (RF-35)

| Fonte | O que entra | Limite confirmado |
|---|---|---|
| APAC `/estacoes_rios` e `/historico_rios` (sem cadastro, JSON) | Nível do Capibaribe e de rios vizinhos com os **limiares oficiais da estação** (pré-alerta, alerta, enchente), em cm | A única estação de nível com o Recife no cadastro é `39187800` São Lourenço da Mata, **a montante da cidade**. Atraso visto de cerca de 30 h numa leitura |
| APAC `/reservatorio` | Volume e situação (inclusive "vertendo") de Tapacurá, Goitá e Carpina, como contexto da bacia | Codificação de texto irregular; descartar data futura |
| ANA `ServiceANA.asmx` (legado, sem token, XML) | Redundância da mesma estação, mais fresca no teste (cerca de 7 h) | Serviço legado, sem limiares, pode ser desligado |
| Cemaden `wsAlertas2` (já integrado) | "Risco Hidrológico" por município, ao lado do nível | Qualitativo, nunca nível |

- **Não existe estação pública de nível dentro do Recife**, nem nos rios Beberibe, Tejipió, Jordão e Pina. A tela diz
  isso ("Dados insuficientes. Falta: estação de nível no rio X"). O SGB não tem sistema de alerta (SACE) para o
  Capibaribe. A Prefeitura não publica sensores de canal (P-35).
- A leitura é **do rio na estação**, não do bairro. Aplicar a leitura a bairros ribeirinhos exige um mapeamento
  bairro → rio de referência com fonte documentada (P-49); até lá, a leitura aparece só como "rio de referência".
- "Possibilidade de inundação por território" (nível + reservatórios + chuva) é inferência do projeto: entra **só como
  Experimental**, e não antes da resposta a P-49.

### 2. Meteorologia observada (RF-36)

- **Chuva medida em 24 h e 72 h por distrito:** campos `24_horas` e `72_horas` da APAC `/precipitacao_acumulada`, que o
  conector `apac-chuva` já coleta (janelas de 1 h a 120 h). Distrito sem estação válida: "Dados insuficientes".
- **Série horária medida daqui para frente:** a APAC não tem série horária histórica para o Recife (a rota horária vem
  vazia). A série existe a partir do início da coleta, e a tela diz isso; o passado **nunca** é preenchido com modelo.
- **Temperatura:** medida só no INMET A301, que exige token (P-36). Até lá, só previsão (INMET `apiprevmet3`, APAC
  `/previsao_municipio` depois de validar o código do município, P-33) e modelo (Open-Meteo), sempre rotuladas assim.
- **Umidade do solo:** não há medida pública no Recife. Entra como estimativa de modelo (Open-Meteo, ERA5-Land), com
  selo Experimental. O acumulado medido de 72 h e 120 h segue como o indicador medido mais próximo.

### 3. Cobertura territorial dos 94 bairros (RF-37)

- **Suscetibilidade a deslizamento do SGB/CPRM** (camada `Hosted/Suscebilidade_Deslizamento` da Prefeitura, 489
  polígonos, 94 de 94 bairros com classe), rotulada sempre "suscetibilidade do terreno (SGB, 2012 a 2014)", nunca
  "risco". Os setores R1 a R4 da Sedec seguem como camada operacional onde existem.
- **Atendimentos com grau R3 ou R4 por bairro**, da coluna `Grau_de_Risco` dos atendimentos da Defesa Civil (2014 a
  2024): um fato com data ("atendimentos com grau R3/R4"), nunca "bairro de risco".
- **Alagamento de 2026 agregado por bairro** (camadas ArcGIS de comunidades, logradouros e lotes): só contagem por
  bairro, sem lote, endereço ou CEP, e só depois de confirmar licença, autoria e método (P-32). É retrato do evento,
  sem data por registro.
- **Pessoas com deficiência por bairro não existe** em fonte pública (o IBGE publica só por município: 122.531 pessoas,
  8,4%). A tela mostra o total municipal real e "Dados insuficientes" no bairro. Nada é estimado sem decisão do
  cliente (P-41).
- A camada de inundação do SGB **não** vira classe por bairro: "Alta" cobre quase toda a planície e não discrimina.

### 4. Cruzamento de camadas por território (RF-38)

Por bairro: chuva prevista, suscetibilidade, vulneráveis (Censo 2022), equipamentos de saúde próximos (CNES) e
ocorrências (Defesa Civil). As camadas aparecem **lado a lado**, cada uma com fonte, data e quantos dos 94 bairros
cobre. **Não há índice composto** nem peso entre camadas até o cliente decidir (P-22). Cruzamento por geometria
(ponto em polígono, fração de área), nunca por nome de bairro.

### 5. Saúde durante o evento (RF-39)

- **Comparativo antes, durante e depois, por semana epidemiológica**, com o que já está integrado (InfoDengue,
  SINAN leptospirose) e duas fontes novas abertas:
  - **SAMU Recife** (Dados Abertos, ODbL, mensal): chamados por dia, bairro e subtipo, mostrados como **demanda de
    urgência agregada por distrito ou cidade**, nunca como caso de doença. O conector agrega na leitura e descarta
    endereço, sexo, idade e hora (RN-13).
  - **SISAGUA** (API do Ministério da Saúde, cerca de 1 semana de atraso): resultados de análise da água por bairro
    (E. coli, coliformes, cloro, turbidez), mostrados como **qualidade da água**, nunca como doença. "Sem coleta" não é
    "água boa".
- Texto fixo na tela: **"Coincidência temporal, não prova de causa."** Selo Experimental. Sem variação percentual
  enquanto o "depois" tiver semana incompleta. Sem evento registrado (RF-41), não há comparativo.
- **Dado de doença durante o evento só existe com convênio** com a Vigilância/SESAU (atendimentos de UPA/SPA/UBS por
  causa, DDA, SINAN local por bairro e semana: P-38, P-39, P-40). Até lá, cartão "Dados insuficientes" com a fonte que
  falta.

### 6. Central de alertas (RF-40)

- **Alertas oficiais organizados:** APAC, INMET, Cemaden e IDAP (já integrados), com origem, nível, emissão, validade,
  território e link. O histórico passa a ser guardado: `silver.alertas_oficiais` já registra `primeira_vez_em` e
  `visto_em`; as fontes guardam pouco (IDAP cerca de 12 h, APAC cerca de 14 avisos), então só existe histórico a partir
  da coleta.
- **Sinalizações internas de apoio à análise** (ex.: rio de referência acima do pré-alerta, chuva medida em 72 h acima
  do gatilho, estação parada), com fonte, hora, confiança e justificativa, visualmente separadas dos alertas oficiais
  (P-53).
- **O sistema nunca emite alerta em nome da APAC, da Defesa Civil ou do COP**, não reclassifica aviso oficial e não
  envia nada automaticamente.

### 7. Histórico de eventos e relatório executivo (RF-41)

- Evento com início e fim, comunicados (registrados pela equipe, com órgão, hora e link: não é o fluxo de comunicados
  à população do ADR 0011), distritos afetados, evolução (linha do tempo de alertas, estágios e ações), indicadores,
  ações, situação final e pendências.
- O sistema só escreve o que veio de medição ou de fonte oficial citada; o resto é registro da equipe com autor e hora.
  A situação final e o relatório são aprovados por **outra pessoa** (RN-05).
- **Eventos antigos entram como retrospectivos:** Atlas Digital de Desastres (Sedec/MIDR, CSV anual, 16 registros do
  Recife de 1991 a 2022, com danos oficiais e protocolo S2iD) e episódios dos atendimentos da Defesa Civil (2014 a
  2024). Sem estágio, sem comunicados e sem linha do tempo horária: a tela diz "não disponível nesta fonte". O evento de
  abril e maio de 2026 não está no Atlas (vai até 2025) nem nos atendimentos (param em 06/2024, P-42).
- A regra de início e fim e quem registra e aprova dependem do cliente (P-43, P-44).

### 8. Metadados de cada dado (RF-42)

Todo indicador traz fonte, hora da última atualização, **data de referência** (até quando o dado vai), frequência da
fonte, situação da integração (integrada, registro manual, planejada, com falha, sem fonte) e confiabilidade quando
houver (medido, previsão, modelo, oficial; número de estações válidas). Amplia RF-19 e o `meta.fontes` que já existe.

### O que NÃO entra

| Item | Motivo |
|---|---|
| Raspagem de rede social (Instagram, X, Telegram) e de portais sem API | Viola termos das plataformas, é frágil e não é fonte oficial; estágio e comunicados do COP seguem por registro da equipe |
| S2iD direto | Só tela JSF sem API; o Atlas Digital é a versão aberta dos mesmos registros |
| EM-DAT | Exige cadastro e aceite de termos; cobre só desastres grandes, que o Atlas já cobre melhor |
| Microdados individuais (SINAN, SIH, SAMU linha a linha) | RN-13 e RNF-03: o conector agrega na leitura e não guarda a linha |
| Base Celpe com nome de cliente (`Base_Celpe_032026_Alagamento_2026_V1`) | Dado pessoal (nome, medidor, endereço); não ler, não guardar; possível vazamento a avisar ao cliente (P-45) |
| CadÚnico individual (CSV de 2023 do CKAN) | Microdado com data de nascimento e sem bairro; risco de reidentificação e não resolve o pedido |
| API `/arboviroses` do Ministério da Saúde | Devolve a ficha individual do SINAN, repete o que o FTP já entrega e não traz bairro |
| Abrigos | Fora do escopo (ADR 0016), mesmo citados no pedido do dono |
| Estimativa de deficiência por bairro | Seria dado modelado mostrado como real (ADR 0008); só com decisão do cliente (P-41) |
| Previsão de casos de doença pela chuva | Sem dado nem modelo que sustente causalidade (RN-06, RN-11) |

## Alternativas consideradas

- **Construir uma tela por módulo (oito telas novas):** rejeitada. O PRD pede telas simples, só com o que o cliente
  pediu (RF-20, RNF-08); os módulos cabem nas cinco telas atuais.
- **Ler as PCDs do Cemaden pelo mapa interativo ou por `getJson2.php`:** rejeitada. Sem contrato documentado, sem
  acumulados e com risco de bloqueio; o Cemaden chega pela APAC e o acesso oficial fica em P-37.
- **Preencher a série horária passada de chuva com o Open-Meteo:** rejeitada. Seria modelo mostrado como medida.
- **Usar a inundação do SGB como risco por bairro:** rejeitada. Não discrimina (quase toda a planície é "Alta").
- **Índice composto de risco por território:** adiada até o cliente decidir os pesos (P-22). Mostrar as camadas lado a
  lado é honesto e simples.

## Consequências

- **Conectores novos previstos (tarefa do `etl-dados`, depois da aprovação):** `apac-rios` (rios e reservatórios),
  `ana-telemetria` deixa de ser "planejado" e passa a usar o serviço legado sem token, `sgb-suscetibilidade`,
  `recife-alagamento-2026` (depois de P-32), `samu-recife`, `sisagua`, `atlas-desastres`. Cada um com verbete no
  dicionário de dados e limite em `frescor.toml` pela cadência real (ADR 0015).
- **Reuso:** `apac-chuva` (janelas de 24 h e 72 h), `GET /situacao/chuva`, `silver.alertas_oficiais`,
  `recife-alagamento` (grau de risco), `meta.fontes` do envelope.
- **Entidade nova de evento** (`app`), somente inclusão para a linha do tempo; o desenho fica para o `backend-api`
  depois de P-43 e P-44.
- **PRD §5 muda:** o histórico de eventos entra (RF-41); lições aprendidas continuam fora.
- **Dependências do cliente:** P-32 a P-54. Nenhuma fonte nova vai a produção sem a licença ou os termos confirmados
  quando a fonte não os declara (APAC, ArcGIS da Prefeitura, Atlas, SISAGUA, InfoDengue), salvo decisão do dono.

## Riscos

| Risco | Mitigação |
|---|---|
| A leitura do rio a montante ser lida como nível do bairro | Texto fixo "estação a montante do Recife"; aplicação a bairros só com P-49 |
| Atraso variável da APAC (horas a mais de um dia) | Idade da leitura sempre na tela; ANA como segunda fonte; selo de desatualizado |
| Serviço legado da ANA ser desligado | Marcar como legado; o HidroWebService novo com token é o plano B |
| Licença não declarada (APAC, ArcGIS, Atlas, SISAGUA) | Perguntas P-32 a P-34 e P-51; uso interno até a resposta; citar sempre a fonte |
| Open-Meteo gratuito ser só para uso não comercial | Pergunta P-46; afeta previsão, maré, temperatura e umidade do solo já em uso |
| SAMU e SISAGUA lidos como casos de doença | Rótulos "demanda de urgência" e "qualidade da água"; texto "coincidência temporal, não prova de causa" |
| Sinalização interna confundida com alerta oficial | Separação visual, rótulo "sinalização interna, não é alerta oficial", nada enviado |
| Camadas ArcGIS "Hosted" trocadas ou removidas sem aviso | Bronze guarda a resposta; falha aparece como "com falha", nunca como ausência de risco |
| Dado pessoal em camadas e arquivos públicos (Celpe, lotes, SAMU) | Agregar na leitura; nunca gravar lote, endereço, nome ou medidor (RN-13) |
| Escopo crescer e o painel perder simplicidade | Nenhuma tela nova; revisão do `qa-ux` antes de cada entrega |
