# Abrigos e pontos de apoio no Recife (lista curada)

Coleta feita em **04/11/2026**. Arquivo: `abrigos-curados.csv` (separador `;`, UTF-8), com **193 locais**.
Os 17 locais do dataset CKAN `abrigos-temporarios-disponiveis` (Ação Inverno 2022) **não** estão duplicados aqui.
Onze deles aparecem porque a camada de 2023 traz informação nova (capacidade, categoria), e a coluna `observacao`
marca "também no CKAN 2022". Os outros seis (27 de Novembro, Igreja Poço da Panela, Igreja Orai, Casa de Dona Érica,
Associação Vila Vintém II, Igreja Batista Córrego do Tiro) existem só no CKAN.

## Fontes

| Fonte | Data | O que cobre | Linhas |
|---|---|---|---|
| Camada ArcGIS pública **ABRIGOS_2023** da Prefeitura do Recife (org. "Prefeitura do Recife Comunidade do Hub"): <https://services7.arcgis.com/pJB1h0yZdGxcwObC/arcgis/rest/services/ABRIGOS_2023___ABRIGOS/FeatureServer/0> | última edição em 13/06/2025 | Cadastro mestre dos locais mapeados para abrigo ou ponto de apoio: 170 locais, sendo 157 abrigos e 13 pontos de apoio (escolas, creches, igrejas, associações). Traz coordenadas, o estágio operacional em que cada local é ativado, a capacidade estimada e um campo STATUS. | 170 |
| **Plano de Contingência Recife 2026** (SEDEC), p. 92 e Anexo 24 / Quadro 17: <https://acaoinverno.recife.pe.gov.br/wp-content/uploads/2026/04/PLANO-DE-CONTINGENCIA-RECIFE-2026__final.pdf> | abr/2026 | 7 abrigos prioritários. Dois deles já ficam preparados: o CSU Bidu Krause, para até 80 pessoas, e o Abrigo Emergencial do Cajueiro, para até 100. O plano diz que há "50 locais mapeados" e até 4,2 mil vagas, mas não publica essa lista de 50. | 1 nova (Cajueiro); as outras 6 viram anotação |
| Folha de PE, 01/05/2026: <https://www.folhape.com.br/noticias/recife-amplia-numero-de-abrigos-e-aumenta-capacidade-para-14mil/484610/> | 01/05/2026 | 12 abrigos abertos, com 1.413 vagas no total | 1 nova; as outras viram anotação |
| Diario de PE, 01/05/2026: <https://www.diariodepernambuco.com.br/vida-urbana/2026/05/11713347-com-chuva-acima-da-media-recife-abre-400-vagas-em-abrigos-emergenciais.html> | 01/05/2026 | 8 abrigos abertos, com cerca de 400 vagas | anotação |
| Folha de PE, 07/04/2026: <https://www.folhape.com.br/noticias/recife-reduz-para-o-estagio-de-atencao-e-retoma-aulas-da-rede/478958/> | 07/04/2026 | 3 abrigos abertos, com 39 pessoas acolhidas | anotação |
| Diario de PE, 15/05/2025: <https://www.diariodepernambuco.com.br/vida-urbana/2025/05/3893653-recife-dispoes-de-dois-abrigos-abertos-para-acolhimento-da-populacao.html> | 15/05/2025 | 2 abrigos abertos (Bidu Krause e Arruda) | anotação |
| Diario de PE, 24/05/2023: <https://www.diariodepernambuco.com.br/noticia/vidaurbana/2023/05/recife-retoma-ao-estagio-de-atencao-e-amplia-para-10-abrigos-temporari.html> | 24/05/2023 | 10 abrigos, com 910 vagas | anotação |
| Folha de PE, 28/05/2022: <https://www.folhape.com.br/noticias/prefeitura-do-recife-abre-escolas-e-creches-para-familias/228480/> | 28/05/2022 | 15 escolas e creches, sem endereço | 5 novas |
| CKAN `rede-de-educacao-municipal` (unidades de ensino 2023): <https://dados.recife.pe.gov.br/dataset/rede-de-educacao-municipal> | 2023 | Endereço e coordenadas das 3 escolas e creches de 2022 que não estão na camada | (geo) |
| CKAN `censo-socioassistencial-2024`, recurso CRAS Dados Gerais: <https://dados.recife.pe.gov.br/dataset/censo-socioassistencial-2024> | 2024 | 16 CRAS. Na fonte, as coordenadas vêm com os separadores corrompidos (ex.: `-8.024.843...`) e foram reconstruídas. Duas coordenadas genéricas (centro da cidade) foram descartadas. | 16 |

Coordenadas: só uma foi geocodificada por nós, a do Abrigo Emergencial do Cajueiro, via Nominatim/OpenStreetMap, com
o número exato do imóvel. Sete locais ficaram sem coordenada.

Dados pessoais: a camada ABRIGOS_2023 e o feed `Abrigos_Ativos` trazem nome e telefone de coordenadores e gestores.
Esses campos **não** foram copiados para o CSV e **não** devem ir para a landing pública.

Outros datasets do CKAN que podem ser úteis: `defesa-civil` (áreas de risco da Regional Sul),
`registro-de-atendimentos-da-defesa-civil`, `centro-comunitario-da-paz-compaz` e `censo-socioassistencial-2024`
(que também tem CREAS, Centro POP e Unidades de Acolhimento, sem endereço útil).
Não existe no CKAN um dataset de NUPDECs ou de pontos de apoio comunitário.

## Status em tempo real (o que existe)

- **Feed oficial "Abrigos Ativos" do COP Recife**:
  `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/COP/Abrigos_Ativos/FeatureServer/0`.
  É a fonte por trás do "Painel Abrigos Ativos – Site Ação Inverno" (item ArcGIS `c209fc20bb4e4e399a21624bb770bd9b`,
  mapa `079c74f2e7764f35ad824df24187f486`), que aparece na seção "Lista de Abrigos Ativos" de <https://acaoinverno.recife.pe.gov.br/>.
  O feed é público e aceita consulta (`/query?where=1=1&outFields=...&f=json`). Em **04/11/2026 ele retornava `count: 0`**,
  ou seja, nenhum abrigo ativo, o que é coerente com o período seco. Os campos incluem `no_entidade`, `endereco`,
  `latitude`/`longitude`, `status`, `estagio_operacional` e as capacidades. Na consulta, peça só os campos não pessoais.
- O campo `STATUS` da camada ABRIGOS_2023 é um retrato de 2025, não o status atual.

## Limitações

- **Uma lista estática não diz que o abrigo está aberto agora.** Os abrigos são ativados conforme o estágio operacional
  (atenção, alerta, alerta máximo). Para a população, a landing deve mostrar "abrigos ativos" só a partir do feed do COP
  e tratar o resto como "locais que podem ser ativados".
- Há endereços divergentes entre as fontes (ex.: Jardim Uchôa, Florestan Fernandes, Água Fria, Luiz Vaz de Camões).
  As divergências estão registradas em `observacao`.
- O Plano 2026 cita 50 locais mapeados, mas publica apenas 7.

## Canais oficiais para a população

- **Defesa Civil do Recife: 0800 081 3400** (gratuito, 24h) e **(81) 3036-4873**. Comprovação: <https://acaoinverno.recife.pe.gov.br/> e a Folha de PE de 01/05/2026 citada acima.
- **WhatsApp da Defesa Civil do Recife**: <https://wa.me/558191171407?text=%23defesacivil> (link publicado em <https://acaoinverno.recife.pe.gov.br/>).
- **Cadastro para alertas (Conecta Recife)**: <https://conecta.recife.pe.gov.br/acesso/minhaspreferencias?go=defesa_civil>. **Central 156** e solicitação de vistoria: <https://conectaservicospublicos.recife.pe.gov.br/>.
- **Defesa Civil de Pernambuco: 199**. Bombeiros 193, SAMU 192, PM 190. Alertas por WhatsApp da Defesa Civil nacional: (61) 2034-4611. Comprovação: <https://agenciabrasil.ebc.com.br/geral/noticia/2026-05/tempestades-em-pe-deixam-quatro-mortos-e-mais-de-mil-desalojados> (02/05/2026).

## Anexo: Região Metropolitana (fora do CSV)

- **São Lourenço da Mata**, 01/05/2026: 7 escolas viraram abrigo (Ariano Suassuna, no Caiara; Josué Pereira, em Barro Vermelho; Vovó Isaura, em Beira Rio;
  Carmela Orrico, em Ettore Labanca; Senador José Esmírio de Moraes, em Tiúma; Luiz Corrêa, no Lot. São João e São Paulo; Clodoaldo Gomes, no Penedo).
  A fonte não dá endereço. <https://www.diariodepernambuco.com.br/vida-urbana/2026/05/11713376-sete-escolas-se-tornam-abrigos-para-moradores-de-sao-lourenco-da-mata-apos-chuvas-intensas.html>
- Em maio de 2022 havia mais de 70 abrigos na RMR: <https://www.folhape.com.br/noticias/regiao-metropolitana-tem-mais-de-70-abrigos-para-desalojados-pela/228521/>. Essa lista não foi extraída.

Script de montagem: não versionado. Os dados foram baixados das URLs acima em 04/11/2026.
