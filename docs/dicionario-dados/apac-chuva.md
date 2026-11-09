# APAC — pluviômetros do Recife (APAC + Cemaden)

- **Identificador:** `apac-chuva`
- **Situação:** Implementada (verificada em 04/11 e 06/11/2026)
- **Acesso:** API pública da APAC, sem cadastro: `https://api.apac.pe.gov.br/api.php` (Swagger em `/swagger.json`).
  Erro vem como `{"erro": ...}` com HTTP 200 e vira falha explicada na execução.
- **Licença:** dados públicos da APAC (sem licença declarada na API); citar "APAC".
- **Cadência:** tempo real a cada 10–15 min (`etl tempo-real`); histórico diário, janela de 2 meses no `atualizar`
  e carga completa desde 2022 com `etl run apac-chuva --modo historico`.
- **Bronze (Mongo):** `bronze.apac_chuva` (resposta de `/precipitacao_acumulada`, uma por estação e execução) e
  `bronze.apac_chuva_historico` (resposta de `/historico_pluviometrico_mensal`, uma por estação e mês, com `_consulta`).
- **Silver (Postgres):** `silver.estacoes` (id `apac-<codigo>`), `silver.apac_chuva_leituras`, `silver.apac_chuva_diaria`,
  `silver.apac_chuva_passos` e `silver.apac_estacoes_cadastro` (migração 0021).
- **Gold:** `gold.chuva_apac_agora` e `gold.chuva_apac_diaria`, por bairro, distrito e Recife; e, da migração 0021,
  `gold.chuva_obs_hora_distrito`, `gold.chuva_obs_72h_distrito` e `gold.estacoes_chuva_status` (ver
  [meteorologia-observada.md](meteorologia-observada.md)).

## Tempo real — `GET /precipitacao_acumulada?municipio=Recife`

| Campo da fonte | Silver | Observação |
|---|---|---|
| `codigo_estacao` | `estacoes.codigo_fonte`, `estacao_id = apac-<código>` | **18 estações** em 06/11/2026 (eram 19 em 04/11): 3 da APAC e 15 do Cemaden republicadas pela APAC. O número varia com o que a API devolve; nunca é fixo |
| `estacao`, `latitude`, `longitude` | `estacoes.nome/lat/lon` | |
| (calculado) | `estacoes.territorio_id` | ponto-em-polígono na malha oficial de bairros (`data/territorio/bairros-do-recife.geojson`, Dados Abertos, conjunto "área urbana"); fora da malha, distrito; fora do Recife, descartada |
| `data_hora_ultima_leitura` | `apac_chuva_leituras.lida_em` | hora local do Recife (UTC−3), gravada em UTC |
| `1_hora`, `3_horas` … `120_horas` | `janela_h` + `valor_mm` | `"-"`, null e negativos = **ausente (nulo), nunca 0** (RN-02) |
| `ultima_medicao` | `apac_chuva_passos.valor_mm` | chuva do último intervalo de 10-15 min da estação; `-1` (erro do sensor) e `"-"` = nulo. Chave (`estacao_id`, `lida_em`): a leitura que se repete entre coletas não duplica |
| (coleta) | `coletado_em`, `visto_em` | `visto_em` é a última coleta que viu aquela leitura |

Uma leitura não se repete: chave (`estacao_id`, `lida_em`, `janela_h`).

## Cadastro das estações — `GET /estacoes?municipio=Recife`

Chamado junto do tempo real; se falhar, a chuva segue sem ele (as estações ficam sem o `status_dados`). Em 06/11/2026
vieram 48 cadastros do Recife, entre eles pluviômetros convencionais e a estação do INMET; entra um por `codigo_gmmc` (o
mesmo código pode vir duas vezes, uma delas vazia: fica a que tem hora de leitura).

| Campo da fonte | Silver (`apac_estacoes_cadastro`) | Observação |
|---|---|---|
| `codigo_gmmc` | `codigo_fonte` | liga com `estacoes.codigo_fonte` |
| `status_dados` | `status_dados` | `atualizada`, `desatualizada`, `em manutenção`, `observação` |
| `tempo_min` | `tempo_min` | minutos desde a última leitura segundo a APAC (nulo se a API não informa) |
| `data_hora_leitura` | `ultima_leitura_em` | hora local gravada em UTC |

## Textos e acentos

Em 06/11/2026 a API entregou os acentos certos: `/estacoes` em UTF-8 com `charset` no cabeçalho e as outras rotas com
escape `\uXXXX`. O "Torre?o" visto na pesquisa era do console do Windows, não da fonte. Mesmo assim o ETL decodifica o
corpo como UTF-8 e repara texto que chegue com U+FFFD ou com UTF-8 lido como Latin-1 (`apac.corrigir_texto`), para
nenhuma estação aparecer com nome quebrado.

**Desatualizada:** leitura com mais de 120 min em relação à coleta mais recente (`max(visto_em)`). Ela continua na
silver, mas fica fora das estatísticas da gold, e o serviço de estágios também a recusa se tiver mais de 120 min
em relação à hora da consulta. Desatualizada não é zero.

## Histórico — `GET /historico_pluviometrico_mensal?dataInicial=&dataFinal=&tipo=diario&municipio=Recife`

| Campo da fonte | Silver (`apac_chuva_diaria`) | Observação |
|---|---|---|
| `codigo_gmmc`, coordenadas | `estacao_id` | também inclui pluviômetros convencionais (ex.: Alto da Brasileira) |
| `dados[].chuva_diaria{AAAA-MM-DD: mm}` | `dia`, `valor_bruto_mm`, `valor_mm` | dia sem chave = sem linha (ausente); dia futuro é ignorado |
| (qualidade) | `qualidade` | `ok`; `falha` = mês da estação com total < 10% da mediana das vizinhas (≥ 2 vizinhas com ≥ 20 dias, mediana ≥ 30 mm), defeito de equipamento provável; `suspeito` = pico isolado ≥ 80 mm quando o dia das vizinhas (≥ 3) fica abaixo de 1/20. Nos dois casos `valor_mm` é nulo e o bruto é guardado |

Cobertura real carregada: 2022 tem só os 2 pluviômetros convencionais; as automáticas entram a partir de 2024.
Carga de 04/11/2026: 14.746 dias válidos, 2.241 em meses de falha, 4 picos suspeitos (estação Campina do Barreto,
jan–abr/2026).

## Gold

- `gold.chuva_apac_agora`: por território, `chuva_24h_max_mm`, `chuva_24h_mediana_mm`, `chuva_1h_max_mm`,
  `n_estacoes`, `n_atualizadas`, `lida_em`, `referencia_em`, `estacoes`. Bairro sem estação atualizada herda do
  distrito; distrito sem estação atualizada herda do Recife. `herdado_de` diz de onde veio (RN-07).
- `gold.chuva_apac_diaria`: por território e dia, `max_mm`, `mediana_mm`, `n_estacoes`, `herdado_de`.
- `gold.chuva_obs_hora_distrito`, `gold.chuva_obs_72h_distrito` e `gold.estacoes_chuva_status`: chuva medida por hora,
  acumulado de 72 h por distrito e estações com e sem leitura. Contrato e regras em
  [meteorologia-observada.md](meteorologia-observada.md).
- Uso: `servicos/estagios.chuva_24h` usa o **máximo** de 24 h do distrito (alerta não confirmado é melhor que
  evento não avisado) e informa `chuva_24h_fontes = ["apac-chuva"]`; sem leitura válida, cai para ERA5 e previsão.

## Limitações

- O acumulado de 24 h termina na última leitura de cada estação, não na hora exata da consulta.
- Uma estação com defeito no tempo real pode inflar o máximo; a mediana fica ao lado para conferência.

## Frescor

- Limite: 1 h (configurado em `backend/climasense/etl/frescor.toml`, chave `apac-chuva`; lido por `climasense.etl.frescor`).
- Motivo: as estacoes atualizam de forma sub-horaria; mais de 1 h indica estacao ou portal parado.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
