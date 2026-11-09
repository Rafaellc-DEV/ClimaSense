# Prefeitura do Recife (ESIG) — alagamento de 2026: comunidades, lotes e trechos

- **Identificador:** `recife-alagamento-2026`
- **Situação:** Implementada (06/11/2026). RF-02, RF-04, RF-19. Migração 0022.
- **Órgão:** Prefeitura do Recife, portal ESIG. Quem produziu as camadas e com que método não está dito (P-59).
- **Licença:** nenhuma das camadas declara licença. **Não confirmada**: P-32 e P-59 (a enviar à Sedec e à Emprel).
- **Cadência:** retrato de um evento (camadas editadas de 08/05 a 17/06/2026); carga manual
  (`python -m climasense.etl run recife-alagamento-2026`), fora de `etl atualizar`.

## Rótulo obrigatório

> evento de 2026, sem data por registro

Nenhuma das três camadas tem data por registro: é o retrato acumulado de um evento. Não se compara com chuva medida em um dia.
Bairro **sem registro** nas camadas = sem dado, nunca zero (RN-01, RN-02). Zero só aparece onde a fonte o diz
(7 comunidades têm `qtd_registros = 0`).

## Camadas lidas (ArcGIS, sem autenticação, `/query?...&outSR=4326&f=geojson`)

| Camada (`Hosted/...`) | Feições | Campos pedidos | Uso |
|---|---|---|---|
| `Poligonos_Alagamentos_2026_5` | 78 comunidades | `id`, `comunidade`, `rpa`, `qtd_registros` | comunidade alagada; bairro = maior interseção com a malha oficial |
| `Lotes_Areas_Alagadas_2026_V1` | 5.761 lotes | **só `qtdunhab`** (unidades habitacionais) | contagem de lotes e soma de unidades por bairro |
| `Logradouros_Alagamentos_2026_V1` | 552 trechos | **só `fid`** | contagem de trechos por bairro (ponto médio do trecho) |

`qtd_registros`: o significado exato não é documentado na camada (chamados? vistorias?). Aparece como "registros" com essa
ressalva (P-59). A soma por bairro é a das comunidades cuja maior parte está nele; uma comunidade que cruza bairros é atribuída a um só.

### O que NÃO é lido (RN-13, RNF-03)

- **`Base_Celpe_*`**: tem nome de cliente, código de medidor e endereço (P-45). Nunca consultada; o conector nem cita a camada além do aviso.
- Dos **lotes** e **logradouros** não se pede endereço, número, complemento, CEP, inscrição do imóvel, nome do logradouro
  nem tipo de empreendimento (`outFields` é uma lista fechada, nunca `*`).
- **Nenhuma coordenada de lote ou trecho é gravada**, nem na bronze: a posição de um imóvel é dado de residência. Na extração, o ponto
  representativo do lote (ou o ponto médio do trecho) vira o `bairro_id` pela malha oficial e a coordenada é descartada. Só as
  comunidades (polígonos de lugar, com nome público) guardam a geometria, arredondada a 6 casas.
- `Alagamento_2026_V2` (42 polígonos, sem `qtd_registros`) não é usada: é uma versão anterior das mesmas comunidades.
- `pontos_alagamento_arcgis` (54 pontos, campos de risco todos vazios) e `Comunidades_Interesse_Social` não entram (P-54).

## Camadas de dados

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.recife_alagamento_2026` | `registro = consulta` (camada, url, nº de feições, `amostra`, `ultima_edicao_fonte`), `comunidade` (propriedades e geometria), `lote` (`bairro_id`, `qtdunhab`) e `trecho` (`bairro_id`) |
| Silver | `silver.alagamento_2026` | `id` pk (`com-<id>`, `lotes-<bairro>`, `trechos-<bairro>`); `camada` in (`comunidades`, `lotes`, `trechos`); `bairro_id`; `comunidade`, `rpa`; `itens` (1 por comunidade; nº de lotes ou de trechos); `qtd_registros`; `unidades_habitacionais` (soma de `qtdunhab`; nulo se nenhum lote do bairro informa) |
| Gold | `gold.indicador_territorial` | `alagamento_2026_comunidades`, `_registros`, `_lotes`, `_unidades_habitacionais`, `_trechos`; `periodo = 2026`; rótulo acima |
| Gold | `gold.cobertura_indicador` | `bairros_com_dado`, `bairros_com_valor_positivo`, `bairros_total`, `observacao` |

Lote sem `qtdunhab` (739 de 5.761) conta no nº de lotes e **não entra na soma** de unidades (ausente, não zero). Lote ou trecho
fora de qualquer bairro (41 lotes) é descartado e contado. Extração parcial (`--limite`) vira amostra e só grava a bronze (RN-10).

## Cobertura medida (carga real de 06/11/2026, sem banco)

- **45 de 94 bairros** têm algum registro. Por indicador (bairros com dado): comunidades **34**, registros (`qtd_registros`) **34**,
  lotes **37**, unidades habitacionais **36**, trechos de rua **43**.
- Totais: 78 comunidades (soma de `qtd_registros` 19.560), 5.720 lotes em bairro (soma de unidades 10.058), 552 trechos.
- Os outros 49 a 60 bairros, conforme o indicador, ficam **"Dados insuficientes"** (ou "sem registro no retrato de 2026"): a camada lista
  só o que alagou, então ausência não prova que não alagou.

## Frescor

- Limite: 8760 h (12 meses) (`frescor.toml`, chave `recife-alagamento-2026`). O dado envelhece como evento: a tela mostra a data da carga
  e a `ultima_edicao_fonte` da bronze.
