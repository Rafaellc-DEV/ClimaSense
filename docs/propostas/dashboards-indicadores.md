# Proposta: página Dashboards e indicadores de decisão

Data: 26/11/2026 · Status: **proposta, não aprovada** · Pedido do dono do projeto em 26/11/2026

> **Fora do PRD.** O PRD v4 diz "A v4 não cria tela nova" (resumo e §12) e lista cinco telas (§7). Uma página
> "Dashboards" é tela nova: nada aqui deve ser construído antes da decisão do dono e da validação do cliente
> (pergunta **P-61** em `docs/perguntas-abertas.md`). O pedido conversa com a P-10 (o cliente ficou de dizer quais
> indicadores e painéis quer). Alternativa sem tela nova: o mesmo conteúdo como bloco no topo da tela **Situação do
> evento** (RF-09, RF-16, RF-36, RF-40).

Requisitos que a proposta usa: RF-01, RF-05, RF-09, RF-10, RF-16, RF-19, RF-20, RF-22, RF-29, RF-33, RF-35, RF-36,
RF-38, RF-40, RF-42. Regras: RN-01, RN-02, RN-05, RN-06, RN-07, RN-11, RN-13.

## 1. Resumo

- O problema do topo do Mapa: "Bairros por estágio: 94 Observação" conta estados, não diz **o que fazer**. Com tempo
  seco, 94 em Observação é o esperado e não informa nada; com chuva, a equipe precisa saber **onde decidir**, **quanto
  falta para o próximo gatilho** e **quem está exposto**.
- Proposta: 12 indicadores de decisão (seção 4). **11 dá para fazer só no frontend**, com os endpoints que já
  existem. **1 precisa de endpoint novo**: rios e reservatórios (I-09; a gold já existe, falta a rota). Os alertas
  oficiais (I-08) funcionam no frontend, mas pedem uma rota própria, porque hoje vêm repetidos dentro de cada item de
  `/estagios`.
- Topo do Mapa: trocar a contagem por 4 números (seção 6).

## 2. Dados reais que o sistema já tem

Todas as rotas abaixo ficam sob `/api/v1`, pedem a permissão `CONSULTAR` e devolvem `meta.fontes` com fonte, hora e
frescor (RF-19, RF-42), menos `/painel/resumo` e `/acoes`, que têm formato próprio.

### 2.1 Com endpoint

| Dado | Endpoint | Granularidade | Frequência da fonte | Limite de frescor (`frescor.toml`) | Observação |
|---|---|---|---|---|---|
| Estágio oficial da cidade (COP) | `GET /estagios/oficial` e `/estagios/oficial/historico` | cidade | a cada mudança, registro da equipe | — | null = sem registro (RN-01) |
| Estágio sugerido e declarado | `GET /estagios?nivel=distrito\|bairro` | distrito e bairro (bairro herda chuva e maré do distrito, RN-07) | recalculado a cada leitura | depende das fontes | `sugerido.insumos`: chuva 24 h medida, prevista 24 h e 72 h, pico de chuva, maré máxima e no pico, ocorrências históricas; `motivos` e `faltando` |
| Limiares dos estágios | `GET /estagios/parametros` | cidade | quando a coordenação muda | — | padrão: 24 h 25/50/90 mm; prevista 72 h 60/100/150 mm; maré 0,6 m a até 3 h do pico; 3 ocorrências no bairro |
| Alertas oficiais vigentes | dentro de cada item de `GET /estagios` (`alertas_oficiais`) | território (o mesmo alerta se repete em todos) | APAC, INMET, Cemaden, IDAP a cada 10–15 min | 1 h | origem, nível, emissão, validade, link |
| Chuva medida 24 h e 72 h | `GET /situacao/chuva` | distrito (maior pluviômetro), mais o maior da cidade | APAC, 10–15 min | 1 h | estações com e sem leitura por distrito; distrito sem pluviômetro = "Dados insuficientes" |
| Série horária medida (72 h) | `GET /situacao/chuva` (`observada.serie`) | cidade e distrito | APAC, por hora | 1 h | só desde o início da coleta; hora sem leitura = lacuna, não zero (RN-02) |
| Chuva prevista horária e maré | `GET /situacao/chuva` (`previsao`) | cidade (média dos distritos) e ponto do porto | Open-Meteo, 6 h (chuva) e diária (maré) | 6 h e 24 h | faixa mín./máx. entre emissões; experimental |
| Chuva diária e mensal (histórico) | `GET /series?variavel=chuva_mm&territorio_id=&frequencia=` | cidade e distrito | ERA5 (reanálise), cerca de 7 dias de atraso | 192 h | é modelo, não pluviômetro |
| Média e mediana por mês | `GET /series/referencia?territorio_id=` | cidade e distrito | anos completos desde 2021 | 192 h | base para "acima da média do mês" |
| Calendário ano × mês | `GET /series/sazonalidade` | cidade e distrito | idem | 192 h | mês incompleto = lacuna |
| Impacto previsto por regras | `GET /cenarios/impacto-previsto?horizonte_h=` | bairro e distrito | a cada leitura (previsão 6 h) | depende das fontes | classe de alagamento e deslizamento, estágio sugerido, confiança, motivos, idosos, crianças e equipamentos de saúde por bairro, `pessoas_vulneraveis_em_alerta`, ordem de atenção dos distritos, arboviroses por distrito; experimental |
| Prioridades | `GET /territorios/prioridades?nivel=&horizonte_h=` | distrito e bairro | previsão 6 h | 6 h | lista ordenada com `resumo` em texto |
| Ordem por histórico | `GET /territorios/prioridade` | distrito e bairro | atendimentos da Defesa Civil 2014–2024 | 2.160 h | fato histórico, não chance |
| Idosos e crianças | `GET /territorios/camadas/vulneraveis` | bairro | Censo 2022 (fixo) | — | supressão abaixo de 5 (RN-13); deficiência = "Dados insuficientes" |
| Equipamentos de saúde | `GET /territorios/camadas/equipamentos-saude` | ponto (bairro e distrito) | CNES, mensal | 1.440 h | só público e SUS |
| Áreas de risco | `GET /territorios/camadas/areas-risco` | setor (24 de 94 bairros) | Sedec, rara | 13.140 h | cobertura parcial |
| Cruzamento do território | `GET /territorios/{id}/resumo-vulnerabilidade` | bairro, distrito, cidade | — | — | idosos, crianças, equipamentos, equipamentos em área de risco |
| Dengue, chikungunya, leptospirose | `GET /saude/resumo` e `GET /saude/semanal?agravo=` | cidade | InfoDengue semanal; SINAN 1–3 semanas | 192 h e 360 h | nível de alerta 1–4 do InfoDengue, Rt, semanas incompletas; janela de leptospirose de 30 dias (NT 138/2022) |
| Arboviroses por bairro | `GET /saude/bairros?agravo=&ano=` | bairro | anual | 13.140 h | retrato histórico; zika = "Dados insuficientes" |
| Ocorrências históricas | `GET /ocorrencias/historico?tipo=alagamento\|deslizamento` | bairro | até 06/2024 (P-42) | 2.160 h | bairro sem registro não é bairro sem risco |
| Ações | `GET /acoes` | cidade, distrito, bairro | imediata (registro da equipe) | — | contagens por situação e `por_distrito` (RF-16) |
| Eventos e relatório | `GET /eventos`, `/eventos/{id}/relatorio` | evento | registro da equipe | — | RF-41 |
| Boletim | `GET /boletim` | cidade ou distrito | consolidado | — | já junta estágios, chuva, maré, ações e saúde |
| Fontes e frescor | `GET /fontes` e `GET /painel/resumo` (`fontes`) | — | cada execução do ETL | — | `desatualizado`, `limite_frescor_h`, `ultima_atualizacao` |
| Risco de alagamento por ML | `GET /risco-alagamento` | bairro e distrito | — | — | hoje `disponivel: false` (o modelo não superou a regra simples); não usar no painel |

### 2.2 Só na gold, sem endpoint (o ETL já grava; falta a rota)

| Dado | Tabela gold | Granularidade | Frequência | Limite de frescor | Requisito |
|---|---|---|---|---|---|
| Nível dos rios com limiares oficiais (classe) | `gold.rio_situacao` | estação (8; a de referência fica a montante, em São Lourenço da Mata) | leitura de 15 min a 1 h; atraso de 7 h a 30 h | 3 h (coleta); leitura > 12 h = "Dados insuficientes" | RF-35 |
| Reservatórios do Capibaribe | `gold.reservatorio_situacao` | reservatório (Tapacurá, Goitá, Carpina, Matriz da Luz) | diária | 30 h | RF-35 |
| Estações de chuva paradas | `gold.estacoes_chuva_status` | estação | 10–15 min | 1 h | RF-36 (o resumo já sai em `/situacao/chuva`) |
| Umidade do solo (modelo) | `gold.solo_modelo_distrito` | distrito | 6 h | 6 h | RF-36, Experimental (P-58) |
| Previsão, tendência e radar da APAC | `silver.apac_previsao_horaria`, `apac_tendencia_chuva`, `apac_radar` | cidade e mesorregião | 10–15 min | 2 h | RF-36 |
| Demanda de urgência (SAMU) | `gold.samu_demanda_semana` | bairro, distrito, cidade, por semana | mensal | 1.440 h | RF-39 (fase 2) |
| Qualidade da água (SISAGUA) | `gold.agua_vigilancia_semana` | bairro, distrito, cidade, por semana | semanal, atraso mediano de 14 dias | 192 h | RF-39 (fase 2) |
| Desastres do Atlas | `gold.desastres_historico` | cidade, por evento | anual (até 2025) | 13.140 h | RF-41 |
| Suscetibilidade, grau R3/R4, alagamento de 2026 | `silver.suscetibilidade_deslizamento`, `atendimentos_grau_risco`, `alagamento_2026` | bairro | estática ou anual | 43.800 h, 13.140 h, 8.760 h | RF-37 (a suscetibilidade já entra em `/cenarios/impacto-previsto`) |

### 2.3 O que não existe

Não há caso de doença durante o evento (só semanal e municipal), zika, deficiência por bairro, nível de rio dentro do
Recife, ocorrências da Defesa Civil depois de 06/2024, nem estágio do COP por máquina (PRD §9). Nenhum indicador
abaixo depende disso; onde tocaria, o card mostra "Dados insuficientes. Falta: ...".

## 3. O que se usa lá fora (pesquisa de 26/11/2026)

| Referência | O que monitoram | O que trazemos para cá |
|---|---|---|
| Ministério da Saúde: Plano de Contingência para Emergências em Saúde Pública por Chuvas Intensas e Desastres Associados; Guia de preparação e resposta por inundação (2017) | níveis de resposta, sistema de monitoramento, unidades de saúde afetadas, agravos de transmissão hídrica e por vetores | estágio como eixo da página; unidades de saúde expostas; agravos ligados à chuva |
| Vigidesastres de Porto Alegre (CISC-POA): painel de monitoramento do estágio operacional e Informes de Risco | estágio vigente, alerta hidrológico por região, orientação às unidades de saúde | uma faixa de estado no topo; territórios em alerta com o que fazer |
| Cemaden: níveis Observação, Moderado, Alto, Muito Alto; painel de alertas vigentes | alertas por município e tipo (hidrológico, geológico) | alertas oficiais contados por origem e nível, separados das sinalizações internas (RF-40) |
| APAC e INMET: avisos amarelo, laranja e vermelho (na imprensa: 20–30 mm/h ou até 50 mm/dia no amarelo; 50–100 mm/dia no laranja) | chuva prevista e acumulada | comparar a chuva medida e prevista com o limiar do próximo estágio, não com uma escala própria |
| InfoDengue (Fiocruz/FGV): níveis verde, amarelo, laranja e vermelho; Rt | transmissão de arboviroses por semana | usar o nível do InfoDengue como classe, nunca uma taxa inventada |
| NT 138/2022 (leptospirose em inundações) | monitoramento extra de casos depois da exposição | janela de 30 dias com o dia atual, já calculada em `/saude/resumo` |

Fontes:
[Plano de contingência por chuvas intensas (MS)](https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/svsa/emergencia-em-saude-publica/plano-de-contingencia-para-emergencias-em-saude-publica-por-chuvas-intensas-e-desastres-associados) ·
[Guia de preparação e resposta por inundação (MS, cópia da SMS Rio)](https://saude.prefeitura.rio/wp-content/uploads/sites/47/2023/04/01.guiadepreparacaoerespostasaemergenciaemsaudepublicaporinundacao.pdf) ·
[Plano de contingência por inundação, 2ª ed. 2019](https://saude.prefeitura.rio/wp-content/uploads/sites/47/2023/04/planocontingenciasaudeinundacao2ed_2019.pdf) ·
[Guia para a gestão municipal do SUS (Fiocruz)](https://dssbr.ensp.fiocruz.br/wp-content/uploads/2013/04/guia_preparacao_resposta_desastre_inundacoes_gestao_municipal_SUS.pdf) ·
[CISC Porto Alegre](https://prefeitura.poa.br/sms/vigilancia-em-saude/cisc-centro-de-informacao-em-saude-e-clima) ·
[Informe de Risco 02/2026, Porto Alegre](https://prefeitura.poa.br/sites/default/files/usu_doc/hotsites/sms/vigilancia-em-saude/INFORME%20DE%20RISCO%2002_2026.pdf) ·
[Informe Vigidesastres Porto Alegre 2024](https://prefeitura.poa.br/sites/default/files/usu_doc/hotsites/sms/vigilancia-em-saude/Info%20Vigi%202024.pdf) ·
[Cemaden: risco geo-hidrológico](https://www.gov.br/cemaden/pt-br/paginas/risco-geo-hidrologico) ·
[Cemaden: sala de situação](https://www.gov.br/cemaden/pt-br/paginas/sala-de-situacao) ·
[Níveis de alerta do Cemaden (apresentação ao MPF)](https://www.mpf.mp.br/atuacao/ccr4/coordenacao/eventos/eventos-2024/arquivos/min-publico-ago-24.pdf) ·
[Alerta amarelo da APAC (Diario de Pernambuco)](https://www.diariodepernambuco.com.br/vida-urbana/2026/04/11711322-confira-os-municipios-de-pernambuco-onde-mais-choveu-nas-ultimas-12h-segundo-a-apac.html) ·
[Alerta laranja da APAC (Folha de Pernambuco)](https://www.folhape.com.br/noticias/apac-emite-alerta-de-chuvas-para-pernambuco/482142/) ·
[InfoDengue: glossário](https://lac.tghn.org/recursos/infodengue-glossary) ·
[Níveis do InfoDengue (Prefeitura de Porto Alegre)](https://prefeitura.poa.br/sms/onde-esta-o-aedes/dados-de-porto-alegre) ·
[NT 138/2022, leptospirose em inundações](https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/notas-tecnicas/2022/nota-tecnica-138-2022-estrategias-para-enfrentamento-da-leptospirose-durante-inundacoes.pdf)

Limite da pesquisa: os critérios numéricos oficiais da APAC (mm por classe) e os cortes do InfoDengue não foram
achados em documento oficial, só em notícia. **Nenhum limiar desta proposta vem deles**: os limiares são os de
`/estagios/parametros`, que a coordenação já edita (P-06).

## 4. Indicadores de decisão

Legenda da coluna Origem: **F** = só frontend com endpoint existente; **E** = precisa de endpoint novo.

| Nº | Nome curto | Pergunta que responde | Cálculo | Origem | Gráfico | Limiar e leitura |
|---|---|---|---|---|---|---|
| I-01 | **Decisões pendentes** | Onde a equipe precisa decidir agora? | Distritos e bairros com `sugerido.estagio` em atenção, alerta ou crítico **e** sem `declarado`, ou com `declarado` abaixo do sugerido | F: `/estagios?nivel=distrito` e `?nivel=bairro` | número grande + lista curta (até 5, mais vulneráveis primeiro, RF-22) | 0 = "Nenhuma sugestão acima do declarado". Maior que 0 = botão "Revisar" que abre o Mapa no território |
| I-02 | **Falta para o próximo estágio** | Quanto mais de chuva muda o estágio? | Para cada distrito: `limiar do próximo nível − insumo` em 24 h medida, prevista 24 h e prevista 72 h; mostra o menor | F: `/estagios` (insumos) + `/estagios/parametros` | barra horizontal por distrito com marcas de atenção, alerta e crítico (bullet chart) | "DS-4: faltam 7 mm em 72 h para Atenção". Mais perto do limiar fica no topo |
| I-03 | **Chuva medida 24 h e 72 h** | Onde já choveu muito? | `chuva_24h_mm` e `chuva_72h_mm` por distrito; maior da cidade | F: `/situacao/chuva` | barras horizontais por distrito, com linhas dos limiares de 24 h | Acima de 25/50/90 mm = Atenção/Alerta/Crítico (limiares atuais). Estações com leitura "12 de 19" ao lado |
| I-04 | **Chuva prevista x média do mês** | A previsão é fora do normal? | `chuva_prev_24h_mm` do distrito ÷ (média do mês em `/series/referencia` ÷ dias do mês). Mostrado como "2,1 vezes a média diária de novembro" | F: `/estagios` + `/series/referencia?territorio_id=ds-N` | barras por distrito com marca da média diária | Razão de 1,5 ou mais gera insight. É comparação com a reanálise ERA5 (modelo), dito no rótulo |
| I-05 | **Maré no pico da chuva** | A maré alta vai coincidir com a chuva? | `mare_no_pico_m` e `pico_chuva_em` dos insumos; série de chuva e maré de 72 h | F: `/estagios` + `/situacao/chuva` (`previsao`) | linha dupla: barras de chuva por hora e linha de maré, com faixa sombreada onde maré ≥ 0,6 m a até 3 h do pico | "Maré de 2,1 m às 14h, 1 h depois do pico de chuva: sobe um nível" |
| I-06 | **Pessoas em bairros em alerta** | Quantas pessoas vulneráveis estão onde o sistema sugere alerta ou mais? | `resumo.pessoas_vulneraveis_em_alerta` (bairros, idosos 60+, crianças 0–14); `parcial` quando algum bairro ficou sem número | F: `/cenarios/impacto-previsto?horizonte_h=24` | 3 números (bairros, idosos, crianças) | Contagem de residentes, não de atingidos. Deficiência: "Dados insuficientes" (P-41) |
| I-07 | **Unidades de saúde expostas** | Quais unidades ficam nos bairros com atenção ou mais? | Soma de `impacto_pessoas.equipamentos_saude` dos bairros com estágio sugerido ≥ atenção; lista por distrito | F: `/cenarios/impacto-previsto` (+ `/territorios/camadas/equipamentos-saude` para o nome) | número + lista por distrito | Exposição potencial, não unidade fechada (RF-14 ainda sem fonte) |
| I-08 | **Alertas oficiais vigentes** | Quem já alertou e até quando? | Alertas únicos (origem + emissão + nível) com validade em vigor | F provisório: juntar `alertas_oficiais` dos itens de `/estagios` sem repetir. E ideal: `GET /alertas/vigentes` | lista com selo por origem e nível, ordenada pela validade | Zero alertas = "Nenhum alerta oficial vigente às 14h20 (APAC, INMET, Cemaden, IDAP)", nunca "sem risco". Separado das sinalizações internas (RF-40) |
| I-09 | **Capibaribe e reservatórios** | O rio de referência está subindo para o limiar? | Classe da estação em `gold.rio_situacao` (normal, pré-alerta, alerta, enchente) com nível em cm e idade da leitura; reservatórios em `gold.reservatorio_situacao` | E: `GET /situacao/rios` (RF-35) | régua vertical por estação com os 3 limiares oficiais + mini série 72 h | Classe é da APAC. Texto fixo: "estação a montante do Recife". Beberibe, Tejipió, Jordão e Pina: "Dados insuficientes. Falta: estação de nível no rio" |
| I-10 | **Saúde: arboviroses e leptospirose** | Algum agravo pede atenção além da chuva? | Nível de alerta do InfoDengue (dengue e chikungunya) e tendência das 4 semanas como seta (sobe, estável, cai); janela de leptospirose ativa com o dia (ex.: dia 9 de 30) | F: `/saude/resumo` | 3 linhas com selo de nível e seta; contador da janela | Seta só com base suficiente; semana incompleta não vira queda. Escala do InfoDengue, citada. Cidade inteira, não bairro |
| I-11 | **Ações nos territórios em alerta** | Há distrito em alerta sem ação em andamento? | Cruzar `/acoes` (`por_distrito`, situação `em_andamento`) com o estágio (declarado ou sugerido) do distrito | F: `/acoes` + `/estagios?nivel=distrito` | tabela de 8 linhas: distrito, estágio, ações em andamento, planejadas | Distrito em atenção ou mais com 0 em andamento sobe para o topo e vira insight |
| I-12 | **Confiança dos dados** | Posso confiar nos números de agora? | Fontes com `desatualizado = true`; estações de chuva sem leitura; distritos sem medição própria | F: `/painel/resumo` (`fontes`) + `/situacao/chuva` (`estacoes`) | uma linha de selos: "APAC há 12 min · Previsão há 3 h · Maré há 9 h" | Qualquer fonte vencida = selo "Desatualizado" no card que usa a fonte |

Fica de fora da primeira versão (fase 2 ou sem pedido do cliente): SAMU e SISAGUA (RF-39, dependem de evento
registrado e de P-50), umidade do solo (Experimental, P-58), radar e tendência da APAC, histórico do Atlas, ML de
alagamento (não publicado).

### 4.1 Como cada indicador respeita as regras

| Regra | Como aparece na página |
|---|---|
| RN-01: sem dado não é baixo | Card sem dado mostra "Dados insuficientes. Falta: \<fonte\>" (usar `motivo`, `faltando` e `meta.dados_insuficientes` das respostas). Sem dado nunca entra no cálculo como zero: I-01 conta "sem dados" à parte; I-02 não calcula a distância sem o insumo; I-03 deixa o distrito sem barra e com o selo |
| RN-02: zero medido é diferente de ausente | 0 mm com leitura aparece como "0 mm" com a hora; ausente aparece como lacuna. Na série horária, hora sem leitura é espaço vazio, não barra zero |
| RN-06: classe, não percentual | Estágio, classe do rio, nível do InfoDengue e classe de alagamento aparecem como rótulo e cor. A razão de I-04 ("2,1 vezes a média") compara volume de chuva, não é chance. `variacao_4s_pct` de I-10 vira seta, sem número percentual (RF-39 proíbe percentual com semana incompleta) |
| RN-11: Experimental | I-01, I-02, I-05, I-06 e I-07 usam o estágio sugerido ou o impacto previsto: selo "Experimental" no card. I-04 usa previsão: selo também |
| RN-07: herança | Bairro herda chuva e maré do distrito; I-01 em nível de bairro diz "chuva do DS-x" |
| RN-13: só agregado | Só contagens; I-06 respeita `parcial` e a supressão abaixo de 5 |
| RN-05 e decisão humana | Nenhum card muda estágio. I-01 leva ao Mapa, onde a pessoa declara (RF-30) |
| RF-19 e RF-42 | Cada card tem rodapé "Fonte · atualizado às HH:MM" a partir de `meta.fontes[].atualizado_em`; vencido ganha o selo "Desatualizado" (`desatualizado`). O card que mistura fontes lista todas |

## 5. Layout da página

Princípios: poucos números (RF-20), o mais grave primeiro, funcionar no celular em uma coluna (RF-21), atualizar
sozinho a cada 1 a 5 min com a hora no topo (RF-10).

### 5.1 Acima da dobra (o que se vê sem rolar, no celular e no computador)

1. **Faixa de estado** (uma linha): estágio oficial do COP com a hora em que foi informado (`/estagios/oficial`) e a
   hora da última atualização da página. Sem registro: "Estágio do COP não registrado".
2. **Quatro números**: I-01 Decisões pendentes · I-03 Maior chuva medida em 24 h (com o distrito) · maior chuva
   prevista em 24 h (com o distrito, de I-04) · I-08 Alertas oficiais vigentes.
3. **Até 3 insights** em frases curtas (seção 5.3), o mais grave primeiro, cada um com fonte e hora.

### 5.2 Abaixo, em ordem

| Ordem | Bloco | Indicadores |
|---|---|---|
| 1 | Onde agir primeiro: tabela dos 8 distritos (estágio sugerido e declarado, chuva 24 h, prevista 24 h, falta para o próximo estágio, pessoas em alerta, ações em andamento), ordenada pelo estágio e depois pela vulnerabilidade | I-01, I-02, I-06, I-11 |
| 2 | Chuva: medida por distrito x limiares; prevista x média do mês | I-03, I-04 |
| 3 | Chuva e maré nas próximas 72 h | I-05 |
| 4 | Rios e reservatórios (quando houver o endpoint) | I-09 |
| 5 | Exposição: pessoas e unidades de saúde | I-06, I-07 |
| 6 | Saúde | I-10 |
| 7 | Confiança dos dados (rodapé fixo) | I-12 |

### 5.3 Filtros mínimos

| Filtro | Opções | Padrão | Por quê |
|---|---|---|---|
| Território | Recife · DS-1 a DS-8 | Recife | a chuva só existe por distrito; bairro se vê no Mapa ao clicar |
| Horizonte | Próximas 24 h · 72 h | 24 h | é o que `/cenarios/impacto-previsto` e os gatilhos usam |
| Período (só nos blocos de série) | Últimas 72 h · 7 dias · 30 dias | 72 h | série medida só desde a coleta; 7 e 30 dias usam ERA5, dito no rótulo |

Sem filtro de bairro, de data livre ou de agravo na primeira versão (RF-20).

### 5.4 Insights automáticos

Regras fixas, em texto simples, calculadas no frontend a partir das respostas; nenhuma chamada a modelo de linguagem.
Mostra no máximo 3, por gravidade. Cada um cita fonte e hora. Os números das frases abaixo são **exemplos de
formato**, não dados medidos.

| Quando | Frase (exemplo) | Dados |
|---|---|---|
| Sugerido acima do declarado | "3 distritos com sugestão de Alerta e sem declaração da equipe: DS-4, DS-6, DS-7." | `/estagios` |
| Razão prevista/média ≥ 1,5 | "Chuva prevista para 24 h no DS-4 (62 mm) é 2,1 vezes a média diária de novembro (ERA5, 2021–2025)." | `/estagios`, `/series/referencia` |
| Distância ao limiar ≤ 10 mm | "DS-2 está a 7 mm de chuva em 72 h do estágio Atenção." | `/estagios`, `/estagios/parametros` |
| Maré alta perto do pico | "Maré de 2,1 m às 14h, 1 h depois do pico de chuva previsto no DS-1." | `/estagios` (insumos) |
| Distrito em atenção sem ação | "DS-7 em Alerta (sugerido) e nenhuma ação em andamento." | `/estagios`, `/acoes` |
| Alerta oficial novo | "APAC: aviso laranja até 18h para a Região Metropolitana. Confira na APAC." | `/estagios` (alertas) |
| Pessoas expostas | "Bairros em alerta somam 18.400 idosos e 21.300 crianças (Censo 2022)." | `/cenarios/impacto-previsto` |
| Janela de leptospirose | "Janela de leptospirose: dia 9 de 30, período de maior atenção (5º ao 14º dia)." | `/saude/resumo` |
| Falta de dado | "DS-5 sem medição de chuva: 0 de 2 pluviômetros com leitura nas últimas 2 h." | `/situacao/chuva` |
| Fonte vencida | "Previsão de chuva desatualizada: última emissão há 9 h." | `/painel/resumo` |
| Nada a destacar | "Nenhum gatilho de chuva disparado. O mais perto: DS-3, a 18 mm de Atenção em 72 h." | `/estagios` |

A última linha substitui o "94 Observação": em vez de dizer que nada acontece, diz quanto falta.

## 6. Topo do Mapa: no lugar de "Bairros por estágio"

Manter o cartão do estágio oficial (RF-01) e trocar `ContagemBairros` (`frontend/src/features/mapa/EstagioOficial.tsx`)
por 4 números. Todos saem de rotas que o Mapa já chama ou que já existem; nenhum precisa de backend novo.

| Número | Exemplo | Fonte | Sem dado |
|---|---|---|---|
| Decisões pendentes | "3 territórios com sugestão acima do declarado" (clique filtra o mapa) | `/estagios?nivel=bairro` (já carregado) | "Sem dados em 12 bairros" à parte, nunca somado a Observação |
| Próximo gatilho | "Mais perto: DS-3, faltam 18 mm em 72 h para Atenção" | `/estagios` + `/estagios/parametros` | "Dados insuficientes: falta a previsão" |
| Maior chuva medida 24 h | "38 mm no DS-4 · 12 de 19 estações" | `/situacao/chuva` (`maior_24h`, `estacoes`) | "Dados insuficientes: nenhum pluviômetro com leitura" |
| Pessoas em bairros em alerta | "2 bairros · 4.100 idosos · 5.200 crianças" (Experimental) | `/cenarios/impacto-previsto` | "Nenhum bairro em alerta" só quando há previsão; sem previsão, "Dados insuficientes" |

A contagem por estágio pode continuar, menor, como legenda do mapa.

## 7. O que dá para fazer e o que falta

| Item | Onde | Esforço |
|---|---|---|
| I-01 a I-07, I-10 a I-12, insights e topo do Mapa | frontend (`frontend/src/features/` nova pasta, `charts/`) | médio; nenhum dado novo |
| I-08 consolidado | backend: `GET /alertas/vigentes` (lista única, com histórico de RF-40) | pequeno; hoje dá para deduplicar no frontend |
| I-09 | backend: `GET /situacao/rios` lendo `gold.rio_situacao` e `gold.reservatorio_situacao`, com `meta.fontes` de `apac-rios` e `apac-reservatorios` | pequeno; gold pronta. D-19: não ligar em produção antes da P-33 |
| I-04 com menos chamadas (opcional) | backend: incluir a média diária do mês em `/estagios` ou `/situacao/chuva` | pequeno; sem isso são 8 chamadas a `/series/referencia`, com cache longo |
| Resumo único da página (opcional) | backend: `GET /painel/decisao` juntando estágios, chuva, impacto e ações | médio; reduz chamadas no celular (RNF-06) |

## 8. Perguntas para validar

- P-61 (nova): a página Dashboards entra no PRD, ou o conteúdo vai para o topo da Situação do evento?
- P-10: estes são os indicadores que o cliente queria na resposta 9?
- P-06 e P-15: os limiares e os limites de frescor usados nos cards valem?
- P-22: a ordem de "Onde agir primeiro" pode usar idosos e crianças no desempate?
- P-53: as frases da seção 5.4 servem como sinalizações internas da central de alertas?
