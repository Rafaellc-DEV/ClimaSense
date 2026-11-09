# Dicionário de dados

Cada fonte do ClimaSense tem um verbete. **Todas são reais**; as planejadas ainda não têm conector e aparecem como “Planejada” na tela de Fontes (nunca com dados inventados).

| Fonte | Situação |
|---|---|
| [Open-Meteo — Historical Weather (ERA5)](open-meteo-historico.md) | Implementada |
| [Open-Meteo — Forecast](open-meteo-previsao.md) | Implementada |
| [Open-Meteo — Marine](open-meteo-mare.md) | Implementada |
| [Prefeitura do Recife — distritos, bairros e faixas hídricas](territorio-oficial.md) | Implementada |
| [APAC — pluviômetros do Recife (APAC + Cemaden)](apac-chuva.md) | Implementada |
| [APAC — nível dos rios e reservatórios do Capibaribe (ANA como segunda fonte)](apac-rios.md) | Implementada |
| [Meteorologia observada e de modelo: chuva por hora e 72 h, solo, temperatura, tendência e radar](meteorologia-observada.md) | Implementada |
| [Alertas oficiais que atingem o Recife (APAC, INMET, Cemaden, IDAP)](alertas-oficiais.md) | Implementada |
| [Dados Abertos do Recife — atendimentos de alagamento e deslizamento (Defesa Civil)](recife-alagamento.md) | Implementada |
| [InfoDengue — dengue e chikungunya no Recife por semana](infodengue.md) | Implementada |
| [SINAN (DATASUS) — leptospirose no Recife por semana de sintomas](sinan-leptospirose.md) | Implementada |
| [Dados Abertos do Recife — dengue e chikungunya por bairro e ano](recife-arboviroses.md) | Implementada |
| [SAMU Recife — demanda de urgência por semana e bairro (não é caso de doença)](samu-recife.md) | Implementada |
| [SISAGUA (MS) — qualidade da água por bairro e semana, coleta de rotina](sisagua.md) | Implementada |
| [Atlas Digital de Desastres (Sedec/MIDR) — histórico de desastres do Recife](atlas-desastres.md) | Implementada |
| [CNES — equipamentos de saúde do Recife (públicos e SUS)](cnes-equipamentos.md) | Implementada |
| [IBGE — Censo 2022: moradores por bairro e faixa de idade](ibge-censo-2022-bairro.md) | Implementada |
| [Sedec — setores de risco (cobertura parcial)](recife-areas-risco.md) | Implementada |
| [SGB/CPRM — suscetibilidade do terreno a deslizamento, por bairro (94 de 94)](sgb-suscetibilidade-deslizamento.md) | Implementada |
| [Defesa Civil — atendimentos com grau de risco R1 a R4, por bairro e ano](recife-atendimentos-grau-risco.md) | Implementada |
| [Prefeitura do Recife — alagamento de 2026: comunidades, lotes e trechos](recife-alagamento-2026.md) | Implementada |
| [ANA — HidroWebService (telemetria)](ana-telemetria.md) | Planejada |
| [INMET — estação automática A301 (Recife)](inmet.md) | Planejada |
| [Cemaden — pluviômetros automáticos](cemaden.md) | Planejada |
| [Marinha do Brasil — tábua de marés (Porto do Recife)](mare-marinha.md) | Planejada |

**Fonte retirada:** `recife-abrigos` (abrigos e pontos de apoio: Dados Abertos, lista curada e feed de abrigos ativos
do COP) saiu do produto em 06/11/2026 (PRD v3, ADR 0016). O verbete foi apagado; o histórico fica no git. A migração
0019 remove a fonte de `app.fontes`; as coleções bronze `recife_abrigos` e `recife_abrigos_ativos` no Atlas não são
mais alimentadas (destino em P-31).
