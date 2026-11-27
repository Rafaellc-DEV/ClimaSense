# Análise exploratória: chuva, ocorrências e população exposta (insights para a gestão)

Data: 26/11/2026 · Status: **análise, não é requisito** · Pedido do dono do projeto · Complementa
`docs/propostas/dashboards-indicadores.md`

> Pergunta da cliente (Vigidesastres): "Se vier um dia de chuva grande, consigo ver quais áreas estão mais
> vulneráveis, quem são essas pessoas (perfil agregado) e qual impacto a chuva vai ter (alagamentos,
> deslizamentos)?"
>
> Crítica do dono: números sem período ("Ocorrências de alagamento 48 / deslizamento 1.237") não ajudam a reagir.
> Esses dois números são o **total do DS-7 de 01/2014 a 06/2024** (seção 2.1). Sem o período, parecem situação de agora.

Requisitos que a análise toca: RF-04, RF-06, RF-19, RF-22, RF-34, RF-37, RF-38, RF-39, RF-41, RF-42. Regras: RN-01,
RN-02, RN-06, RN-07, RN-11, RN-13. Nada aqui muda o PRD; os pedidos de rota nova estão na seção 7 e dependem do dono.

## 0. Como foi feito

- Leitura **somente SELECT** no banco do produto (Neon), em 26/11/2026, com `climasense.infra.postgres.obter_sessao`
  e transação `read only`. Nada foi gravado. Scripts ficaram fora do repositório (pasta temporária).
- Só dados reais e agregados (bairro, distrito, cidade, dia ou semana). Nenhum dado de pessoa.
- Percentuais desta análise são **parcela de registros** ou **parcela da população** (descrição do passado), nunca
  chance de acontecer (RN-06). Frequências de "dias com ocorrência" estão em contagem ("33 de 40 dias").

### Fontes (códigos usados nas tabelas)

| Código | Fonte | Tabela | Período no banco | Granularidade |
|---|---|---|---|---|
| **DC** | Atendimentos da Defesa Civil do Recife (Dados Abertos, ODbL): alagamento e deslizamento | `silver.ocorrencias` (data = `registrado_em`, dia da vistoria) | 09/01/2014 a 25/06/2024 | bairro e dia |
| **APAC** | Pluviômetros APAC + Cemaden no Recife, acumulado diário | `gold.chuva_apac_diaria` (cidade = maior estação; também mediana) | 01/01/2022 a 26/11/2026 | cidade, distrito, bairro (herdado) |
| **ERA5** | Reanálise ERA5 via Open-Meteo (modelo, não pluviômetro) | `gold.chuva_diaria` | 31/12/2020 a 29/10/2026 | cidade e distrito |
| **IBGE** | Censo 2022, população por faixa etária e bairro | `silver.populacao_bairro` | 2022 | bairro |
| **CNES** | Equipamentos de saúde públicos e SUS | `silver.equipamentos_saude` (271) | carga atual | ponto |
| **SEDEC** | Setores de risco R1 a R4 (Prefeitura do Recife) | `silver.areas_risco` (677 setores) | carga atual | polígono, 24 de 94 bairros |
| **SINAN** | Leptospirose por semana de sintomas | `silver.leptospirose_semanal` | SE 01/2015 a SE de 18/10/2026 | cidade e semana |

Tabelas **vazias** hoje: `gold.desastres_historico` e `silver.desastres_atlas` (Atlas), `silver.alertas_oficiais`,
rios e reservatórios, `silver.suscetibilidade_deslizamento`, `silver.atendimentos_grau_risco`,
`silver.alagamento_2026`, SAMU, SISAGUA, solo.

## 1. Resposta curta

| Parte da pergunta | O que os dados permitem dizer hoje | Período e fonte |
|---|---|---|
| Quais áreas | **Deslizamento:** DS-7, DS-8 e DS-2 (Nova Descoberta, Cohab, Dois Unidos, Passarinho, Córrego do Jenipapo). **Alagamento:** DS-4 e DS-5 (Várzea, Areias, Caxangá, Afogados, Imbiribeira) | DC 2014–06/2024 |
| Quem são | Os 10 bairros com mais deslizamentos somam 284.975 moradores, 40.636 idosos (60+) e 56.256 crianças (0–14) | IBGE 2022 × DC 07/2019–06/2024 |
| Qual impacto | Acima de **50 mm em 24 h** ou **100 mm em 72 h** (maior pluviômetro), os deslizamentos por dia sobem de 2 a 3 para 9 a 29, e o DS-7 concentra metade deles | APAC × DC, 01/2022–06/2024 (907 dias) |
| E depois | Notificações de leptospirose sobem 1 a 2 semanas após semanas de chuva extrema (cidade, não bairro) | SINAN × APAC, 2022–2024 (156 semanas) |

## 2. Onde acontece (a)

### 2.1 Totais por distrito e período

Fonte: DC. "Últimos 5 anos" = 01/07/2019 a 25/06/2024. "Mais recente" = 01/07/2023 a 25/06/2024 (12 meses que
fecham a base; não há atendimento depois de 06/2024, P-42).

| Distrito | Alag. 2014–06/2024 | Desl. 2014–06/2024 | Alag. 5 anos | Desl. 5 anos | Alag. 12 meses finais | Desl. 12 meses finais |
|---|---:|---:|---:|---:|---:|---:|
| DS-1 | 55 | 0 | 37 | 0 | 22 | 0 |
| DS-2 | 566 | 713 | 156 | 481 | 16 | 33 |
| DS-3 | 20 | 199 | 14 | 128 | 8 | 5 |
| DS-4 | 539 | 165 | 295 | 93 | 22 | 0 |
| DS-5 | 323 | 232 | 214 | 182 | 43 | 1 |
| DS-6 | 106 | 0 | 75 | 0 | 25 | 0 |
| DS-7 | 48 | **1.237** | 24 | 836 | 0 | 24 |
| DS-8 | 65 | 720 | 29 | 352 | 6 | 7 |
| **Recife** | **1.722** | **3.266** | **844** | **2.072** | **142** | **70** |

Zero em DS-1 e DS-6 para deslizamento é "nenhum atendimento registrado", não "sem risco" (RN-01/RN-02).

### 2.2 Série anual (cidade)

Fonte: DC, 2014–2024 (2024 só até 25/06).

| Ano | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Alagamento | 100 | 344 | 219 | 26 | 170 | 35 | 8 | 3 | 614 | 82 | 121 |
| Deslizamento | 359 | 350 | 267 | 79 | 60 | 240 | 43 | 285 | **1.372** | 162 | 49 |

Deslizamento por distrito e ano (DC):

| Distrito | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DS-2 | 53 | 106 | 72 | 1 | 0 | 129 | 10 | 116 | 153 | 50 | 23 |
| DS-3 | 34 | 17 | 12 | 8 | 0 | 1 | 0 | 9 | 95 | 19 | 4 |
| DS-4 | 30 | 16 | 13 | 6 | 6 | 25 | 1 | 18 | 40 | 10 | 0 |
| DS-5 | 10 | 20 | 5 | 8 | 3 | 6 | 2 | 37 | 139 | 2 | 0 |
| DS-7 | 112 | 109 | 131 | 20 | 15 | 14 | 23 | 41 | **691** | 60 | 21 |
| DS-8 | 120 | 82 | 34 | 36 | 36 | 65 | 7 | 64 | 254 | 21 | 1 |

**Tendência:** não há tendência linear. A série é feita de **anos-evento**: 2022 sozinho tem 40% de todos os
atendimentos de 10,5 anos (1.986 de 4.988), e 2015/2016 são os outros picos. O que muda o total do ano é a
intensidade do pior episódio, não o número de dias chuvosos: 2022 teve 28 dias pesados e 1.372 deslizamentos; 2023
teve 30 dias pesados e 162 (APAC × DC; dia pesado = 24 h ≥ 50 mm ou 72 h ≥ 100 mm no maior pluviômetro). A
diferença é o 28/05/2022: 190 mm em 24 h e 296 mm em 72 h. Alagamento de 2020 e 2021 (8 e 3) é baixo demais para
anos com chuva normal e parece mudança de registro na fonte (seção 6).

### 2.3 Bairros que mais concentram

Fonte: DC. "Dias com registro" conta dias distintos e corrige lançamentos em lote (seção 6).

| Deslizamento | DS | Registros 2014–06/2024 | Dias com registro | Registros 5 anos |
|---|---|---:|---:|---:|
| Cohab | DS-8 | 483 | 120 | 275 |
| Nova Descoberta | DS-7 | 410 | 116 | 266 |
| Dois Unidos | DS-2 | 392 | 111 | 306 |
| Passarinho | DS-7 | 255 | 77 | 195 |
| Guabiraba | DS-7 | 227 | 81 | 155 |
| Dois Irmãos | DS-3 | 190 | 67 | 120 |
| Barro | DS-5 | 183 | 65 | 142 |
| Várzea | DS-4 | 165 | 53 | 93 |
| Córrego do Jenipapo | DS-7 | 122 | — | 112 |
| Linha do Tiro | DS-2 | 117 | 61 | 76 |

Os 10 primeiros em 5 anos somam 84% dos deslizamentos do período (DC 07/2019–06/2024). Só 29 dos 94 bairros têm
algum registro de deslizamento.

| Alagamento | DS | Registros 2014–06/2024 | Dias com registro | Maior lote em um dia | Registros 5 anos |
|---|---|---:|---:|---:|---:|
| Areias | DS-5 | 182 | 28 | 106 (05/04/2022) | 140 |
| Caxangá | DS-4 | 131 | 28 | 88 | 22 |
| Várzea | DS-4 | 226 | 27 | 44 | 214 |
| Campina do Barreto | DS-2 | 57 | 26 | 25 | — |
| Jardim São Paulo | DS-5 | 41 | 25 | 8 | — |
| Linha do Tiro | DS-2 | 353 | 22 | 135 | 4 |
| Imbiribeira | DS-6 | 40 | 22 | 9 | 38 |
| Ibura | DS-8 | 63 | 18 | 12 | 28 |

71 dos 94 bairros têm algum registro de alagamento. Para alagamento, **use dias com registro**, não registros: Linha
do Tiro tem 353 registros, mas 135 vêm de um único dia.

## 3. Chuva × ocorrências (b)

Janela comum: **01/01/2022 a 25/06/2024 (907 dias)**, onde existem APAC e DC ao mesmo tempo. Chuva da cidade =
**maior pluviômetro** (é o que `/situacao/chuva` usa). Nesse período a rede tinha **2 estações** até 01/2024 e 11 a 14
depois. Ocorrências da cidade por dia, sem registro = 0 registros (não prova que não houve). 1.583 deslizamentos e
817 alagamentos na janela.

### 3.1 Percentis da chuva (para ler os limiares)

APAC, maior estação, 01/2022–06/2024, 907 dias.

| Percentil | p50 | p75 | p90 | p95 | p99 |
|---|---:|---:|---:|---:|---:|
| 24 h (mm) | 2,3 | 10,0 | 27,0 | 44,4 | 85,0 |
| 72 h (mm) | 13,4 | 36,2 | 77,8 | 108,9 | 200,2 |

50 mm em 24 h fica perto do p96; 100 mm em 72 h, perto do p94. São os mesmos limiares de "Alerta" de
`/estagios/parametros` (24 h 25/50/90 mm; 72 h 60/100/150 mm).

### 3.2 Ocorrências por dia em cada faixa de chuva de 24 h

APAC × DC, 01/2022–06/2024. "D ou D+1" conta o dia e o seguinte (a vistoria pode vir depois).

| Chuva 24 h | Dias | Desl./dia | Dias com desl. (D ou D+1) | Alag./dia | Parcela dos desl. | Parcela dos alag. |
|---|---:|---:|---|---:|---:|---:|
| até 5 mm | 560 | 0,41 | 55 de 560 (no dia)* | 0,61 | 14% | 42% |
| 5 a 10 | 121 | 1,64 | — | 0,72 | 13% | 11% |
| 10 a 25 | 127 | 2,35 | — | 0,98 | 19% | 15% |
| 25 a 50 | 59 | 2,88 | — | 0,59 | 11% | 4% |
| **50 a 90** | 31 | **14,55** | — | **4,65** | 28% | 18% |
| **acima de 90** | 9 | **26,22** | 9 de 9 | **9,33** | 15% | 10% |

\* contado só no próprio dia (deslizamento com até 5 mm costuma ser vistoria atrasada de chuva anterior). Com 24 h ≥ 25 mm: 64 de 99 dias tiveram deslizamento
em D ou D+1 (mediana 1). Com ≥ 50 mm: **33 de 40 dias** (mediana 11 por dia). Com ≥ 90 mm: 9 de 9 (mediana 17).

### 3.3 Faixas de chuva de 72 h

| Chuva 72 h | Dias | Desl./dia | Alag./dia | Parcela dos desl. | Parcela dos alag. |
|---|---:|---:|---:|---:|---:|
| até 10 mm | 390 | 0,30 | 0,59 | 7% | 28% |
| 10 a 30 | 252 | 0,42 | 0,52 | 7% | 16% |
| 30 a 60 | 132 | 1,85 | 0,76 | 15% | 12% |
| 60 a 100 | 75 | 2,23 | 0,81 | 11% | 7% |
| **100 a 150** | 33 | **8,52** | **3,12** | 18% | 13% |
| **acima de 150** | 23 | **29,09** | **8,22** | 42% | 23% |

Com 72 h ≥ 100 mm: 44 de 56 dias com deslizamento em D ou D+1; com ≥ 150 mm: 21 de 23.

**Onde dispara:** deslizamento sobe aos poucos a partir de 30 mm em 72 h e **salta** (de 5 a 10 vezes) em
**50 mm/24 h** e **100 mm/72 h**. Alagamento só se separa do ruído acima de 50 mm/24 h ou 100 mm/72 h.

### 3.4 Robustez: sem o evento de maio e junho de 2022

Tirando 20/05 a 10/06/2022 (885 dias restantes, APAC × DC):

| Faixa | Desl./dia | Alag./dia |
|---|---:|---:|
| 24 h 25 a 50 mm | 1,90 | 0,60 |
| 24 h 50 a 90 mm | 5,73 | 2,42 |
| 24 h acima de 90 mm | 10,83 | 6,33 |
| 72 h 60 a 100 mm | 1,25 | 0,85 |
| 72 h 100 a 150 mm | 5,48 | 0,86 |
| 72 h acima de 150 mm | 6,00 | 2,71 |

O salto em 50 mm/24 h e 100 mm/72 h continua (cerca de 3 a 4 vezes), menor. Os números do evento de 2022 são o
teto, não o típico.

### 3.5 Os estágios atuais contra o histórico

Estágio da cidade pela regra de chuva dos parâmetros padrão (24 h 25/50/90 ou 72 h 60/100/150, maior pluviômetro),
aplicada a cada dia de 01/2022–06/2024 (APAC × DC). Sem maré e sem previsão: é só a parte de chuva medida.

| Estágio pela chuva | Dias | Parcela dos dias | Desl./dia | Alag./dia | Parcela dos desl. | Parcela dos alag. |
|---|---:|---:|---:|---:|---:|---:|
| Observação | 737 | 81% | 0,53 | 0,60 | 25% | 54% |
| Atenção | 100 | 11% | 2,11 | 0,44 | 13% | 5% |
| Alerta | 45 | 5% | 5,98 | 3,16 | 17% | 17% |
| Crítico | 25 | 3% | 28,56 | 7,56 | **45%** | 23% |

Os limiares atuais separam bem deslizamento: 8% dos dias (Alerta + Crítico) concentram 62% dos deslizamentos. Para
alagamento separam pior, porque metade dos registros caiu em dias secos (lançamento em lote, seção 6). Isso apoia os
parâmetros atuais (P-06), com a ressalva da rede de 2 estações.

### 3.6 Onde cai o impacto nos dias pesados

Dias pesados (24 h ≥ 50 mm ou 72 h ≥ 100 mm): 70 dias; com o dia seguinte, 97 dias (11% dos 907). Eles somam
**1.076 de 1.583 deslizamentos (68%)** e **347 de 817 alagamentos (42%)** da janela. APAC × DC, 01/2022–06/2024.

| Distrito | Desl. em dias pesados | Parcela | Desl. por 10 mil hab. | Alag. em dias pesados | Parcela | Alag. por 10 mil hab. |
|---|---:|---:|---:|---:|---:|---:|
| DS-7 | 541 | **50%** | **31,2** | 19 | 5% | 1,1 |
| DS-8 | 196 | 18% | 15,3 | 15 | 4% | 1,2 |
| DS-2 | 192 | 18% | 9,1 | 43 | 12% | 2,0 |
| DS-3 | 91 | 8% | 7,0 | 10 | 3% | 0,8 |
| DS-4 | 28 | 3% | 1,0 | **131** | **38%** | **4,6** |
| DS-5 | 28 | 3% | 1,2 | 66 | 19% | 2,7 |
| DS-6 | 0 | 0% | 0,0 | 43 | 12% | 1,8 |
| DS-1 | 0 | 0% | 0,0 | 20 | 6% | 2,7 |

População por distrito: IBGE 2022. Bairros que mais aparecem nesses dias: deslizamento em Nova Descoberta (173),
Cohab (142), Passarinho (121), Dois Unidos (116), Córrego do Jenipapo (99), Dois Irmãos (83); alagamento em Várzea
(87, 25% dos alagamentos de dias pesados), Areias (21), Caxangá (17), Boa Viagem (15), Afogados (15).

Chuva por distrito não foi usada: em 2022–2023 só DS-1 e DS-7 tinham estação própria; os outros herdavam o valor da
cidade (RN-07). A análise é "chuva da cidade → onde caiu o impacto".

### 3.7 Os dias mais chuvosos da janela

APAC (maior estação) × DC.

| Dia | 24 h (mm) | 72 h (mm) | Desl. no dia | Desl. D e D+1 | Alag. no dia |
|---|---:|---:|---:|---:|---:|
| 28/05/2022 | 190,0 | 257,5 | 81 | 221 | 13 |
| 25/05/2022 | 137,4 | 208,2 | 72 | 132 | 15 |
| 07/02/2023 | 122,6 | 235,7 | 4 | 9 | 0 |
| 15/06/2024 | 122,0 | 164,8 | 10 | 10 | 28 |
| 29/04/2024 | 109,7 | 119,4 | 0 | 1 | 0 |
| 22/03/2022 | 105,6 | 109,0 | 45 | 49 | 0 |
| 07/06/2022 | 101,4 | 163,9 | 18 | 31 | 18 |
| 29/05/2022 | 85,2 | 296,1 | 140 | 229 | 1 |

Picos parecidos deram de 9 a 221 deslizamentos: chuva que cai sobre solo já encharcado (72 h alto por vários dias,
como em 25 a 30/05/2022) pesa mais que o pico isolado.

## 4. Quem está exposto (c)

### 4.1 Bairros com mais deslizamento (5 anos)

IBGE 2022 (residentes, não atingidos); CNES (públicos e SUS); SEDEC (setores R3/R4 no bairro); equipamento "em área
de risco" = ponto do CNES dentro de qualquer setor R1–R4 (mesmo cálculo de `/territorios/{id}/resumo-vulnerabilidade`).
Ocorrências: DC 07/2019–06/2024. Média da cidade: 17,8% de idosos 60+ e 17,8% de crianças 0–14 (IBGE 2022).

| Bairro | DS | Moradores | Idosos 60+ | Crianças 0–14 | 0–4 anos | Equip. saúde | Em área de risco | Setores R3/R4 | Desl. 5 anos |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dois Unidos | DS-2 | 31.437 | 4.137 | 6.482 (20,6%) | 2.088 | 4 | 1 | 27 | 306 |
| Cohab | DS-8 | 62.632 | 9.639 | 12.647 (20,2%) | 3.790 | 10 | **8** | 48 | 275 |
| Nova Descoberta | DS-7 | 28.697 | 4.120 | 5.617 | 1.770 | 3 | 1 | **69** | 266 |
| Passarinho | DS-7 | 24.297 | 2.417 | 5.728 (23,6%) | 1.813 | 2 | 2 | 20 | 195 |
| Guabiraba | DS-7 | 11.095 | 1.306 | 2.478 (22,3%) | 795 | 2 | 0 | 2 | 155 |
| Barro | DS-5 | 30.565 | 4.604 | 6.123 | 1.925 | 3 | 0 | 10 | 142 |
| Dois Irmãos | DS-3 | 3.026 | 400 | 586 | 180 | 1 | 0 | 6 | 120 |
| Córrego do Jenipapo | DS-7 | 8.086 | 1.207 | 1.515 | 449 | 0 | 0 | 12 | 112 |
| Várzea | DS-4 | 70.938 | 10.848 | 12.241 | 3.797 | 3 | 1 | 42 | 93 |
| Linha do Tiro | DS-2 | 14.202 | 1.958 | 2.839 | 859 | 1 | 0 | 26 | 76 |
| **Soma** | | **284.975** | **40.636** | **56.256** | | **29** | **13** | | 84% dos desl. |

Perfil: bairros de morro têm **mais crianças** e **menos idosos** que a média (Passarinho 23,6% de 0–14 e 9,9% de
60+).

### 4.2 Bairros com mais alagamento (5 anos)

| Bairro | DS | Moradores | Idosos 60+ | Crianças 0–14 | Equip. saúde | Alag. 5 anos (dias com registro no histórico) |
|---|---|---:|---:|---:|---:|---:|
| Várzea | DS-4 | 70.938 | 10.848 | 12.241 | 3 | 214 (27) |
| Areias | DS-5 | 26.740 | 5.985 (**22,4%**) | 4.288 | 4 | 140 (28) |
| Bomba do Hemetério | DS-2 | 7.728 | 1.369 | 1.381 | 1 | 97 (lote único) |
| Imbiribeira | DS-6 | 52.153 | 8.333 | 9.986 | 6 | 38 (22) |
| Torrões | DS-4 | 31.127 | 4.417 | 6.654 | 6 | 33 (15) |
| Ibura | DS-8 | 45.443 | 6.388 | 9.008 | 10 | 28 (18) |
| Afogados | DS-5 | 31.457 | 5.887 (18,7%) | 5.737 | 5 | 24 |
| Caxangá | DS-4 | 13.813 | 1.689 | 2.706 | 3 | 22 (28) |
| São José | DS-1 | 8.876 | 1.106 | 2.006 | 0 | 21 (14) |
| Boa Viagem | DS-6 | 125.755 | **29.987 (23,8%)** | 17.220 | 5 | 15 |
| **Soma** | | **414.030** | **76.009** | **71.227** | **43** | 75% dos alag. |

Perfil: a planície que alaga tem **mais idosos** (Areias, Afogados, Boa Viagem acima da média), o que muda a
logística: idosos pedem retirada assistida; morros com crianças pedem escola e creche no plano.

### 4.3 Unidades de saúde em setores de risco

CNES × SEDEC, carga atual. 271 equipamentos; **26 dentro de algum setor de risco R1–R4**, 4 dentro de R3/R4.

| Distrito | Em setor de risco | Destaques (tipo e bairro) |
|---|---:|---|
| DS-8 | 12 | 7 UBS na Cohab, 3 no Ibura, 1 no Jordão; UPA da Cohab |
| DS-7 | 9 | UBS em Brejo de Beberibe (R3/R4), Nova Descoberta (R3/R4), Macaxeira (R3/R4), Passarinho (2), Vasco da Gama (2); **UPA de Brejo de Beberibe** |
| DS-2 | 3 | UBS em Bomba do Hemetério, Água Fria, Dois Unidos |
| DS-4 | 2 | UBS na Várzea (R3/R4); UPA da Caxangá |

Os setores cobrem só 24 de 94 bairros (DS-2, DS-3, DS-4, DS-5, DS-7, DS-8). Unidade fora de setor mapeado não é
unidade segura (RN-01). Sem fonte de unidade fechada ou danificada (RF-14).

## 5. Quando acontece (d)

### 5.1 Meses críticos

| Mês | Jan | Fev | Mar | Abr | Mai | Jun | Jul | Ago | Set | Out | Nov | Dez |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Desl. (DC 2014–06/2024) | 33 | 83 | 220 | 343 | **913** | **897** | 519 | 119 | 109 | 8 | 5 | 17 |
| Alag. (DC 2014–06/2024) | 67 | 181 | 263 | **414** | 209 | **370** | 106 | 20 | 67 | 14 | 10 | 1 |
| Dias pesados (APAC 01/2022–11/2026) | 10 | 13 | 11 | 18 | **28** | **27** | 9 | 7 | 1 | 1 | 0 | 1 |
| Leptospirose notificada (SINAN 2015–2025) | 137 | 199 | 211 | 243 | 337 | **609** | 442 | 233 | 158 | 136 | 101 | 100 |

Maio a julho = 71% dos deslizamentos (2.329 de 3.266); março a junho = 73% dos alagamentos (1.256 de 1.722). Outubro a
dezembro quase não têm registro. A leptospirose segue a chuva com cerca de um mês: pico em junho e julho.

### 5.2 Janela de leptospirose depois de chuva extrema

Cidade inteira (não há leptospirose por bairro). Semanas epidemiológicas fechadas (sem semanas incompletas ou
preliminares, que começam em 29/12/2024).

| Medida | APAC mediana das estações, 01/2022–12/2024 (156 semanas) | ERA5, 01/2021–12/2024 (208 semanas) |
|---|---|---|
| Correlação de postos (Spearman) chuva × confirmados, mesma semana | 0,39 | 0,39 |
| Idem, 1 semana depois | 0,50 | 0,46 |
| Idem, 2 semanas depois | **0,51** | 0,43 |
| Idem, 4 semanas depois | 0,28 | 0,29 |
| Semanas de chuva extrema (≥ p95) | 8 semanas (≥ 162 mm) | 11 semanas (≥ 72 mm) |
| Notificados nas 4 semanas seguintes: após chuva extrema × demais | **112 × 22** | 83 × 19 |
| Confirmados nas 4 semanas seguintes | 42 × 8 | 31 × 7 |

Evento de 2022 (SINAN, semana iniciada em): 22/05 → 16 notificados; 29/05 → 40; **05/06 → 132** (61 com exposição a
enchente); 12/06 → 80; 19/06 → 38; volta a menos de 20 em meados de julho. O pico veio **1 a 2 semanas** após o
pior dia de chuva e o excesso durou cerca de 5 semanas, coerente com a janela de 30 dias da NT 138/2022 já usada em
`/saude/resumo` e com as "até 6 semanas" de RF-39. Correlação é coincidência temporal, não prova de causa (RF-39).
Junho de 2024 (122 mm em 15/06) não teve pico visível (9 a 10 notificados por semana): o efeito aparece em evento com
alagamento extenso, não em qualquer dia de chuva forte.

## 6. Qualidade dos dados (e)

| Tema | O que achamos | Efeito | Período e fonte |
|---|---|---|---|
| Fim do histórico de ocorrências | Último atendimento em 25/06/2024. Depois disso houve 56 dias pesados (24 h ≥ 50 mm ou 72 h ≥ 100 mm), incluindo o evento de abril e maio de 2026, sem nenhuma ocorrência na base | Toda "ocorrência" no produto é **retrato de 2014 a 06/2024** e precisa dizer isso na tela | DC; APAC 26/06/2024–26/11/2026 (P-42) |
| Data é da vistoria | `ocorrido_em` é nulo; `registrado_em` é o dia da vistoria | Desloca o registro para D+1 ou mais tarde | DC |
| Lançamento em lote (alagamento) | 106 registros de Areias em 05/04/2022, 97 de Bomba do Hemetério em 01/04/2022, 135 de Linha do Tiro em um dia, 44 da Várzea em 27/06 e 22/09/2022, todos com menos de 6 mm de chuva | 42% dos alagamentos da janela caem em dias com até 5 mm. Para alagamento, contar **dias com registro**, não registros | DC × APAC 2022–2024 |
| Mudança de registro | Alagamento em 2020 = 8 e 2021 = 3; 32 meses sem nenhum atendimento entre 2014 e 2023 | Série anual de alagamento não serve para tendência | DC |
| Rede de pluviômetros | Cidade com 2 estações de 01/2022 a 01/2024; 11 a 19 depois. Maior estação sobe quando a rede cresce | Limiares calibrados com 2 estações; contagem de dias pesados depois de 2024 não é comparável com antes | APAC |
| Chuva por distrito | Na janela com ocorrências, só DS-1 e DS-7 têm estação própria; DS-2 a DS-6 a partir de 02/2024, DS-8 de 04/2026 | Não dá para calibrar limiar por distrito | APAC |
| ERA5 suaviza | p99 de 24 h = 30 mm no ERA5 contra 85 mm na APAC; ERA5 tem só 3 dias acima de 50 mm em 2021–2024 | ERA5 serve para mês e semana, não para gatilho diário | ERA5 × APAC |
| Amostra pequena nos extremos | 9 dias acima de 90 mm e 23 acima de 150 mm em 72 h; um evento (maio de 2022) pesa muito | Números de "Crítico" são teto; mostrar faixa e não ponto | APAC × DC |
| Áreas de risco | 24 de 94 bairros; nada em DS-1 e DS-6 | "Em área de risco" é mínimo, não total | SEDEC |
| Equipamentos | 55 dos 271 pontos do CNES caem em Santo Amaro (DS-1 com 97) | Possível endereço administrativo ou geocodificação; conferir antes de usar "unidades por bairro" no DS-1 | CNES |
| Leptospirose | Só cidade e semana; desde 29/12/2024 as semanas estão preliminares | Sem "onde"; só "quando" | SINAN |
| Tabelas vazias | Atlas de desastres, alertas oficiais, rios, reservatórios, suscetibilidade SGB, grau R3/R4 dos atendimentos, alagamento de 2026, SAMU, SISAGUA | Impacto oficial (desalojados, danos) não está disponível hoje | banco em 26/11/2026 |
| Deficiência | Não existe por bairro (P-41) | "Dados insuficientes" no perfil | IBGE |

**O que falta para responder a pergunta inteira:** (1) atendimentos da Defesa Civil de 07/2024 em diante (P-42),
sem isso não há como validar nada de 2025 e 2026; (2) carregar o Atlas (impacto oficial por evento) e a suscetibilidade
SGB (cobre os 94 bairros, RF-37); (3) chuva por distrito com série longa (só existe desde 2024); (4) leptospirose
por distrito (convênio, P-38 a P-40); (5) deficiência por bairro.

## 7. Insights de gestão

Cada um com o dado, o período e a fonte. Percentual = parcela dos registros, não chance.

| Nº | Insight | Suporte | Período e fonte |
|---|---|---|---|
| G-01 | **Gatilho de deslizamento: 50 mm em 24 h ou 100 mm em 72 h.** Acima disso, deslizamentos por dia vão de 2 a 3 para 9 a 29; em 33 de 40 dias com ≥ 50 mm houve deslizamento no dia ou no seguinte | Seções 3.2 e 3.3; 907 dias | APAC × DC, 01/2022–06/2024 |
| G-02 | **Em dia pesado, metade dos deslizamentos é no DS-7.** DS-7, DS-8 e DS-2 somam 86%; pré-posicionar equipes em Nova Descoberta, Passarinho, Córrego do Jenipapo, Cohab e Dois Unidos | 541 + 196 + 192 de 1.076 | APAC × DC, 01/2022–06/2024 |
| G-03 | **Em dia pesado, alagamento é DS-4 e DS-5** (57% dos registros), com a Várzea sozinha em 25% | 131 + 66 de 347; Várzea 87 | APAC × DC, 01/2022–06/2024 |
| G-04 | **Acumulado de 72 h pesa mais que o pico.** 72 h acima de 150 mm (23 dias, 3% dos dias) concentrou 42% dos deslizamentos; dias com mais de 120 mm em 24 h deram de 9 a 221 deslizamentos (D e D+1), conforme o solo vinha encharcado | Seções 3.3 e 3.7 | APAC × DC, 01/2022–06/2024 |
| G-05 | **Os estágios atuais funcionam para deslizamento.** Alerta + Crítico = 8% dos dias e 62% dos deslizamentos. Manter os limiares e acompanhar com mais estações (P-06) | Seção 3.5 | APAC × DC, 01/2022–06/2024 |
| G-06 | **Perfil por tipo de área.** Morros com deslizamento: mais crianças (Passarinho 23,6% de 0–14) e menos idosos. Planície que alaga: mais idosos (Boa Viagem 29.987 idosos, 23,8%; Areias 22,4%). Plano de crianças nos morros, retirada assistida de idosos na planície | Seções 4.1 e 4.2 | IBGE 2022 × DC 07/2019–06/2024 |
| G-07 | **Quem está exposto nos 10 bairros de deslizamento:** 284.975 moradores, 40.636 idosos e 56.256 crianças, em 29 unidades de saúde, 13 delas em setor de risco | Seção 4.1 | IBGE 2022, CNES, SEDEC, DC 07/2019–06/2024 |
| G-08 | **Unidades de saúde dentro de área de risco: 26** (12 no DS-8, 9 no DS-7), incluindo as UPAs de Brejo de Beberibe e Cohab. Checar acesso e plano de contingência dessas unidades antes da quadra chuvosa | Seção 4.3 | CNES × SEDEC, carga atual |
| G-09 | **Quadra crítica: maio e junho.** 55% dos deslizamentos de 10 anos (1.810 de 3.266) e 55 dos 126 dias pesados desde 2022 caíram nesses dois meses; preparar equipes e estoques em abril | Seção 5.1 | DC 2014–06/2024; APAC 01/2022–11/2026 |
| G-10 | **Leptospirose: vigilância ativa 1 a 2 semanas depois do evento, por 5 semanas.** Após semanas de chuva extrema, 112 notificações nas 4 semanas seguintes contra 22 nas demais; em 2022 o pico (132) veio 8 dias após o pior dia | Seção 5.2 | SINAN × APAC, 2022–2024 (156 semanas) |
| G-11 | **Todo número de ocorrência precisa do período.** "Deslizamento 1.237" é o DS-7 de 01/2014 a 06/2024; nos 12 meses finais da base foram 24. A tela deve dizer "2014 a jun/2024 · Defesa Civil" ou mostrar o ano | Seção 2.1 | DC |
| G-12 | **O histórico parou em 06/2024 e houve 56 dias pesados depois.** Pedir à Sedec os atendimentos de 2024 a 2026 (P-42) é a ação de dados mais valiosa: sem eles não se valida nada da cheia de 2026 | Seção 6 | DC; APAC 06/2024–11/2026 |

## 8. Como a tela responde num dia de chuva grande

Três passos, na tela do Mapa (sem tela nova; ver P-61 sobre a página Dashboards).

| Passo | Pergunta da equipe | O que mostrar | Rotas |
|---|---|---|---|
| 1. Quanto vai chover e se passa do gatilho | "É dia de deslizamento?" | Chuva medida 24 h e 72 h (maior estação e por distrito) e prevista 24 h e 72 h, contra os limiares (25/50/90 e 60/100/150), com "faltam X mm para Alerta". Frase fixa: "Acima de 50 mm em 24 h ou 100 mm em 72 h, o histórico de 2022 a 2024 teve deslizamento em 33 de 40 dias (Defesa Civil × APAC)". Selo Experimental na previsão | `/situacao/chuva`, `/estagios`, `/estagios/parametros` (existem) |
| 2. Onde | "Onde mando equipe?" | Distritos e bairros ordenados por estágio sugerido; ao lado, **o histórico em dias pesados com período**: "DS-7: 50% dos deslizamentos em dias pesados (2022 a jun/2024)". Separar cor de deslizamento (morro) e alagamento (planície) | `/cenarios/impacto-previsto`, `/territorios/prioridades` (existem); a parcela em dias pesados exige rota nova |
| 3. Quem e o que vem depois | "Quem está lá e o que preparo?" | Por bairro em alerta: moradores, idosos, crianças, unidades de saúde e quantas em setor de risco; aviso de leptospirose: "vigilância de 1 a 2 semanas após o evento, por até 6 semanas" | `/cenarios/impacto-previsto` (`pessoas_vulneraveis_em_alerta`), `/territorios/{id}/resumo-vulnerabilidade`, `/saude/resumo` (existem) |

Regras da tela: cada número com fonte e "até quando vai o dado" (RF-19, RF-42); ocorrência sempre como "registros de
2014 a jun/2024"; sem dado = "Dados insuficientes. Falta: ..."; estágio como classe, nunca percentual; idosos e
crianças são residentes, não atingidos.

### 8.1 O que já sai dos endpoints e o que exigiria rota nova

| Número desta análise | Hoje | Observação |
|---|---|---|
| Chuva 24 h e 72 h medida e prevista × limiares | **Sim**: `/situacao/chuva`, `/estagios`, `/estagios/parametros` | — |
| Pessoas e unidades de saúde nos bairros em alerta | **Sim**: `/cenarios/impacto-previsto`, `/territorios/{id}/resumo-vulnerabilidade` | resumo dá a contagem em área de risco, não a lista nem o grau |
| Total de ocorrências por bairro **com período** | **Sim, falta mostrar**: `/ocorrencias/historico` já devolve `periodo_inicio`, `periodo_fim`, `dias_com_registro`; `/territorios/prioridade` devolve `desde` | correção só no frontend (resolve a crítica do "48 / 1.237") |
| Dias com registro em vez de registros (alagamento) | **Sim**: `dias_com_registro` em `/ocorrencias/historico` | frontend |
| Janela de leptospirose | **Sim**: `/saude/resumo` | — |
| Sazonalidade da chuva | **Sim**: `/series/sazonalidade`, `/series/referencia` | ERA5 e anos desde 2021 |
| Ocorrências por ano, por mês ou "últimos 12 meses" por distrito e bairro | **Não** | rota nova: `GET /ocorrencias/serie?tipo=&nivel=&de=&ate=` lendo `silver.ocorrencias` (só contagens) |
| Ocorrências por faixa de chuva e parcela por distrito em dias pesados | **Não** | rota nova `GET /ocorrencias/por-chuva` ou tabela gold estática gerada pelo ETL (`gold.ocorrencias_faixa_chuva`); muda pouco, pode ser estudo fixo em `docs/ml/` exibido como referência |
| Unidades de saúde em área de risco com nome e grau | **Parcial** | ampliar `resumo-vulnerabilidade` com a lista (CNES, tipo, grau do setor) |
| Leptospirose depois de evento comparada à linha de base | **Não** | RF-39 (fase 2), depende de evento registrado (RF-41) |

Nada disso está decidido. Para não construir fora do PRD: as duas rotas novas se apoiam em RF-34, RF-38 e RF-41
(episódios retrospectivos), mas precisam de pergunta própria em `docs/perguntas-abertas.md` (sugestão: **P-62**,
"o painel deve mostrar o impacto histórico por faixa de chuva e por período?") antes de qualquer código.
