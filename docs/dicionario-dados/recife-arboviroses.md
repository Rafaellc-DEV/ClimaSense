# Dados Abertos do Recife — dengue e chikungunya por bairro e ano

- **Identificador:** `recife-arboviroses`
- **Situação:** Implementada (05/11/2026)
- **Acesso:** CKAN `https://dados.recife.pe.gov.br/api/3/action/package_show?id=casos-de-dengue-zika-e-chikungunya`.
  Um CSV por agravo e ano: dengue 2013–2025, chikungunya 2015–2025 (zika fica de fora). O download redireciona
  para uma URL assinada de 1 h (`ckan-storage-download.app.emprel.gov.br`); o conector segue o redirecionamento.
- **Órgão:** Secretaria de Saúde do Recife. **Licença:** ODbL.
- **Granularidade:** bairro de **residência** × ano (ano do arquivo publicado).
- **Atraso:** publicação anual. 2025 saiu em 03/2026; **em 11/2026 não há nada de 2026**.
- **Cadência:** no `atualizar`, no máximo a cada 30 dias.

## Formatos

Dois layouts convivem (o conector reconhece pelos nomes de coluna, sem diferenciar maiúsculas):

| Anos | Bairro | Classificação | Residência | Separador |
|---|---|---|---|---|
| dengue 2021–2025, chik 2021–2025 | `NM_BAIRRO` (2023: `nm_bairro`) | `CLASSI_FIN` | `ID_MN_RESI` | `;` |
| dengue 2013–2020, chik 2015–2020 | `no_bairro_residencia` | `tp_classificacao_final` | `co_municipio_residencia` | `;` (2015 e 2019: `,`) |

Códigos vêm às vezes como `10.0`; são normalizados.

## Minimização (LGPD)

Cada linha dos CSVs é um caso com **logradouro, CEP, data de nascimento e número da notificação**. O conector lê o
arquivo em memória e o **agrega na hora** por (bairro escrito na fonte, classificação final). A bronze recebe só:

- um resumo por arquivo: `agravo`, `ano`, `url`, `atualizado_em`, `sha256`, `linhas`, `colunas`,
  `colunas_sensiveis_descartadas` (só os nomes) e `motivos` de descarte;
- contagens `bairro_fonte` × `classificacao` → `n`.

Nenhuma linha individual é gravada em lugar nenhum.

## Classificação final

| Agravo | Confirmado | Descartado | `outros` |
|---|---|---|---|
| dengue | 10 (dengue), 11 (sinais de alarme), 12 (grave); código antigo 1, 2, 3, 4 | 5 | 8 (inconclusivo), em branco |
| chikungunya | 13 | 5 | 8, em branco e os códigos 1 e 2 dos arquivos de 2015–2016 (não pertencem ao agravo; **não interpretados**) |

Atenção: o recurso "Casos confirmados de Chikungunya" traz também descartados; sempre filtrar pela classificação.

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.recife_arboviroses` | resumos e contagens |
| Silver | `silver.arboviroses_bairro_ano` | `agravo`, `ano`, `bairro_fonte`, `territorio_id` (nulo se não casar), `notificados`, `confirmados`, `descartados`, `outros`, `fonte_atualizada_em`; carga completa |
| Gold | `gold.arboviroses_bairro_ano` | por bairro oficial: `casos` (= confirmados), `notificados`, `distrito_id` |

Bairro: o nome escrito é normalizado e casado com os 94 bairros oficiais pelo mesmo critério da Defesa Civil
(`climasense/ml/alagamento/ocorrencias.py`). Em branco ou grafia truncada ("GRAAS", "VAR\EA") fica com
`territorio_id` nulo: entra no total da rota (`confirmados_sem_bairro`), nunca no mapa.

## Limitações

- Retrato histórico para planejamento; **não serve para o pós-evento** (sem 2026).
- Endereço de residência, não local da infecção.
- Bairros pequenos com poucos casos mudam muito de posição de um ano para o outro.
- 2015 de chikungunya tem 68% das linhas sem bairro.
- Os códigos de distrito 546 e 547 dos arquivos recentes não estão na "Tabela Distrito"; o distrito usado é o do
  bairro oficial, não o da fonte.

## Frescor

- Limite: 9600 h (400 dias) (configurado em `backend/climasense/etl/frescor.toml`, chave `recife-arboviroses`; lido por `climasense.etl.frescor`).
- Motivo: publicacao anual.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
