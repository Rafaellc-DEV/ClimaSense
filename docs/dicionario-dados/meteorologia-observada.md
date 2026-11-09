# Meteorologia observada e de modelo (RF-36)

- **Identificadores:** `apac-chuva` (chuva medida, ver [apac-chuva.md](apac-chuva.md)), `apac-previsao`,
  `open-meteo-temperatura` e `open-meteo-solo`.
- **Situação:** Implementada (migração 0021; verificada em 06/11/2026 com respostas gravadas em
  `backend/tests/unit/etl/fixtures/`).
- **Natureza de cada dado (nunca se mistura):**

| Indicador | Natureza | Fonte | Selo |
|---|---|---|---|
| Chuva acumulada em 72 h por distrito | **Medida** (pluviômetros APAC e Cemaden) | `apac-chuva` | — |
| Chuva por hora por distrito | **Medida**, só a partir do início da coleta | `apac-chuva` | — |
| Umidade do solo e sua classe | **Modelo** (ECMWF IFS e ERA5-Land) | `open-meteo-solo` | **Experimental** (RN-11) |
| Temperatura do ar | **Previsão** de modelo | `open-meteo-temperatura` | previsão |
| Temperatura, umidade e chuva horárias do Recife | **Previsão** oficial | `apac-previsao` | previsão |
| Tendência de chuva da mesorregião Metropolitana | **Contexto** (categoria diária) | `apac-previsao` | contexto |
| Radar (URL e hora da imagem) | **Contexto** | `apac-previsao` | contexto |

Temperatura **medida** não existe sem token do INMET (P-36): a tela mostra "Dados insuficientes" para ela e nunca usa o
modelo no lugar. Nada aqui vira percentual de risco (RN-06).

## 1. Chuva medida

### 1.1 Acumulado de 72 h por distrito — `gold.chuva_obs_72h_distrito`

Uma linha por distrito (`nivel = 'distrito'`) e uma do município (`nivel = 'municipio'`, id `recife`). Vem de `72_horas` da
última leitura de cada estação (`silver.apac_chuva_leituras`, `janela_h = 72`).

| Coluna | Significado |
|---|---|
| `territorio_id`, `nivel` | distrito (`ds-N`) ou município |
| `status` | `com_leitura`, `sem_leitura` (há estação, mas nenhuma com leitura recente) ou `sem_pluviometro` |
| `chuva_72h_max_mm`, `chuva_72h_mediana_mm` | entre as estações **com leitura recente**; nulos nos outros status |
| `n_estacoes`, `n_com_leitura`, `n_sem_leitura` | estações do distrito que já tiveram leitura no tempo real; `n_com_leitura + n_sem_leitura = n_estacoes` |
| `lida_em` | hora da leitura mais recente que entrou na conta (UTC) |
| `referencia_em` | última coleta (`max(visto_em)`) usada como "agora" |
| `estacoes` | ids das estações do distrito |

Regras:

- **Leitura recente** = no máximo 120 min mais velha que a coleta mais recente, e `72_horas` presente.
- **Distrito sem pluviômetro próprio não herda do Recife**: `status = sem_pluviometro`, valores nulos e `n_estacoes = 0`
  (RN-01, RN-02). Quem herda do distrito ou do município é só a `gold.chuva_apac_agora` (24 h), que continua como estava.
- Sem nenhuma coleta da APAC na silver, a tabela fica **vazia** (nem "sem pluviômetro" se afirma sem ter coletado): a
  tela mostra "Dados insuficientes: falta a fonte apac-chuva".
- Estação com leitura antiga sai da conta (o valor fica nulo, nunca zero).
- O valor do distrito é o **máximo** entre as estações (alerta não confirmado é melhor que evento não avisado); a mediana
  fica ao lado para conferência.

### 1.2 Série horária — `gold.chuva_obs_hora_distrito`

Construída **daqui para frente**: soma, por hora e estação, de `ultima_medicao` das leituras únicas que chegam a cada
10–15 min (`silver.apac_chuva_passos`). Nada do passado é preenchido, nem com modelo.

| Coluna | Significado |
|---|---|
| `territorio_id`, `hora_inicio` | distrito e início da hora (timestamptz; hora local = UTC−3) |
| `chuva_max_mm`, `chuva_mediana_mm` | maior valor e mediana, entre as estações **com leitura na hora** (mm, 2 casas) |
| `n_estacoes` | estações do distrito que já tiveram leitura (hoje, não na hora) |
| `n_com_leitura` | estações com ao menos uma leitura medida na hora |
| `n_completas` | estações com 4 ou mais leituras na hora (`gold.LEITURAS_POR_HORA_COMPLETA`) |
| `primeira_leitura_em`, `ultima_leitura_em` | horas das leituras que entraram (UTC) |
| `estacoes` | ids das estações com leitura na hora |

Regras:

- **Hora sem leitura não tem linha** (lacuna, nunca zero). Leitura sem valor (`-`, `-1`) não entra: nem a soma nem a
  contagem. Zero medido entra como zero.
- Se `n_completas < n_com_leitura`, o valor da hora é um **mínimo medido** (faltou leitura no intervalo): a tela diz "pelo
  menos X mm".
- Convenção de hora: a leitura das 22:00 fecha o intervalo que termina às 22:00 e entra na hora das 21:00 (hipótese;
  pergunta P-55). O passo de 10 min da `ultima_medicao` também precisa de confirmação da APAC.
- A gold é recalculada inteira a cada coleta (cresce com o histórico gravado: cerca de 1.700 passos por dia com 18
  estações). Se pesar, passa a janela móvel.

### 1.3 Estações com e sem leitura — `gold.estacoes_chuva_status`

| Coluna | Significado |
|---|---|
| `estacao_id`, `nome`, `distrito_id`, `bairro_id` | estação e onde ela está (bairro nulo se só casou com o distrito) |
| `situacao` | `com_leitura`, `sem_valor` (leitura recente sem `72_horas`) ou `leitura_antiga` (mais de 120 min) |
| `lida_em`, `referencia_em` | última leitura e coleta de referência |
| `status_dados`, `tempo_min` | do cadastro da APAC (`atualizada`, `desatualizada`, `em manutenção`, `observação`); nulos se a rota `/estacoes` falhou ou a estação não consta |

Em 06/11/2026: 18 estações, 15 com leitura recente, 3 antigas (Campina do Barreto 08:20, Imbiribeira 13:10, Torreão 16:00).
Os cadastros fora do tempo real (convencionais, em manutenção) não aparecem aqui: estão em `silver.apac_estacoes_cadastro`.

### 1.4 Contrato para a API (`servicos/situacao_chuva.py` não foi alterado)

`situacao_chuva.py` continua lendo `gold.chuva_apac_agora`, `gold.chuva_apac_diaria` e a silver
`apac_chuva_leituras`, e seus campos seguem válidos (`chuva_72h_mm` = máximo de `72_horas` das leituras recentes do
distrito; `estacoes_com_leitura` e `estacoes_sem_leitura`; série observada de 1 h, que usa `1_hora` da APAC).
As tabelas novas são o contrato para a API/serviço que trocar esse cálculo:

| O que a tela precisa | Onde ler | Se faltar |
|---|---|---|
| 72 h do distrito | `gold.chuva_obs_72h_distrito.chuva_72h_max_mm` com `status = 'com_leitura'` | "Dados insuficientes: falta a fonte apac-chuva neste distrito" (`sem_pluviometro`) ou "sem leitura nas últimas 2 h" (`sem_leitura`) |
| Estações do distrito | `n_com_leitura`, `n_sem_leitura`, `n_estacoes` da mesma linha | idem |
| Hora da última leitura | `lida_em` (e `referencia_em` para a coleta) | — |
| Barras horárias do distrito | `gold.chuva_obs_hora_distrito` (`chuva_max_mm`, `hora_inicio`), hora ausente = sem barra | lacuna na série, nunca zero; avisar que a série começa na data da primeira linha (`min(hora_inicio)`) |
| Quais estações estão paradas | `gold.estacoes_chuva_status` (`situacao`, `status_dados`) | — |

Fonte do selo e do rodapé: `apac-chuva` (`app.fontes`), com a hora da última execução bem-sucedida.

## 2. Umidade do solo — modelo, Experimental (`open-meteo-solo`)

- **Acesso:** `api.open-meteo.com/v1/forecast` (ECMWF IFS; `past_days=2`, `forecast_days=3`) e
  `archive-api.open-meteo.com/v1/archive` (ERA5-Land; atraso de 5 a 7 dias), sem chave, CC BY 4.0. Termos: P-46.
- **Pontos:** um por distrito sanitário (ponto representativo da geometria oficial), como os demais conectores Open-Meteo.
- **Camadas:** `soil_moisture_0_to_7cm` → `0_7cm` e `soil_moisture_7_to_28cm` → `7_28cm`, em m³/m³ (a mesma camada na
  previsão e no histórico). Fora de 0 a 1 ou nulo: a hora não vira linha (contada nos descartes).
- **Modos:** padrão `previsao` e `--modo historico` (janela móvel de 45 dias no `atualizar`; a carga completa desde
  2021 é `etl run open-meteo-solo --modo historico`).
- **Bronze (Mongo):** `bronze.open_meteo_solo` e `bronze.open_meteo_solo_historico`, um documento por ponto e execução, com
  as séries da resposta (acumulativa, RN-09).
- **Silver:** `silver.solo_modelo_horario` (última emissão de cada hora; chave território, camada e hora) e
  `silver.solo_modelo_diario` (média diária UTC do ERA5-Land; só dia com 24 h).
- **Gold:** `gold.solo_modelo_distrito`, uma linha por distrito e camada:

| Coluna | Significado |
|---|---|
| `valor_24h_m3m3`, `n_horas` | média das últimas 24 h do modelo até a última emissão; nula com menos de 20 h |
| `percentil` | posição (0–100) da média entre as médias diárias do histórico **do próprio ponto**; nulo com menos de 365 dias de histórico |
| `p25_m3m3`, `p75_m3m3`, `p90_m3m3`, `n_historico_dias` | limites e tamanho do histórico |
| `classe` | `seco` (< P25), `normal` (P25 a < P75), `umido` (P75 a < P90), `muito_umido` (≥ P90); nula sem percentil |
| `natureza`, `selo` | sempre `modelo` e `experimental` |

A tela deve mostrar "Estimativa de modelo, Experimental" e nunca "medida". Sem histórico suficiente: "Dados insuficientes:
histórico do ponto curto (open-meteo-solo)".

Limitações: o modelo tem resolução de dezenas de km e não conhece solo urbano impermeabilizado; o percentil compara o
IFS (previsão) com o ERA5-Land (histórico), que não têm a mesma calibração (P-58); não há medida local para validar.

## 3. Temperatura — previsão

- **`open-meteo-temperatura`:** `temperature_2m` do modelo, `silver.observacoes` com `variavel = 'temp_c'`,
  `tipo = 'prevista'`, `emitido_em` e `horizonte_h` (`forecast_days=3`, `past_days=1`; as horas passadas têm horizonte 0).
  Toda emissão fica acumulada (como a previsão de chuva).
- **`apac-previsao` → `silver.apac_previsao_horaria`:** previsão oficial horária de 5 dias do Recife (`temperatura_c`,
  `umidade_pct`, `precipitacao_mm`), uma linha por hora prevista com a última coleta (`coletado_em`) e o `codigo_recebido`.
  **Validação antes de gravar:** o lote só entra se `municipio` for Recife, `codigo_municipio` for 2611606 (IBGE) ou 2612000
  (o que a APAC devolve para o Recife) e as coordenadas caírem na caixa do Recife; qualquer outro lote (como Pombos, que a
  API devolve para o código IBGE) é descartado inteiro e contado em `previsao_de_outro_municipio_ou_codigo_invalido`. P-56.
- A previsão por período do INMET (`apiprevmet3/previsao/2611606`) não foi integrada nesta entrega.

## 4. Tendência de chuva e radar (contexto de aviso, não é chuva medida)

Ambos pela rota pública da APAC, no conector `apac-previsao`; cada rota falha sem derrubar as outras
(`rota_indisponivel:<rota>` nos descartes).

- **`/tendencia_precipitacao` → `silver.apac_tendencia_chuva`:** só a mesorregião Metropolitana. `categoria` (ex.:
  "Sem chuva"), `faixa_mm` (ex.: "<2 mm"), `dia`, `atualizado_em` (hora da APAC). Chave (mesorregião, dia).
- **`/radar_meteorologico` → `silver.apac_radar`:** `data_referencia`, posição do radar e as URLs de `acumulado_1h`,
  `acumulado_24h` e `cappi_1km`. **Só a URL e a hora são guardadas; a imagem nunca é baixada.** URL só vale se for `https` e do
  domínio `.apac.pe.gov.br`. A API devolve as últimas 10 imagens (a cada 10 min). A hora da imagem: P-57.
- Para a API: a tela mostra "Fonte: APAC · hora" com `data_referencia` (radar) ou `atualizado_em` (tendência). Sem linha,
  "Dados insuficientes: falta a fonte apac-previsao".

## Frescor (RF-19)

| Fonte | Limite | Motivo |
|---|---|---|
| `apac-chuva` | 1 h | pluviômetros sub-horários (ver [apac-chuva.md](apac-chuva.md)) |
| `apac-previsao` | 2 h | roda no `etl tempo-real` (10–15 min); o radar sai a cada 10 min |
| `open-meteo-temperatura` | 6 h | modelo reprocessado a cada 6 h, como a previsão de chuva |
| `open-meteo-solo` | 6 h | previsão a cada 6 h; o histórico entra no mesmo `atualizar` |

Limites em `backend/climasense/etl/frescor.toml`. Sem dado registrado, o indicador mostra "Dados insuficientes", nunca
"em dia" (RN-01).

## Privilégios e reprodutibilidade

O papel `climasense_app` só tem SELECT nas tabelas novas. A gold é recalculada só por SQL a partir da silver e entra em
`gold.verificar` (reproduzível, CA-04).
