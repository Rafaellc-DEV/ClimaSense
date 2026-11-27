# Proposta: Mapa v2, tela de decisão rápida

Status: **proposta, não aprovada**. Não altera código. Protótipo navegável em [`mapa-v2.html`](mapa-v2.html) (abrir direto no navegador; dados de exemplo marcados no topo).

Requisitos atendidos: RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RF-19, RF-20, RF-21, RF-22, RF-29, RF-30, RF-32, RF-40 (a), RF-42, RNF-08. Regras: RN-01, RN-02, RN-05, RN-06, RN-07, RN-11, RN-13.

## 1. Objetivo

Quem abre o Mapa precisa responder três perguntas em poucos segundos, sem rolar a página:

1. **Como está a cidade agora?** Estágio do COP, quantos bairros em cada estágio, chuva e maré.
2. **Onde agir primeiro?** Os bairros mais graves e os mais vulneráveis, em ordem.
3. **O que sei deste bairro?** Estágio (declarado ou sugerido e por quê), chuva do distrito, pessoas vulneráveis, saúde e risco, alertas oficiais. E o botão para declarar.

O dono reclamou de "muito zoom" e fontes grandes. A causa está no código: `base.css` fixa `html { font-size: 18px }` e `--t-corpo` é 1,125 rem (≈ 20 px). Tudo cresce junto. A proposta reduz a escala **só nas telas de trabalho** e reorganiza a tela para caber em 1366 × 768 sem rolagem de página.

## 2. O que muda em relação à tela atual

| Tela atual | Mapa v2 |
| --- | --- |
| Menu lateral de 296 px com texto | Trilho de ícones de 56 px (com nome no `title` e `aria-label`); no celular, barra de 5 ícones embaixo |
| Faixa do COP e "Bairros por estágio" em dois cartões grandes | Uma **barra de indicadores** de ~78 px: COP (com o alerta oficial ativo), contagem por estágio clicável, chuva 24 h, prevista 24 h, maré |
| Mapa geográfico é a única vista; o retrato por bairro fica escondido em "Ver os 94 bairros em lista" | **Grade dos 94 bairros** como vista padrão: um bloco por distrito, cada bairro uma célula com nome e cor do estágio, os mais graves primeiro. O mapa geográfico continua a um clique ("Geográfico") |
| Painel em dois níveis com blocos longos, títulos de seção e textos explicativos | Painel compacto de 352 px com 5 seções curtas; números em trincas (3 colunas) |
| Prioritários abaixo do mapa (rolar para ver) | Prioritários sempre à vista na coluna da esquerda, 12 linhas de 2 linhas cada |
| Camadas recolhidas em "Mais camadas" | Dois botões na barra de ferramentas: "Áreas de risco" e "Saúde" marcam as células; a população vulnerável vai para o painel |
| Corpo de 18 px, títulos até 44 px | Escala compacta 12 / 13 / 14 / 16 / 20 px |

## 3. Referências consultadas

| Referência | O que levamos |
| --- | --- |
| [Google Flood Hub](https://support.google.com/flood-hub) e [guia da Bellingcat](https://bellingcat.gitbook.io/toolkit/more/all-tools/google-flood-hub) | Clicar num ponto abre um **painel lateral** com tendência, medição e limiares oficiais; nível de confiança visível e "virtual" separado de "verificado" (no nosso caso, sugerido × declarado) |
| [GDACS](https://www.gdacs.org/) e [nota sobre o redesenho](https://www.govtech.com/em/emergency-blogs/disaster-zone/the-global-disaster-alert-and-coordination-system-gdacs-has-a-new-look.html) | **Mapa + lista** lado a lado; três níveis de cor; o que piorou fica em destaque e o antigo fica esmaecido (nossa ordem "mais grave primeiro" e o filtro por estágio) |
| [ArcGIS Dashboards, "Effective dashboards"](https://doc.arcgis.com/en/dashboards/latest/reference/author-effective-dashboards.htm) | Um painel por público; o mais importante maior e no caminho da leitura; mapa junto da legenda e lista junto do detalhe; **no máximo duas notificações**; cor só para diferença de dado |
| [Painel Rio / COR](https://en.prefeitura.rio/cidade/cor-ganha-letreiro-em-led-na-sala-de-situacao-com-as-cores-dos-estagios-operacionais/) e [estágios operacionais do Rio](https://www.band.com.br/noticias/o-que-sao-e-quais-sao-os-estagios-operacionais-do-rio-de-janeiro-202510282054) | O estágio oficial da cidade é o primeiro elemento e a cor do estágio domina a sala; o mapa é o panorama para coordenar estágios |
| [Windy, discussão da comunidade sobre a interface nova](https://community.windy.com/topic/32400/i-do-not-like-the-new-interface/13) | Contra-exemplo: trocar rótulos de texto por ícones no seletor de camadas confundiu os usuários. Mantemos **texto** nos botões de camada e de cor |

## 4. Princípios

1. **Uma tela, sem rolagem de página no computador.** Cada coluna rola por dentro quando precisar; a barra de indicadores nunca sai da vista.
2. **A cor do estágio é a única cor forte.** Distrito aparece como uma barra fina à esquerda do bloco; prioridade usa uma escala de um só azul.
3. **O mais grave sobe sempre** (RF-22): dentro de cada distrito, nas listas e no painel do distrito.
4. **Texto em vez de ícone** onde houver dúvida. Ícone sozinho só no trilho de telas, com nome acessível.
5. **Fonte e hora colam no número** (RF-19): toda linha de indicador tem uma linha de metadado de 12 px logo abaixo.
6. **Um clique para cada pergunta**: célula → bairro; nome do distrito → distrito; contagem → filtra o estágio; "Começar pelo mais grave" → bairro mais grave.

## 5. Layout

### 5.1 Desktop 1366 × 768 (área útil ≈ 1366 × 650)

Colunas: trilho 56 px · prioritários 264 px · grade flexível (≈ 690 px, 3 colunas de blocos) · painel 352 px.

```
┌────┬───────────────────────────────────────────────────────────────────────────────────────────┐
│ ▦  │ Mapa          Estágio do COP Atualizar │ Bairros por estágio (94)                │Chuva 24h│Prevista │Maré alta │
│    │ Atualizado    [ATENÇÃO] COP, 14:05     │ ■3 Crítico ■9 Alerta ■21 Atenção        │ 38 mm D7│ 62 mm D7│2,4 m 16:40│
│ ~  │ às 14:12      1 alerta oficial: APAC   │ ■52 Observação □9 Sem dados ▬▬▬▬▬▬▬▬    │APAC 14:00│OM 13:00 │OM 06:00  │
│    ├──────────────────┬──────────────────────────────────────────────────┬──────────────────────┤
│ ⊞  │ Prioritários     │ [Grade|Geográfico] Cor [Estágio|Distrito|Prior.] │ ‹ Distrito 7       ✕ │
│    │ [Bairros|Distr.] │ [▲ Áreas de risco] [+ Saúde]   [Buscar bairro…]  │ Nova Descoberta      │
│ ✓  │ 1 Nova Descob. ■ │ ┃Distrito 7 [Alerta] 11 ┃Distrito 3 [Aten.] 18┃D4 │ Distrito 7, 1º de 94 │
│    │   D7, 41 alag.…  │ ┃[Nova Descoberta]      ┃[Sítio dos Pintos]    ┃.. ├──────────────────────┤
│ ▥  │ 2 Ibura        ■ │ ┃[Passarinho][Vasco…]   ┃[Casa Amarela][Alto…] ┃   │ Estágio              │
│    │   D8, 38 alag.…  │ ┃[Córrego do Jenipapo]  ┃[Aflitos][Derby]…     ┃   │ [CRÍTICO] declarado  │
│    │ 3 Passarinho   ■ │ ┃…                      ┃[Pau Ferro]┆[Guabiraba]┆   │ por Carla, 13:50     │
│    │ …                │ ┃Distrito 2 [Alerta] 18 ┃Distrito 8 [Crít.] 3  ┃   │ “Morros com solo…”   │
│    │ 12 …             │ ┃[Dois Unidos][Linha…]  ┃[Ibura][Jordão][Cohab]┃   │ Sugerido: Alerta…    │
│    │ Ver os 94 bairros│ ┃…                      ┃Distrito 1 …          ┃   │ (Declarar) (Retirar) │
│    ├──────────────────┤ ──────────────────────────────────────────────────├──────────────────────┤
│    │ Fonte: Defesa    │ ■Crítico ■Alerta ■Atenção ■Obs. ┆Dados insuf.┆    │ Chuva no Distrito 7  │
│    │ Civil, 14:10…    │ cheio = declarado, listrado = sugerido. Fonte…  │ 38 mm│62 mm│118 mm   │
└────┴──────────────────┴──────────────────────────────────────────────────┴ (rola por dentro) ───┘
```

### 5.2 Desktop 1920 × 1080

Mesma estrutura; prioritários 300 px, painel 400 px. A grade cabe em 5 colunas de blocos e **os 94 bairros aparecem inteiros**, sem rolagem nenhuma. O painel do bairro cabe inteiro.

### 5.3 Celular (390 × 844)

Uma coluna. Barra de indicadores no topo (COP em uma linha, contagem por estágio, trinca chuva / prevista / maré). Abaixo, abas **Bairros | Prioritários** para não empilhar as duas listas. O painel abre como **folha de baixo** (até 72 % da altura), com alça, botão Fechar e Esc. Navegação entre telas na barra de 5 ícones embaixo, com `safe-area`.

```
┌──────────────────────────────┐
│ EXEMPLO — protótipo          │  ← só no protótipo
├──────────────────────────────┤
│ Mapa       Atualizado 14:12  │
│ Estágio do COP  Atualizar    │
│ [ATENÇÃO] COP, 14:05         │
│ 1 alerta oficial: APAC 11:30 │
│ ─────────────────────────────│
│ Bairros por estágio (94)     │
│ ■3 Crítico ■9 Alerta ■21 At. │
│ ■52 Observação □9 Sem dados  │
│ ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬ │
│ Chuva 24h │ Prevista │ Maré  │
│ 38 mm D7  │ 62 mm D7 │ 2,4 m │
│ APAC 14:00│ OM 13:00 │ 16:40 │
├──────────────────────────────┤
│ [  Bairros  |  Prioritários ]│
│ [Grade|Geográfico]           │
│ Cor [Estágio|Distrito|Prior.]│
│ [▲ Áreas de risco] [+ Saúde] │
│ [ Buscar bairro…           ] │
│ ┃Distrito 7 [Alerta] 11      │
│ ┃[Nova Descoberta][Passar…]  │
│ ┃[Vasco da Gama][Córrego…]   │
│ …                            │
├──────────────────────────────┤
│  ▦     ~     ⊞     ✓     ▥   │  ← navegação
└──────────────────────────────┘

Ao tocar num bairro:
┌──────────────────────────────┐
│            ───               │
│ ‹ Distrito 8              ✕  │
│ Ibura                        │
│ Distrito 8, prioridade 2º    │
│ [CRÍTICO] declarado 13:50    │
│ (Declarar estágio) (Retirar) │
│ Chuva no Distrito 8          │
│ 35 mm │ 58 mm │ 104 mm       │
│ …                            │
└──────────────────────────────┘
```

## 6. Hierarquia: o que fica acima da dobra

Em 1366 × 768, sem rolar nada:

1. **Barra de indicadores** (sempre): COP, contagem por estágio, chuva, prevista, maré, hora da última atualização.
2. **Grade**: os blocos dos distritos mais prioritários inteiros (D7, D2, D3, D8, D4, D5) e o começo dos demais. Os bairros críticos e em alerta de cada distrito ficam na primeira linha do bloco.
3. **Prioritários**: os 10 primeiros.
4. **Painel**: estágio, motivo, botão Declarar, chuva do distrito e as pessoas do bairro. Saúde, risco e alertas exigem uma rolagem curta **dentro do painel**.

Em 1920 × 1080 tudo cabe.

## 7. Componentes

| Componente | Conteúdo | Origem dos dados (já existe) |
| --- | --- | --- |
| **Trilho** | 5 telas, ícone + nome acessível | rotas atuais |
| **Barra de indicadores** | COP (selo, fonte, hora, Atualizar/Informar, 1 linha do alerta oficial ativo); contagem por estágio com barra proporcional de 94; Chuva 24 h (maior distrito, estações válidas); Prevista 24 h (maior distrito); Maré alta hoje | `/estagios/oficial`, `contarPorEstagio`, `insumos.chuva_24h_mm`, `chuva_prev_24h_mm`, `mare_max_m`, `alertas_oficiais` |
| **Contagem clicável** | Toque em "9 Alerta" deixa só esses bairros acesos na grade; toque de novo desfaz | mesmo dado |
| **Grade dos 94 bairros** | Um bloco por distrito na ordem de prioridade (RF-22); cabeçalho com nome (abre o distrito), selo do estágio do distrito e nº de bairros; células com o nome do bairro | `/estagios?nivel=bairro`, `/estagios?nivel=distrito`, `/territorios/prioridade`, `distrito_id` do GeoJSON |
| **Célula** | Cor do estágio; **cheia e em negrito = declarado**, **listrada = sugerido**, **cinza tracejado = Dados insuficientes**; marca ▲ se tem área de risco e "+n" se tem unidades de saúde (quando as camadas estão ligadas) | `emVigor()`, `resumo-vulnerabilidade` |
| **Cor** | Estágio (padrão) · Distrito · Prioridade | `distritos.ts`, `classePrioridade` |
| **Geográfico** | O `MapaBairros` atual (MapLibre), com as mesmas cores e o mesmo painel | sem mudança |
| **Busca** | Apaga as células que não casam; Enter abre o primeiro | `semAcento` |
| **Prioritários** | Abas Bairros/Distritos; posição, nome, selo, "D7, 41 alagamentos, 23 deslizamentos"; 12 primeiros e "Ver os 94 bairros"; rodapé com fonte, hora e "não é chance de acontecer" | `/territorios/prioridade` |
| **Painel do bairro** | Cabeçalho (voltar ao distrito, nome, distrito e prioridade, Fechar) → Estágio → Chuva no distrito → Pessoas que moram no bairro → Saúde e risco → Alertas oficiais | `ItemEstagio`, `ResumoVulnerabilidade` |
| **Painel do distrito** | Estágio do distrito e Declarar; números (idosos, crianças, alagamentos, deslizamentos); bairros do distrito em células, mais graves primeiro | `ItemPrioridadeTerritorio`, `PainelDistrito` atual |
| **Painel vazio** | "Escolha um bairro" e o atalho **Começar pelo mais grave** | `ordenarPorGravidade` |
| **Painel de alertas** | Aberto pelo link do COP: alertas ativos com origem, nível, emissão, validade, território e link; fontes sem alerta | `alertas_oficiais` |

Nada novo é pedido ao backend. A grade usa os mesmos dados da lista de bairros que já existe.

## 8. Tipografia e densidade

| Token proposto | Tamanho | Uso |
| --- | --- | --- |
| `--t-meta` | 12 px | fonte e hora, rótulos de indicador, detalhes de lista |
| `--t-apoio` | 13 px | nomes nas células, textos do painel, botões |
| `--t-corpo` | 14 px | texto base da tela |
| `--t-titulo` | 16 px | título do painel, números do painel |
| `--t-numero` | 20 px | valores da barra de indicadores |

- Fonte única: Atkinson Hyperlegible Next (já é a do projeto). Outfit só no "Mapa" e nos títulos dos blocos.
- `font-variant-numeric: tabular-nums` em todos os números.
- Alvos: 32 px com mouse (`pointer: fine`), **44 px no toque** (`pointer: coarse`). Células da grade: 24 px no mouse, 40 px no toque.
- Zoom do navegador continua livre. A pessoa que precisar de letra maior usa Ctrl + ou o zoom do celular; a tela reflui em uma coluna.
- **Decisão necessária:** `specs/requirements.md` RNF-ACE-02 pede texto base de 18 px. O PRD não fixa tamanho (vale o PRD), mas a mudança deve virar ADR ("densidade compacta nas telas de trabalho, texto mínimo 12 px, zoom livre") e pergunta em `docs/perguntas-abertas.md` para validar com as duas usuárias. A sugestão é aplicar a escala compacta por `data-densidade="compacta"` na área da equipe, sem tocar no login e na landing.

## 9. Textos finais

| Lugar | Texto |
| --- | --- |
| Título | Mapa |
| Hora | Atualizado às 14:12 · (erro) falhou às 14:12 |
| COP | Estágio do COP · Atualizar · Informar · COP, informado às 14:05 |
| COP sem dado | Dados insuficientes. Falta o estágio do COP. Não é risco baixo. |
| Alerta na barra | 1 alerta oficial ativo: APAC, 11:30 |
| Contagem | Bairros por estágio (94) · 3 Crítico · 9 Alerta · 21 Atenção · 52 Observação · 9 Sem dados |
| Linha da contagem | 12 declarados pela equipe, 73 sugeridos pelo sistema |
| Indicadores | Chuva 24 h · Prevista 24 h · Maré alta hoje |
| Ferramentas | Grade · Geográfico · Cor: Estágio, Distrito, Prioridade · Áreas de risco · Saúde · Buscar bairro… |
| Bloco | Distrito 7 · 11 bairros |
| Selo curto (listas, cabeçalhos de bloco) | Sem dados (nome do estágio no RF-29); o painel sempre diz "Dados insuficientes" e o que falta |
| Legenda | cheio e negrito: declarado · listrado: sugerido · Cinza tracejado é falta de dado, não risco baixo. |
| Legenda (prioridade) | Mais prioritários … Menos · Prioridade é onde agir primeiro, não chance de acontecer. |
| Lista | Prioritários · Bairros · Distritos · Ver os 94 bairros · Mostrar só os 12 primeiros |
| Linha da lista | D7, 41 alagamentos, 23 deslizamentos |
| Painel vazio | Escolha um bairro · Toque num bairro na grade ou na lista. Toque no nome do distrito para ver o distrito inteiro. Esc fecha. · Começar pelo mais grave |
| Painel: seções | Estágio · Chuva no Distrito 7 · Pessoas que moram no bairro · Saúde e risco · Alertas oficiais |
| Origem | declarado por {nome} às {hora} · sugerido pelo sistema; ninguém declarou · o sistema não consegue sugerir e ninguém declarou |
| Sem sugestão | Falta: {insumo}. Isso não quer dizer risco baixo. |
| Botões | Declarar estágio · Retirar · Declarar estágio do distrito |
| Chuva | Medida 24 h · Prevista 24 h · Prevista 72 h · 3 de 3 estações · O bairro usa a chuva do distrito. |
| Pessoas | Idosos (60+) · Crianças (0 a 14) · Com deficiência: Dados insuficientes, sem fonte por bairro · IBGE, Censo 2022. Só contagens agregadas. |
| Saúde e risco | 3 unidades de saúde, 1 em área de risco · em área de risco · 12 áreas de risco mapeadas, cobertura parcial |
| Alertas | APAC: chuva moderada a forte · Emitido às 11:30, vale até 23:59 · Território: … · Ver na fonte · Confira sempre na APAC ou no Cemaden antes de agir. |

## 10. Estados

O protótipo tem um seletor **Estado** no topo para ver cada um.

| Estado | Barra de indicadores | Grade | Prioritários | Painel |
| --- | --- | --- | --- | --- |
| **Carregando** | rótulos fixos + esqueleto no lugar do valor; "Carregando…" na hora | blocos dos distritos com células-esqueleto (a malha aparece antes dos estágios, como hoje) | 9 linhas-esqueleto; leitor de tela ouve "Carregando as prioridades…" | o que já chegou; "Carregando…" no resto |
| **Sem dado** | cada indicador diz **Dados insuficientes** e **Falta: {fonte}** | todas as células cinza tracejadas e uma caixa: "Dados insuficientes em todos os bairros. Falta a previsão de chuva e de maré… Cinza não quer dizer risco baixo." | se faltar a fonte de ocorrências: "Dados insuficientes. Falta a fonte de ocorrências…" | "o sistema não consegue sugerir e ninguém declarou" + o insumo que falta |
| **Sem dado parcial** | — | D6 sem estação válida: bairros do D6 cinza tracejados; os demais normais | normal | "Medida 24 h: Dados insuficientes, 0 de 2 estações válidas" |
| **Erro** | mantém o último dado com selo **desatualizado**; hora "Atualizado às 13:40, falhou às 14:12" | faixa amarela: "Não foi possível atualizar os estágios às 14:12. Mostrando os de 13:40. **Tentar de novo**" | último dado | último dado |
| **Zero medido** | "0 mm" com fonte e hora (RN-02), nunca "Dados insuficientes" | normal | normal | "0 mm" |

## 11. Como cada regra do CLAUDE.md é atendida

| Regra | Como |
| --- | --- |
| 1. Só dados reais (ADR 0008, RF-12.10) | Nenhum dado novo: tudo vem dos endpoints atuais. Os números do HTML são exemplo, marcados "EXEMPLO — protótipo" e não vão para o produto |
| 2. Ausência não é risco baixo (RN-01, RN-02) | "Dados insuficientes" + "Falta: {fonte}" em cada indicador, célula e seção; cinza **tracejado**, nunca o azul de Observação; zero medido mostra "0 mm" |
| 3. Prioridade não é probabilidade (RN-06) | Estágio e prioridade só como classe e posição ("1º de 94"); escala de prioridade em um azul com legenda "não é chance de acontecer"; nenhum percentual na tela |
| 4. Experimental até validar (RN-11) | A tela não mostra previsão de alagamento. Se o `risco_ml` entrar nos motivos da sugestão, a linha leva o selo **Experimental** (estilo `.selo-exp` já no protótipo) |
| 5. Decisão humana por último (RN-05) | Sugerido (listrado) e declarado (cheio, com autor e hora) sempre distintos; a sugestão nunca muda o estágio; "Declarar" abre o diálogo atual com justificativa e mensagem de WhatsApp |
| 6. Fonte e hora em todo indicador (RF-19, RF-42) | Linha de metadado de 12 px abaixo de cada número; selo "desatualizado" quando a fonte vence |
| 7. Simples, só o que o cliente pediu (RF-20, RNF-08) | 5 indicadores no topo (eram 2 cartões + legendas + "Mais camadas"); nenhum dado ou recurso fora do PRD; a grade substitui a lista escondida dos 94 bairros em vez de somar outra |
| 8. Só agregados (RN-13, RNF-03) | Só contagens por bairro e distrito; números pequenos seguem a supressão atual ("oculto para proteger a privacidade"); nenhum nome de pessoa atendida |
| 9. Segurança | Protótipo estático, sem segredos; só carrega fontes do Google Fonts |

## 12. Acessibilidade

- Cada célula é um `<button>` com `aria-label` completo ("Ibura: Crítico, declarado; prioridade 2º de 94"); o estado não depende só da cor (negrito, listra, tracejado e texto no painel).
- Foco visível em laranja (`--cs-foco`); Esc sobe um nível (bairro → distrito → cidade); foco vai para o título do painel ao abrir.
- A grade é a alternativa ao mapa para teclado e leitor de tela (hoje é a lista escondida).
- `prefers-reduced-motion` desliga o brilho do esqueleto e a animação da folha de baixo.
- Tema escuro com os mesmos tokens do projeto.
- O endereço guarda a seleção (`#bairro=Ibura`, `#distrito=7`) para mandar o link pelo WhatsApp.

## 13. Tokens novos propostos

Preenchimento das células, mais forte que o `--n-*-bg` atual para leitura de longe (contraste do texto ≥ 4,5:1):

```
--grade-obs: #d6e6f5  --grade-ate: #f7d980  --grade-ale: #f2a27a
--grade-cri: #a41f15 (texto branco)  --grade-sem: #eef1f3 (borda tracejada #6b7a85)
```

## 14. Caminho de implementação (se aprovada)

1. ADR 0015: densidade compacta na área da equipe e revisão do RNF-ACE-02.
2. `design-system`: tokens `--grade-*` e escala compacta sob `data-densidade="compacta"`.
3. `features/mapa`: `BarraIndicadores` (junta `FaixaOficial` e `ContagemBairros`), `GradeBairros` (nova, reaproveita `ordenarPorGravidade` e `emVigor`), `PainelTerritorio` e `PainelDistrito` compactos, `Prioritarios` na coluna fixa. `MapaBairros` fica como vista "Geográfico".
4. Casca: trilho de ícones em vez do menu de 296 px.
5. Testes: e2e de 1366 × 768 sem rolagem de página; RN-01 (célula sem dado nunca azul); axe.

## 15. Perguntas para o cliente

- A grade como vista padrão serve, ou a equipe prefere abrir no mapa geográfico?
- 14 px de base é confortável no monitor da sala? (testar com as duas usuárias)
- O alerta oficial ativo na barra basta, ou precisa de um indicador próprio?
