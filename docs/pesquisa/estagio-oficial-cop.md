# Estágio operacional oficial da cidade (COP/Defesa Civil): busca de fonte (T2.1, RF-01)

> **Nota de 06/11/2026:** abrigos saíram do escopo do produto (PRD v3, ADR 0016); o feed de abrigos ativos do COP
> citado abaixo não é mais lido. As menções ficam como histórico da pesquisa.

Data da busca: 2026-11-06. Chamadas reais, sem autenticação.

## Conclusão

Não existe fonte pública e máquina-legível do estágio oficial (Observação/Atenção/Alerta/Crítico ou equivalente) nos serviços testados. Nenhum conector `cop-estagio` foi criado, para não inventar dado. O estágio oficial entra por **registro manual da equipe**, com fonte "Registro manual da equipe (COP)", hora do registro e autor (RF-19, RF-32). Sem registro vigente, a tela mostra "Dados insuficientes" e diz que falta o estágio do COP.

## O que foi testado

| URL | Resultado |
|---|---|
| `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/COP?f=json` | 200. Sem subpastas. Serviços: `Abrigos_Ativos` (Feature/Map), `BASE_METEOBLUE_CONSULTA` (Feature/Map, previsão Meteoblue), `BASE_SENSORES_PLUVIOMETRICOS_RECIFE` (Map, histórico de chuva por pulso). Nenhum com estágio, alerta, nível, status ou ativação da cidade. |
| `.../services?f=json` (raiz) | Lista 50+ pastas (APAC, CEMADEN, COMAR, Hosted, PainelChuvas, Geoevent...). Nenhum serviço de nível raiz com estágio. |
| `.../COP/Abrigos_Ativos/MapServer` | Uma camada, `Abrigos`. Já usada em `etl/conectores/abrigos.py`. Descreve abrigos, não estágio. |
| `.../PainelChuvas`, `.../CEMADEN`, `.../Geoevent` | `PainelChuvas/MD_APAC` (ImageServer), `CEMADEN/BASE_CEMADEN_ESTACOES_GEOTECNICAS`; `Geoevent` vazia. Sem estágio. |
| `.../Hosted/BOLETIM_METEOROLOGICO/FeatureServer/0` | Campos: num_boletim, data, condicao_tempo, previsao_24, temp_min/max, vento, descritivo. Último boletim `424/2023` (set/2023), desatualizado. Zero registros com "estágio" ou "alerta" no texto. Não serve. |
| `.../Hosted/dadosclimaticos_gdb` | Série climática histórica (INMET), sem relação com estágio. |
| `.../Paineis_PHP_Portal/Painéis_PHP_Portal`, `.../Hosted/Previsão_de_chuvas_CPTEC` | Listados na pasta, mas a camada responde 404 "Service not found". |
| Pasta `Hosted` (200+ serviços) | Nomes com interesse: `Setores_Risco_SEDEC`, `SedecRegionais`, `Alagamento_2026_V2`, `pontos_Ativações_Balanço`. São áreas de risco, regionais e ocorrências; "Ativações" é de eventos urbanos (balanço), não de estágio. |
| CKAN `https://dados.recife.pe.gov.br/api/3/action/package_search?q=...` | "estagio": 0 resultados. "alerta": 0. "boletim": 0. "defesa civil": 5 (`defesa-civil`, `efetivo-da-defesa-civil`, `registro-de-atendimentos-da-defesa-civil`, `abrigos-temporarios-disponiveis`, `demandas-dos-cidadaos...`), todos de atendimentos, áreas de risco, efetivo ou abrigos. "plano de contingencia": 11 resultados, todos sem relação (zoneamento, ciclovias, orçamento). Com acento ("estágio") a API retorna 400. |
| `https://www.recife.pe.gov.br/defesacivil` | 404. |
| `https://www2.recife.pe.gov.br/servico/defesa-civil` | Sem resposta (falha de conexão) no momento do teste; sem RSS/JSON conhecido. |

Limites da busca: não foi feita raspagem de HTML de páginas institucionais nem de redes sociais do COP. Isso seria contornar a falta de API e é frágil. O Plano de Contingência foi tratado só como referência dos critérios; não há publicação do estágio vigente em formato de dados.

## Pergunta para o COP (dono da decisão)

O COP/Defesa Civil do Recife publica, em algum endpoint, feed, planilha ou serviço ArcGIS, o estágio operacional vigente da cidade (nome, hora de início e hora de fim)? Se sim, qual a URL e a frequência de atualização? Se não, aceita informar a equipe do ClimaSense por canal fixo (e quem registra) a cada mudança de estágio, para o registro manual manter fonte e hora corretas?
