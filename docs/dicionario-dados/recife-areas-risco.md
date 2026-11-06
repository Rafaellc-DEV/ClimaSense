# Prefeitura do Recife (Sedec) — setores de risco

- **Identificador:** `recife-areas-risco`
- **Situação:** Implementada (06/11/2026). RF-04, RF-02. **Cobertura parcial.**
- **Órgão:** Defesa Civil do Recife (Sedec), publicada no portal ESIG da Prefeitura.
- **Acesso:** camada ArcGIS `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted/Setores_Risco_SEDEC/FeatureServer/0`
  (consulta pública, sem autenticação). A carga usa `/query?where=1=1&outFields=...&outSR=4326&f=geojson&returnGeometry=true`
  (GeoJSON direto em WGS84; limite de 2.000 por página, a camada tem 677).
- **Licença:** a camada não declara (nem `copyrightText`); o conjunto equivalente do CKAN da Prefeitura é ODbL. Confirmar
  com a Sedec antes de redistribuir a geometria.
- **Granularidade:** polígono de setor de risco. **Atualização:** sem data na camada; tratada como cadastro de revisão
  rara (anual).
- **Cadência no ETL:** `python -m climasense.etl run recife-areas-risco`.
- **Por que não o CKAN `defesa-civil`:** ele só tem a Regional Sul (CSV + GeoJSON de 02/03/2026), que a camada ESIG já inclui
  (77 setores).

## Campos da camada

| Campo | Uso |
|---|---|
| `cod_setor` | identificador do setor (único; vira `id = sedec-<cod_setor>`) |
| `risco` | grau **R1, R2, R3, R4** da Sedec (`grau`) |
| `regional` | `regional` |
| `bairro` | nome do bairro escrito pela Sedec (sem acento; "Ibura / Cohab"): só serve de apoio ao casamento |
| `localidade`, `edificacoe` (nº de edificações), `area`, `hectares`, `perimeter`, `id` (sempre 0), `fid` | `localidade`/`edificacoe`/`id`/`fid` ficam na bronze, não vão à silver |

A camada **não informa o tipo de perigo** (deslizamento, alagamento). `silver.areas_risco.tipo` recebe o nome do
mapeamento, `setor-de-risco-sedec`. Pergunta P-25.

## COBERTURA REAL (carga de 06/11/2026) — a tela deve rotular "cobertura parcial"

- **677 setores** em **5 regionais**: Noroeste 202, Norte 161, Oeste 120, Nordeste 117, Sul 77. (Não há setores das
  demais áreas, como o Centro.)
- **Graus:** R1 137, R2 133, R3 327, R4 80.
- Bairros que a Sedec cita na camada: **21** (Água Fria, Alto José Bonifácio, Alto Santa Terezinha, Apipucos,
  Beberibe, Bomba do Hemetério, Brejo da Guabiraba, Coqueiral, Córrego do Jenipapo, Dois Irmãos, Dois Unidos,
  Guabiraba, Ibura, Ibura/Cohab, Jordão, Linha do Tiro, Macaxeira, Nova Descoberta, Passarinho, Várzea, Vasco da Gama).
- Bairros **oficiais com pelo menos um setor** pela geometria: **24 dos 94**: Água Fria, Alto José Bonifácio, Alto Santa
  Terezinha, Apipucos, Barro, Beberibe, Bomba do Hemetério, Brejo da Guabiraba, Brejo de Beberibe, Cohab, Coqueiral,
  Córrego do Jenipapo, Dois Irmãos, Dois Unidos, Guabiraba, Ibura, Jordão, Linha do Tiro, Macaxeira, Nova Descoberta,
  Passarinho, Sítio dos Pintos, Várzea, Vasco da Gama. **Os outros 70 bairros não têm dado** (ausência de dado, não
  "sem risco": RN-01).
- Setores por bairro oficial (maior sobreposição): Nova Descoberta 100, Cohab 86, Dois Unidos 66, Várzea 54, Água
  Fria 44, Passarinho 40, Vasco da Gama 37, Linha do Tiro 35, Alto Santa Terezinha 30 e demais abaixo de 23.
- O resumo é impresso a cada carga (`[areas-risco] COBERTURA PARCIAL: ...`).

## Território

`bairro_id` = bairro da malha oficial com **maior área de interseção** com o setor (a Sedec usa fronteiras próprias:
em **148 dos 677** setores o bairro assim obtido difere do nome escrito na camada, por exemplo "Alto José
Bonifácio" sobre o polígono de Alto Santa Terezinha). Setor fora da malha cai para o nome da camada. Setor que cruza
bairros é atribuído a um só; a geometria completa fica em `geometria` (GeoJSON Polygon/MultiPolygon, WGS84,
6 casas decimais).

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.recife_areas_risco` | `registro = consulta` (url, nº de setores) e um `registro = setor` por polígono, com propriedades e `geometry` como vieram |
| Silver | `silver.areas_risco` | `id` (pk), `tipo`, `grau`, `regional`, `bairro_id`, `geometria` (jsonb), `fonte_id`, `execucao_id`; carga completa (apaga e regrava a fonte) |

## Limitações

- **Cobertura parcial:** 24 de 94 bairros (ver acima); o resto é "Dados insuficientes", nunca risco baixo.
- Sem tipo de perigo e sem data de atualização na camada.
- Sem população por setor; a camada traz só o número de edificações (não usado).
- Classificação R1 a R4 é a da Sedec; o sistema não a recalcula nem a reinterpreta (RN-06: prioridade não é
  probabilidade).
- Nada identifica pessoa: só geometria, grau, regional e nome de bairro/localidade.

## Frescor

- Limite: 8760 h (365 dias) (configurado em `backend/climasense/etl/frescor.toml`, chave `recife-areas-risco`; lido por `climasense.etl.frescor`).
- Motivo: mapeamento de risco revisado raramente.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
