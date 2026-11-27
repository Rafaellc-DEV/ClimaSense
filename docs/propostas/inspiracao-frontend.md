# Inspiração para o redesign do frontend

Proposta de referência visual e de interação para o redesign do painel ClimaSense. Não é requisito: qualquer mudança que sair daqui precisa citar um ID do PRD (RF-19, RF-20, RNF-08 e afins) antes de virar tarefa.

- Data: 26/11/2026
- Escopo: Mapa (distritos e bairros), estágio oficial, indicadores de chuva, maré, rios e saúde, ações da equipe e a futura página de Dashboards.
- Método: pesquisa web de 43 sites e produtos reais, cruzada com a base do skill `ui-ux-pro-max` (estilo "Data-Dense Dashboard", padrão "Real-Time / Operations", recomendações de gráfico para mapa coroplético, KPI e série temporal, e guias de UX de acessibilidade), com as orientações de `frontend-design` e `web-interface-guidelines`.

## 1. Diagnóstico rápido: por que "as fontes estão grandes" e "tem muito zoom"

O motivo é multiplicação de unidades, não só a escolha de tamanho:

| Onde | Valor hoje | Tamanho real na tela |
|---|---|---|
| `design-system/base.css` | `html { font-size: 18px }` | toda unidade `rem` vale 18 px |
| `--t-corpo` | `1.125rem` | **20,25 px** (o spec pede 18 px) |
| `--t-apoio` | `1rem` | 18 px |
| `--t-4` / `--t-3` | `1.375rem` / `1.75rem` | 24,75 px / 31,5 px |
| `--t-1` | `2.75rem` | 49,5 px |
| `Indicador` (valor) | `2.5rem` | 45 px |
| `--t-estado` | `clamp(2.5rem, 6vw, 4.5rem)` | até 81 px |

Ou seja: o texto corrido está 12% maior do que o próprio `specs/design.md` define, e os títulos e números chegam a 2 ou 3 vezes o que painéis operacionais de referência usam (NWS, UKHSA, Grafana, Datadog e Linear ficam entre 13 e 16 px no corpo e entre 24 e 32 px no número de destaque). Somado a cartões com muito respiro, a tela parece "ampliada".

Ponto de atenção: `specs/requirements.md` (RNF-ACE-02) pede texto base de 18 px. Este documento propõe 16 px de base com corpo de 15 a 16 px (seção 5). Pelo CLAUDE.md, o PRD prevalece sobre o spec; como a mudança toca um requisito de acessibilidade, a sugestão é registrar a pergunta em `docs/perguntas-abertas.md` e decidir num ADR (próximo número livre) antes de implementar.

## 2. Os 43 sites pesquisados

Legenda da coluna "Fonte": **B** = página ou documentação encontrada na pesquisa desta sessão; **C** = endereço canônico conhecido, não aberto nesta sessão (conferir antes de citar em material oficial).

### 2.1 Emergência, defesa civil e clima (Brasil)

| # | Site | URL | O que fazer igual | Fonte |
|---|---|---|---|---|
| 1 | Cemaden (Sala de Situação e Painel de Alertas Vigentes) | https://www.gov.br/cemaden/pt-br | Quatro níveis com nome fixo (Observação, Moderado, Alto, Muito Alto), o mesmo vocabulário em mapa, lista e boletim. Lista de alertas vigentes antes do mapa. | B |
| 2 | APAC, monitoramento pluviométrico | https://www.apac.pe.gov.br | Acumulado por estação em janelas fixas de 3, 12 e 24 h, lado a lado. A equipe já lê chuva assim; usar as mesmas janelas e rótulos. | C |
| 3 | Alerta Rio | http://alertario.rio.rj.gov.br | Tabela de estações com chuva 15 min, 1 h, 24 h e 96 h, densa e legível; mapa como apoio, não como única entrada. | B |
| 4 | Centro de Operações Rio (estágios operacionais) | https://cor.rio | Estágio da cidade como faixa única no topo, com número + cor + nome ("Estágio 3, laranja, Atenção"). Nunca só a cor. | B |
| 5 | IDAP / Defesa Civil Alerta (MIDR) | https://idap.mdr.gov.br | Cada alerta com território, horário de início e fim, severidade e órgão emissor no mesmo cartão. Bom modelo para RF-32. | B |
| 6 | InfoDengue (Fiocruz e FGV EMAp) | https://info.dengue.mat.br | Nível de alerta semanal por município em cores verde, amarelo, laranja e vermelho, com a semana epidemiológica sempre visível ao lado da classe. | B |
| 7 | Observatório e painel de arboviroses (Ministério da Saúde) | https://www.gov.br/saude/pt-br/composicao/svsa/cnie/observatorio-de-arboviroses | Indicadores de saúde com recorte temporal explícito (semana, ano) e nota metodológica a um clique. | B |

### 2.2 Emergência, clima e risco (internacional)

| # | Site | URL | O que fazer igual | Fonte |
|---|---|---|---|---|
| 8 | NWS, mapa de avisos (Hazard Simplification) | https://www.weather.gov | O NWS saiu de 122 cores para poucas classes porque o mapa ficava ilegível em evento ativo. Limitar o mapa a 4 ou 5 classes de risco. | B |
| 9 | NWS Impact-Based Warnings | https://www.weather.gov/impacts | Todo aviso separado em três linhas: Perigo, Fonte, Impacto. Mesma estrutura serve ao cartão de alerta e à mensagem de WhatsApp (RF-31). | B |
| 10 | FEMA National Risk Index | https://hazards.fema.gov/nri/map | Clicar no território abre painel lateral com classe em texto ("Relativamente alto") + barra comparativa; relatório do território a um botão. | B |
| 11 | Copernicus EMS, Rapid Mapping | https://mapping.emergency.copernicus.eu | Cada ativação tem página própria com URL estável (deep link). Copiar isso para "bairro X durante evento Y". | B |
| 12 | GDACS | https://www.gdacs.org | Três níveis (verde, laranja, vermelho) com ícone de tipo de evento + cor de nível; lista cronológica ao lado do mapa. | B |
| 13 | ReliefWeb Response | https://response.reliefweb.int | Números-chave da crise no topo, curtos e com fonte e data embaixo de cada um. | B |
| 14 | Windy | https://www.windy.com | Linha do tempo fixa na base do mapa para passar de "agora" para "próximas horas". Evitar o erro relatado pela comunidade: menu de camadas que cobre o mapa no celular. | B |
| 15 | Ventusky | https://www.ventusky.com | Clique no ponto abre painel lateral com o detalhe local; legenda de escala contínua pequena e fixa no canto. | B |
| 16 | Google Flood Hub | https://sites.research.google/floods | Painel de camadas que liga e desliga sem sair do mapa; painel do ponto com gráfico de previsão e limiares desenhados como faixas. | B |
| 17 | Meteoalarm (EUMETNET) | https://meteoalarm.org | Branco significa "sem dado, incompleto ou desatualizado", distinto de verde. É o RN-01 aplicado ao mapa. Oferece mapa em tons de cinza para daltonismo. | B |
| 18 | GOV.UK Check for flooding | https://check-for-flooding.service.gov.uk | Três níveis com frase de ação ("inundação possível", "esperada", "risco à vida"); lista de avisos primeiro, mapa opcional. Linguagem simples. | B |
| 19 | USGS Latest Earthquakes | https://earthquake.usgs.gov/earthquakes/map/ | Lista e mapa sincronizados: a lista filtra pela área visível e o clique em um realça o outro. No celular, configurações atrás de um ícone. | B |
| 20 | ArcGIS Dashboards, guia de visão móvel | https://doc.arcgis.com/en/dashboards/latest/reference/dashboards-on-your-smartphone.htm | No celular: um único mapa, uma camada operacional, sem pop-ups, indicadores primeiro, demais blocos em abas. | B |
| 21 | Esri Living Atlas | https://livingatlas.arcgis.com | Toda camada com ficha de metadados (fonte, atualização, licença) acessível pelo item da legenda. Modelo para RF-19 e metadados de RF-35 a RF-42. | C |
| 22 | Santa Cruz County SAFER (ArcGIS) | https://www.esri.com/en-us/lg/industry/public-safety/stories/how-santa-cruz-countys-safer-app-enhances-emergency-response | Mapa de zona de inundação + tendência do nível do rio + radar numa mesma vista. Referência para rios do Capibaribe (RF-35). | B |

### 2.3 Saúde pública

| # | Site | URL | O que fazer igual | Fonte |
|---|---|---|---|---|
| 23 | HealthMap | https://healthmap.org | Lista de alertas com fonte, data, local e significância ao lado do mapa. Lição negativa documentada: bolhas grandes enganam; ler além da cor. | B |
| 24 | JHU Coronavirus Resource Center | https://coronavirus.jhu.edu/map.html | Totais grandes à esquerda, ranking por território em lista rolável, mapa no centro. Lição negativa: muitos mapas carregados juntos deixaram o painel lento. | B |
| 25 | CDC COVID Data Tracker (Community Levels) | https://covid.cdc.gov/covid-data-tracker | Mapa por condado sempre acompanhado de tabela com classe e taxas; data de atualização e cadência ("toda quinta, 20 h") explícitas. | B |
| 26 | UKHSA data dashboard | https://ukhsa-dashboard.data.gov.uk | Número de destaque + seta de tendência + período, depois gráfico e tabela, e download. Construído sobre o GOV.UK Design System, com acessibilidade auditada. | B |
| 27 | ONS, guia de dashboards e visualização | https://service-manual.ons.gov.uk/data-visualisation/guidance/dashboards | Dashboard só com justificativa de uso; minimizar rolagem e cliques; títulos que dizem a conclusão. Bom critério para a futura página de Dashboards. | B |
| 28 | OpenSAFELY (relatórios) | https://www.opensafely.org | Cada gráfico acompanhado do método e do código que o gerou. Inspira o "como este número foi calculado" do selo Experimental (RN-11). | C |

### 2.4 Design de mapas e de dashboards

| # | Site | URL | O que fazer igual | Fonte |
|---|---|---|---|---|
| 29 | Mapbox, The Guide to Map Design | https://go.mapbox.com/rs/117-NXK-490/images/the-guide-to-map-design.pdf | Mapa base apagado (cinza claro, poucos rótulos) para que a camada de risco seja a única coisa com cor forte. | B |
| 30 | Mapbox GL JS, controles de navegação | https://docs.mapbox.com/mapbox-gl-js/example/navigation/ | Zoom e reorientação agrupados num canto, botões de 32 a 36 px no desktop e 44 px no toque. | B |
| 31 | Kepler.gl | https://kepler.gl | Painel lateral recolhível com abas Camadas, Filtros e Interações; o mapa ocupa o restante. | B |
| 32 | Felt | https://felt.com | Legenda que também é controle: clicar na classe liga e desliga; o painel de detalhe só aparece quando algo é selecionado. | B |
| 33 | Apple HIG, Maps | https://developer.apple.com/design/human-interface-guidelines/maps | Controles com contraste próprio sobre o mapa (fundo sólido), nunca texto solto sobre o mapa base. | B |
| 34 | Linear | https://linear.app | Densidade alta sem ruído: corpo por volta de 13 a 14 px, linhas de 32 a 36 px, grade de 4 px, cinza para metadados e cor só para estado. | B |
| 35 | Vercel Geist | https://vercel.com/geist | Escala tipográfica nomeada por uso (copy-14, label-12, heading-24), não por "h1/h2". Números com fonte de largura fixa. | B |
| 36 | Stripe, padrões de gráfico | https://docs.stripe.com/stripe-apps/patterns/chart-layout | Visão geral com poucos números e uma sparkline sem eixos embaixo de cada um; detalhe só no clique. | B |
| 37 | Datadog, Query Value | https://docs.datadoghq.com/dashboards/widgets/query_value/ | Cor do número definida por regra de limiar sobre o valor bruto; sem regra, número neutro. Equivale a "sem classe, sem cor". | B |
| 38 | Grafana, boas práticas | https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/ | Semântica de cor consistente em todos os painéis e linhas organizadas por hierarquia (cidade, depois distrito, depois bairro). | B |
| 39 | Our World in Data (Grapher) | https://ourworldindata.org | O mesmo indicador em abas Gráfico, Mapa e Tabela, com fonte e nota de rodapé sempre presentes. Modelo para a página de Dashboards. | B |
| 40 | Observable Framework | https://observablehq.com/framework/ | Grade de até 4 colunas que se reorganiza pela largura; cartões que ocupam 1, 2 ou 4 colunas conforme a importância. | B |
| 41 | Tableau Public (Viz of the Day) | https://public.tableau.com/app/discover/viz-of-the-day | Mapa coroplético integrado a linha do tempo e filtro de local; boa referência para "antes, durante e depois" do evento. | B |
| 42 | Dribbble, Flood Monitoring System (pangeranmw) | https://dribbble.com/pangeranmw | Composição de monitoramento de enchente com mapa central e coluna de sensores; usar só como referência de composição, não de estilo. | B |
| 43 | Stamen, "Designing the avocado of uncertainty" | https://stamen.com/designing-the-avocado-of-uncertainty/ | Como mostrar incerteza de previsão sem parecer certeza. Direto ao ponto do selo Experimental (RN-11). | B |

Referência complementar de composição para operações: Dribbble "Connnect - Map Overview" (https://dribbble.com/shots/22942267-Connnect-Map-Overview), painel para equipes de primeira resposta.

## 3. Padrões recomendados (priorizados)

Cada padrão indica os requisitos que atende. Os de prioridade 1 a 5 resolvem a reclamação atual; os seguintes consolidam a linguagem.

1. **Faixa de estado da cidade no topo, compacta (uma linha, 56 a 72 px de altura).** Estágio oficial com número + cor + nome + "declarado por COP às 14h20". Inspirado em COR Rio, NWS e GOV.UK. Hoje `--t-estado` chega a 81 px; reduzir para 28 a 32 px. (RF-09, RF-19, RN-05)
2. **Base tipográfica de 16 px no `html`, corpo de 15 px no desktop e 16 px no celular.** Corrige a multiplicação de rem descrita na seção 1. Atkinson Hyperlegible continua legível nesses tamanhos. Campos de formulário em 16 px no celular para o iOS não aplicar zoom automático. (RNF-08, RF-20)
3. **Fileira de 3 a 5 indicadores acima da dobra, cada um com: rótulo curto, valor (28 px), unidade, classe em texto, e linha de rodapé "Fonte · hh:mm".** Padrão UKHSA, ReliefWeb e Stripe. Sparkline opcional sem eixos. Desatualizado ganha selo textual "Desatualizado há 3 h", não só cor apagada. (RF-09, RF-19)
4. **"Sem dado" tem visual próprio, diferente de risco baixo.** No mapa: hachura cinza ou branco com contorno tracejado (Meteoalarm). No cartão: "Dados insuficientes" + nome da fonte que falta. Zero medido mostra "0 mm" com classe normal. (RN-01, RN-02)
5. **Escala de risco com no máximo 4 classes + "sem dado", sempre cor + texto + forma.** Observação, Atenção, Alerta, Crítico; legenda com rótulo escrito e, nos chips, um ícone ou número de nível. Nada de percentual. Paleta testada para daltonismo e versão em tons de cinza. (RN-06, NWS, GDACS, InfoDengue)
6. **Mapa com base apagada e uma camada operacional por vez.** Base cinza claro com poucos rótulos (Mapbox); o risco por bairro é a única cor forte. Trocar a camada por um seletor segmentado (Chuva, Rios, Maré, Saúde), não por várias camadas sobrepostas. (RF-35 a RF-42, Esri, Flood Hub)
7. **Painel lateral do território (desktop 360 a 400 px; celular bottom sheet com 3 alturas).** Abre ao clicar no bairro: nome, distrito, classe em texto, chuva 3/12/24 h, rio e maré próximos, saúde, ações abertas, cada linha com fonte e hora. Só aparece quando há seleção (Felt, FEMA NRI, Ventusky). (RF-19, RF-36)
8. **Lista e mapa sincronizados.** Ranking de bairros ao lado do mapa, filtrado pela área visível; passar o mouse ou focar num item realça o bairro e vice-versa (USGS, JHU, CDC). A lista é também a alternativa acessível ao mapa (navegação por teclado). (RNF-08, acessibilidade)
9. **Controles do mapa agrupados e discretos.** Zoom e "voltar à cidade" no canto inferior direito, legenda recolhível no inferior esquerdo, seletor de camada no topo do mapa. Botões com fundo sólido, 32 px no desktop e 44 px no toque. Sem bússola, sem rotação, sem troca de mapa base. (Mapbox, Apple HIG, Esri)
10. **Linha do tempo única na base do mapa: "Últimas 24 h · Agora · Próximas 24 h".** Mostra medido e previsto separados, com o previsto marcado como Experimental quando vier de modelo (Windy, Ventusky, Flood Hub). (RF-09, RN-11)
11. **Alertas no formato Perigo, Fonte, Território, Hora, Ação.** Cartão curto e a mesma estrutura gera a mensagem padronizada de WhatsApp. Inclui "Confira na APAC ou no Cemaden" (NWS Impact-Based, IDAP). (RF-31, RF-32)
12. **Celular: indicadores primeiro, mapa em seguida em altura fixa (cerca de 55% da tela), demais blocos em abas.** Sem pop-ups no toque: o toque abre o bottom sheet. Uma coluna, gutter de 16 px. (Esri mobile, USGS)
13. **Números com algarismos tabulares e alinhados à direita em tabelas.** `font-variant-numeric: tabular-nums`, formatação com `Intl.NumberFormat("pt-BR")` e horas com `Intl.DateTimeFormat`. (Geist, web-interface-guidelines)
14. **Selo Experimental com explicação a um toque.** Selo pequeno (12 px, contorno, sem cor de risco) junto do valor previsto; ao tocar, mostra método e período de validação, como OpenSAFELY e Stamen. (RN-11)
15. **Página de Dashboards no modelo Gráfico, Mapa e Tabela por indicador.** Um indicador por cartão, título que diz a conclusão, abas para trocar a forma, fonte e nota sempre visíveis, download da tabela. Grade de 4 colunas que vira 1 no celular (Our World in Data, ONS, Observable). (só quando entrar no PRD)

## 4. Anti-padrões a evitar

1. **Cor como única informação.** Mapa ou chip que só muda de cor. Toda classe precisa de texto e, nos chips, de um número ou ícone. Lição do HealthMap: bolhas coloridas induziram leitura errada.
2. **Ausência pintada como "verde" ou "normal".** Território sem dado nunca usa a cor da menor classe. Usar o estado "sem dado" do Meteoalarm (branco ou hachura) com o texto "Dados insuficientes" (RN-01).
3. **Arco-íris de categorias e camadas sobrepostas.** O NWS precisou sair de 122 cores. Mais de 5 cores no mapa ou várias camadas ligadas ao mesmo tempo tornam o painel ilegível justamente no evento.
4. **Tipografia de landing page num painel operacional.** Números de 45 a 80 px, títulos de 50 px e cartões com 32 px de respiro empurram o que importa para baixo da dobra. Reservar o tamanho grande apenas para o estágio da cidade, e mesmo assim em 28 a 32 px.
5. **Menus e pop-ups que cobrem o mapa no celular.** Reclamação principal dos usuários do Windy. Pop-up preso ao ponto, menu de camadas aberto por padrão e tooltip dependente de hover não funcionam no toque. Usar bottom sheet e seletor segmentado.

Outros a vigiar: percentual de probabilidade no lugar de classe (RN-06); indicador sem fonte e hora (RF-19); animação contínua no mapa sem botão de pausa e sem respeito a `prefers-reduced-motion`.

## 5. Escala tipográfica e espaçamento sugeridos

Base: `html { font-size: 100% }` (16 px, o padrão do navegador). Tokens em rem a partir de 16 px. Família mantida: Atkinson Hyperlegible Next para texto e números, Outfit só para o nome da marca e o título da tela.

### 5.1 Tipografia

| Token proposto | Uso | Desktop | Celular | Altura de linha | Peso |
|---|---|---|---|---|---|
| `--t-meta` | Fonte e hora, selo Experimental, eixos | 12 px (0.75rem) | 12 px | 1.35 | 500 |
| `--t-rotulo` | Rótulo de indicador, cabeçalho de tabela, legenda | 13 px (0.8125rem) | 14 px | 1.35 | 600 |
| `--t-denso` | Linhas de tabela e ranking, painel lateral | 14 px (0.875rem) | 15 px | 1.45 | 400 |
| `--t-corpo` | Texto corrido, mensagens, formulários | 15 px (0.9375rem) | 16 px | 1.5 | 400 |
| `--t-subtitulo` | Título de cartão ou seção | 16 px (1rem) | 17 px | 1.3 | 600 |
| `--t-titulo` | Título da tela | 20 px (1.25rem) | 20 px | 1.25 | 650 |
| `--t-valor` | Número do indicador | 28 px (1.75rem) | 26 px | 1.1 | 650, tabular |
| `--t-estado` | Estágio oficial da cidade | `clamp(1.5rem, 2.5vw, 2rem)` (24 a 32 px) | 24 px | 1.1 | 700 |

Regras: nenhum texto abaixo de 12 px; contraste de pelo menos 4.5:1 no texto até 18 px (o cinza de metadados precisa passar também); campos de formulário com 16 px no celular; largura de linha do texto corrido até 70 caracteres; nada de caixa alta com espaçamento em rótulos.

Comparação com hoje: corpo cai de 20,25 px para 15 px (desktop) e 16 px (celular); título da tela cai de 31,5 a 49,5 px para 20 px; número do indicador cai de 45 px para 28 px; estágio cai de até 81 px para até 32 px.

### 5.2 Espaçamento e medidas

Grade de 4 px, usando os tokens que já existem (`--e-1` a `--e-6`):

| Uso | Desktop | Celular |
|---|---|---|
| Gutter lateral da página | 24 px | 16 px |
| Espaço entre cartões | 12 px | 8 a 12 px |
| Padding interno do cartão | 12 a 16 px | 12 px |
| Espaço entre rótulo e valor | 4 px | 4 px |
| Espaço entre seções | 24 px | 16 a 24 px |
| Altura do cabeçalho do app | 48 a 56 px | 52 px |
| Altura da linha de tabela ou ranking | 36 px | 44 px (área de toque) |
| Largura do painel lateral do território | 360 a 400 px | bottom sheet, alturas 25%, 55% e 90% |
| Botões de controle do mapa | 32 a 36 px | 44 px |
| Raio | campo 4 px, cartão 8 px, pílula total | igual |

Os tokens `--secao-y` e `--bloco-y` (até 120 px e 40 px) são de landing page e não devem ser usados nas telas da equipe.

### 5.3 Esboço de layout acima da dobra (desktop, 1366 x 768)

```
+--------------------------------------------------------------------------+
| ClimaSense  Mapa  Situação  Saúde  Ações          Atualizado 14:32  [Eu] |  48 px
+--------------------------------------------------------------------------+
| Estágio 2 · Atenção   declarado pelo COP às 14:20    [Mensagem WhatsApp] |  64 px
+--------------------------------------------------------------------------+
| Chuva 24 h   | Previsão 24 h  | Maré agora    | Rio Capibaribe | Saúde    |  96 px
| 38 mm        | 60 mm  Experim.| 1,9 m subindo | Atenção        | Dados    |
| APAC · 14:10 | APAC · 12:00   | DHN · 14:00   | APAC · 14:15   | insufic. |
+--------------------------------------------------------------------------+
| [Chuva | Rios | Maré | Saúde]                     | Bairro: Ibura      |
|                                                   | Distrito VI        |
|                 MAPA (base apagada)               | Classe: Alerta     |
|                                                   | Chuva 3/12/24 h    |
| [Legenda]                              [+][-][o]  | Fonte · hora       |
| Últimas 24 h ---------- Agora ------- Próximas 24 h | Ações abertas: 2   |
+--------------------------------------------------------------------------+
```

No celular: cabeçalho, faixa de estágio, indicadores em carrossel de 2 colunas, mapa com 55% da altura, e o território num bottom sheet.

## 6. Próximos passos sugeridos

1. Registrar em `docs/perguntas-abertas.md` a divergência entre o texto base de 18 px (RNF-ACE-02, specs) e a proposta de 16 px com corpo de 15 a 16 px, e decidir num ADR.
2. Validar a escala da seção 5 com a equipe do Vigidesastres em dois aparelhos reais (um celular comum e o computador da sala), medindo se encontram o estágio, a chuva de 24 h e o bairro mais crítico em até 10 segundos.
3. Só depois, abrir as tarefas para o agente de frontend, cada uma citando RF-09, RF-19, RF-20 ou RNF-08.
