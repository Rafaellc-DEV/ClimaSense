# Fontes públicas candidatas: população vulnerável, equipamentos de saúde e áreas de risco

Pesquisa de 06/11/2026 (Onda 0, agente `arquiteto`). Consultei só metadados e listagens; **nada foi carregado** no
Atlas nem no Neon. Coluna "Verificação": o que de fato respondeu na consulta.

## 1. População vulnerável agregada (pessoas com deficiência, idosos, crianças)

| Fonte | URL | Recorte | Verificação | Prós | Contras |
|---|---|---|---|---|---|
| IBGE Censo 2022: Agregados **por bairro** (demografia) | `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/` (`Agregados_por_bairros_demografia_BR.zip`) | Bairro do IBGE, idade (anos e grupos de 5 anos) | Diretório e arquivos listados | Pronto por bairro; resultado do universo; público, sem dado pessoal | Bairro do IBGE pode não casar com os 94 bairros oficiais (conferir); células suprimidas ("X") |
| IBGE Censo 2022: Agregados **por setor censitário** | `…/Agregados_por_Setor_csv/` (`Agregados_por_setores_demografia_BR.zip`), malha em `…/malha_com_atributos/`, dicionário `dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx` | Setor (~2.400 no Recife) | Diretório e arquivos listados | Granularidade fina para planejar resgate; soma exata para o bairro oficial por ponto em polígono | Mais supressão; arquivo nacional grande; mais polígonos no mapa |
| IBGE Censo 2022: questionário da **amostra** (deficiência) | `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Microdados_e_Areas_de_Ponderacao/` | Área de ponderação (agrupa vários bairros) | Diretório existe (`Areas_de_Ponderacao/`, `Microdados_de_acesso_Publico/`, `Documentacao/`) | Única fonte pública nacional de deficiência abaixo do município | **Não existe deficiência por bairro**; seria estimativa redistribuída (método a validar); conferir se a variável já está publicada |
| Assistência Social do Recife (CadÚnico, BPC) | Sem conjunto público encontrado; o CKAN do Recife tem só `gerencia-de-promocao-e-defesa-dos-direitos-humanos-divisao-da-pessoa-com-deficiencia` (serviços) | — | Busca no CKAN `dados.recife.pe.gov.br/api/3/action/package_search?q=risco` | Seria o dado mais útil para resgate | Depende de acordo; só **agregado** por bairro (LGPD, RNF-03) |

**Recomendação:** idosos e crianças pelo Censo 2022 por bairro (ou setor, se o casamento de bairros falhar);
deficiência só depois da resposta do cliente (perguntas abertas), sem estimar por conta própria.

## 2. Equipamentos de saúde (e situação)

| Fonte | URL | Verificação | Prós | Contras |
|---|---|---|---|---|
| CNES — API de dados abertos do Ministério da Saúde | `https://apidadosabertos.saude.gov.br/cnes/estabelecimentos?codigo_municipio=261160` | HTTP 200, JSON com `codigo_cnes`, `nome_fantasia`, `codigo_tipo_unidade`, `descricao_esfera_administrativa`, endereço, bairro, latitude/longitude | Nacional, oficial, código CNES estável, atualização mensal | Inclui **consultórios de pessoa física** com nome do profissional e telefone: filtrar por esfera e tipo de unidade e descartar nome e telefone antes da bronze |
| Dados Abertos do Recife — "Rede de Saúde Municipal" | `https://dados.recife.pe.gov.br/dataset/rede-de-saude-municipal` | GeoJSON + metadados (PDF/JSON); modificado em 04/03/2026 | Já georreferenciado; só a rede municipal | Atualização esporádica; conferir se traz CNES para casar |
| Dados Abertos do Recife — conjuntos por tipo | `unidades-basica-de-saude`, `unidades-saude-da-familia-usf`, `maternidades`, `unidades-especializadas`, `farmacias-da-familia` | Listados na busca do CKAN | Mesmo portal do conector de abrigos | Vários arquivos para juntar |
| ESIG Recife (ArcGIS) — `Equipamentos_Saúde` | `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Equipamentos_Sa%C3%BAde/MapServer` | Serviço responde (camada "Equipamentos Saúde") | Mesmo servidor do feed de abrigos do COP | MapServer sem documentação; campos a inspecionar |
| Situação (fechado, danificado) | Nenhuma fonte pública | — | — | Registro da equipe ou de quem a equipe indicar |

**Recomendação:** CNES como cadastro (código estável), enriquecido com a rede municipal do CKAN para coordenadas;
situação por registro da equipe.

## 3. Áreas de risco (deslizamento e alagamento) e relevo

| Fonte | URL | Verificação | Prós | Contras |
|---|---|---|---|---|
| Dados Abertos do Recife — "Defesa Civil" | `https://dados.recife.pe.gov.br/dataset/defesa-civil` | Recursos: "Áreas de Risco da Regional Sul" (CSV), "Coordenadas geográficas da Região Sul" (GeoJSON), dicionário (PDF/JSON); modificado em 02/03/2026 | Oficial do município, já com geometria | **Só a Regional Sul**; o mapeamento completo é da Sedec |
| Defesa Civil do Recife (Sedec) — R3/R4 | Sem URL pública; reportagem de 2024 cita 21 áreas de alto risco com 206 mil pessoas | — | É a classificação usada na operação | Depende de pedido à Sedec |
| Serviço Geológico do Brasil (SGB/CPRM) — setorização de risco | `https://rigeo.sgb.gov.br` e `https://geoportal.sgb.gov.br/geosgb/` | Portais respondem; **não encontrei registro do Recife** (há Igarassu, Camaragibe e outros de PE) | Metodologia nacional, shapefile/KML | Talvez não exista para o Recife |
| IBGE + Cemaden — População em áreas de risco (BATER, 2018) | `https://www.ibge.gov.br/geociencias/organizacao-do-territorio/tipologias-do-territorio/21538-populacao-em-areas-de-risco-no-brasil.html` | Página recusou acesso automatizado (403); **não verificado** | Cruza risco com população | Base do Censo 2010 |
| Histórico de ocorrências (já carregado) | `https://dados.recife.pe.gov.br/dataset/registro-de-atendimentos-da-defesa-civil` | Em uso (`gold.ocorrencias_bairro`) | Real, por bairro | Rótulo fraco (data da vistoria) |
| Relevo — INPE Topodata (MDE 30 m) | `http://www.dsr.inpe.br/topodata/` | HTTP 200 | Nacional, público | 30 m é grosseiro para encostas |
| Relevo — ESIG Recife (`PainelChuvas/MD_APAC`, `pgdbesig_esi2_MD_APAC_v2`, ImageServer) | `https://esigportal2.recife.pe.gov.br/arcgis/rest/services` | Serviços listados | Possível modelo digital local | A confirmar o que é e a licença |

**Recomendação:** começar pelas ocorrências já carregadas + Regional Sul do CKAN; pedir à Sedec o mapeamento R3/R4
de toda a cidade (perguntas abertas). Declividade só com um modelo digital de melhor resolução que o Topodata.

## 4. Achados laterais

- `Assistencial_Social/BASE_ABRIGOS_ATUALIZA` (ESIG): 175 abrigos com `estagio_operacional`, `status`, salas e vagas;
  **sem desabrigados**; traz `coordenador_*` e `contato_*` (dados pessoais: não pedir esses campos).
- `Medicamentos_Unidade/Medicamentos_por_unidade` (ESIG) é empenho de compras da COVID-19, não dispensação.
- O campo `estagio_operacional` do feed `COP/Abrigos_Ativos` é candidato a estágio do COP, mas é por abrigo.
