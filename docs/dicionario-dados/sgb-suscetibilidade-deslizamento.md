# SGB/CPRM — suscetibilidade do terreno a deslizamento (carta 2012–2014), por bairro

- **Identificador:** `sgb-suscetibilidade-deslizamento`
- **Situação:** Implementada (06/11/2026). RF-02, RF-04, RF-19. Migração 0022.
- **Órgão:** Serviço Geológico do Brasil (SGB/CPRM), carta de suscetibilidade a movimentos gravitacionais de massa e
  inundação do Recife (2015), servida pela Prefeitura do Recife no portal ESIG.
- **Acesso:** camada ArcGIS `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted/Suscebilidade_Deslizamento/FeatureServer/0`
  (sem autenticação). A carga usa `/query?where=1=1&outFields=classe,processo,fonte&outSR=4326&returnGeometry=true&f=geojson`
  (limite de 2.000 por página; a camada tem 489). O nome da camada tem o erro de grafia da fonte ("Suscebilidade").
- **Licença:** a camada não declara licença nem `copyrightText`; o original do SGB consta no RIGEO como acesso aberto, sem
  nome de licença. **Não confirmada**: pergunta P-59 (a enviar à Sedec e à Emprel).
- **Tipo:** derivada (mapa modelado, validado em campo; a fração por bairro é calculada pelo ClimaSense).
- **Cadência:** carta estática (2012–2014, publicada em 2015); a camada foi editada pela última vez em 24/08/2025 (campo
  `editingInfo.lastEditDate`, guardado na bronze como `ultima_edicao_fonte`). `python -m climasense.etl run sgb-suscetibilidade-deslizamento`.
  Não está em `etl atualizar`: carga manual, uma vez.

## O que é e o que não é

**Suscetibilidade do terreno**, modelada em escala 1:45.000. NÃO é setor de risco (R1 a R4 da Sedec, ver
`recife-areas-risco`), NÃO é previsão e NÃO mapeia moradias. Rótulo obrigatório em tela e no relatório:

> suscetibilidade do terreno (carta 2012–2014, escala 1:45.000)

Nunca "risco". Classe "Baixa" ou ausência de "Alta" não significa ausência de ocorrência (RN-01).

## Campos da camada

| Campo | Uso |
|---|---|
| `classe` | `Alta`, `Média` ou `Baixa` (o acento chega quebrado em alguns clientes; o conector tolera). Vira `alta`, `media`, `baixa` |
| `processo` | sempre "Deslizamento" nesta camada; outro valor é descartado (`processo_fora_do_escopo`) |
| `fonte` | texto do SGB ("modelagem validada por trabalho de campo pela CPRM entre 2012 e 2014") |
| `munic?pio`, `uf`, `obs`, `geometria`, `SHAPE__*` | não pedidos (o nome `município` chega com byte quebrado; `obs` é só espaço) |

## Cálculo por bairro

Para cada bairro da malha oficial local (`data/territorio/bairros-do-recife.geojson`, 94 bairros) e cada classe:

`fração = área(bairro ∩ união dos polígonos da classe) / área(bairro)`

em SIRGAS 2000 UTM 25S (EPSG:31985, metros), com `shapely` e `pyproj` (já são dependências do backend). A união por classe
evita contar duas vezes polígonos sobrepostos (medido: 0,0 km² sobrepostos entre classes). A classe `coberta` é a fração do
bairro que a carta cobre com qualquer classe; **o resto do bairro é sem dado, nunca "baixa"**. Bairro que a carta não toca
fica sem nenhuma linha (nenhum caso na carga real).

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.sgb_suscetibilidade_deslizamento` | `registro = consulta` (url, nº de polígonos, `amostra`, `ultima_edicao_fonte`) e um `registro = poligono` por polígono, com `classe`, `processo`, `fonte` e `geometry` como vieram |
| Silver | `silver.suscetibilidade_deslizamento` | `(bairro_id, classe)` pk; `classe` in (`alta`, `media`, `baixa`, `coberta`); `area_km2`; `fracao` (0 a 1); `fonte_id`; `execucao_id`. Carga completa (apaga e regrava a fonte) |
| Gold | `gold.indicador_territorial` | indicadores `suscetibilidade_deslizamento_alta`, `_media`, `_baixa`, `_coberta` (valor = fração, unidade `fracao_da_area_do_bairro`, `periodo = 2012-2014`, `rotulo`, `fonte_id`, `atualizado_em` = hora da carga) |
| Gold | `gold.cobertura_indicador` | por indicador: `bairros_com_dado`, `bairros_com_valor_positivo`, `bairros_total`, `observacao` |

Extração parcial (`--limite`) vira **amostra**: `amostra = true` na bronze, e a silver e a gold anteriores ficam intactas (RN-10).

## Cobertura medida (carga real simulada com a camada de 06/11/2026, sem banco)

- 489 polígonos: Alta 189, Média 104, Baixa 196. Nada descartado. A carta cobre 218,5 km² do município.
- **94 de 94 bairros** têm carta. Cobertura média da carta no bairro: 99,5% (mínimo 80,8%).
- Bairros com **pelo menos 1%** da área na classe: **Alta 22**, **Média 36**, Baixa 94. Com qualquer área positiva: Alta 24,
  Média 39, Baixa 94.
- Maiores frações de "Alta": Brejo de Beberibe 12,0%, Pau Ferro 9,5%, Nova Descoberta 9,4%, Dois Irmãos 8,1%, Cohab 7,9%,
  Passarinho 7,3%, Dois Unidos 6,5%, Guabiraba 6,5% (igual à medição da pesquisa em `docs/pesquisa/api-territorial.md`).

## Limitações

- Escala 1:45.000 e dados de 2012–2014: bom para ordenar bairros por exposição estrutural, não para decidir sobre uma rua.
- "Alta" toca poucos bairros e cobre uma fração pequena de cada (no máximo 12%): a tela deve mostrar a fração e o rótulo, nunca
  uma etiqueta "bairro de alto risco".
- Inundação do SGB (`Inundacao_A`) **não foi integrada**: só existe em shapefile de 107 MB no RIGEO (sem API) e discrimina
  pouco (P-60).

## Frescor

- Limite: 43800 h (5 anos) (`backend/climasense/etl/frescor.toml`, chave `sgb-suscetibilidade-deslizamento`).
- Motivo: carta estática; o relógio mede a última carga bem-sucedida. Sem carga registrada, "Dados insuficientes", nunca "em dia" (RN-01).
