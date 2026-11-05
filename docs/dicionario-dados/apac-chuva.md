# APAC — pluviômetros do Recife (APAC + Cemaden)

- **Identificador:** `apac-chuva`
- **Situação:** Implementada (verificada em 04/11/2026)
- **Acesso:** API pública da APAC, sem cadastro: `https://api.apac.pe.gov.br/api.php` (Swagger em `/swagger.json`).
  Erro vem como `{"erro": ...}` com HTTP 200 e vira falha explicada na execução.
- **Licença:** dados públicos da APAC (sem licença declarada na API); citar "APAC".
- **Cadência:** tempo real a cada 10–15 min (`etl tempo-real`); histórico diário, janela de 2 meses no `atualizar`
  e carga completa desde 2022 com `etl run apac-chuva --modo historico`.
- **Bronze (Mongo):** `bronze.apac_chuva` (resposta de `/precipitacao_acumulada`, uma por estação e execução) e
  `bronze.apac_chuva_historico` (resposta de `/historico_pluviometrico_mensal`, uma por estação e mês, com `_consulta`).
- **Silver (Postgres):** `silver.estacoes` (id `apac-<codigo>`), `silver.apac_chuva_leituras`, `silver.apac_chuva_diaria`.
- **Gold:** `gold.chuva_apac_agora` e `gold.chuva_apac_diaria`, por bairro, distrito e Recife.

## Tempo real — `GET /precipitacao_acumulada?municipio=Recife`

| Campo da fonte | Silver | Observação |
|---|---|---|
| `codigo_estacao` | `estacoes.codigo_fonte`, `estacao_id = apac-<código>` | 19 estações no Recife: 3 da APAC, 16 do Cemaden (republicadas pela APAC) |
| `estacao`, `latitude`, `longitude` | `estacoes.nome/lat/lon` | |
| (calculado) | `estacoes.territorio_id` | ponto-em-polígono na malha oficial de bairros (`data/territorio/bairros-do-recife.geojson`, Dados Abertos, conjunto "área urbana"); fora da malha, distrito; fora do Recife, descartada |
| `data_hora_ultima_leitura` | `apac_chuva_leituras.lida_em` | hora local do Recife (UTC−3), gravada em UTC |
| `1_hora`, `3_horas` … `120_horas` | `janela_h` + `valor_mm` | `"-"`, null e negativos = **ausente (nulo), nunca 0** (RN-02) |
| (coleta) | `coletado_em`, `visto_em` | `visto_em` é a última coleta que viu aquela leitura |

Uma leitura não se repete: chave (`estacao_id`, `lida_em`, `janela_h`).

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
- Uso: `servicos/estagios.chuva_24h` usa o **máximo** de 24 h do distrito (alerta não confirmado é melhor que
  evento não avisado) e informa `chuva_24h_fontes = ["apac-chuva"]`; sem leitura válida, cai para ERA5 e previsão.

## Limitações

- O acumulado de 24 h termina na última leitura de cada estação, não na hora exata da consulta.
- Uma estação com defeito no tempo real pode inflar o máximo; a mediana fica ao lado para conferência.
