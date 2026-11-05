# Alertas oficiais que atingem o Recife (APAC, INMET, Cemaden, IDAP)

- **Identificador:** `alertas-oficiais`
- **Situação:** Implementada (verificada em 04/11/2026; nenhum aviso vigente para o Recife nesse dia)
- **Acesso:** quatro endpoints públicos, sem cadastro, consultados de forma independente (uma origem fora do ar
  aparece em `motivos_descarte` como `origem_indisponivel:<origem>` e não derruba as outras):
  - APAC `https://api.apac.pe.gov.br/api.php/alertas`
  - INMET `https://apiprevmet3.inmet.gov.br/avisos/ativos` (`{hoje, futuro}`)
  - Cemaden `https://painelalertas.cemaden.gov.br/wsAlertas2`
  - IDAP / Defesa Civil Nacional `https://idapfile.mdr.gov.br/idap/api/rss/cap` (Atom com CAP 1.2, ~15 MB; o feed
    guarda ~12 h). XML com DTD/ENTITY é recusado.
- **Cadência:** 10–15 min (`etl tempo-real`).
- **Bronze:** `bronze.alertas_oficiais`: um resumo por consulta (`url`, `bytes`, `sha256`, `itens_pe`, ou `erro`) e
  os avisos que **tocam Pernambuco** (pré-filtro: geocode 26xxxxx, UF PE ou área "/PE"). O feed nacional inteiro
  não vai para a bronze (estouraria o Atlas gratuito). Da APAC saem `corpo_html` e `imagem_base64`.
- **Silver:** `silver.alertas_oficiais` (upsert por `origem` + `codigo_fonte`; guarda `primeira_vez_em` e `visto_em`).

## Filtro geográfico (só o Recife)

| Origem | Aceita quando | `criterio_geo` |
|---|---|---|
| APAC | `regioes_afetadas` contém a mesorregião "Metropolitana de Recife" (lista ou texto repr Python) | `regiao` |
| INMET | `geocodes` contém 2611606, ou o `poligono` GeoJSON intercepta o contorno do Recife | `geocode` / `poligono` |
| Cemaden | `codibge` = 2611606 e `status` = 1 | `geocode` |
| IDAP | `<geocode><valueName>IBGE</valueName><value>2611606` ou um `<polygon>` ("lat,lon …") intercepta o Recife | `geocode` / `poligono` |

O contorno do Recife é a união dos 8 distritos sanitários oficiais. Aviso já vencido na hora da coleta é
descartado (`vencido:<origem>`), o resto vai para `fora_do_recife:<origem>`.

## Campos da silver

| Campo | Origem | Observação |
|---|---|---|
| `origem`, `codigo_fonte` | APAC `numero_aviso_meteorologico`; INMET `codigo` (URN CAP); Cemaden `cod_alerta`; IDAP `identifier` | |
| `evento` | APAC `tipo`; INMET `descricao`; Cemaden `evento`; IDAP `event` | com o nome da origem |
| `nivel` | normalizado: `amarelo`/`laranja`/`vermelho` | APAC AMARELO/LARANJA/VERMELHO; INMET Perigo Potencial/Perigo/Grande Perigo; Cemaden Moderado/Alto/Muito Alto; IDAP Minor+Moderate/Severe/Extreme |
| `nivel_original` | texto da fonte | |
| `emitido_em`, `inicio_em`, `expira_em` | APAC `data_envio`/`data_validade_aviso` (hora local); INMET `created_at`/`inicio`/`fim`; Cemaden `datahoracriacao` (sem validade); IDAP `sent`/`onset`/`expires` | hora local do Recife (UTC−3) quando a fonte não traz fuso |
| `url` | APAC `url_aviso`; IDAP `web`; INMET e Cemaden: página pública do órgão | o link direto do aviso INMET não respondeu em 04/11 |
| `descricao`, `area` | texto e área declarada pela fonte | |

## Uso

`servicos/estagios.alertas_oficiais(territorio, db, agora)` devolve os vigentes (expira no futuro; Cemaden sem
validade: visto nas últimas 2 h), do nível mais alto para o mais baixo. Os filtros são municipais, então o mesmo
aviso vale para todos os territórios do Recife; a tela deve sempre mostrar origem, hora e o link "confira na
APAC/Cemaden" (F7).
