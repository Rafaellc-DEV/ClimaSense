# Fontes reais para o eixo territorial e de impactos (áreas de risco, vulneráveis, equipamentos, ocorrências)

Pesquisa de 06/11/2026. Só leitura: consultei endpoints públicos por GET e baixei amostras para um diretório temporário.
Nada foi carregado no banco e nenhum código foi alterado. Cada número abaixo é uma medição minha nesta data, salvo onde
está escrito "não testado".

Ponto de partida (já existe no produto): áreas de risco Sedec cobrem 24 dos 94 bairros (`recife-areas-risco`); o Censo
2022 por bairro cobre 94 de 94, mas só até "70 anos ou mais" (`ibge-censo-2022-bairro`); CNES filtrado
(`cnes-equipamentos`); atendimentos da Defesa Civil 2014 a 2024 (`recife-alagamento`).

## 1. Resumo para quem tem pressa

| Necessidade | Melhor fonte encontrada | Cobertura medida | Veredito |
|---|---|---|---|
| Deslizamento/encostas nos 94 bairros | Carta de suscetibilidade a movimentos de massa (SGB/CPRM 2015), servida pela Prefeitura em `Hosted/Suscebilidade_Deslizamento` | 489 polígonos (Alta 189, Média 104, Baixa 196); cobre 99,1% da área da cidade; **os 94 bairros têm classe**, mas "Alta" só toca 24 bairros | **Resolve a lacuna** de cobertura, com ressalva: é suscetibilidade modelada (2012 a 2014), não setor de risco |
| Alagamento/inundação nos 94 bairros | Mesma carta SGB/CPRM, camada de inundação (`Inundacao_A`, só no ZIP do RIGEO) | 506 polígonos (Alta 28, Média 317, Baixa 161); cobre só 51% da área; Alta aparece em 84 bairros | Cobre quase todos, mas "Alta" é quase toda a planície: **baixo poder de discriminar**. Serve como camada de contexto, não como risco por bairro |
| Idosos e crianças por bairro | Já temos (Censo 2022 por bairro, 94 de 94) | 0 a 4, 0 a 14, 60+, 70+ | Suficiente. Falta só "80+" e "5 a 14" separados (não publicados por bairro) |
| Pessoas com deficiência por bairro | **Não existe fonte pública por bairro nem por setor** | Só município: 122.531 pessoas (8,4% dos 1.460.199 com 2 anos ou mais) | Lacuna real. Ver seção 4 |
| Ocorrências e danos por bairro e data | Atendimentos da Defesa Civil (CKAN), já em uso | 886.263 linhas de 2014 a 2024; **o arquivo de 2025 está vazio (1 linha)** | Histórico bom; **não há dado de 2025 e 2026 no portal**. Danos (pessoas, imóveis) não existem na fonte |
| Evento de 2026 | Camadas ArcGIS "Alagamento 2026" (polígonos de comunidades, logradouros e lotes) | 78 polígonos com `qtd_registros`, 552 trechos de logradouro, 5.761 lotes alagados | Único retrato territorial de um evento recente. Sem data por registro |
| Cruzamento por território | Todas as camadas do ESIG têm geometria; bairros oficiais em `Bairros_Censo2022_final` | 94 bairros, 2.574 setores | Viável por ponto em polígono e interseção de área |

## 2. Achado principal: o portal ArcGIS da Prefeitura é a fonte mais rica

O servidor `https://esigportal2.recife.pe.gov.br/arcgis/rest/services` lista ao todo mais de 200 serviços na pasta
`Hosted`. Todos os que testei respondem por GET sem autenticação (`/FeatureServer/<n>/query?...&f=geojson`). Limite de 2.000
registros por página. **Nenhuma camada declara licença ou `copyrightText`.** O conector atual de áreas de risco já usa esse
servidor, então a política (confirmar a licença com a Sedec antes de redistribuir geometria) continua valendo para todas.

Camadas relevantes, com a contagem medida e a última edição que o servidor informa:

| Camada (`Hosted/...`) | Tipo | Registros | Última edição | Uso |
|---|---|---|---|---|
| `Suscebilidade_Deslizamento` | polígono | 489 | 24/08/2025 | Suscetibilidade a deslizamento (SGB/CPRM) |
| `Setores_Risco_SEDEC` | polígono | 677 | (já em uso) | Setores R1 a R4 (24 de 94 bairros) |
| `Comunidades_Interesse_Social` | polígono | 547 | 04/08/2026 | Favelas e comunidades: `populacao_`, `ind_alagam`, `drenagem`, `unidade_pa`, `bairro_pre`, `precarieda` |
| `ProjetoEncostasURB_gdb` | ponto/polígono | 458 contratos, 427 fases, 428 polígonos de encosta, 195 localidades | 27/08/2025 | Obras de contenção de encostas: `bairro`, `risco`, `status`, `popcis`, `imoveiscis` |
| `Alagamento_2026_V2` | polígono | 42 | 19/05/2026 | Comunidades alagadas em 2026 |
| `Poligonos_Alagamentos_2026_5` | polígono | 78 | 17/06/2026 | Comunidades alagadas com `qtd_registros` |
| `Logradouros_Alagamentos_2026_V1` | linha | 552 | 08/05/2026 | Trechos de rua alagados |
| `Lotes_Areas_Alagadas_2026_V1` | polígono | 5.761 | 20/05/2026 | Lotes atingidos (tem `qtdunhab`, `tipoempreendimento`) |
| `pontos_alagamento_arcgis` | ponto | 54 | 25/09/2026 | Pontos críticos (EMLURB). **Campos de risco vazios** (ver seção 3.4) |
| `Bairros_Censo2022_final` | polígono | 94 | 19/07/2024 | Os 94 bairros com população e domicílios do Censo 2022 |
| `Setores_Censitarios_Recife_2022_V1` | polígono | 2.574 | 03/07/2024 | Setores do Censo 2022 (`v0001` a `v0007`) |
| `Rede_de_Saúde_de_Recife` | ponto | 673 | 31/08/2026 | Rede municipal com `cnes`, `tipo_equipamento`, `bairro`, `area_vulneravel` |
| `BASE_SAUDE` | polígono | 12.048 quadras | 16/06/2026 | Quadras por distrito sanitário, microárea e bairro |
| `Barreiras_GCMR`, `Barreiras_SECON` | linha | 12 e 15 | 18/12/2024 | Poucas linhas; sem uso claro |

**Camadas que não devemos usar:** `Base_Celpe_032026_Alagamento_2026_V1` (30.045 pontos) traz `nomecliente`, `codmedidor` e
endereço: dado pessoal, fora do escopo (RN-13, RNF-03). Se algum dia for útil como "imóveis sem energia por alagamento",
só em agregado por bairro e depois de acordo formal com a concessionária. Também não usar `pop_de_rua` (8 pontos).

Os serviços de declividade (`RGB_MDT_2_5MTS_DECLIVIDADE_tif` e os `Teste_Declividade_*`) são **só tiles** (`TilesOnly`),
sem consulta de valor, e o de classes que abri é de **Caruaru**, não do Recife. Não servem para calcular encosta por bairro.

## 3. Fonte por fonte

### 3.1 Suscetibilidade a deslizamento: `Hosted/Suscebilidade_Deslizamento` (SGB/CPRM 2015)

- **URL:** `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted/Suscebilidade_Deslizamento/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`
- **Autenticação:** nenhuma. **Formato:** GeoJSON/JSON ArcGIS. **Frequência:** estática (campo `fonte`: "modelagem validada por trabalho de campo pela CPRM entre os anos de 2012 e 2014").
- **Cobertura medida:** 489 polígonos (Alta 189, Média 104, Baixa 196); união cobre 99,1% da área do município. Alta cobre
  ao menos 1% da área em 22 bairros (maiores: Brejo de Beberibe 12%, Pau Ferro 9,5%, Nova Descoberta 9,4%, Dois Irmãos 8,1%,
  Cohab 7,9%, Passarinho 7,3%); Média em 36 bairros. Medi por interseção entre os polígonos e `Bairros_Censo2022_final`.
- **Exemplo real:** `{"classe":"Baixa","processo":"Deslizamento","município":"Recife","uf":"PE"}`.
- **Licença:** não declarada na camada. O original é do SGB (RIGEO lista o acesso como "open", sem nome de licença).
- **Qualidade:** escala 1:45.000, produto de 2015. Bom para ordenar bairros por exposição estrutural. **Não é setorização
  de risco** (R1 a R4) nem mapeia moradias em risco. Mostrar sempre como "suscetibilidade do terreno".
- **Esforço:** baixo, é o mesmo padrão do conector `recife-areas-risco` (uma camada, 489 registros, uma página).
- **Risco LGPD:** nenhum (polígonos de terreno).

### 3.2 Carta de suscetibilidade completa do SGB/CPRM (movimento de massa e inundação)

- **URL do item:** `https://rigeo.sgb.gov.br/handle/doc/15030` ("Carta de suscetibilidade a movimentos gravitacionais de massa e
  inundação: município de Recife - PE", 2015, escala 1:45.000, folha SC.25-V-A-III-1).
- **Download vetorial (SIG):** `https://rigeo.sgb.gov.br/bitstreams/21a73b6f-57a0-4620-9113-27b01904aea5/download`
  (`sig_recife_pe.zip`, 107,5 MB; baixei e abri). Também há o PDF da carta (`CS-Recife.pdf`), base cartográfica e produtos de
  modelo digital de elevação.
- **Autenticação:** nenhuma. **Formato:** shapefile SIRGAS 2000 UTM 25S. **Frequência:** estática (2015).
- **Conteúdo útil (pasta `Suscetibilidade/`):** `Inundacao_A.shp` (506 polígonos: Alta 28, Média 317, Baixa 161) e
  `Movimento_de_Massa_A.shp`. Outras pastas: `Feicoes/` (cicatrizes de deslizamento, feições erosivas, áreas alagadas e úmidas), `Relevo/`, `Geologia/`, `Solos/`, `Curvas_de_nivel/` (20 m).
- **Cobertura medida (inundação):** união dos polígonos cobre 51,4% da área do município. Alta toca 84 bairros e passa de 10% da
  área em 77: ou seja, **quase toda a planície é "Alta"**. Casa Forte, Boa Vista, Hipódromo, Rosarinho e outros aparecem 100%
  Alta. Médias altas: Ipsep 91%, Caçote 74%, Areias 72%, Estância 52%. Observação: li os polígonos com um leitor
  de shapefile escrito à mão (sem GDAL); vale conferir com GDAL/geopandas antes de adotar.
- **Licença:** o RIGEO marca acesso aberto, sem nome de licença. Citar o SGB como fonte.
- **Qualidade:** o mesmo caveat do item anterior. Para "Alta" de inundação, o discriminador por bairro é fraco.
- **Esforço:** médio (arquivo grande, shapefile, reprojeção). Carga única.
- **Pesquisa que não deu certo:** a **setorização de risco** do SGB (R3/R4 "alto e muito alto") **não existe publicada para o
  Recife**: o portal tem relatórios de Camaragibe, Ipojuca, Gameleira e outros de PE, mas nenhum do Recife. O endpoint
  `geoportal.sgb.gov.br/arcgis/rest/services` devolveu 404. Quem faz a setorização no Recife é a própria Sedec.

### 3.3 Setores de risco da Sedec (já no produto) e dados de apoio

- Cobertura confirmada: 677 setores, **24 de 94 bairros**. O CKAN `defesa-civil` só tem a Regional Sul (CSV com pontos e
  descrições como "Área de Risco Nível 3", "Deslizamento", "Ponto de Colocação de Lona"; o dicionário diz frequência "Anual").
  Não há versão do CKAN para as outras regionais. O único caminho para os 70 bairros restantes é pedir à Sedec o mapeamento
  completo (pergunta aberta), ou aceitar a suscetibilidade do SGB como camada complementar.
- **Grau de risco nos atendimentos (achado novo):** o CSV de atendimentos tem a coluna `Grau_de_Risco` (R1 a R4). Em 2024,
  de 80.174 linhas, 31.355 trazem grau (R3 16.461, R2 10.729, R1 2.829, R4 1.336). Somando 2014 a 2024 e casando o bairro
  pelo nome oficial, **88 dos 94 bairros têm ao menos um registro com grau e 86 têm ao menos um R3 ou R4**. Isso mostra onde a
  Defesa Civil já avaliou risco, mas **não** é um mapeamento: o grau vem do atendimento, pode refletir o ponto vistoriado e não
  o bairro, e não apliquei limite mínimo de registros. Meu casamento por nome deixou de fora localidades escritas como bairro
  ("Alto da Esperança", "Boqueirão"), então o número é aproximado. Uso sugerido: indicador de "atendimentos com grau
  R3/R4 por bairro" (fato, com data), nunca de "bairro de risco".
- **Endereços ofuscados:** o campo `Endereco` vem com o número trocado por símbolos (por exemplo "Rua Taipu, #_|/"), o que
  protege a identidade. Não tentar geocodificar; usar só `Bairro` e `Localidade`.

### 3.4 Alagamento: camadas de 2026 e pontos críticos

- **Polígonos de comunidades alagadas:** `Hosted/Poligonos_Alagamentos_2026_5` (78) e `Alagamento_2026_V2` (42). Exemplo real:
  `{"comunidade":"Malvinas / Apuleu Vieira / Melvin Jones","rpa":4,"qtd_registros":202}`. Sem data por registro: retrato
  acumulado do evento.
- **Logradouros e lotes:** 552 trechos e 5.761 lotes. Os lotes têm unidades habitacionais (`qtdunhab`) e tipo, úteis para
  estimar exposição de moradias por bairro (agregando por ponto em polígono). Não trazem o nome do morador.
- **Pontos críticos (`pontos_alagamento_arcgis`, 54 pontos, 28 bairros, última edição 25/09/2026):** o esquema é rico
  (`pop_exposta`, `vuln_social`, `nota_risco`, `classe_risco`, `recorrencia`, `lamina`, `obra_relacionada`), mas **todos os campos
  de risco estão nulos** nos 54 registros e o campo `obs` diz "Geocodificação automática (OSM)". É uma planilha de trabalho da
  Prefeitura ainda sem preenchimento. Acompanhar; hoje só serve como lista de locais e bairros.
- **Outras camadas de pontos:** `PONTOS_ALAGAMENTOS_16032023` (181), `ALAGAMENTOS_EMLURB` (60) e `Alagamento_24h_190823` (596 alertas
  do Waze; ver aviso de dado de terceiros e de moderação duvidosa). Úteis para validar histórico, não como fonte primária.
- **Licença:** nenhuma declarada. **Esforço:** baixo para polígonos e pontos; médio para lotes (5.761 polígonos).

### 3.5 Comunidades de interesse social (favelas): vulnerabilidade territorial

- **CKAN:** `https://dados.recife.pe.gov.br/dataset/relacao-das-favelas-corticos-e-loteamentos-irregulares` (GeoJSON, ODbL,
  545 feições, dados de 2014) **e** a camada ArcGIS atual `Hosted/Comunidades_Interesse_Social` (547, editada em 04/08/2026).
  Prefira a camada ArcGIS (mais nova).
- **Campos reais:** `nome_atual`, `bairro_pre`, `populacao_` (592 em "21 de Abril"), `qtde_imove`, `unidade_pa` (unidade de paisagem:
  planície, morro), `precarieda`, e índices de 0 a 10 de `abastecime`, `esgotament`, `drenagem`, `pavimentac`, `ind_alagam` (9,3 em
  "21 de Abril"), `dist_saude`, `indice_com`.
- **Valor:** é a única fonte municipal com um **indicador de alagamento por comunidade** e a **unidade de paisagem
  (morro ou planície)** ao mesmo tempo, mais população por comunidade. Ajuda a cruzar risco com vulnerabilidade social.
- **Ressalvas:** população de 2014 (anterior ao Censo 2022); `ind_alagam` é um índice composto da Prefeitura, de metodologia
  não documentada na camada. Honesto: usar como "indicador da comunidade", com o ano.
- **Esforço:** baixo. **LGPD:** só agregados por comunidade.

### 3.6 Encostas e obras de contenção (URB Recife)

- `Hosted/ProjetoEncostasURB_gdb`, camada 0 `BaseEncostaContrato` (458 pontos): `bairro`, `status`, `risco`, `popcis`, `imoveiscis`,
  `inicio_prev`, `termino_real`, `data_atualizacao`. Camada 3 `FCBASEENCOSTAFASE` traz 428 polígonos de encosta.
- **Valor:** lista **onde há encosta mapeada e o que já foi (ou não) contido**, com bairro e população estimada. É a melhor pista
  de "encostas por bairro" que não depende da Sedec. A camada `ENCOSTAS_NÃO_INICIADAS...` (22 pontos) lista as pendentes.
- **Ressalva:** a Prefeitura não documenta o que significa cada valor de `risco` aqui; confirmar antes de exibir.
  Tem contratos e valores (`custo_est_*`): não exibir (fora do pedido do cliente).

### 3.7 CKAN dos Dados Abertos do Recife: o que há e o que não há

`https://dados.recife.pe.gov.br/api/3/action/package_search?q=<termo>` (JSON, sem autenticação, licença ODbL em todos que olhei).
Há 223 conjuntos. Resultado das buscas:

- **encosta/morro/barreira:** só `registro-de-atendimentos-da-defesa-civil` e o conjunto "Dados Vivos". **Não há conjunto de encostas.**
- **ocorrências Defesa Civil:** `registro-de-atendimentos-da-defesa-civil` (um CSV por ano). Medi: 2014 a 2024 completos (886.263 linhas
  no total, com colunas deslocadas em 2020 e 2022 como já documentado); **2025 tem 1 linha** (340 bytes) e não há 2026. O metadado
  do conjunto muda em 19/10/2026, mas o arquivo de 2025 segue vazio.
- **"Tempo real" da Sedec** (dentro de `demandas-dos-cidadaos-e-servicos-dados-vivos-recife`): `sedec-solicitacoes-tempo-real.csv` e
  `sedec-vistorias-tempo-real.csv`. Apesar do nome, **estão congelados**: 173 solicitações de um único dia (29/03/2023) e 1 vistoria
  (2021). Descartar.
- **156 (Emlurb):** `central-de-atendimento-de-servicos-da-emlurb-156`, um CSV por ano de 2012 a 2026 (o de 2026 é `156_cco_diario_2026.csv`,
  alterado em 19/06/2026), ODbL. Cobre limpeza, drenagem e poda; **não é indicador de dano de chuva**, mas "desobstrução de bueiro/canal"
  pode ser sinal de drenagem. Não li as categorias (dicionário JSON/PDF no próprio conjunto); estimativa de esforço médio.
- **Cadastro Único:** `cadastro-unico-para-programas-sociais`, CSV de 2023 (72 MB, 82.346 pessoas, ODbL). Tem deficiência
  (`p.cod_deficiencia_memb`: 6.136 com e 76.209 sem) e data de nascimento, mas é **microdado individual** e **não tem coluna de bairro**
  ou endereço. Sem território, não resolve o pedido e traz risco de reidentificação (data de nascimento + composição familiar).
  **Não usar.** Não é a base completa do CadÚnico do Recife (que tem muito mais famílias): é uma amostra sem critério declarado.
- **Saúde:** `rede-de-saude-municipal`, `unidades-basica-de-saude`, `unidades-saude-da-familia-usf`, `hospitais`, `maternidades`, `unidades-de-saude`,
  `equipes-de-saude-da-familia`. A camada ArcGIS `Rede_de_Saúde_de_Recife` é mais atual (31/08/2026) e traz `cnes`.
- **Pessoa com deficiência:** só o conjunto de serviços da Divisão da Pessoa com Deficiência (não é população).
- **Censo socioassistencial 2024 (Censo SUAS):** dados de equipamentos (CRAS, CREAS, Centro POP, acolhimento), não população por bairro.

### 3.8 IBGE: Censo 2022

- **Agregados por bairro** (já em uso) e **por setor**: `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/`
  (`Agregados_por_Bairro_csv/` e `Agregados_por_Setor_csv/`). Pacotes presentes hoje: alfabetização, básico, características do
  domicílio 1 a 3, cor ou raça, demografia, óbitos, parentesco, indígenas e quilombolas. **Nenhum pacote de deficiência**, nem por bairro
  nem por setor. O dicionário (`dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx`) não tem variável de deficiência.
  Por setor, a faixa de idade continua em "70 anos ou mais": o setor não resolve o 80+.
- **Deficiência só por município:** a API de agregados `https://servicodados.ibge.gov.br/api/v3/agregados/10125/metadados` e a API
  SIDRA, por exemplo
  `https://apisidra.ibge.gov.br/values/t/10125/n6/2611606/v/all/p/2022/c2/6794/c58/all?formato=json`
  (sem autenticação, JSON), devolvem para o Recife: **1.460.199 pessoas de 2 anos ou mais; 122.531 com deficiência (8,4%)**.
  A tabela 10125 tem idade em grupos de 5 anos até "100 anos ou mais" e sexo. As tabelas `10125` a `10139` do Censo trazem
  deficiência por município com cortes de idade, cor ou raça e escolaridade. **Os níveis territoriais publicados são Brasil, Grande
  Região, UF e município (N1, N2, N3, N6): não há bairro.** Os microdados e áreas de ponderação (já listados na pesquisa anterior)
  são da amostra; a deficiência vem do questionário da amostra, então o nível mais fino possível seria a área de ponderação,
  que agrupa vários bairros. Não verifiquei se há microdados de deficiência por área de ponderação do Recife.
- **Malha:** `.../Agregados_por_Setores_Censitarios/malha_com_atributos/{bairros,setores,distritos}/` (geometria com atributos).
  Alternativa mais prática: a camada ArcGIS `Setores_Censitarios_Recife_2022_V1` (2.574 setores) e `Bairros_Censo2022_final` (94).
- **Licença:** dados públicos do IBGE. **Qualidade:** alta; o 2022 é retrato fixo. **LGPD:** só agregados.

### 3.9 Equipamentos de saúde

- **CNES (já em uso):** `https://apidadosabertos.saude.gov.br/cnes/estabelecimentos?codigo_municipio=261160` (4.740 estabelecimentos; filtrado).
- **Rede municipal da Prefeitura:** `Hosted/Rede_de_Saúde_de_Recife` (673 pontos; 86 bairros; todos com `cnes`). Tipos: 82 USF+, 62 USF,
  51 RT, 43 PAC, 27 ambulâncias, 13 policlínicas, 8 NDI, e outros; natureza: 597 próprio, 39 complementar, 25 parceria. O campo
  `area_vulneravel` marca Sim em 24, Não em 352 e vazio em 297 (os 297 sem `tipo_equipamento` parecem ser serviços, não prédios; checar antes de contar).
  Vantagem sobre o CKAN: coordenadas, CNES e `equipe`. Serve para casar com o CNES por código e dar a localização.
- **OpenStreetMap via Overpass:** `https://overpass-api.de/api/interpreter` (precisa de `User-Agent` identificado; sem ele
  devolve 406). Consulta de hoje, dentro do limite administrativo do Recife: **180 elementos `amenity=hospital`** (49 pontos, 126 áreas,
  5 relações; contam prédios e anexos, não hospitais distintos) e **551 de `amenity=clinic|doctors` ou `healthcare`**. Licença ODbL
  (atribuir "© colaboradores do OpenStreetMap"). **Qualidade irregular:** mistura prédios e pontos duplicados; não substitui o CNES.
  Serve apenas para conferir coordenadas faltantes.
- Situação (fechado, danificado): nenhuma fonte pública (igual à pesquisa anterior).

### 3.10 Fontes federais de suscetibilidade e população (não testadas ou sem ganho)

- **IBGE/Cemaden "População em áreas de risco" (BATER):** página recusou acesso automatizado na pesquisa anterior; **não testei de novo**.
  Base do Censo 2010 e de municípios prioritários; para o Recife o produto é grosseiro e velho. Baixa prioridade.
- **Cemaden:** já documentado em `docs/dicionario-dados/cemaden.md` (pluviômetros e alertas). A camada ArcGIS
  `CEMADEN_Historico_Pluviometros_Visualizacao` é a mesma fonte espelhada pela Prefeitura. Não traz áreas de risco do Recife.
- **MapBiomas e INPE TerraBrasilis:** **não testados**. TerraBrasilis trata de desmatamento e queimadas; MapBiomas de cobertura da terra.
  Nenhum dos dois oferece risco de deslizamento ou alagamento por bairro. Cobertura da terra do Recife já existe no CKAN
  (`cobertura-da-terra`, tag "alagável"), de metodologia não verificada. Sem prioridade.
- **CadÚnico/SAGI/VIS DATA (MDS):** a ferramenta `aplicacoes.cidadania.gov.br/vis/data3/` respondeu 302 (redirecionamento) e **não testei a
  consulta**. Por conhecimento geral, entrega agregados por município (inclusive famílias com pessoa com deficiência e BPC), não
  por bairro. O CECAD (por bairro) exige login institucional. Só o gestor municipal da Assistência Social tem o recorte por bairro.
- **Topodata (INPE, 30 m):** válido, mas grosseiro para encostas (já avaliado). Alternativa melhor: o modelo digital de 2,5 m da
  Prefeitura **se** for liberado em formato matricial (hoje só tiles) ou o MDE do próprio ZIP do SGB (`produtos_mde_recife_pe.zip`, não baixei).

## 4. Pessoas com deficiência: a lacuna que não fecha com dado público

O que se sabe de fonte pública e o que não:

| O que existe | Nível | Valor |
|---|---|---|
| Censo 2022, SIDRA 10125 a 10139 | município | 122.531 pessoas (8,4%), com idade, sexo, cor ou raça, tipo de dificuldade |
| Cadastro Único 2023 no CKAN | indivíduo, sem bairro | descartado (seção 3.7) |
| Rede de serviços do CKAN | serviços, não população | só localiza atendimento |

**Honestidade:** não há deficiência por bairro nem por setor em fonte pública. Qualquer número por bairro seria **estimativa**
(redistribuir a taxa municipal por faixa de idade). Isso viola o princípio de só exibir dado real (ADR 0008, RF-12.10) se for
mostrado como medido; só caberia como "estimativa" rotulada e com método documentado, e dependeria de decisão do cliente
(perguntas abertas). Recomendação: mostrar o fato real do município (122.531; 8,4%) e a taxa por idade, e para o bairro
exibir "Dados insuficientes: o IBGE não publica deficiência por bairro" (RN-01). Se o cliente quiser o recorte local,
o caminho legítimo é pedir à Secretaria de Assistência Social/Prefeitura um **agregado por bairro** (contagem de pessoas com deficiência
cadastradas no CadÚnico/BPC), sem nome, com supressão de células pequenas.

## 5. Recomendação priorizada

### (1) Cobrir os 94 bairros com risco de deslizamento/encostas e de alagamento

1. **Adicionar a suscetibilidade a deslizamento do SGB (`Hosted/Suscebilidade_Deslizamento`)** como segunda camada, ao lado dos
   setores Sedec. Rotular "suscetibilidade do terreno (SGB, 2012 a 2014)", não "risco". Resultado: 94 de 94 bairros com classe.
   Esforço baixo. Mantém RN-01: onde só existe "Baixa" por fundo de modelo, dizer "suscetibilidade baixa", sem sugerir ausência de ocorrência.
2. **Manter os setores Sedec (R1 a R4)** como a camada operacional onde existe (24 de 94) e **pedir à Sedec o mapeamento dos demais**.
   Em paralelo, mostrar o indicador factual "atendimentos com grau R3/R4 por bairro" (seção 3.3).
3. **Encostas:** usar `ProjetoEncostasURB_gdb` para exibir "encostas com obra de contenção, em andamento, não iniciadas" por bairro, depois de confirmar com a
   Prefeitura o significado de `risco` e `status`.
4. **Alagamento:** a camada de inundação do SGB cobre quase todos os bairros, mas "Alta" é quase a planície inteira; usar só como contexto.
   O retrato mais discriminante é o **histórico de atendimentos** (já carregado) mais as camadas de **2026** (comunidades, logradouros e lotes).
   Reforçar que a previsão de alagamento segue "experimental" (RN-11).
5. Não usar `pontos_alagamento_arcgis` para classe de risco até a Prefeitura preencher os campos (hoje 0 de 54).

### (2) Idosos, crianças e pessoas com deficiência

1. **Idosos (60+, 70+) e crianças (0 a 4, 0 a 14):** manter o Censo 2022 por bairro. É dado real, 94 de 94.
2. **80+ e faixas finas:** indisponível por bairro. Não estimar. Se for essencial, só no município (SIDRA 10125).
3. **Pessoas com deficiência:** mostrar o total municipal real (122.531) e dizer que bairro não existe. Pedir agregado por bairro à Assistência Social. Nada de microdado individual (RN-13).
4. **Vulnerabilidade territorial complementar:** `Comunidades_Interesse_Social` (população, precariedade, `ind_alagam`, drenagem) por comunidade, agregada ao bairro.

### (3) Ocorrências e danos por bairro e data

1. **Ocorrências:** o histórico atual (2014 a 2024) é bom, mas **está parado em 2024**. O arquivo de 2025 do CKAN está vazio. Registrar como pergunta aberta
   para a Sedec e a Emprel: onde estão 2025 e 2026? Hoje o produto precisa mostrar a data da última ocorrência disponível (RF-19) e **não** sugerir que 2025 foi calmo.
2. **Danos:** a fonte não tem pessoas afetadas, desabrigados nem imóveis danificados. Os lotes alagados de 2026 (5.761, com `qtdunhab`) são o mais próximo
   de "imóveis atingidos", agregáveis por bairro, sem data. O dado de dano por data só virá do registro da equipe (RF do PRD).
3. Evitar `Base_Celpe` (dado pessoal) e Waze (terceiros).

### (4) Cruzamento de camadas por território

- **Chave:** `bairro-<slug>` (já existe) com os 94 polígonos de `Bairros_Censo2022_final`. Para camadas poligonais, calcular a **fração da área do
  bairro** por classe (como fiz para o SGB); para pontos, contar por ponto em polígono; para setores censitários (2.574), somar população e
  depois agregar ao bairro (o bairro do IBGE já casa 94 de 94, mas confirmar que o polígono ESIG e o do IBGE coincidem).
- **Camadas prontas para cruzar:** suscetibilidade (deslizamento, inundação), setores Sedec, comunidades (população, `ind_alagam`), encostas, rede de saúde
  (CNES por código), população 2022, atendimentos por bairro e data, e a cobertura por equipes de saúde (`BASE_SAUDE`).
- **Armadilhas:** nomes de bairro divergem entre fontes (Sedec "Ibura / Cohab", IBGE "Sítio dos Pintos - São Brás"): usar polígonos, não nomes, sempre que houver geometria.
  Cobertura desigual: cada indicador deve dizer em quantos dos 94 bairros existe, e mostrar "Dados insuficientes" no resto (RN-01).

## 6. Lacunas e perguntas abertas sugeridas

1. Licença das camadas ESIG da Prefeitura (nenhuma declara). Pedir autorização formal à Sedec/Emprel antes de redistribuir.
2. Setorização de risco da Sedec das demais regionais (70 bairros sem dado). Existe? Pode ser cedida?
3. Atendimentos 2025 e 2026: o CSV de 2025 está vazio no portal. Há outra via (arquivo interno, API)?
4. Tipo de perigo por setor Sedec (já P-25) e significado de `risco` e `status` em `ProjetoEncostasURB_gdb`.
5. Deficiência por bairro: aceita-se estimativa rotulada, ou só agregado oficial da Assistência Social?
6. Pontos críticos de alagamento (`pontos_alagamento_arcgis`): quando a EMLURB preencherá `classe_risco` e `pop_exposta`?
7. Validação do leitor de shapefile e dos percentuais por bairro com GDAL (medi com código próprio).

## 7. Resumo das URLs testadas (todas GET, sem autenticação)

- `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted/<Camada>/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`
- `https://dados.recife.pe.gov.br/api/3/action/package_search?q=<termo>` e `package_show?id=<nome>`
- `https://rigeo.sgb.gov.br/handle/doc/15030` e `https://rigeo.sgb.gov.br/bitstreams/21a73b6f-57a0-4620-9113-27b01904aea5/download`
- `https://servicodados.ibge.gov.br/api/v3/agregados` e `https://apisidra.ibge.gov.br/values/t/10125/...`
- `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/`
- `https://overpass-api.de/api/interpreter` (POST de consulta, exige `User-Agent`)
