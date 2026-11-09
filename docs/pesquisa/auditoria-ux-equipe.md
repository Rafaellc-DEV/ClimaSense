# Auditoria de UX da área da equipe

> **Nota de 06/11/2026:** abrigos saíram do escopo do produto (PRD v3, ADR 0016). As propostas sobre abrigos abaixo
> ficam como histórico e não devem ser implementadas.

> Pesquisa e proposta de produto de 05/11/2026. Base: `specs/foco-chuvas.md`, `docs/funcionalidades-equipe.md`,
> personas de `specs/requirements.md` (seção 3), a entrevista com o Vigidesastres (23/10/2026), a avaliação do dono
> do produto e capturas reais das 12 telas (Edge, 1440 px, conta `gestor@climasense.dev`, dados de 05/11/2026 17h).
> Não altera código. Onde a proposta pede mudança de API, isso está dito.

## 0. Quem usa e o critério

**Duas pessoas** do Vigidesastres (Mari Siqueira e Mari Lima). Já usam o painel do COP, conferem a APAC e o Cemaden à
mão e mandam o aviso por WhatsApp. O critério do dono do produto é o critério desta auditoria:

> "Uma boa solução tem que ser simples e não ser preciso explicar para usá-la."

Teste aplicado a cada tela: **a pessoa abre, faz uma pergunta e tem a resposta em 5 segundos, sem abrir dica (ⓘ),
sem rolar e sem saber o que é ERA5, mediana ou horizonte.**

### O que as capturas mostraram (achados transversais)

1. **A mesma informação aparece em 4 lugares.** A fila "Territórios por prioridade" está em Cenários, em
   Territórios ("Atenção primeiro"), em Painel ("Detalhes técnicos") e, com outro nome, em "Onde agir". Estágio por
   distrito aparece em Painel, Estágios, Boletim e no mapa.
2. **Ranking sem diferença não é ranking.** Em 05/11 os 8 distritos de Cenários têm exatamente os mesmos chips
   ("Nenhum aviso ativo · Chuva prevista dentro do comum · Maré alta junto com a chuva · Confiança baixa"). A ordem de 1
   a 8 sugere uma diferença que não existe. E o detalhe do cenário falhou ("Não foi possível carregar o cenário").
3. **"Maré alta junto com a chuva" com 1,6 mm previstos** é ruído: o limiar de 0,6 m é ultrapassado em quase todo
   ciclo de maré de sizígia. Vira alarme permanente e ensina a ignorar o chip.
4. **Fonte repetida e com jargão.** Em Séries a frase "Fonte: Chuva horária por distrito (reanálise ERA5) (derivada
   (modelo))" aparece 3 vezes na mesma tela, com parênteses dentro de parênteses. A fonte é uma só e deveria aparecer
   uma vez, no rodapé.
5. **Rótulos de sistema no lugar de rótulos de pessoa:** "Variável", "Frequência", "Horizonte da previsão",
   "Cobertura", "Mediana", "Série curta", "Confiança baixa", "Detalhes técnicos", "Pendências: Baixa".
6. **Telas de registro vazias dominam o menu.** Abrigos (199 linhas "Sem informação / não informada / sem dado"),
   Ações (vazia), Avaliações (vazia), Comunicados (vazia). A equipe não vai preencher abrigos (decisão já tomada).
7. **O que funciona é frase + número + data.** O dono entendeu "Maio é, em média, o mês mais chuvoso" e "Maior mês:
   maio de 2022, 438 mm" sem ajuda. Esse é o padrão a copiar em todas as telas analíticas.

---

## 1. Tela a tela

Legenda do teste de 5 s: **Sim**, **Parcial**, **Não**.

| Tela | Pergunta ao abrir | 5 s? | Cortar, juntar, esconder | Veredito |
|---|---|---|---|---|
| **Painel** | "Preciso fazer alguma coisa agora? Onde?" | **Parcial.** A faixa azul responde ("Nenhum território pede decisão agora"), mas o resto repete outras telas. | Cortar "Detalhes técnicos" (repete Cenários e Territórios). Cortar cartão "Abrigos abertos" (sem dado, a equipe não atualiza). Juntar "Onde agir" na faixa azul (dizem a mesma coisa). "Pendências: Baixa / Fonte desatualizada" vira um selo no rodapé ("3 fontes atrasadas"). Manter: frase do dia, chuva prevista, maré, alerta oficial ativo, botão "Avisar os distritos". | **Fundir com Situação.** Vira o topo da tela "Hoje". |
| **Estágios** (já renomeado "Situação" no código em andamento) | "Em que situação está cada distrito e preciso mudar algo?" | **Parcial.** 8 cartões iguais, cada um com "Declarado / Sugerido / Números e fonte / Ver bairros / Histórico / Declarar". Repetição de "Nenhuma situação declarada" 8 vezes. | Trocar 8 cartões por uma **tabela de 8 linhas** (distrito · situação atual · sugestão · por quê em 1 frase · botão). Mostrar bairros só quando a sugestão sobe. Motivo comum aos 8 dito uma vez ("Nenhum distrito passou dos limites"). Limiares para Administração. | **Manter e simplificar.** É o coração do produto (D1, D2, D5). |
| **Abrigos** | "Quantos abrigos abertos e onde?" | **Não.** Responde "0" e 199 linhas sem informação. | Remover cadastro, ocupação, desabrigados e histórico. Manter só o **feed do COP de abrigos ativos** (existe API) como bloco "Abrigos abertos agora (COP)" dentro de "Hoje" e no mapa. | **Remover** como tela (decisão já tomada). Sobra um bloco somente leitura. |
| **Ações** | "O que está sendo feito em campo?" | **Parcial.** Tela clara, mas sempre vazia; a seleção de território é uma lista de 102 nomes. | Ver seção 5. | **Fundir com Situação** como "Registro do evento". |
| **Boletim** | "O que mando para o diretor e para os distritos?" | **Não.** Não diz para quem é, nem quando mandar; a tabela tem 8 linhas "Nenhum declarado / Observação"; "Fontes e horários" é um parágrafo de 6 fontes entre parênteses. | Ver seção 4. | **Manter e redesenhar** com marca e seções fixas. |
| **Territórios** (mapa) | "Onde fica e qual bairro está pior?" | **Parcial.** Mapa bom, mas a frase de abertura tem 30 palavras e a lateral repete a fila de Cenários; "Colorir por: Situação / Prioridade / Ocorrências". | Deixar duas camadas: **Situação de hoje** e **Onde já alagou** (ocorrências da Defesa Civil). Tirar "Prioridade" (é Cenários de novo). Tirar "Baixar mapa offline" e "Exportar CSV" para um menu "⋯". | **Fundir:** o mapa vira o centro de "Hoje" (camada situação) e de "Histórico" (camada alagamentos). Não precisa de item de menu próprio. |
| **Comunicados** | "Tem aviso para escrever, revisar ou publicar?" | **Sim.** | Nada a cortar. Ligar com Situação: ao subir para Alerta, oferecer "Escrever aviso à população" já preenchido. | **Manter** (validado pelo dono). |
| **Avaliações** | "Por que esse território precisa de atenção?" | **Não.** O conceito não existe no dia a dia da equipe; o fluxo pede evidência, revisão por outra pessoa e é sempre vazio. Duas pessoas não fazem revisão cruzada de avaliação (já decidido para o estágio). | A justificativa já existe na declaração de situação. "Registrar avaliação" em Cenários vira "Usar na justificativa". | **Remover** (absorvido pela justificativa da Situação). Dados antigos ficam só leitura no histórico. |
| **Cenários** | "Amanhã vai dar problema? Onde?" | **Não.** Ranking sem diferença, 3 indicadores, 2 gráficos, chips e "Confiança baixa"; leigo pergunta "para quê?". | Ver seção 3.2. | **Simplificar e renomear "Próximos 3 dias"**, como parte de "Antes da chuva". |
| **Séries** | "Este ano está chovendo mais que o normal? Quando costuma ser pior?" | **Não** no topo; **Sim** no calendário de baixo. | Ver seção 3.1. | **Simplificar e renomear "Histórico de chuva"**, com o calendário no topo. |
| **Fontes** | "Posso confiar no número que estou vendo?" | **Sim** para técnico; **não** para a equipe (frescor, limite, tipo "Derivada (modelo)"). | Para a equipe: um único selo global ("Dados em dia" / "2 fontes atrasadas: previsão de chuva desde ontem 23h"). Tabela completa para Administração. | **Mover para "Plataforma"** (fora do dia a dia). |
| **Administração** | "Quem tem acesso e o que foi feito?" | **Sim.** | Receber Fontes e Limiares da Situação. | **Manter** em "Plataforma". |

---

## 2. Nova navegação (6 itens)

Organizada pelo ciclo do evento de chuva, como a referência AerVita, mas com o vocabulário da equipe.

```
┌──────────────────────────────┐
│ climasense                   │
│                              │
│  HOJE                        │
│  ● Situação          (início)│  ← painel + estágios + mapa + abrigos COP + registro do evento
│                              │
│  ANTES DA CHUVA              │
│  ○ Próximos 3 dias           │  ← era Cenários
│  ○ Histórico de chuva        │  ← era Séries (+ alagamentos por bairro)
│                              │
│  AVISAR                      │
│  ○ Comunicados          (2)  │  ← aviso à população, com revisão
│  ○ Boletins                  │  ← boletim com marca, arquivo dos enviados
│                              │
│  DEPOIS DA CHUVA             │
│  ○ Saúde depois da chuva  ◇  │  ← futuro: leptospirose, arboviroses, acidentes
│                              │
│ ──────────────────────────── │
│  PLATAFORMA (rodapé, menor)  │
│  ○ Fontes · Administração    │
└──────────────────────────────┘
```

Itens principais: **Situação, Próximos 3 dias, Histórico de chuva, Comunicados, Boletins, Saúde depois da chuva**
(6). Fontes e Administração ficam no rodapé do menu, menores, e só a Administração exige permissão.

Por que "Hoje" e não "Durante": a equipe abre o sistema todo dia, com ou sem chuva. "Situação" é a tela inicial e
serve para os três momentos: em dia seco ela mostra "Sem chuva relevante nos próximos 3 dias" e o atalho para o
histórico; no evento ela mostra o que mudar e o registro do evento.

**Onde entra "Saúde depois da chuva":** no grupo "Depois da chuva", com o mesmo formato da tela de Arboviroses da
referência: 3 KPIs no topo (casos de leptospirose nas últimas 4 semanas, comparação com o mesmo período do ano
anterior, distritos acima do esperado), gráfico por semana epidemiológica com uma linha por agravo e **uma faixa
vertical marcando os eventos de chuva forte** (o cruzamento que a referência não tem), e ranking por distrito com
barras. A janela típica de leptospirose é de 1 a 4 semanas após a exposição, então a tela pode dizer: "Choveu forte em
12/05. Fique atento a casos de leptospirose até 09/06 nos distritos V e VII, que mais alagaram." Depende do extrato
por bairro que a própria Vigilância precisa fornecer (o SINAN público só tem município). Até lá o item fica fora do
menu, não como item "em breve" vazio.

---

## 3. Redesenho

### 3.1 Séries → "Histórico de chuva"

**Ideia central:** responder 3 perguntas, na ordem em que uma pessoa leiga pensaria, cada uma com uma frase grande
antes do gráfico. Nada de filtros técnicos no topo.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Histórico de chuva                                    [ Recife inteiro ▾ ]  │
│ Como a chuva deste ano se compara com os anteriores e quando costuma ser    │
│ pior.                                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. ESTE ANO ATÉ AGORA                                                       │
│                                                                             │
│   Em 2026 choveu 1.540 mm no Recife, 6% acima da média de 2021 a 2025       │
│   para o mesmo período.                                                     │
│                                                                             │
│   ▇ 2026  ┄ média        mm por mês                                         │
│   400 ┤        ▇                                                            │
│   200 ┤   ▇ ▇ ▇ ▇ ▇ ┄ ┄                                                     │
│     0 ┼─jan─fev─mar─abr─mai─jun─jul─ago─set─out─nov─dez                     │
│                                                                             │
│   [ 1.540 mm ]        [ maio: 402 mm ]          [ 21/06: 75,7 mm ]          │
│   no ano              mês mais chuvoso          dia mais chuvoso            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. EM QUE MESES CHOVE MAIS?                (o calendário atual, sem mudar)  │
│   Maio é, em média, o mês mais chuvoso.   Maior mês: maio de 2022, 438 mm   │
│   [mapa de calor ano × mês, a partir de 2021]                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. ONDE MAIS ALAGOU?                        (novo, dados da Defesa Civil)   │
│   Desde 2014, Ibura, Jordão e Cohab tiveram mais atendimentos de            │
│   alagamento. 7 em cada 10 aconteceram em abril, maio e junho.              │
│   Ibura     ████████████████  62 dias com atendimento                       │
│   Jordão    ███████████       44                                            │
│   Cohab     █████████         37                                            │
│   ...  (10 bairros)                               [ Ver no mapa ]           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Dados: chuva estimada por satélite e modelo (ERA5, via Open-Meteo), desde   │
│ 2021, atualizada em 04/11 23h33. Alagamentos: atendimentos da Defesa Civil  │
│ do Recife, 2014 a 2024.  · 7 dias sem dado aparecem riscados ·  Baixar CSV  │
└─────────────────────────────────────────────────────────────────────────────┘
```

Os números acima são ilustrativos de formato; os reais vêm das rotas `/series`, `/series/sazonalidade` e de uma
agregação nova sobre `recife-alagamento`.

**O que sai e para onde vai**

| Hoje | Proposta |
|---|---|
| Filtro **Variável** (Chuva / Maré / Nível dos rios / Temperatura) | **Remover.** Maré não tem histórico útil aqui, nível dos rios e temperatura não têm fonte ("Ainda não há série histórica"). Mostrar opção que leva a tela vazia é o pior caso. A tela é só de chuva. |
| Filtro **Frequência** (Diária / Semanal / Mensal) | **Remover.** O gráfico 1 é sempre mensal (12 barras legíveis). Quem quer o diário clica numa barra do mês e abre os dias daquele mês. |
| Botão **Média histórica** (desabilitado fora do mensal) | **Remover o botão.** A linha da média está sempre ligada, porque é a comparação que dá sentido ao gráfico. |
| Período pelo filtro global "1 jan a 5 nov 2026" | **Escolha de ano** (2026 ▾). O "até agora" é implícito. |
| Selo **"Série curta"** + dica | **Remover.** Com 5 anos de referência, dizer na frase: "média de 2021 a 2025". Se houver menos de 3 anos, a frase vira "Ainda há poucos anos para comparar (2 anos)". |
| **"1 aviso"** + dica | Remover; o aviso vira parte da frase ou do rodapé. |
| "Faltam dados em 7 dias" na frase principal | Sai da frase; vai ao rodapé: "7 dias sem dado aparecem riscados". |
| Fonte repetida 3 vezes, "(reanálise ERA5) (derivada (modelo))" | **Uma vez**, no rodapé: "Dados: chuva estimada por satélite e modelo (ERA5, via Open-Meteo), desde 2021, atualizada em 04/11 23h33." |
| Cartões **Média / Mediana / Máximo / Cobertura / Dias sem dado** | Trocar por 3 números com sentido: **chuva no ano**, **mês mais chuvoso**, **dia mais chuvoso** (com a data). Média diária de 5,1 mm e mediana de 2,7 mm não ajudam a decidir nada. "Ver todas as medidas" vai para o CSV. |
| Linha 2020 inteira riscada no calendário | Começar no primeiro ano com dado (2021). |
| "Ver como tabela", "Usar texturas nas cores" | Manter, em menu "⋯" do gráfico (acessibilidade sem poluir). |

**Textos exatos**

| Lugar | Texto atual | Texto novo |
|---|---|---|
| Título | Séries e sazonalidade | **Histórico de chuva** |
| Subtítulo | Quanto choveu no território e no período escolhidos, comparado com os anos anteriores. | **Como a chuva deste ano se compara com os anteriores e quando costuma ser pior.** |
| Título do gráfico 1 | Quanto choveu em Recife inteiro? | **Este ano até agora** |
| Frase do gráfico 1 | Setembro de 2026 teve 5% menos chuva que a média de 2021 a 2025 (84,7 mm contra 89,1 mm). Faltam dados em 7 dias. | **Em 2026 choveu {total} mm no {território}, {x}% {acima/abaixo} da média de 2021 a 2025 para o mesmo período.** (Se \|x\| < 10%: "perto da média de 2021 a 2025".) |
| Legenda | Chuva acumulada / Média histórica do mês | **2026 / Média dos anos anteriores** |
| Lacuna | Sem dado (lacuna da fonte, não é zero) | **Riscado: dia sem dado (não quer dizer que não choveu)** |
| Cartões | Média / Mediana / Máximo / Cobertura / Dias sem dado | **Chuva no ano · Mês mais chuvoso · Dia mais chuvoso** |
| Seção 2 | Em que meses choveu mais? | **Em que meses chove mais?** (frases atuais mantidas) |
| Seção 3 | (não existe) | **Onde mais alagou?** / "Desde 2014, {b1}, {b2} e {b3} tiveram mais atendimentos de alagamento da Defesa Civil. {n} em cada 10 aconteceram em {meses}." |
| Rodapé | Fonte: Chuva horária por distrito (reanálise ERA5) (derivada (modelo)), atualizada ontem, 23h33. | **Dados: chuva estimada por satélite e modelo (ERA5, via Open-Meteo), desde 2021, atualizada {quando}. Alagamentos: atendimentos da Defesa Civil do Recife, 2014 a 2024.** |

### 3.2 Cenários → "Próximos 3 dias"

**Ideia central:** a pergunta do leigo é "vai dar problema? onde? quando?". A tela responde com uma frase, depois uma
lista curta **só dos distritos que se destacam** e, por fim, o gráfico de chuva e maré juntos. Ranking de 8 itens
iguais some.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Próximos 3 dias                          Previsão de hoje, 17h · Recife     │
│ O que a previsão de chuva e maré indica até sábado, distrito por distrito.  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ☁  Sem chuva forte prevista até sábado.                                    │
│     O máximo previsto é 1,6 mm em 24 h no Distrito I; o Recife costuma ter  │
│     problema a partir de 40 mm.                                             │
│                                                                             │
│     (em dia de chuva, a mesma faixa diz:)                                   │
│  ⚠  Chuva forte prevista para amanhã à tarde, com maré alta às 15h.         │
│     Os distritos V, VI e VIII devem receber mais de 50 mm entre 12h e 18h.  │
│     [ Ver bairros que já alagaram com chuva parecida ]  [ Ir para Situação ]│
├─────────────────────────────────────────────────────────────────────────────┤
│ CHUVA E MARÉ, HORA A HORA                         [ Recife ▾ ] [ DS V ▾ ]   │
│  mm/h ▇ chuva prevista            ── maré (m)                               │
│   ┤          ▇▇                 ╭─╮                                         │
│   ┤        ▇▇▇▇▇▇              ╱   ╲         ░░░ chuva forte + maré alta    │
│   ┼──qui──────────sex──────────sáb──                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ POR DISTRITO                                                                │
│  Distrito          Chuva em 24 h (pior período)   Quando           Situação │
│  DS V              62 mm  ████████████            sex 12h-18h      sobe ▲   │
│  DS VIII           55 mm  ██████████              sex 12h-18h      sobe ▲   │
│  DS VI             51 mm  █████████               sex 13h-17h      sobe ▲   │
│  Outros 5 distritos: menos de 20 mm.                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Previsão: Open-Meteo, atualizada hoje 17h. Maré: em frente ao Porto do      │
│ Recife. É uma previsão, não um alerta oficial: confira APAC e Cemaden.      │
│ Experimental.                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**O que sai e para onde vai**

| Hoje | Proposta |
|---|---|
| Ranking 1 a 8 com chips iguais | **Remover.** Lista só os distritos que passam do limite; os demais viram "Outros 5 distritos: menos de 20 mm". Ordenação por chuva prevista (número que todos entendem), não por "prioridade". |
| Chip "Maré alta junto com a chuva" | Só aparece se a chuva da mesma janela passar do limite de atenção. Maré alta sozinha não é notícia. |
| Chip "Nenhum aviso ativo" × 8 | Uma linha no topo, só se houver aviso: "Aviso oficial ativo: APAC, chuva moderada, até sex 18h." |
| "Confiança baixa" | Remover do cartão. Se a previsão for instável, dizer na frase: "As previsões mudaram bastante desde ontem; confira de novo à noite." |
| Seletor "Horizonte da previsão 24 h / 48 h / 72 h" | **Remover.** Mostrar sempre 72 h; o eixo em dias da semana ("qui, sex, sáb") já responde "quando". |
| 3 indicadores (Janela de atenção, Chuva prevista em 24 h, Maré máxima) | Viram parte da frase principal. |
| Dois gráficos (chuva; maré) alinhados | **Um gráfico** com barras de chuva e linha de maré, com faixa sombreada onde as duas coincidem. |
| "Faixa entre previsões", "emissões", "método versão registro" | Para a dica "Como é calculado" no rodapé. |
| Botão "Registrar avaliação" | **"Ir para Situação"** (declarar com a justificativa já preenchida a partir da previsão). |
| Selo "Experimental" no topo e no cartão | Uma vez, no rodapé. |
| Erro "Não foi possível carregar o cenário" | Corrigir (bug observado em 05/11 17h14). |

**Textos exatos**

| Lugar | Texto atual | Texto novo |
|---|---|---|
| Título | Cenários | **Próximos 3 dias** |
| Subtítulo | Quais territórios olhar primeiro nas próximas 24 a 72 horas, e por quê. É uma indicação para avaliar, não a chance de alagar. | **O que a previsão de chuva e maré indica até {dia da semana}, distrito por distrito.** |
| Frase, dia calmo | (não existe) | **Sem chuva forte prevista até {dia}.** O máximo previsto é {x} mm em 24 h no {distrito}; o Recife costuma ter problema a partir de {limiar atenção} mm. |
| Frase, dia de chuva | (não existe) | **Chuva forte prevista para {quando}{, com maré alta às {hora}}.** Os distritos {lista} devem receber mais de {x} mm entre {h1} e {h2}. |
| Título da fila | Territórios por prioridade | **Por distrito** |
| Coluna | (chips de motivo) | **Chuva em 24 h (pior período) · Quando · Situação** |
| "sobe ▲" | (não existe) | Quando a chuva prevista leva a sugestão acima da situação declarada: **"sobe para Atenção"**. |
| Gráfico | Quanta chuva está prevista em DS I? / A maré alta coincide com a chuva? (Porto do Recife) | **Chuva e maré, hora a hora** — legenda da faixa: **"chuva forte + maré alta"** |
| Rodapé | (fontes em 4 lugares) | **Previsão: Open-Meteo, atualizada {quando}. Maré: em frente ao Porto do Recife. É uma previsão, não um alerta oficial: confira APAC e Cemaden. Experimental.** |

O limiar "o Recife costuma ter problema a partir de 40 mm" deve vir dos limiares configurados da Situação, não ser
fixo no texto.

---

## 4. Boletim com a marca ClimaSense

### Para quem, quando e como

| Boletim | Para quem | Quando | Formato |
|---|---|---|---|
| **Boletim de situação** | Gerência da Vigilância em Saúde, diretores dos 8 distritos sanitários, COP | **Ao mudar a situação de qualquer distrito para Atenção ou acima** e, durante o evento, **2 vezes ao dia (8h e 17h)** até voltar para Observação | PDF de 1 página A4 + resumo de 6 linhas para WhatsApp |
| **Boletim de encerramento** | Mesmos + coordenação da SEVS | Ao voltar para Observação em todos os distritos | PDF de 1 página: linha do tempo do evento, situações declaradas, registro do evento, lições |
| (sem evento) | Ninguém | Não se envia boletim em dia sem evento | A tela mostra "Nenhum evento em andamento. O último boletim foi em 12/05." |

A tela "Boletins" passa a ser um **arquivo**: lista dos boletins emitidos (número, data, autor, situação máxima),
cada um congelado como foi enviado. Isso responde "de onde veio" e cria o histórico para a reunião pós-evento. Pede
mudança de API: guardar o boletim emitido (`POST /boletins`, imutável).

### A página

```
┌───────────────────────────────────────────────────────────────────────────┐
│ [logo climasense]                         BOLETIM DE SITUAÇÃO Nº 007/2026 │
│ Vigilância em Saúde do Recife · Vigidesastres      sex 15/05/2026, 08h00  │
│ ═══════════════════════════════ (faixa na cor da situação máxima) ═══════ │
│                                                                           │
│ 1. EM UMA FRASE                                                           │
│   Três distritos em Alerta (V, VI e VIII) por chuva forte prevista para   │
│   hoje à tarde com maré alta às 15h.                                      │
│                                                                           │
│ 2. SITUAÇÃO POR DISTRITO                    [mini-mapa dos 8 distritos]   │
│   Alerta    DS V, DS VI, DS VIII      declarado por M. Siqueira, 07h40    │
│   Atenção   DS IV                     declarado por M. Lima, 07h45        │
│   Observação  DS I, II, III, VII                                          │
│                                                                           │
│ 3. CHUVA E MARÉ                                                           │
│   Últimas 24 h     38 mm (maior: Ibura, 61 mm)          medida            │
│   Próximas 24 h    até 62 mm, sex 12h-18h (DS V)        prevista          │
│   Maré alta        2,4 m às 15h10                       prevista          │
│   Aviso oficial    APAC: chuva forte, até sex 18h       oficial           │
│                                                                           │
│ 4. BAIRROS QUE JÁ ALAGARAM COM CHUVA PARECIDA                             │
│   Ibura, Jordão, Cohab, Afogados, San Martin (Defesa Civil, 2014-2024)    │
│                                                                           │
│ 5. ABRIGOS ABERTOS (COP)                                                  │
│   4 abertos: Escola X (Ibura), ...                                        │
│                                                                           │
│ 6. O QUE ESTÁ SENDO FEITO                                                 │
│   07h50 DS V: orientação às equipes de saúde da família do Ibura          │
│   08h10 DS VIII: vigilância de agravos nos abrigos                        │
│                                                                           │
│ ───────────────────────────────────────────────────────────────────────── │
│ De onde vêm os números: chuva medida, APAC e Cemaden (19 pluviômetros);   │
│ chuva prevista e maré, Open-Meteo; aviso, APAC/INMET/Cemaden; alagamentos,│
│ Defesa Civil do Recife; abrigos, COP. Atualizados às 07h30.               │
│ O ClimaSense apoia a decisão da equipe. Não é alerta oficial. Defesa      │
│ Civil: 199.                               Próximo boletim: sex, 17h00     │
└───────────────────────────────────────────────────────────────────────────┘
```

### De onde vem cada número

| Seção | Número | Origem | Regra se faltar |
|---|---|---|---|
| Cabeçalho | Nº, data, autor | Boletim emitido (novo registro) | — |
| 1 | Frase | Gerada a partir das seções 2 e 3, editável antes de emitir | Obrigatória; a pessoa pode reescrever |
| 2 | Situação por distrito | Situação **declarada** (`/estagios`, declarado). A sugestão **não** entra no boletim: boletim é o que a equipe decidiu | Distrito sem declaração entra como "Observação (não declarado)" |
| 3 | Chuva 24 h | APAC `precipitacao_acumulada` (pluviômetros) | "sem leitura desde {hora}" |
| 3 | Chuva prevista | Open-Meteo forecast por distrito | "previsão indisponível" |
| 3 | Maré | Open-Meteo Marine | idem |
| 3 | Aviso oficial | Conector `alertas-oficiais` filtrado para o Recife | "Nenhum aviso oficial ativo para o Recife" |
| 4 | Bairros que já alagaram | `recife-alagamento` cruzado com chuva ERA5 do dia (seção 6, diferencial 1) | Seção some se não houver chuva prevista acima de Atenção |
| 5 | Abrigos abertos | Feed COP `Abrigos_Ativos` | "Sem informação do COP" (nunca "0") |
| 6 | Ações | Registro do evento (seção 5) | Seção some se vazia |

Seções fixas: 1, 2, 3 e rodapé sempre aparecem; 4, 5 e 6 só quando têm conteúdo (uma página nunca tem blocos
"Nenhum..."). Ocupação de abrigo e desabrigados saem.

---

## 5. Ações: resolve a D3?

**Honestamente, não como está.** A tela é bem feita, mas parte de premissas que a entrevista não sustenta:

1. **Quem registra?** A equipe tem duas pessoas, que no pico estão declarando situação, conferindo APAC/Cemaden e
   escrevendo no WhatsApp. As ações em campo são feitas pelos distritos, que não usam o ClimaSense. Registrar
   "tipo + descrição + responsável + situação + início" e depois "Iniciar" e "Concluir" é trabalho de gestão de
   projeto que ninguém vai fazer durante a chuva. A tela vai ficar vazia, como está hoje.
2. **O ciclo planejada → em andamento → concluída** é de gestão de tarefas. A dor D3 é outra: "não dá para
   acompanhar o que foi feito" e "as lições ficam em planilha". O que precisa ficar é **um diário com hora**, não um
   quadro de tarefas.
3. **Lição aprendida por ação** fragmenta o que é discutido por evento na reunião pós-evento.

**Proposta: "Registro do evento" dentro da Situação.**

```
REGISTRO DO EVENTO · iniciado sex 15/05 07h40 (primeira declaração de Atenção)
┌───────────────────────────────────────────────────────────────────────┐
│ [ Escreva o que aconteceu… ]  [ DS V ▾ ]  [ Anotar ]                  │
└───────────────────────────────────────────────────────────────────────┘
 08h10  DS VIII   Vigilância de agravos nos abrigos (M. Lima)
 07h50  DS V      Orientação às ESF do Ibura (M. Siqueira)
 07h45  ◆ sistema DS IV declarado Atenção: "previsão de 45 mm"  
 07h40  ◆ sistema DS V, VI, VIII declarados Alerta
 07h32  ◆ sistema Aviso APAC: chuva forte até 18h
```

- Uma linha de texto livre + distrito opcional + hora automática. Cola-se também o que chegou pelo WhatsApp.
- O sistema escreve sozinho as entradas que já conhece (declarações, avisos oficiais, mensagens copiadas, boletins
  emitidos), marcadas com ◆. Assim o diário existe mesmo se ninguém digitar nada.
- Ao encerrar o evento (todos em Observação), o sistema pergunta uma vez: **"O que funcionou e o que mudar da
  próxima vez?"** Isso vira a seção de lições do boletim de encerramento e substitui a planilha.
- A API `/acoes` pode ser reaproveitada (tipo "anotação", situação fixa "concluída"), com um campo novo `evento_id`.

Métrica 7 do piloto ("% de ações encerradas com lição aprendida") deve virar "% de eventos encerrados com lição
registrada".

---

## 6. Diferenciais estratégicos com os dados que já temos

O que o COP e a APAC **não** dão e o ClimaSense pode dar: **memória por bairro** (10 anos de atendimentos da Defesa
Civil) cruzada com **a chuva de amanhã**. Ordem por valor para a equipe e viabilidade.

### D1. "Já aconteceu antes": bairros que alagaram com chuva parecida com a prevista

- **Cruzamento:** atendimentos de alagamento (Defesa Civil, 2014-2024, bairro e dia) × chuva ERA5 do mesmo dia por
  distrito (desde 2021, ou ampliar a carga de ERA5 para 2014) × chuva prevista para amanhã.
- **Regra simples e explicável:** pegar os dias do histórico com chuva de 24 h na mesma faixa da prevista (ex.: 40 a
  70 mm) e listar os bairros com atendimento nesses dias, com contagem.
- **Frase:** "Nos 9 dias desde 2014 com chuva entre 40 e 70 mm, Ibura teve atendimento de alagamento em 7, Jordão em
  5 e Afogados em 4."
- **Por que é forte:** responde a D1 (cidade × bairro) com evidência, não com modelo. Não é probabilidade (RN-06) e
  não depende do ML desligado. Também desmonta o "distrito historicamente vulnerável às vezes nada sofre": a lista
  muda com a faixa de chuva.
- Onde aparece: Próximos 3 dias, Situação (justificativa pronta), Boletim (seção 4).

### D2. Limiar próprio do Recife (calibração com a história)

- **Cruzamento:** para cada distrito, a partir de quantos mm em 24 h começaram os atendimentos de alagamento.
- **Frase:** "No DS V, 8 em cada 10 dias com atendimento de alagamento tiveram mais de 35 mm."
- **Uso:** dar aos limiares da Situação uma origem verificável ("40 mm porque…"), que hoje é proposta sem validação.
  Responde à desconfiança (D5): o número tem lastro local.

### D3. Chuva + maré: o agravante que a cidade sente

- **Cruzamento:** atendimentos × chuva × maré do mesmo dia (maré histórica ERA5/Open-Meteo Marine).
- **Frase:** "Com mais de 40 mm e maré acima de 2,2 m, os atendimentos nos bairros ribeirinhos do DS VI dobraram."
- **Uso:** tornar o chip "maré alta" útil, ligado só onde e quando a maré mudou o resultado no passado.

### D4. Concordância com os alertas oficiais

- **Cruzamento:** alertas oficiais filtrados para o Recife × situação declarada × atendimentos depois.
- **Frase:** "Nos últimos 12 avisos da APAC para o Recife, 8 tiveram atendimento de alagamento em até 24 h, quase
  todos nos DS V e VIII."
- **Uso:** substitui a conferência manual de "este alerta é mesmo do Recife?" por um histórico de quanto cada tipo de
  alerta acertou, e onde. Ataca D5 diretamente. Também mede os "eventos não avisados" (métrica 4 do piloto).

### D5. Abrigo perto de onde alaga

- **Cruzamento:** bairros do D1 × abrigos ativos do COP × locais possíveis (199) no mapa.
- **Frase:** "Ibura deve alagar com a chuva prevista e não tem abrigo aberto a menos de 2 km. Locais possíveis: Escola
  X, Associação Y."
- **Uso:** responde à dor D4 sem pedir que a equipe registre ocupação.

**Saúde depois da chuva** é o sexto, quando houver o extrato por bairro: os eventos de chuva identificados pelo
sistema viram marcadores no gráfico de leptospirose, e o ranking de bairros que alagaram (D1) vira a lista de
vigilância das semanas seguintes.

---

## 7. Prioridades

| Prioridade | O que | Por quê |
|---|---|---|
| **P0** | Corrigir o detalhe de Cenários (erro de carga em 05/11). | Tela quebrada na demonstração. |
| **P0** | Menu de 6 itens (seção 2): fundir Painel + Situação + mapa; remover Abrigos (cadastro), Avaliações e Ações como itens; Fontes e Administração para o rodapé. | É a queixa principal: "informação demais, genérico". |
| **P0** | Situação em tabela de 8 linhas com motivo comum dito uma vez; rótulo "Situação" em todo lugar. | É a tela de valor; hoje repete 8 cartões iguais. |
| **P0** | Uma fonte por tela, no rodapé, em linguagem simples; nada de "(derivada (modelo))". | Ruído citado pelo dono. |
| **P1** | Histórico de chuva (seção 3.1) com textos exatos. | Tela mais confusa segundo o dono; a parte que ele entendeu vira o modelo. |
| **P1** | Próximos 3 dias (seção 3.2): sem ranking de iguais, chip de maré só com chuva, um gráfico. | "Para quê?" do leigo. |
| **P1** | Boletim com marca, número, seções fixas, destinatários e arquivo dos emitidos (seção 4). | Pedido explícito e é o produto que sai da sala. |
| **P1** | Registro do evento dentro da Situação, com entradas automáticas e lição ao encerrar (seção 5). | D3 real, sem exigir digitação no pico. |
| **P2** | Diferencial D1 "já aconteceu antes" e D2 limiar local. | Vantagem estratégica; precisa de agregação nova e ERA5 desde 2014. |
| **P2** | D3 maré, D4 concordância de alertas, D5 abrigo perto de onde alaga. | Cruzamentos de segunda onda. |
| **P2** | Saúde depois da chuva, quando a Vigilância fornecer o extrato por bairro. | Depende de terceiros. |
