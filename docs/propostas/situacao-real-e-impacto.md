# Situação real e impacto por área: diagnóstico, análise chuva × maré × rio × alagamento e proposta de telas

Data: 26/11/2026 · Status: **proposta e análise, não é requisito** · Pedido do dono do projeto · Complementa
`analise-insights-gestao.md` (chuva × ocorrências), `dashboards-indicadores.md`, `mapa-v2.md` e `inspiracao-frontend.md`.

> Pedido do dono: "quero que as telas mostrem melhor a visualização e a situação real, não apenas informem alguns
> dados". Exemplo dele: cruzar nível do mar e maré, chuva e alagamentos históricos nas mesmas áreas para ver o impacto
> real. Pedido adicional: incluir o nível dos rios (Capibaribe, Beberibe, Tejipió, Jiquiá) e os reservatórios a
> montante (Carpina, Tapacurá, Goitá).
>
> Pergunta mais frequente da cliente: "Num dia de chuva grande, consigo ver quais áreas estão mais vulneráveis, quem são
> essas pessoas (perfil agregado) e qual o impacto que a chuva vai ter (alagamentos, deslizamentos)?"

Requisitos tocados: RF-01, RF-02, RF-06, RF-07, RF-09, RF-19, RF-20, RF-22, RF-23, RF-25, RF-29, RF-34, RF-35, RF-36,
RF-37, RF-38, RF-40, RF-41, RF-42 e PRD §8.2 ("índice de impacto em pessoas"). Regras: RN-01, RN-02, RN-05, RN-06,
RN-07, RN-11, RN-13. Decisões e perguntas: D-19, P-06, P-22, P-33, P-35, P-42, P-49, P-61. **Nada aqui muda o PRD nem
autoriza código**; o que não está no PRD vira pergunta (seção 9).

## 0. Resumo

1. **Diagnóstico.** As telas respondem "quanto choveu e qual o estágio", mas não respondem "o que isso vai causar,
   onde e para quem". O dado existe em pedaços (estágio, chuva, maré, idosos, unidades, ocorrências), mostrado como
   números soltos, alguns sem período ("deslizamento 1.237" é o DS-7 de 2014 a jun/2024) e um deles enganoso (seção 2.2).
2. **Maré, como está hoje, não discrimina nada.** A regra "maré ≥ 0,6 m a até 3 h do pico de chuva sobe um nível" é
   verdadeira em **93,6% dos dias** (a maré passa de 0,6 m quase todo dia) e disparou em **69 de 99 dias** com chuva
   ≥ 25 mm em 2022–2024. A pergunta "A maré agrava a chuva?" dos Dashboards responde "Sim" quase sempre.
3. **O "nível do mar" do produto é tábua de maré, não nível observado.** A série do Open-Meteo Marine é reproduzida
   por ajuste harmônico com R² de 0,993 (erro de 5 cm): não tem efeito de vento e pressão, e o ponto servido fica a
   cerca de 17 km da costa.
4. **Chuva × maré × alagamento (Defesa Civil × APAC, 904 dias de 2022 a jun/2024):** controlando a chuva, a maré **não
   mostrou efeito mensurável** no alagamento por distrito, nem em DS-4, DS-5, DS-6 e DS-1. Os piores eventos (maio e
   junho de 2022, 15/06/2024) foram em maré intermediária ou de quadratura. O que antecede alagamento é **chuva
   acumulada em 72 h** (seção 3). Há um sinal fraco de **alagamento sem chuva em preamar de sizígia** (9 de 12
   bairro-dias secos com registro, 2014–2024), amostra mínima.
5. **Rios:** o banco não tem nenhuma leitura (cargas nunca concluíram), mas a API pública da APAC devolve a **série
   diária desde 2010** da estação de referência (São Lourenço da Mata, a montante). Com o Capibaribe ≥ alerta (300 cm),
   bairros ribeirinhos tiveram alagamento em **16 de 37 dias**, contra **70 de 2.421** com o rio abaixo de 200 cm. Mas
   bairros não ribeirinhos sobem junto: o rio alto marca **chuva regional grande**, não um efeito só dos ribeirinhos
   (seção 4). Os dois maiores picos (499 cm em 28/05/2022 e 474 cm em 01/05/2026) ocorreram **com Tapacurá abaixo do
   vertedouro**.
6. **Proposta central:** trocar "números soltos" por **quatro leituras de situação**: (a) mapa de impacto previsto por
   bairro (classe, separando alagamento e deslizamento); (b) linha do tempo de 72 h com chuva, maré (faixa de sizígia,
   não 0,6 m) e rio contra as cotas oficiais, com marcador "agora"; (c) "da última vez que choveu assim" (eventos
   parecidos no passado, com período e fonte); (d) quem está na área afetada (moradores, idosos, crianças e unidades de
   saúde dentro das classes alto e muito alto). Detalhe na seção 6.
7. **Prioridade de dados:** atendimentos da Defesa Civil de 07/2024 a 2026 (P-42) continuam sendo o dado mais valioso;
   sem eles não se valida nada recente. Depois: lista georreferenciada dos pontos críticos de alagamento da Emlurb,
   ligação bairro → rio (P-49) e carga das fontes APAC de rios e reservatórios (com D-19/P-33 resolvidos).

## 1. O problema, relido

### 1.1 O que a cliente precisa ver num dia de chuva grande

| Pergunta da equipe | De onde vem (PRD §2) | O que é "situação real" | Hoje no produto |
|---|---|---|---|
| "Vai ser grave?" | Cenário demora 1–2 h para montar | Chuva medida e prevista **contra os gatilhos**, com o histórico do que acontece acima deles | Números de chuva e estágio sugerido; sem o "o que acontece acima disso" |
| "Onde vai pesar?" | Estágio único para a cidade; cada bairro é afetado de um jeito | Bairros coloridos pelo impacto **previsto**, separando morro (deslizamento) e planície (alagamento) | Cor por estágio sugerido (mesma regra para os dois perigos) ou por prioridade histórica |
| "Quem está lá?" | Sem mapa de vulneráveis e áreas de risco | Moradores, idosos, crianças e unidades de saúde **dentro da área afetada** | Por bairro, ao clicar; soma só no Dashboards (`pessoas_vulneraveis_em_alerta`) |
| "Da última vez que foi assim, o que aconteceu?" | Desconfiança de alerta automático; falta de memória dos eventos | Eventos parecidos no passado: chuva, maré, rio, onde houve ocorrência | **Não existe** |
| "Maré e rio vão piorar?" | Foco v3/v4: chuva, maré, rios | Maré alta perto do pico **com limiar calibrado**; rio de referência contra as cotas oficiais | Regra de maré quase sempre ligada; rios "Ainda não disponível" |
| "Posso confiar?" | Alerta com localização errada | Fonte, hora, cobertura e o que falta, junto de cada leitura | Bem resolvido (RF-19, RF-42) |

### 1.2 Personas e contexto de uso

Duas usuárias (Mariana Siqueira e Mariana Lima) que **só consomem dados**, trabalham muito pelo celular e pelo
WhatsApp e precisam montar cenário em menos de 1 hora (PRD §3). Isso pede **frases e mapas que já dizem a leitura**
("DS-7 acima do gatilho de deslizamento; da última vez, 33 de 40 dias assim tiveram deslizamento"), não grades de
números para interpretar.

## 2. Avaliação crítica da solução atual

Leitura de `backend/climasense/api/routers/` e `frontend/src/features/` em 26/11/2026 (Dashboards em redesenho por
outro agente; avaliação do conteúdo, não do layout).

### 2.1 Por tela

| Tela | O que já responde | O que só "informa dados" | Lacunas |
|---|---|---|---|
| **Mapa** (`features/mapa`) | Estágio sugerido e declarado por bairro e distrito; estágio do COP; painel do bairro com idosos, crianças, unidades e áreas de risco; "Prioridade é onde agir primeiro, não chance" | Painel do bairro é uma grade de contagens (moradores, equipamentos, ocorrências) sem dizer o que significam hoje; ocorrências sem período na tela | Não há cor por **impacto previsto** por tipo de perigo; não há camada de rio nem de maré; não diz "este bairro, em dias como hoje, teve registro em X de Y dias" |
| **Dashboards** (`features/dashboards`, P-61) | Decisões pendentes, falta para o próximo estágio, pessoas em bairros em alerta, contexto do histórico com período | "A maré agrava a chuva?" responde com a regra de 0,6 m (seção 2.2); KPIs de contagem | Sem rios (cartão "Ainda não disponível"); sem "eventos parecidos"; sem pessoas e unidades por classe de impacto |
| **Situação do evento** (`features/situacao`) | Estágio do COP, chuva medida e prevista, maré máxima, gráfico chuva × maré com marcador "agora" e faixa de incerteza, chuva por distrito, mensagem de WhatsApp | Maré mostrada como "máxima de 72 h" sem leitura (sizígia ou não, coincide com o pico ou não) | Sem rios e reservatórios (RF-35); a linha do tempo não mostra faixas de risco nem o passado medido junto do previsto |
| **Simulador** (`features/simulador`) | Premissas (chuva, acumulada, maré, horizonte), classe de alagamento e deslizamento por bairro, estágio por distrito, ordem de atenção, arboviroses como contexto | Evidências em texto longo por bairro ("Insumos da previsão atual…") | Não compara o cenário com eventos reais parecidos; não soma pessoas e unidades expostas por classe; a maré usa o mesmo limiar não calibrado |

### 2.2 Problemas transversais

| Nº | Problema | Evidência | Efeito na leitura |
|---|---|---|---|
| T-1 | **Limiar de maré de 0,6 m não discrimina** | `dominio/estagio.py:65` e `dominio/cenario.py:28` (o próprio código diz "não foi calibrado"). A maré máxima diária passa de 0,6 m em 93,6% dos dias (2014–2026) | O estágio sobe um nível quase sempre que chove forte; "A maré agrava a chuva?" vira "Sim" fixo. Alerta inflado sem base (contra o princípio "explicável") |
| T-2 | **"Nível do mar" é maré astronômica de modelo** | Open-Meteo Marine em (-8,04; -34,71), ~17 km da costa; ajuste harmônico 2023–2025 com R² 0,993 e erro de 4,9 cm; validação em 2026 com erro de 5,3 cm | Não captura maré meteorológica (vento, pressão). Rotular como "maré prevista (tábua calculada)", não "nível do mar" |
| T-3 | **Referência de altura diferente da que a equipe usa** | Produto: metros acima do nível médio (máx. ~1,6 m). Tábua da Marinha (Porto do Recife): metros acima do nível de redução (preamar de sizígia ~2,5 m) | "Maré de 1,1 m" no painel e "maré de 2,4 m" no jornal são a mesma maré. Confunde quem lê |
| T-4 | **Ocorrências param em 25/06/2024** (P-42) | `silver.ocorrencias`: alagamento 16/01/2014 a 25/06/2024; 56 dias pesados depois disso, incluindo abril e maio de 2026, sem registro | Todo "histórico" é retrato de 2014 a jun/2024; tem de dizer isso em cada número |
| T-5 | **Rios sem nenhum dado no banco** | `silver.rios_leituras`, `gold.rio_situacao`, `gold.reservatorio_situacao`: 0 linhas; 9 execuções `em_andamento` presas por fonte desde 13/11 | RF-35 inteiro em "Dados insuficientes", embora a APAC sirva a série |
| T-6 | **Cor única de "estágio" para dois perigos** | `/estagios` mistura gatilhos de chuva, maré e histórico de qualquer tipo | Morro e planície reagem diferente (análise anterior: DS-7 concentra 50% dos deslizamentos de dias pesados; DS-4 e DS-5, 57% dos alagamentos) |
| T-7 | **Nenhuma tela olha para trás** | Não há rota de "eventos parecidos" | A equipe não consegue ancorar o alerta no que já aconteceu, que é o que gera confiança |

## 3. Análise: chuva × maré × alagamento por área

### 3.1 Como foi feito

- **Somente leitura.** Banco do produto (Neon) com `climasense.infra.postgres.obter_sessao` em transação `READ ONLY`
  (só SELECT; nada gravado; sem segredos impressos). Scripts e arquivos baixados ficaram no scratchpad, fora do
  repositório.
- **Fontes:**

| Código | Fonte | Período usado | Granularidade |
|---|---|---|---|
| DC | Atendimentos da Defesa Civil (`silver.ocorrencias`, data = dia da vistoria) | 2014 a 25/06/2024 | bairro e dia |
| APAC | Chuva medida, maior pluviômetro da cidade (`gold.chuva_apac_diaria`, `recife`) | 01/2022 a 11/2026 | cidade e dia |
| ERA5 | Reanálise horária (Open-Meteo Archive, ponto do Recife), para a **hora do pico** e o período 2014–2021 | 2014 a 06/2024 | cidade e hora |
| MARÉ | Open-Meteo Marine `sea_level_height_msl` (real de 22/11/2022 em diante; antes, reconstrução harmônica com o mesmo método de `ml/alagamento/clima.py`, ajustada em 2023–2025) | 2014 a 11/2026 | hora |

- **Classes de maré** (tercis da maré máxima diária, 2014–2026): **quadratura** < 0,86 m; **intermediária** 0,86 a
  1,11 m; **sizígia** ≥ 1,11 m (acima do nível médio). Percentis: p10 0,64; p50 0,99; p90 1,31; máximo 1,64 m.
- **Alvo:** dia com registro de alagamento no dia D ou D+1 (a vistoria atrasa), na cidade, na planície (DS-1, DS-4,
  DS-5, DS-6) ou por distrito. Para alagamento, conta-se **dia com registro**, não número de registros (lotes, ver
  `analise-insights-gestao.md` §6).
- **Controle negativo:** deslizamento. A maré não pode causar deslizamento; se aparecer "efeito" da maré nele, é viés.

### 3.2 A regra atual de maré

| Medida | Valor |
|---|---|
| Dias com maré máxima ≥ 0,6 m (2014–2026) | **93,6%** |
| Horas com maré ≥ 0,6 m | 27,8% |
| Dias com chuva APAC ≥ 25 mm em que a maré passou de 0,6 m a até 3 h do pico de chuva (ERA5) | **69 de 99** |
| Alagamento (D ou D+1) nesses 69 dias | 15 de 69 |
| Alagamento nos 30 dias em que a regra **não** disparou | 10 de 30 |
| Maré no pico ≥ 1,0 m: alagamento | 7 de 29 (abaixo de 1,0 m: 18 de 70) |
| Maré no pico ≥ 1,1 m: alagamento | 2 de 16 (abaixo: 23 de 83) |

Leitura: com chuva forte, o histórico **não** tem mais alagamento quando a maré está alta perto do pico. A regra de
0,6 m sobe o estágio em dois terços dos dias chuvosos sem ganho de acerto.

### 3.3 Chuva × classe de maré (APAC × DC, 03/01/2022 a 24/06/2024, 904 dias)

Maré real em 573 dias e reconstruída em 331. Dias com alagamento na cidade: 70; na planície: 60; com deslizamento: 220.
Formato: dias com registro / dias na célula.

**Alagamento, cidade**

| Chuva 24 h (APAC) | Quadratura | Intermediária | Sizígia |
|---|---|---|---|
| 0 a 5 mm | 2 de 201 | 11 de 163 | 13 de 194 |
| 5 a 25 mm | 5 de 73 | 8 de 86 | 6 de 88 |
| 25 a 50 mm | 2 de 17 | 2 de 23 | 4 de 19 |
| ≥ 50 mm | **7 de 16** | **7 de 14** | **3 de 10** |

**Alagamento, planície (DS-1, DS-4, DS-5, DS-6)**

| Chuva 24 h (APAC) | Quadratura | Intermediária | Sizígia |
|---|---|---|---|
| 0 a 5 mm | 2 de 201 | 10 de 163 | 7 de 194 |
| 5 a 25 mm | 5 de 73 | 7 de 86 | 6 de 88 |
| 25 a 50 mm | 2 de 17 | 2 de 23 | 3 de 19 |
| ≥ 50 mm | 7 de 16 | 7 de 14 | 2 de 10 |

**Dias com chuva ≥ 25 mm (99 dias), por distrito**

| Alvo | Quadratura (33 dias) | Intermediária (37) | Sizígia (29) |
|---|---|---|---|
| DS-1 | 8 | 2 | 4 |
| DS-2 | 8 | 8 | 6 |
| DS-4 | 9 | 8 | 5 |
| DS-5 | 9 | 8 | 4 |
| DS-6 | 9 | 5 | 4 |
| DS-7 / DS-8 (alag.) | 2 / 5 | 1 / 0 | 0 / 0 |
| Cidade, alagamento | 9 | 9 | 7 |
| Cidade, deslizamento (controle) | 26 | 21 | 17 |

**Modelo logístico** (alvo diário; chuva 24 h e 72 h em log; maré máxima padronizada). Coeficiente da maré, em
desvios-padrão (z): cidade +1,67; planície +0,62; DS-4 +0,36; DS-5 +0,58; DS-6 +0,44; DS-1 −0,07; DS-2 +1,06.
Controle (deslizamento): **+2,00**. Só dias com chuva ≥ 10 mm: alagamento −0,25; planície −0,58. Com controle de
estação chuvosa (março a agosto): alagamento +1,65; deslizamento +1,70. **Nenhum efeito da maré se separa do
ruído**, e o controle negativo mostra o mesmo tamanho de "efeito", sinal de confusão com a estação (a maré média
mensal é maior de fevereiro a maio).

**Robustez com ERA5, 2014 a 06/2024 (3.828 dias, 234 com alagamento).** z da maré: alagamento +2,6; planície +1,9;
deslizamento +1,1. O sinal vem dos dias **secos ou de chuva fraca** (≤ p50 da chuva: 15 de 653 em quadratura, 22 de 666
em intermediária, 34 de 644 em sizígia). Nos dias mais chuvosos (> p97) não sobe: 12 de 28, 16 de 50, 8 de 36.

### 3.4 Alagamento sem chuva em maré de sizígia

Bairro-dias com alagamento e menos de 1 mm de chuva (ERA5) no dia e no anterior, 2014 a 06/2024: **12**, dos quais
**9 em sizígia** (Linha do Tiro, Ibura, Iputinga, Areias, Boa Viagem, bairro do Recife, Beberibe, Jardim São Paulo,
Várzea). É coerente com alagamento por maré em áreas baixas e estuarinas, mas a amostra é mínima e pode ser vistoria
atrasada. Vale pergunta à Defesa Civil e à Emlurb (seção 9).

### 3.5 Dias pesados (24 h ≥ 50 mm ou 72 h ≥ 100 mm) por classe de maré

| Classe de maré | Dias pesados | Com alagamento (D ou D+1) | Registros de alagamento | Registros de deslizamento | Chuva 24 h mediana |
|---|---|---|---|---|---|
| Quadratura | 32 | 10 | 280 | 438 | 46,6 mm |
| Intermediária | 24 | 11 | 285 | 1.235 | 54,0 mm |
| Sizígia | 14 | 5 | 29 | 199 | 59,8 mm |

Exemplos (APAC × DC × maré): 28/05/2022, 190 mm e maré 1,08 m (intermediária), 14 alagamentos e 221 deslizamentos em D
e D+1; 30/05/2022, maré 1,07 m, 91 alagamentos (71 no DS-4); 07/06/2022, 101 mm e maré 0,76 m (quadratura), 53
alagamentos; 15/06/2024, 122 mm e maré 0,64 m (quadratura), 28 alagamentos; 07/02/2023, 123 mm em sizígia (1,22 m), 0
alagamentos registrados.

Depois de 06/2024 houve **56 dias pesados sem nenhuma ocorrência na base** (P-42). Os maiores: 06/02/2025 (165 mm,
quadratura), 02/05/2026 (147 mm, intermediária 1,08 m), 15/05/2025 (143 mm, intermediária), 13/01/2025 (122 mm,
sizígia 1,20 m).

### 3.6 O que a análise permite e o que não permite dizer

| Pode dizer | Não pode dizer |
|---|---|
| A chuva acumulada em 72 h é o melhor sinal de alagamento e de deslizamento (z de 4 a 6 em todos os recortes) | Que maré alta "piora" o alagamento por chuva no Recife: o dado diário não mostra |
| A regra de maré de 0,6 m não discrimina e infla o estágio | Que a maré não importa: a resolução é diária, a maré é astronômica de modelo (sem maré meteorológica) e o registro é da vistoria, não da hora do alagamento |
| Há indício (12 casos) de alagamento sem chuva em preamar de sizígia em bairros baixos | Qual a "combinação chuva × maré que antecede alagamento por distrito": a amostra de dias com chuva forte por célula é de 10 a 37 dias |

**Limitações:** (1) data da vistoria, não do evento; (2) lançamentos em lote em dias secos; (3) chuva da cidade (maior
pluviômetro; até 01/2024 só 2 estações); (4) maré de modelo sem sobre-elevação, ponto a 17 km da costa, e 2022
reconstruído; (5) hora do pico vem do ERA5, que suaviza; (6) nenhuma ocorrência depois de 06/2024; (7) 70 dias com
alagamento em 904, poucos eventos grandes dominam (maio e junho de 2022).

**Consequência para o índice de impacto:** a maré entra como **contexto visível** (classe de maré e se coincide com o
pico), **não como degrau automático**, até haver validação com dado horário de ocorrência (P-42) ou com maré observada.
Se a coordenação quiser manter o degrau, o limiar defensável é a **sizígia (≥ 1,11 m acima do nível médio)**, não 0,6 m,
restrito aos bairros baixos e estuarinos, com selo Experimental (pergunta nova, seção 9).

## 4. Rios

### 4.1 O que há no banco e nas fontes

| Item | Situação em 26/11/2026 |
|---|---|
| `silver.rios_estacoes`, `silver.rios_leituras`, `gold.rio_situacao` | **0 linhas** |
| `silver.reservatorios_leituras`, `gold.reservatorio_situacao` | **0 linhas** |
| `app.etl_execucoes` de `apac-rios` e `apac-reservatorios` | 9 execuções `em_andamento` cada, presas desde 13/11 23:01 UTC (ver `pendencias.md`, item 4) |
| `silver.rio_referencia_territorio` (ligação bairro → estação) | vazia; depende de P-49 |
| Conectores | `etl/conectores/apac_rios.py` (APAC `/estacoes_rios` + `/historico_rios`, ANA `ServiceANA.asmx` como segunda fonte) e `apac_reservatorios.py` (`/reservatorio`) |
| Fixtures | `backend/tests/unit/etl/fixtures/apac_historico_rios_*.json` (6 estações), `ana_dados_39187800_2026-11-06.xml`, `apac_reservatorio_capibaribe_2026-11-06.json` |
| Rota | **não existe** `GET /situacao/rios`; o cartão do Dashboards diz "Ainda não disponível" |
| Decisão | **D-19 / P-33:** fontes sem termos declarados (APAC rios e reservatórios) podem ser construídas e testadas, mas **não vão a produção** antes da resposta da APAC, salvo decisão do dono |

**Estações com dado útil** (cadastro da APAC, fixture de 06/11/2026; limiares oficiais por estação):

| Estação | Rio | Onde | Limiares (pré-alerta / alerta / enchente) | Série diária na API |
|---|---|---|---|---|
| 39187800 São Lourenço da Mata (ANA/SGB) | Capibaribe | a montante do Recife; único cadastro com Recife no município | 250 / 300 / 400 cm | 01/10/2010 a 25/11/2026, 4.719 dias |
| 39150010 Paudalho | Capibaribe | mais a montante | 300 / 350 / 450 cm | 2011 a 11/2026, 2.526 dias (lacuna 2014–2016) |
| 39170000 Vitória de Santo Antão | Tapacurá | afluente acima do reservatório | 385 / 435 / 535 cm | 2011 a 10/2026, 3.588 dias |
| 260790115 e 260790119 (Cemaden) | Jaboatão e Duas Unas | Jaboatão dos Guararapes | 320 / 340 / 440 cm (Vila Natal) | horária recente |
| Beberibe, Tejipió, Jiquiá, Jordão, Pina | — | dentro do Recife | **nenhuma estação pública** | "Dados insuficientes. Falta: estação de nível no rio" |

Reservatórios: `historico_reservatorios` da APAC devolve Tapacurá de 18/12/2004 a 26/11/2026 (10.000 leituras, cota,
volume e cota do vertedouro de 103 m; hoje 91,9%). Goitá e Carpina estão no cadastro (`/reservatorio`).

### 4.2 Qualidade da série de São Lourenço

| Tema | Achado | Efeito |
|---|---|---|
| Lacunas | 2.904 de 3.829 dias com leitura em 2014 a 06/2024 (76%); 1.646 de 1.790 em 2022–2026 | Janela útil para cruzar com ocorrências: 2019 a 06/2024 |
| Mudança de referência | Mediana anual de 61 a 126 cm até 2018 e de 149 a 210 cm de 2019 em diante | Cotas de 250/300/400 cm só são comparáveis de 2019 em diante (sensor ou referência mudou; perguntar à APAC/SGB) |
| Sensor travado | 129 dias com o mesmo valor em 2020, 35 em 2018, 39 em 2021 | Tratar valor repetido por 30 dias como "sem leitura" (RN-02) |
| Resolução | A série integral é **diária** (nível máximo, mínimo e atual do dia); a horária só vem em `periodo=24h/72h` | Não dá para medir defasagem em horas com o histórico; só a partir da coleta própria |

### 4.3 Quanto tempo depois da chuva o rio sobe

58 episódios acima do pré-alerta (2010–2026). O pico em São Lourenço acontece **no mesmo dia ou no dia seguinte** à
maior chuva (mediana de 1 dia; resolução diária). Exemplos (chuva = maior pluviômetro do Recife, APAC; nível = máximo
do dia em São Lourenço):

| Pico | Chuva APAC do Recife nos dias D−4 a D+1 (mm) | Nível D−4 a D+2 (cm) |
|---|---|---|
| 28/05/2022 | 69, 137, 47, 21, **190**, 85 | 296, 392, 293, 296, **499**, 353, 282 |
| 15/06/2024 | 4, 8, 13, 29, **122**, 105 | 191, 188, 189, 306, **347**, 329, 241 |
| 16/05/2025 | 3, 2, 4, **143**, 91, 97 | 170, 171, 231, 247, **349**, 348, 218 |
| 08/04/2026 | 19, 26, 46, **82**, 26, 16 | 196, 258, 255, 294, **369**, 280, 214 |
| 01/05/2026 | 6, 35, 20, 5, 51, **147** | 197, 205, 213, 213, **474**, 396, 271 |

Leitura: o rio de referência acompanha a chuva do mesmo dia; em 01/05/2026 subiu **antes** do pico de chuva no Recife
(chuva maior na bacia). Isso dá horas, não dias, de antecedência. A correlação diária entre subida do rio e chuva é
fraca (Spearman 0,12 a 0,32), porque o rio responde à chuva **da bacia**, não do ponto do Recife.

### 4.4 Rio × chuva × alagamento em bairros ribeirinhos

**Lista provisória (não oficial; P-49)**: Capibaribe = Várzea, Caxangá, Iputinga, Cordeiro, Monteiro, Apipucos, Poço,
Casa Forte, Santana, Torre, Zumbi, Madalena, Ilha do Retiro, Prado, Graças, Ilha do Leite, Boa Vista, Santo Amaro,
Coelhos, Ilha Joana Bezerra, São José, Afogados. Tejipió e Jiquiá = Areias, Jiquiá, Estância, Tejipió, Barro,
Coqueiral, San Martin, Caçote, Mangueira, Bongi, Afogados.

DC × APAC (São Lourenço) × ERA5, 2014 a 06/2024, dias com leitura do rio (2.904). Dias com alagamento em D ou D+1:

| Nível do Capibaribe em São Lourenço | Dias | Ribeirinhos do Capibaribe | Tejipió/Jiquiá | Demais bairros |
|---|---|---|---|---|
| < 200 cm | 2.421 | 70 | 36 | 102 |
| 200 a 250 cm | 298 | 18 | 7 | 15 |
| Pré-alerta (250 a 300) | 126 | 19 | 12 | 17 |
| **≥ alerta (300+)** | **37** | **16** | **16** | **18** |

Só dias com chuva ≥ p90 no Recife (ERA5 ≥ 7,4 mm):

| Nível | Dias | Capibaribe | Tejipió/Jiquiá | Demais |
|---|---|---|---|---|
| < 200 cm | 186 | 20 | 10 | 27 |
| 200 a 250 | 49 | 8 | 3 | 7 |
| Pré-alerta | 37 | 12 | 9 | 9 |
| ≥ alerta | 23 | 12 | 12 | 13 |

**Maré "represando" o rio:** com o rio ≥ pré-alerta, os dias em maré alta (tercil superior, 49 dias) tiveram
alagamento ribeirinho do Capibaribe em 6; os demais 115 dias, em 29. Não há evidência de represamento no dado diário.
Não dá para testar direito: **não existe régua no trecho do Capibaribe sob maré** (do Recife até a foz), e o maior
evento (maio de 2022) foi em maré intermediária.

**Reservatórios:** Tapacurá verteu em 918 dias desde 2004 (2005, 2009–2011, 2022, 2023, 2025, 2026). Os dois maiores
picos do rio foram com Tapacurá **abaixo** do vertedouro (53% em 28/05/2022 e 86% em 01/05/2026): o reservatório
amorteceu, e a cheia veio da chuva na bacia baixa. Episódios com Tapacurá vertendo tiveram níveis moderados (≤ 357 cm).
"Reservatório vertendo" é sinal de atenção, não de cheia.

**Leitura:** rio ≥ alerta (300 cm) em São Lourenço coincide com alagamento ribeirinho em **16 de 37 dias** (43% dos
dias), contra 70 de 2.421 (3%) com o rio baixo. Mas os bairros não ribeirinhos sobem na mesma medida (18 de 37):
o rio alto é **marcador de evento regional grande**, útil para o "vai ser grave?", e ainda não prova efeito próprio
do rio nos ribeirinhos. Para a tela: "Capibaribe a montante em alerta; nos 37 dias assim de 2014 a jun/2024 houve
alagamento em bairros às margens do Capibaribe em 16".

**Limitações:** uma estação, a montante; série diária; referência mudou em 2019; 925 dias sem leitura; lista de
ribeirinhos provisória; ocorrências até 06/2024; poucos dias acima do alerta (37).

### 4.5 Fontes externas para rios (testadas em 26/11/2026)

| Fonte | Teste | Serve? |
|---|---|---|
| APAC `historico_rios?periodo=integral` | Devolveu a série diária desde 2010 com os limiares em cada linha | **Sim**: carga histórica única para "eventos parecidos" e linha de base, além da leitura de 15 a 60 min |
| APAC `historico_reservatorios` | Tapacurá 2004–2026 com cota do vertedouro | Sim, como contexto |
| ANA `ServiceANA.asmx` (legado, sem token) | Já usado no conector; mesma cota que a APAC | Redundância |
| ANA HidroWebService (novo, token) | Pede e-mail a `hidro@ana.gov.br` com CPF/CNPJ | Para série consistida longa; médio prazo |
| Open-Meteo Flood (GloFAS v4, 5 km) | Célula do Capibaribe (-8,025; -35,075): Spearman 0,59 com o nível, mas **erra os picos** (01/05/2026: 474 cm e 2,2 m³/s); de 203 dias em pré-alerta, só 51 com vazão ≥ p97 | **Não** para decisão; bacia costeira pequena demais para o modelo global |
| Google Flood Hub API | Cobre o Brasil; acesso por lista de espera; não verificamos se há "gauge" virtual no Capibaribe | A confirmar; pedir acesso |
| Cemaden PCDs hidrológicas | Só com cadastro na PED (token temporário) | P-37 |
| Sensores do COP (Tejipió) | Não públicos | P-35 |

### 4.6 Como mostrar (proposta; RF-35, fase 1 sem inundação por território)

1. **Camada "Rios" no Mapa:** o traçado do Capibaribe (já existe `GET /territorios/hidrografia.geojson`, faixas
   marginais) colorido pela **classe oficial da estação de referência** (normal, pré-alerta, alerta, enchente), com o
   rótulo fixo "situação medida em São Lourenço da Mata, a montante do Recife, às 14h20". Beberibe, Tejipió, Jiquiá,
   Jordão e Pina em cinza hachurado: "Dados insuficientes. Falta: estação de nível no rio". Nunca pintar bairro pelo
   rio antes de P-49.
2. **Cartão "Rios agora"** (Dashboards e Situação): régua vertical por estação com as três cotas oficiais, o nível
   atual, a tendência de 6 h (sobe, estável, desce; só com 3 leituras ou mais) e a idade da leitura; reservatórios em
   linha ("Tapacurá 91,9%, 0,9 m abaixo do vertedouro; Carpina 24%"). Frase de contexto histórico do 4.4.
3. **Índice ribeirinho (Experimental):** entra como **modificador** na classe de impacto (seção 7) só para bairros da
   lista aprovada em P-49 e só com o rio ≥ alerta; sem leitura do rio = "Dados insuficientes" na linha do rio, nunca
   "normal" (RN-01).
4. **Produção:** nada de rios vai a produção antes da resposta da APAC (D-19, P-33), salvo decisão do dono. Até lá,
   construir e testar com as fixtures e a carga local.

## 5. APIs e soluções externas

"No projeto" = já existe conector ou estudo no repositório. Custos em 26/11/2026.

| Nº | Fonte ou solução | URL | Acesso e custo | Granularidade | O que melhora | Esforço | No projeto? |
|---|---|---|---|---|---|---|---|
| A-01 | **APAC API**: rios, reservatórios, histórico integral, radar, previsão por município | https://api.apac.pe.gov.br/api.php | Sem cadastro, grátis; sem termos escritos (P-33) | estação, 10–60 min; série diária desde 2010 | Rio contra cotas oficiais; "eventos parecidos" com rio | Baixo (conectores prontos) | Sim (rios e reservatórios sem carga) |
| A-02 | **Tábua de marés da Marinha (DHN/CHM), Porto do Recife (tábua 24)** | https://www.marinha.mil.br/chm/tabuas-de-mare · BNDO: https://www.marinha.mil.br/chm/dados-do-bndo/download | Grátis; PDF anual ou pedido ao BNDO (`chm.bndo@marinha.mil.br`, até 10 dias úteis); sem API | preamar e baixa-mar, horário | Maré na referência que a equipe conhece (nível de redução) e oficial | Baixo (importação anual) | Não |
| A-03 | **IOC Sea Level Monitoring**, estação Tamandaré (`tame`) | https://www.ioc-sealevelmonitoring.org/service.php?query=data&code=tame | Grátis, JSON sem cadastro | 1 min, tempo real | Maré **observada** (com efeito de vento) | Médio: série bruta desde 10/2025, lacuna de 12/2025 a 04/2026, saltos de metros sem controle de qualidade; fica a ~80 km; Suape (`supe`) cadastrada e inativa | Não |
| A-04 | PSMSL / UHSLC, Recife | https://psmsl.org/data/obtaining/stations/556.php | Grátis | mensal, 1948–1968 | Só histórico antigo | — | Não; não serve |
| A-05 | IBGE RMPG (rede maregráfica) | https://www.ibge.gov.br/en/geosciences/geodetic-positioning/geodetic-networks/19307-geodetic-permanent-tide-gauge-network.html | Grátis | estações fora do Recife | — | — | Não; não cobre o Recife |
| A-06 | **Open-Meteo Marine** | https://open-meteo.com/en/docs/marine-weather-api | Grátis não comercial, CC BY 4.0 (P-46) | hora; ponto a 17 km da costa | Maré prevista 4 dias | — | **Sim** (renomear para "maré prevista") |
| A-07 | Open-Meteo Flood (GloFAS v4) | https://open-meteo.com/en/docs/flood-api · https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical | Grátis | 5 km, diário, previsão de meses | Pouco: erra os picos do Capibaribe (4.5) | Baixo | Não; não recomendado |
| A-08 | Google Flood Hub API | https://developers.google.com/flood-forecasting · lista de espera: https://sites.research.google/gr/floodforecasting/api-waitlist | Grátis com aprovação | gauge virtual, diário, 7 dias | Previsão de cheia, se houver gauge no Capibaribe | Médio | Não; pedir acesso |
| A-09 | **ANA HidroWebService** (novo) e `ServiceANA.asmx` (legado) | https://www.gov.br/ana/pt-br/assuntos/monitoramento-e-eventos-criticos/monitoramento-hidrologico/orientacoes-manuais/manuais/manual-hidrowebservice_publica.pdf · https://telemetriaws1.ana.gov.br/ServiceANA.asmx | Grátis; novo pede token por e-mail (`hidro@ana.gov.br`) | 15 min; séries consistidas | Segunda fonte e série longa consistida | Baixo a médio | Legado sim |
| A-10 | Cemaden: PCDs (PED) e alertas | https://plataforma-clima-ambiente-readthedocs.readthedocs.io/en/latest/cemaden_data.html | Grátis com cadastro (token temporário) | 10 min | Mais pluviômetros na bacia | Médio | Alertas sim (`wsAlertas2`); PCDs não (P-37) |
| A-11 | INMET `apitempo` | https://portal.inmet.gov.br | Token institucional (P-36) | hora | Temperatura medida | Baixo | Alertas sim; estação não |
| A-12 | **HAND 30 m (ASF, Copernicus GLO-30)** | https://registry.opendata.aws/glo-30-hand/ · https://gis.asf.alaska.edu/arcgis/rest/services/GlobalHAND/GLO30_HAND/ImageServer | Grátis, CC0; S3 sem login | 30 m, estático | Áreas baixas perto da drenagem por bairro ("% da área do bairro com HAND < 2 m"), cobre os 94 bairros | Médio (processar uma vez) | Não |
| A-13 | Copernicus DEM GLO-30 | https://registry.opendata.aws/copernicus-dem/ | Grátis | 30 m | Base do HAND; cota média do bairro | Médio | Não |
| A-14 | MapBiomas (cobertura e impermeabilização) | https://brasil.mapbiomas.org | Grátis, CC BY | 30 m, anual | Contexto de solo impermeável | Médio | Não; baixa prioridade |
| A-15 | **ESIG / Dados Abertos do Recife**: canais, macrodrenagem, áreas críticas, alagamento 2026, setores Sedec, atendimentos da Defesa Civil | https://esigportal2.recife.pe.gov.br · http://dados.recife.pe.gov.br | Grátis; licença não declarada nas camadas ArcGIS (P-32) | polígono, linha, ponto | Pontos críticos e canais no mapa; ocorrências recentes | Baixo a médio | Parcial (setores, alagamento 2026 sem carga, atendimentos até 06/2024) |
| A-16 | Emlurb: 159 pontos críticos de alagamento (citados em estudos e na imprensa) | pedido à Emlurb ou ESIG | A confirmar | ponto | "Onde alaga primeiro" na rua, por bairro | Baixo se houver arquivo | Não (pergunta nova) |
| A-17 | WhatsApp Business Platform (Cloud API) | https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing | Pago por mensagem (utilidade no Brasil ~US$ 0,0068 em 2025, por guias de terceiros) | — | Envio automático | Médio | **Fora do escopo** (PRD §5: sem envio automático). O produto já tem "Copiar" e "Abrir no WhatsApp" (RF-31) |
| A-18 | Telegram Bot API | https://core.telegram.org/bots/api | Grátis | — | Idem | Baixo | Fora do escopo, mesmo motivo |
| A-19 | Referência: Sistema Alerta Rio e COR Rio | https://www.sistema-alerta-rio.com.br · estações: https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Geotecnia/Estacoes_AlertaRio/MapServer · relatório 2025: https://www.sistema-alerta-rio.com.br/wp-content/uploads/2016/07/RELATORIO_ANUAL_CHUVA_2025.pdf | Público | 33 estações, 5 min | Padrão de "estágio + chuva em 15 min, 1 h, 24 h, 96 h por estação, com o histórico do mesmo evento" e relatório anual de eventos | — | Inspiração |
| A-20 | Referência: CEMADEN Educação, CISC Porto Alegre | https://educacao.cemaden.gov.br · https://prefeitura.poa.br/sms/vigilancia-em-saude/cisc-centro-de-informacao-em-saude-e-clima | Público | — | "Informe de risco" com o que fazer por território | — | Inspiração |

**As cinco de maior impacto:** A-01 (APAC rios e reservatórios, já construída, falta carga e D-19), A-15/A-16
(ocorrências recentes e pontos críticos da Prefeitura e da Emlurb), A-02 (tábua oficial da Marinha, na referência
que a equipe usa), A-12 (HAND para "terreno baixo" nos 94 bairros), A-08 (Google Flood Hub, se houver gauge no
Capibaribe).

## 6. Proposta: telas que mostram situação e impacto

### 6.1 Visualizações (prioridade e esforço)

Esforço: **P** (só frontend, rota existe), **M** (rota ou gold nova com dado já no banco), **G** (fonte nova ou
validação). Na coluna "Exemplo", horários e níveis de V-02, V-05 e V-08 mostram **só o formato do texto** (não são
leituras); as contagens históricas citadas são reais e vêm das seções 3 e 4 ou de `analise-insights-gestao.md`.

| Nº | Visualização | O que mostra | Exemplo de leitura | Dado | Prioridade | Esforço |
|---|---|---|---|---|---|---|
| V-01 | **Mapa de impacto previsto** | Bairros coloridos pela classe de impacto (seção 7), com seletor **Alagamento / Deslizamento**; contorno grosso nos bairros com unidades de saúde em setor de risco | "Morros do DS-7 e DS-8 em Muito alto para deslizamento; planície do DS-4 em Alto para alagamento" | `/cenarios/impacto-previsto` (já devolve classe de alagamento e deslizamento por bairro) | 1 | P a M |
| V-02 | **Linha do tempo de 72 h** com marcador "agora" | Barras de chuva medida (passado, sólidas) e prevista (futuro, tracejadas, com faixa); linhas de limiar de 24 h e 72 h; maré como linha com **faixa de sizígia** sombreada (≥ 1,11 m); rio de referência contra as cotas (quando houver) | "Pico de chuva às 03h; preamar de 1,3 m às 05h (sizígia); Capibaribe a 2 m do pré-alerta" | `/situacao/chuva` (`observada.serie`, `previsao`), rios (rota nova) | 1 | P (chuva e maré) + M (rio) |
| V-03 | **"Da última vez que choveu assim"** | Dias do histórico com chuva de 24 h e 72 h parecida (faixa ± 25%), classe de maré e nível do rio; o que aconteceu: dias com registro, distritos e bairros mais atingidos, com período e fonte | "Em 2022–jun/2024, 40 dias tiveram ≥ 50 mm em 24 h; em 33 houve deslizamento no dia ou no seguinte, metade no DS-7 (Nova Descoberta, Passarinho)" | `gold.chuva_apac_diaria` + `silver.ocorrencias` + maré (rota nova) | 1 | M |
| V-04 | **Pessoas e unidades na área afetada** | Por classe (Alto, Muito alto): bairros, moradores, idosos 60+, crianças 0–14, unidades de saúde (e quantas em setor de risco); por distrito | Formato, com dado real dos 10 bairros de mais deslizamento: "284.975 moradores, 40.636 idosos, 56.256 crianças, 29 unidades de saúde, 13 em setor de risco (IBGE 2022, CNES, Sedec, DC 07/2019–06/2024)" | `/cenarios/impacto-previsto` (`impacto_pessoas`), `/territorios/{id}/resumo-vulnerabilidade` | 1 | P |
| V-05 | **Régua histórica da chuva** | Onde a chuva de 72 h de agora cai na distribuição (p50 a p99) e o que acontece em cada faixa (desl./dia, alag./dia) | "Chuva de 72 h no DS-7: 118 mm, faixa 100–150; nessa faixa, 8,5 deslizamentos por dia em 2022–jun/2024" | tabela estática da análise (`analise-insights-gestao.md` §3.2–3.3) ou rota nova | 2 | M |
| V-06 | **Ficha de situação do bairro** (no lugar da grade de números) | 4 linhas: o que vem (chuva prevista do distrito, maré, rio se ribeirinho); o que o bairro já viveu (dias com registro em dias parecidos); quem está lá (perfil agregado); o que tem (unidades, setores R3/R4, suscetibilidade SGB) | Dado real: "Várzea: nos 70 dias pesados de 2022 a jun/2024, teve alagamento (D ou D+1) em 15. 70.938 moradores, 10.848 idosos. 3 unidades de saúde, 1 em setor R3/R4. Às margens do Capibaribe (lista provisória, P-49)" | rotas existentes + V-03 por bairro | 1 | M |
| V-07 | **Camada e cartão de rios** | Seção 4.6 | — | APAC rios e reservatórios | 2 (bloqueado por D-19) | M |
| V-08 | **Frase de situação no topo** | Uma frase gerada por regras, com fonte e hora: estágio do COP, gatilho mais próximo, maré, rio, alerta oficial vigente | "COP: Observação (09h). Chuva de 72 h no DS-7 a 16 mm do Alerta. Preamar de sizígia às 05h. Capibaribe normal (198 cm). Alerta amarelo APAC até 18h." | rotas existentes | 1 | P |
| V-09 | **Terreno baixo** (camada estática) | % da área do bairro com HAND < 2 m e pontos críticos da Emlurb | "Areias: 62% da área a menos de 2 m da drenagem" | HAND (A-12), Emlurb (A-16) | 3 (camada não pedida, P-54) | G |

### 6.2 Mudanças por tela

| Tela | Trocar | Remover | Adicionar |
|---|---|---|---|
| **Mapa** | Cor base: de "estágio" para **impacto previsto** com seletor Alagamento/Deslizamento (V-01); o estágio sugerido vira selo no bairro. Painel do bairro: grade de números vira **ficha de situação** (V-06) | Contagens de ocorrência sem período; "Bairros por estágio: 94 Observação" (já previsto em `mapa-v2.md`) | Camada Rios (V-07), camada de unidades em setor de risco destacada, frase de situação (V-08) |
| **Dashboards** | "A maré agrava a chuva?" vira **"Maré perto do pico"** com a classe (quadratura, intermediária, sizígia) e o horário da preamar, **sem** "Sim/não" e sem subir estágio. Pessoas expostas passam a ser por classe de impacto (V-04) | O "Sim" automático baseado em 0,6 m | "Da última vez que choveu assim" (V-03), "Rios agora" (V-07), régua histórica (V-05) |
| **Situação do evento** | Gráfico chuva × maré ganha chuva **medida** antes do "agora", faixas de limiar e faixa de sizígia (V-02); "Maré máxima 72 h" vira "Próxima preamar: 1,3 m às 05h (sizígia)" com a referência dita | Rótulo "nível do mar" (é maré prevista calculada) | Bloco "Rios e reservatórios" (RF-35) e linha do rio na linha do tempo |
| **Simulador** | Resultado passa a abrir com **comparação com eventos reais parecidos** (V-03) e soma de pessoas e unidades por classe (V-04); a premissa "maré" passa a ser escolha de classe (quadratura, intermediária, sizígia) com a altura da tábua | Texto longo de insumos como primeira leitura (vai para "Detalhes") | "Rio de referência" como premissa opcional (normal, pré-alerta, alerta, enchente), Experimental |

### 6.3 Dados e rotas novas, por fase

| Fase | Item | Onde | Requisito | Depende de |
|---|---|---|---|---|
| **Já dá** (só frontend) | V-01 com a classe de `/cenarios/impacto-previsto`; V-04; V-08; período em todo número de ocorrência (`periodo_inicio`/`periodo_fim` de `/ocorrencias/historico`); remover "Sim/não" da maré; mostrar a classe de maré a partir de `mare_no_pico_m` | `features/mapa`, `dashboards`, `situacao` | RF-01, RF-06, RF-19, RF-22, RF-23 | — |
| **Já dá** (parâmetro) | Coordenação pode subir `mare_alta_m` de 0,6 para 1,1 em `/estagios/parametros` (é editável, P-06) | tela de parâmetros | RF-29 | Decisão da coordenação (pergunta Q-01) |
| **Curto prazo** (dado no banco) | `gold.mare_diaria` (máxima, classe, origem real ou harmônica) a partir do Open-Meteo e da reconstrução harmônica | `etl/gold.py` | RF-29, RF-41 | — |
| **Curto prazo** | `GET /historico/eventos-parecidos?chuva_24h=&chuva_72h=&mare_classe=&nivel=distrito\|bairro` → dias análogos, dias com registro, distritos e bairros, período e fonte | `api/routers/` (nova) | RF-38, RF-41, §8.2 | Pergunta P-62 (sugerida em `analise-insights-gestao.md`) |
| **Curto prazo** | `GET /ocorrencias/serie` e `GET /ocorrencias/por-chuva` (já sugeridas em `analise-insights-gestao.md` §8.1) | idem | RF-37, RF-41 | P-62 |
| **Curto prazo** | `GET /situacao/rios` lendo `gold.rio_situacao` e `gold.reservatorio_situacao` + carga histórica única de `historico_rios?periodo=integral` | `api/routers/situacao.py`, `etl/conectores/apac_rios.py` | RF-35 | D-19/P-33 para produção; destravar execuções presas |
| **Curto prazo** | Classe de impacto por bairro e tipo (seção 7), dentro de `/cenarios/impacto-previsto` | `dominio/cenario.py` | RF-23, §8.2 | P-22 (combinação de camadas), Experimental |
| **Depende de terceiros** | Atendimentos da Defesa Civil 07/2024–2026 | conector `alagamento.py` | RF-37, RF-41 | P-42 |
| **Depende de terceiros** | Pontos críticos da Emlurb; canais e galerias do ESIG | conector novo | RF-02 | Pergunta Q-03, P-32 |
| **Depende de terceiros** | Tábua oficial da Marinha (Porto do Recife) e Z0 da estação | importação anual | RF-09 | Q-07 |
| **Depende de terceiros** | Ligação bairro → rio | `silver.rio_referencia_territorio` | RF-35 | P-49 |
| **Depende de terceiros** | Sensores do COP no Tejipió; PCDs do Cemaden; token ANA; acesso ao Flood Hub | conectores novos | RF-35, RF-36 | P-35, P-37, Q-09 |
| **Depende de terceiros** | HAND por bairro (camada estática) | `etl/` (processamento único) | RF-02, RF-37 | P-54 (camada não pedida) |

### 6.4 Como cada regra é respeitada

| Regra | Como |
|---|---|
| Só dados reais (ADR 0008) | Todas as visualizações usam dado medido, previsão de fonte oficial ou cálculo determinístico rotulado (maré harmônica). "Eventos parecidos" são dias reais, com data |
| RN-01 | Bairro sem previsão de chuva = "Dados insuficientes" na classe; rio sem leitura = "Dados insuficientes. Falta: leitura da estação X", nunca "normal"; bairro sem registro no histórico = "sem registro de 2014 a jun/2024 (não quer dizer sem risco)", nunca classe baixa por isso |
| RN-02 | Zero medido (estação com leitura e 0 mm) aparece como 0 mm; hora sem leitura é lacuna; nível repetido 30 dias = sem leitura |
| RN-05 | O sistema mostra classe e sugestão; o estágio é declarado por pessoa; a ficha de evento é aprovada por outra pessoa |
| RN-06 | Classes (sem sinal, moderado, alto, muito alto) e contagens "X de Y dias", nunca "chance de 43%". Proporções do passado ditas como "16 de 37 dias" |
| RN-07 | Bairro herda chuva e maré do distrito; dito na ficha ("chuva do DS-4") |
| RN-11 | Classe de impacto, modificadores de maré e rio e "eventos parecidos" levam o selo **Experimental** até haver validação temporal documentada em `docs/ml/` (teste em dados posteriores a 06/2024, depende de P-42) |
| RN-13 | Só contagens agregadas por bairro, distrito ou cidade; supressão abaixo de 5; nenhum lote, endereço ou pessoa |
| RF-19 / RF-42 | Cada bloco com fonte, hora da última atualização, data de referência ("histórico 2014 a jun/2024") e cobertura ("1 estação de rio, a montante") |

## 7. Índice de impacto por área (classe, nunca percentual)

O PRD §8.2 pede "índice de impacto em pessoas"; o RF-38 proíbe peso entre camadas até o cliente decidir (P-22). A
proposta respeita os dois: **uma matriz de regras visível**, sem pesos, por bairro e por tipo de perigo, e a ordem
dentro da classe pelas pessoas expostas (RF-22).

**Passo 1. Sinal de chuva do distrito** (limiares atuais de `/estagios/parametros`): 0 = abaixo de Atenção; 1 =
Atenção (24 h ≥ 25 mm ou 72 h ≥ 60 mm); 2 = Alerta (≥ 50 / ≥ 100); 3 = Crítico (≥ 90 / ≥ 150). Usa o maior entre
medida 72 h e prevista 24 h e 72 h. Sem previsão nem medição = **Dados insuficientes** (para aqui).

**Passo 2. Histórico do bairro para o mesmo perigo** (dias com registro em dias pesados, 2014 a jun/2024): H0 = nenhum;
H1 = 1 a 4 dias; H2 = 5 ou mais. H0 nunca reduz a classe por si só e sempre aparece escrito como "sem registro".

**Passo 3. Matriz**

| Sinal de chuva \ Histórico | H0 (sem registro) | H1 | H2 |
|---|---|---|---|
| 0 | Sem sinal | Sem sinal | Moderado |
| 1 | Moderado | Moderado | Alto |
| 2 | Moderado | Alto | Muito alto |
| 3 | Alto | Muito alto | Muito alto |

**Passo 4. Modificadores (Experimental, desligados por padrão até decisão):** (a) **rio** de referência ≥ alerta e
bairro na lista de P-49: +1 nível de alagamento a partir de Moderado; (b) **maré** de sizígia (≥ 1,11 m acima do nível
médio) a até 3 h do pico: só **mostrada**, sem subir nível, até validação (seção 3.6); (c) **terreno** (setor R3/R4,
suscetibilidade alta do SGB, HAND baixo) entra como **contexto** na ficha, não na classe (P-22).

**Passo 5. Ordem e pessoas:** dentro de cada classe, bairros ordenados por idosos + crianças residentes e unidades de
saúde (RF-22); a tela soma pessoas e unidades por classe (V-04).

**Confiança:** alta com estação própria no distrito e previsão recente; média quando o bairro herda a chuva; baixa
quando o histórico é H0 ou a ocorrência mais recente é anterior a 2022.

**Validação antes de tirar o selo (RN-11):** retroteste diário 2022 a jun/2024 (APAC × DC): por classe, "dias com
registro em X de Y"; a classe tem de ser monotônica (Muito alto > Alto > Moderado > Sem sinal) nos dois perigos; teste
em dados posteriores a 06/2024 quando P-42 trouxer as ocorrências; documentar em `docs/ml/`.

## 8. Ordem sugerida

1. Só frontend, com o que existe: V-08, V-04, V-01 (classe já servida), período em todo histórico, maré como classe
   sem "Sim/não" (mudanças pequenas no Mapa, Dashboards e Situação, depois do redesenho em curso).
2. Decisão da coordenação sobre o limiar de maré (Q-01); se aprovar, editar o parâmetro (sem código).
3. `gold.mare_diaria` + `GET /historico/eventos-parecidos` (V-03, V-06), depois de P-62.
4. Rios: destravar execuções presas, carga histórica e `GET /situacao/rios` em ambiente de teste; produção só depois de
   D-19/P-33.
5. Classe de impacto (seção 7) com retroteste e selo Experimental, depois de P-22.
6. Pedidos externos: Defesa Civil 2024–2026 (P-42), Emlurb, Marinha (tábua e Z0), APAC (termos e mudança de referência
   da régua em 2019), acesso ao Flood Hub.

## 9. Perguntas novas (para registrar em `docs/perguntas-abertas.md`)

P-62 já está sugerido em `analise-insights-gestao.md` (impacto histórico por faixa de chuva e período). Numerar as
abaixo a partir de P-63 ao registrar.

| Nº | Pergunta | Para quem | Bloqueia |
|---|---|---|---|
| Q-01 | O limiar de maré alta de 0,6 m (acima do nível médio) é atingido em 93,6% dos dias e não separa dias com e sem alagamento. A coordenação aceita (a) tirar a maré do degrau automático e mostrá-la só como contexto, ou (b) subir para a sizígia (≥ 1,1 m) só para bairros baixos, com selo Experimental? | Coordenação do Vigidesastres, dono | RF-29, P-06, Dashboards |
| Q-02 | Quais bairros alagam **sem chuva** em maré de sizígia (preamar alta)? O histórico tem 12 casos em 10 anos (9 em sizígia) e pode ser vistoria atrasada | Defesa Civil, Emlurb | Modificador de maré |
| Q-03 | A Emlurb tem a lista georreferenciada dos cerca de 159 pontos críticos de alagamento (e canais e galerias)? Pode ser compartilhada (licença)? | Emlurb, Prefeitura | V-09, RF-02 |
| Q-04 | (reforça P-42) Atendimentos da Defesa Civil de 07/2024 a 2026, com hora do chamado (não só da vistoria) | Sedec | Validação de tudo (RN-11) |
| Q-05 | (detalha P-49) A lista provisória de bairros ribeirinhos do Capibaribe e do Tejipió/Jiquiá (seção 4.4) está certa? | Defesa Civil, Vigidesastres | Modificador de rio, camada de rios |
| Q-06 | A régua de São Lourenço da Mata mudou de referência por volta de 2019 (mediana anual de ~90 para ~180 cm)? As cotas de 250/300/400 cm valem para toda a série? | APAC, SGB | Histórico do rio, "eventos parecidos" |
| Q-07 | A equipe lê a maré em "metros da tábua da Marinha" (ex.: 2,4 m)? Podemos mostrar na referência da tábua (nível de redução) usando o Z0 oficial do Porto do Recife? | Vigidesastres, Marinha (CHM) | Rótulos de maré (T-3) |
| Q-08 | A combinação proposta (matriz chuva × histórico, sem pesos, pessoas só para ordenar) atende ao "índice de impacto em pessoas" do PRD §8.2 sem ferir P-22? | Cliente, dono | Seção 7 |
| Q-09 | Pedimos acesso ao Google Flood Hub API e ao HidroWebService da ANA em nome do projeto ou do Vigidesastres? | Dono, Vigidesastres | A-08, A-09 |
| Q-10 | A equipe quer a camada "terreno baixo" (HAND) e os pontos críticos no Mapa? Não foram pedidas (RF-20, P-54) | Vigidesastres | V-09 |
| Q-11 | "Da última vez que choveu assim" (eventos parecidos do passado) ajuda a decidir ou confunde? Validar com as duas usuárias | Mariana Siqueira e Mariana Lima | V-03 |
| Q-12 | Para o PRD: incluir no RF-35 a carga histórica diária dos rios (APAC `periodo=integral`) e, no RF-41, os eventos parecidos como "retrospectivos" | Dono, arquiteto | PRD v5 |

## 10. Reprodutibilidade

- Banco: só SELECT em transação somente leitura; nenhuma escrita; nenhum segredo impresso. Tabelas lidas:
  `app.territorios`, `silver.ocorrencias`, `silver.observacoes`, `gold.chuva_apac_diaria`, `silver.rios_*`,
  `gold.rio_situacao`, `gold.reservatorio_situacao`, `silver.alagamento_2026`, `app.etl_execucoes`.
- APIs públicas consultadas em 26/11/2026 (sem dado pessoal): Open-Meteo Marine (2021–2026), Open-Meteo Archive (ERA5
  2014–2026), Open-Meteo Flood, APAC `historico_rios?periodo=integral` (39187800, 39150010, 39170000) e
  `historico_reservatorios` (Tapacurá), IOC Sea Level Monitoring (lista de estações e `tame`).
- Reconstrução da maré com `climasense.ml.alagamento.clima.ajustar_mare` e `prever_mare` (sem alterar o código).
- Scripts e arquivos ficaram no scratchpad da sessão, fora do repositório; nada foi commitado.

## 11. Validação pela persona

Personas do PRD §4: **T** = técnica de plantão do Vigidesastres (Mariana Siqueira ou Mariana Lima: só consome dados,
usa celular e WhatsApp, monta o cenário); **C** = coordenação do Vigidesastres e gestora da Secretaria de Saúde (decide
o estágio, recebe o relatório executivo). Momentos: **R** rotina (tempo seco), **A** antes da chuva (previsão), **D**
durante, **P** depois. Nota de força: 5 = muda uma decisão real; 1 = só informa. É uma leitura feita a partir do PRD,
não um teste com as usuárias (Q-11).

### 11.1 Indicadores que já existem

| Indicador | Persona / momento | Pergunta que ela faz | Responde? | Ação que toma | Força | Decisão |
|---|---|---|---|---|---|---|
| Dashboards: **Situação agora** | T, C / R, A, D | "Está tudo calmo ou começou?" | Parcial: diz o estado, não o que vem | Decide se abre o painel completo | 3 | **Melhorar**: virar a frase de situação (V-08), com gatilho mais próximo, maré, rio e alerta oficial |
| Dashboards: **Decisões pendentes** | C / A, D | "Onde o sistema sugere mais do que declaramos?" | Sim | Revisa e declara o estágio do território (RF-30) | **5** | Manter |
| Dashboards: **Falta para Atenção** (próximo gatilho) | T / A, D | "Quanto falta para mudar de estágio?" | Sim, mas só o limiar seguinte | Prepara a mensagem e avisa a coordenação antes | **5** | Melhorar: gatilho mais próximo de qualquer nível e o que acontece acima dele (V-05) |
| Dashboards: **Maior chuva 24 h** | T / D | "Onde choveu mais?" | Sim, um número | Olha o distrito; sozinho não decide | 2 | Melhorar: fundir com "Falta para Atenção" (24 h e 72 h no mesmo cartão; 72 h pesa mais, seção 3.6) |
| Dashboards: **Chuva por distrito** | T / D | "Em quais distritos?" | Sim | Escolhe onde olhar o bairro | 3 | Manter, com as linhas de limiar e as estações válidas |
| Dashboards e Mapa: **Bairros por estágio** | C / R | "Quantos bairros em cada estágio?" | Não: 94 em Observação no tempo seco não informa nada | Nenhuma | 1 | **Cortar** (já proposto em `dashboards-indicadores.md` e `mapa-v2.md`) |
| Dashboards: **Onde agir primeiro** | T, C / A, D | "Para onde mando equipe?" | Parcial: um único tipo de perigo, mistura histórico e previsão | Pré-posiciona equipes e avisa o distrito | 4 | Melhorar: separar alagamento e deslizamento e usar a classe de impacto (seção 7) |
| Dashboards: **Dengue** (nível do InfoDengue) | C / R, P | "A arbovirose pede atenção além da chuva?" | Parcial: só cidade, semanal | Reforça a ação de vetor no pós-evento | 2 | Manter como contexto, menor; juntar com a janela de leptospirose, que é a que muda a ação depois do evento |
| Dashboards: **A maré agrava a chuva?** (Sim/Não por 0,6 m) | T / A | "A maré vai piorar?" | **Não**: diz "Sim" em 93,6% dos dias | Sobe o alerta sem base | 1 | **Cortar** o Sim/Não; trocar por "Maré perto do pico" (classe e horário), só como contexto |
| Mapa: **cor por estágio sugerido** | T / A, D | "Onde vai pesar?" | Parcial: um estágio para dois perigos | Abre o bairro | 3 | Melhorar: cor por impacto previsto com seletor Alagamento/Deslizamento (V-01) |
| Mapa: **painel do bairro** (grade de contagens) | T / A, D | "Quem está lá e o que tem?" | Parcial: números sem leitura; ocorrência sem período | Monta a lista de vulneráveis | 3 | Melhorar: ficha de situação (V-06) |
| Mapa: **estágio do COP** | C / sempre | "Qual é o estágio oficial?" | Sim (quando declarado) | Alinha a resposta da Saúde ao COP | 4 | Manter |
| Situação: **gráfico chuva × maré com "agora"** | T / A | "Quando é o pico e a preamar?" | Parcial: sem chuva medida e sem faixas de risco | Define a hora de alertar o distrito | 4 | Melhorar (V-02) |
| Situação: **mensagem de WhatsApp** | T / D | "Como aviso o grupo rápido?" | Sim | Copia e envia | **5** | Manter |
| Simulador: **ordem de atenção dos distritos** | C / A | "Se chover X, qual distrito vem primeiro?" | Parcial: sem comparação com eventos reais | Planeja o plantão | 3 | Melhorar: abrir com "eventos parecidos" (V-03) |

### 11.2 Indicadores novos desta proposta

| Indicador | Persona / momento | Pergunta | Responde? | Ação | Força | Decisão |
|---|---|---|---|---|---|---|
| V-01 **Mapa de impacto previsto** (alagamento e deslizamento) | T, C / A, D | "Quais áreas vão sofrer, e com o quê?" | Sim | Define os bairros para pré-posicionar equipe e avisar as UBS | **5** | Fazer (já dá com a classe servida) |
| V-03 **Da última vez que choveu assim** | T, C / A | "Isso é grave de verdade?" | Sim, com o passado real | Decide subir o estágio e justifica para a chefia | **5** | Fazer (curto prazo, P-62) |
| V-04 **Pessoas e unidades na área afetada** | C / A, D, P | "Quantos idosos, crianças e unidades estão expostos?" | Sim (residentes, não atingidos) | Aciona a Atenção Primária e planeja retirada assistida | **5** | Fazer (já dá) |
| V-06 **Ficha de situação do bairro** | T / D | "Este bairro costuma alagar com isso?" | Sim | Prioriza dentro do distrito | 4 | Fazer (curto prazo) |
| V-07 **Rios agora** (nível × cota oficial, tendência) | T, C / A, D | "O Capibaribe vai encher?" | Parcial: uma estação, a montante | Avisa os bairros ribeirinhos com horas de antecedência | 4 | Fazer em teste; produção depois de D-19/P-33 |
| V-02 **Linha do tempo de 72 h** (chuva medida e prevista, maré por classe, rio) | T / A, D | "Quando é o pior momento?" | Sim | Escolhe a hora do aviso | 4 | Fazer (chuva e maré já dão) |
| V-05 **Régua histórica da chuva** | C / A | "O que acontece nesta faixa de chuva?" | Sim | Justifica o estágio | 3 | Fazer junto de "Falta para Atenção" |
| V-08 **Frase de situação** | T, C / R, A, D | "Resume para mim em uma linha" | Sim | Cola no WhatsApp | 4 | Fazer (já dá) |
| Maré como **modificador** da classe | T / A | "A maré piora?" | Não, pelos dados de hoje | — | 1 | **Não fazer** até validar; só contexto |
| V-09 **Terreno baixo** (HAND, pontos da Emlurb) | T / R | "Onde alaga primeiro na rua?" | Parcial (estático) | Planeja a quadra chuvosa | 2 | Só se a cliente pedir (P-54) |

### 11.3 TOP 6 indicadores fortes (mudam uma decisão real)

| # | Indicador | Definição curta | Fonte | Dá para fazer já? |
|---|---|---|---|---|
| 1 | **Decisões pendentes** | Territórios com estágio sugerido acima do declarado, mais vulneráveis primeiro | `/estagios` (APAC, Open-Meteo, DC) | **Sim** (existe) |
| 2 | **Gatilho mais próximo e o que acontece acima dele** | "DS-7: faltam X mm em 72 h para Alerta; com ≥ 50 mm em 24 h houve deslizamento em 33 de 40 dias (2022 a jun/2024)" | `/estagios`, `/estagios/parametros`; contagem fixa da análise, com período | **Sim** (frontend) |
| 3 | **Mapa de impacto previsto por perigo** | Classe de alagamento e de deslizamento por bairro (Experimental); "Dados insuficientes" sem previsão | `/cenarios/impacto-previsto` | **Sim** com a classe atual; matriz da seção 7 em curto prazo |
| 4 | **Pessoas e unidades na área afetada** | Moradores, idosos 60+, crianças 0–14 e unidades de saúde (e quantas em setor de risco) nos bairros Alto e Muito alto | IBGE 2022, CNES, Sedec, via `/cenarios/impacto-previsto` | **Sim** |
| 5 | **Da última vez que choveu assim** | Dias reais com chuva de 24 h e 72 h parecida: em quantos houve ocorrência, onde, com o período | `gold.chuva_apac_diaria` × `silver.ocorrencias` (2022 a jun/2024) | Não: rota nova (curto prazo, P-62) |
| 6 | **Capibaribe a montante × cota oficial** | Nível em São Lourenço contra 250/300/400 cm, tendência e idade da leitura; "nos 37 dias ≥ alerta, houve alagamento ribeirinho em 16" | APAC `historico_rios` (ANA/SGB) | Não: carga e rota (curto prazo); produção só depois de D-19/P-33 |

Ficou de fora por prazo: validação com as usuárias reais (Q-11), o retroteste da matriz da seção 7 e o controle de
qualidade da série de Tamandaré.
