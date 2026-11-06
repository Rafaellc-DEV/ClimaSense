---
title: PRD — Plataforma ClimaSense (Vigidesastres Recife)
version: 2
date: 2026-11-06
language: pt-BR
status: rascunho para validação com o cliente, alinhado ao repositório existente
product: ClimaSense
client: Vigidesastres, Secretaria de Saúde do Recife
sources: entrevistas com a equipe do Vigidesastres (grupo 1 e grupo 3), specs/foco-chuvas.md, docs/adr/, docs/funcionalidades-equipe.md
---

# PRD — Plataforma ClimaSense (Vigidesastres Recife)

## Resumo para leitura rápida (para IA)

- **O que é:** painel de gestão que antecipa o impacto das chuvas por bairro e acompanha a resposta durante e depois do evento.
- **Ponto de partida:** o repositório ClimaSense já existe (FastAPI, React com TypeScript, Leaflet, ECharts, MongoDB Atlas e Postgres). Não reescrever do zero; marcar cada requisito como manter, adaptar ou remover contra o código atual.
- **Quem usa:** 2 pessoas da equipe do Vigidesastres (Mariana Siqueira e Mariana Lima). Elas só consomem dados.
- **Prioridade nº 1:** dados o mais atualizados possível, com fonte e hora da última atualização em cada indicador.
- **Princípio de UX:** telas e funcionalidades intuitivas e simples de usar; só o que o cliente pediu.
- **Regras herdadas do projeto (valem para todo código):** somente dados reais, sem dado simulado; ausência de dado não é risco baixo; prioridade não é probabilidade; previsão experimental leva selo até validar; a decisão final é sempre humana.
- **Telas:** (1) Mapa, (2) Situação do evento, (3) Saúde, (4) Ações, (5) Simulador de cenário.
- **Critérios que mais pesam:** segurança de dados e integração com sistemas existentes.
- **Preferência de alerta:** melhor alerta que não se confirma do que alerta que falta.
- **Entrega em 3 fases:** Base, Saúde e ML experimental, Evolução.
- **Em caso de conflito** com `specs/requirements.md` ou `specs/foco-chuvas.md`, vale este PRD.
- **Convenção de IDs:** `RF-xx` = requisito funcional deste PRD; `RNF-xx` = requisito não funcional; `RN-xx` = regra de negócio de `specs/requirements.md`.

## 1. Visão geral

A ClimaSense é um painel de gestão para a equipe do Vigidesastres, da Secretaria de Saúde do Recife, que antecipa o impacto das chuvas por bairro e acompanha a resposta durante e depois do evento, com os dados mais atualizados que as fontes permitirem.

O documento reúne as respostas de duas entrevistas com a equipe do Vigidesastres (grupo 1 e grupo 3) e as decisões já tomadas no repositório. O painel é deliberadamente simples e contém apenas o que o cliente pediu.

**Em uma frase:** um painel único que mostra onde a chuva vai pesar mais, quem está mais exposto, o que está acontecendo agora na saúde e nos abrigos, e o que a equipe já fez.

### 1.1 Ponto de partida

A ClimaSense já existe como projeto acadêmico (Grupo 3, AVD 2026.2, CESAR School). Este PRD guia a próxima etapa; não é um projeto novo.

- **Stack decidida em ADR:** FastAPI (ADR 0002), React com TypeScript (0004), ECharts (0005), Leaflet (0006), MongoDB Atlas na camada bronze e Postgres em silver e gold (0003), sessão no servidor (0007).
- **Funcionalidades da equipe já descritas** em `docs/funcionalidades-equipe.md` (05/11/2026): Painel, Estágios, Abrigos, Ações, Boletim, Saúde depois da chuva, Territórios, Comunicados, Análise e Administração.
- **Qualidade e segurança já existentes:** CI, gitleaks, pre-commit e autenticação com papéis (analista, revisor, coordenação e administrador).
- **Conectores de dados reais já existentes:** Open-Meteo, APAC, INMET, Cemaden, Dados Abertos do Recife, InfoDengue e SINAN.
- **Primeira entrega da Onda 0:** a matriz que compara cada requisito deste PRD com o código atual (manter, adaptar ou remover), em `docs/matriz-prd-codigo.md`.

## 2. Problema e oportunidade

Hoje a equipe responde a eventos de chuva sem informação consolidada e sem dados de saúde em tempo real.

| Dor citada | O que acontece hoje | Origem |
| --- | --- | --- |
| Comunicação falha | Troca por WhatsApp, telefone, e-mail e presencial; a APAC só envia comunicados, e o COP faz a ponte | Grupos 1 e 3 |
| Informação urgente indisponível | A falta de dado frustra e atrasa a decisão | Grupos 1 e 3 |
| Sem dados de saúde em tempo real | A equipe não vê o que se desenrola durante o evento | Grupos 1 e 3 |
| Estado de ativação único para a cidade | O COP dá um estágio operacional geral, mas cada bairro é afetado de um jeito | Grupo 3 |
| Cenário demora a ser montado | De 1 a 2 horas, às vezes mais, com os cenários mudando rápido | Grupos 1 e 3 |
| Sem mapa de vulneráveis e áreas de risco | Difícil planejar resgate de idosos, crianças e pessoas com deficiência | Grupos 1 e 3 |
| Ações não monitoradas | Difícil produzir o relatório executivo para a Secretaria de Saúde | Grupos 1 e 3 |
| Desconfiança de alerta automático | Alertas com localização errada obrigam a conferir à mão na APAC e no Cemaden | Entrevista de 23/10 (`specs/foco-chuvas.md`) |

A oportunidade é antecipar o desastre, e não só responder a ele. Desde o grande desastre de 2022 o processo de trabalho do Vigidesastres vem evoluindo, e o cliente não vê resistência da equipe a novas ferramentas.

## 3. Objetivos e métricas

Objetivo geral: a equipe toma decisões mais cedo e com informação atual, antes, durante e depois da chuva.

1. **Antecipar:** indicar, algumas horas antes do evento, os bairros mais prováveis de serem afetados.
2. **Acompanhar:** mostrar em um só painel abrigos, desabrigados, saúde e ações em curso.
3. **Priorizar:** tratar com mais atenção os territórios e as pessoas mais vulneráveis.
4. **Reportar:** gerar o relatório executivo para a Secretaria de Saúde sem trabalho manual extra.
5. **Reconstruir:** consolidar o que foi feito e apoiar a recuperação, como unidades de saúde danificadas.

| Métrica | Como medir | Meta inicial |
| --- | --- | --- |
| Tempo para montar o cenário | Do início do evento até o painel completo | Reduzir a menos de 1 hora (hoje, de 1 a 2 horas); validar com o cliente |
| Frescor dos dados | Idade do dado mais recente por fonte | A definir por fonte (seção 9) |
| Antecipação | Horas entre o alerta de risco e a ocorrência | Algumas horas antes, como o cliente disse ser útil |
| Alertas não confirmados | Alertas de risco sem ocorrência depois | Tolerável: o cliente prefere alerta que não se confirma a alerta que falta |
| Adoção | Uso do painel pelas duas usuárias em cada evento | Uso em todo evento |
| Relatório executivo | Tempo para gerar o relatório após o evento | A definir com o cliente |

## 4. Usuárias e stakeholders

O painel é usado por duas pessoas da equipe do Vigidesastres, Mariana Siqueira e Mariana Lima. Elas só consomem os dados; os sistemas de origem são operados pelos funcionários do centro de vigilância epidemiológica.

| Quem | Papel | Relação com a plataforma |
| --- | --- | --- |
| Mariana Siqueira e Mariana Lima | Equipe do Vigidesastres | Usuárias principais do painel |
| COP (Centro de Operações do Recife) | Governança das informações de todas as secretarias; define abrigos; gerido por um secretário executivo | Principal fonte de dados e do estado de ativação oficial |
| Assistência Social | Órgão com quem a equipe mais trabalha, em segundo lugar | Fonte de dados de abrigos e desabrigados |
| Defesa Civil | Terceiro órgão mais próximo; contato direto diário por WhatsApp, telefone, e-mail ou pessoalmente | Fonte de alertas e ocorrências |
| APAC | Sem contato direto; só envia comunicados, e o COP faz a ponte | Fonte de previsão, via COP |
| Centro de vigilância epidemiológica | Opera os sistemas de saúde | Fonte dos dados de saúde |
| Secretaria de Saúde | Destinatária do relatório executivo | Consome o relatório |

O cliente não relatou resistência a novas ferramentas. A ordem de proximidade com os órgãos é COP, Assistência Social e Defesa Civil.

No sistema, as pessoas da equipe têm papel de analista, revisor, coordenação ou administrador, e ninguém aprova o próprio conteúdo (RN-05).

## 5. Escopo

O produto cobre as cinco telas da seção 7 e o simulador de cenário, entregues em fases (seção 11). Tudo o que o cliente não pediu fica fora.

### Dentro do escopo

- Mapa com estágios de ativação por bairro e distrito sanitário, áreas de risco, população vulnerável, equipamentos de saúde e abrigos.
- Estágio operacional por território: o sistema sugere e a equipe declara, com justificativa.
- Mensagem pronta de WhatsApp para a mudança de estágio, para copiar ou abrir no WhatsApp, sem envio automático.
- Situação do evento: abrigos abertos e desabrigados.
- Saúde: dados de saúde disponíveis, doenças ligadas à chuva e consultas, vacinas e medicamentos nos abrigos (quando houver fonte).
- Monitoramento de ações e relatório executivo, com o boletim situacional de uma página como ponto de partida.
- Simulador de cenário com previsão de áreas mais afetadas e mapa interativo.
- Alertas oficiais disponíveis no painel, com fonte, hora e território.
- Atualização automática dos dados e indicação da hora da última atualização.
- Entrada manual ou importação de dados quando uma fonte não tiver integração.

### Fora do escopo

- Central de mensagens e comunicação entre órgãos, apesar de a comunicação ser a maior frustração do cliente.
- Notificações push e envio automático por WhatsApp.
- Landing pública e fluxo de comunicados à população: já construídos, mas fora do escopo do cliente. Ficam desligados por chave de funcionalidade e sem link no menu, sem apagar o código.
- Módulo separado de registro do evento e de lições aprendidas (o consolidado de ações cobre o pós-evento).
- Comparação de cenários lado a lado e aprendizado contínuo do modelo.

## 6. Princípios de produto

1. **Dado atual acima de tudo.** O painel só vale se estiver o mais atualizado possível; toda informação mostra a fonte e a hora da última atualização.
2. **Simples e só o que o cliente pediu.** Telas e funcionalidades intuitivas e simples de usar, com poucos números por tela e sem recursos que ninguém solicitou.
3. **Melhor alerta que não se confirma do que alerta que falta.** Os limiares de risco são mais sensíveis, e cada previsão mostra seu nível de confiança.
4. **Tratar diferente os diferentes.** Territórios e pessoas mais vulneráveis aparecem primeiro e recebem mais atenção.
5. **Pensado para quem só consome dados.** As usuárias não operam os sistemas de origem; a plataforma exige pouca digitação e traz os dados por integração.
6. **Explicável.** Toda previsão diz por que um bairro foi marcado, para a equipe poder confiar e agir.
7. **Segurança e integração em primeiro lugar.** São os dois critérios que mais pesam para o cliente.
8. **Somente dados reais.** O produto não contém dado simulado. Sem fonte integrada, a tela mostra "Dados insuficientes" e diz qual fonte falta (ADR 0008, RF-12.10).
9. **Ausência de dado não é risco baixo, e prioridade não é probabilidade.** Sem dado suficiente, a tela mostra "dados insuficientes", nunca "baixo" ou "seguro" (RN-01). O risco aparece como classe, nunca como percentual de chance (RN-06).
10. **Decisão humana por último.** O sistema sugere; a equipe declara o estágio e publica avisos. Previsões ainda não validadas levam o selo "Experimental" (RN-11).

## 7. Requisitos funcionais

O painel tem cinco telas. O pós-evento não ganha telas novas: as telas de Saúde e de Ações passam a mostrar as consequências e o consolidado. A coluna Fase indica em qual fase do roadmap (seção 11) o requisito é entregue. Parte dos requisitos já existe no código; a matriz da seção 1.1 diz quais.

### 7.1 Mapa (tela principal)

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-01 | 1 | Mostrar o estágio de ativação de cada bairro e de cada distrito sanitário (o sistema sugere e a equipe declara), ao lado do estágio oficial da cidade dado pelo COP. |
| RF-02 | 1 | Camadas ativáveis: áreas de risco (deslizamento e alagamento), população vulnerável, equipamentos de saúde e abrigos. |
| RF-03 | 1 | A camada de população vulnerável separa pessoas com deficiência, idosos e crianças, para planejar resgate, sempre com dados agregados. |
| RF-04 | 1 | Cruzar equipamentos de saúde com as populações vulneráveis do território. |
| RF-05 | 1 | Mostrar os alertas oficiais disponíveis (COP, APAC via COP, Defesa Civil) com data e hora. |
| RF-06 | 1 | Destacar os distritos e bairros mais vulneráveis, como o distrito sanitário 7. |
| RF-07 | 1 | Ao clicar num bairro, mostrar estágio, população vulnerável, equipamentos de saúde e abrigos próximos. |

### 7.2 Situação do evento

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-08 | 1 | Mostrar o número de abrigos abertos e de desabrigados, as duas métricas que o cliente acompanha durante o evento. |
| RF-09 | 1 | Mostrar esses números por distrito sanitário e na cidade toda. |
| RF-10 | 1 | Atualizar automaticamente, sem recarregar a página, e exibir a hora da última atualização. |

### 7.3 Saúde

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-11 | 2 | Mostrar dados de saúde sobre o que se desenrola durante o evento, na maior atualização que a fonte permitir. |
| RF-12 | 2 | Acompanhar doenças e agravos ligados às chuvas, como leptospirose e acidentes por animais peçonhentos, por território, nas semanas após o evento. |
| RF-13 | 2 | Acompanhar consultas, vacinas e medicamentos dispensados em eventos de chuva e nos abrigos. |
| RF-14 | 2 | Mostrar unidades de saúde fechadas ou danificadas, para apoiar a recuperação no pós-evento. |

### 7.4 Ações

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-15 | 1 | Registrar as ações por distrito, com responsável, status e horário. |
| RF-16 | 1 | Mostrar o andamento das ações em curso. |
| RF-17 | 1 | Gerar o relatório executivo para a Secretaria de Saúde a partir das ações e dos indicadores, partindo do Boletim atual. |
| RF-18 | 3 | No pós-evento, consolidar tudo o que foi feito para apoiar a reconstrução. |

### 7.5 Simulador de cenário

Ver seção 8 (RF-23 a RF-28).

### 7.6 Regras para todas as telas

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-19 | 1 | Cada indicador mostra a fonte e a hora da última atualização; dado vencido recebe aviso de desatualizado. |
| RF-20 | 1 | Telas e funcionalidades intuitivas e simples de usar: poucos indicadores por tela, apenas os que o cliente pediu, e uso compreensível sem treinamento longo. |
| RF-21 | 1 | Funcionar bem no celular, já que a rotina do cliente passa muito por WhatsApp. |
| RF-22 | 1 | Territórios mais vulneráveis aparecem primeiro nas listas e nos destaques. |

### 7.7 Estágio operacional e comunicação

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-29 | 1 | Estágios: sem dados, observação, atenção, alerta e crítico. O sistema sugere o estágio por gatilhos configuráveis (chuva prevista em 24 h e 72 h, chuva acumulada em 24 h, maré alta junto do pico de chuva e histórico de alagamento do bairro). Faltando insumo, o resultado é "sem dados", nunca "observação" (RN-01). |
| RF-30 | 1 | Declarar o estágio é ato humano de analista ou acima, com justificativa curta, autor e hora, auditado. A sugestão nunca muda o estágio sozinha. |
| RF-31 | 1 | Ao declarar ou mudar o estágio, oferecer uma mensagem curta e padronizada para WhatsApp (estágio, territórios, motivo, hora e fonte), com botões Copiar e Abrir no WhatsApp. Nada é enviado automaticamente. |
| RF-32 | 1 | Todo alerta mostra fonte, hora e território exato, com a orientação de conferir na APAC ou no Cemaden, porque a equipe desconfia de alerta automático com localização errada. |

## 8. Simulador de cenário e mapa interativo

A usuária preenche as premissas de um cenário de chuva, o sistema calcula quais áreas serão mais afetadas e o resultado aparece num mapa interativo que se atualiza quando ela muda as premissas. Na fase 1 o cálculo é por regras; um modelo de ML entra como experimental, quando validado (seção 8.4).

### 8.1 Premissas que a usuária preenche

Os campos abaixo são uma proposta inicial, a validar com o cliente e com quem fornece os dados meteorológicos.

| Premissa | Detalhe | Observação |
| --- | --- | --- |
| Chuva prevista | Volume em mm e duração | Pode vir pré-preenchida pela previsão (Open-Meteo) ou pelo boletim climático do COP |
| Chuva acumulada | Chuva dos dias anteriores | Indica solo saturado |
| Maré | Nível previsto | Afeta o escoamento em áreas baixas |
| Horizonte | Próximas horas do cenário | O cliente disse que o alerta é útil de algumas horas a um dia antes |
| Resposta disponível | Abrigos abertos e capacidade | Para estimar a pressão sobre o atendimento |

### 8.2 O que o simulador devolve

- Classe de risco de deslizamento e de alagamento por bairro, nunca apresentada como probabilidade (RN-06).
- Índice de impacto em pessoas, que combina o risco do local com a vulnerabilidade: pessoas com deficiência, idosos, crianças e equipamentos de saúde expostos.
- Estágio de ativação sugerido por bairro, como apoio à decisão e não como estágio oficial.
- Nível de confiança de cada previsão.
- Explicação do motivo do risco de cada bairro.
- Selo "Experimental" enquanto a estimativa não for validada (RN-11).

### 8.3 Mapa interativo

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-23 | 1 | Colorir bairros e distritos pelo risco previsto, com legenda e nível de confiança. |
| RF-24 | 1 | Atualizar o mapa quando a usuária alterar uma premissa, sem recarregar a página. |
| RF-25 | 1 | Ao clicar num bairro, mostrar a explicação do risco e a população vulnerável exposta. |
| RF-26 | 1 | Permitir ligar e desligar as mesmas camadas do mapa principal. |
| RF-27 | 1 | Salvar o cenário com suas premissas, para consulta depois e uso no relatório. |
| RF-28 | 1 | Devolver o resultado em segundos ou poucos minutos, porque os cenários mudam rápido. |

### 8.4 Abordagem do modelo

O cliente informou que a última grande chuva teve poucas ocorrências no distrito sanitário 7, apesar de ele ser muito vulnerável. Isso mostra que os eventos variam muito. O estudo do repositório (`docs/ml/risco-alagamento.md`, 04/11/2026) confirma o problema: o modelo de árvore de decisão não superou a regra simples de limiar de chuva no período de teste (AUC-PR de 0,046 contra 0,050) e por isso não é publicado. A proposta continua híbrida, com as regras na frente:

1. **Base por regras:** os gatilhos de estágio (chuva prevista e acumulada, maré e histórico de alagamento do bairro). É o que o simulador usa na fase 1.
2. **ML experimental:** roda em paralelo, com selo "Experimental", e só é publicado se cumprir os critérios do estudo: pelo menos 100 casos positivos no treino e 30 no teste, recall da classe "alagou" de pelo menos 0,60 e AUC-PR pelo menos 10% acima da melhor referência simples. Hoje o estudo cobre só alagamento; deslizamento ainda não tem estudo.
3. **Limiar sensível:** o modelo aceita mais falsos positivos que falsos negativos, conforme a preferência do cliente.
4. **Recalibração:** após cada evento, as ocorrências reais são registradas e usadas para melhorar o modelo.

Os dados de treino atuais são os atendimentos da Defesa Civil (Dados Abertos do Recife), a chuva e a maré da Open-Meteo. Ainda faltam área e faixa hídrica por bairro (a base territorial só tem geometria de distrito) e ocorrências de deslizamento com bairro e data.

## 9. Dados e integrações

O painel só é tão atual quanto a fonte. Estas são as fontes que o repositório já usa ou mapeou; as demais precisam de confirmação com o cliente.

| Dado | Fonte hoje | Atualização desejada |
| --- | --- | --- |
| Chuva prevista e maré | Open-Meteo (previsão e maré) | A cada rodada de previsão |
| Chuva medida | APAC (19 pluviômetros do Recife, da APAC e do Cemaden) | Contínua |
| Alertas oficiais | APAC, INMET, Cemaden e IDAP; o COP faz a ponte da APAC | A cada novo alerta |
| Abrigos: locais e quais estão abertos | Dados Abertos do Recife e o feed do COP (ArcGIS, abrigos ativos) | Contínua durante o evento |
| Abrigos: ocupação e desabrigados | Não existe API; registro manual da equipe, com hora e autor | Imediata |
| Ocorrências de alagamento | Dados Abertos do Recife (atendimentos da Defesa Civil) | Diária, com defasagem |
| Dengue, chikungunya e leptospirose | InfoDengue, SINAN (DATASUS) e Dados Abertos do Recife | O mais próximo do tempo real que a fonte permitir; hoje, semanal |
| Animais peçonhentos; consultas, vacinas e medicamentos nos abrigos | Sem fonte integrada | "Dados insuficientes" até haver fonte |
| Ações em andamento | Registro da própria equipe | Imediata |
| Áreas de risco, população vulnerável e equipamentos de saúde | Base territorial oficial e cadastros | Estáticos, revisados periodicamente |

### Regras de frescor

- Cada indicador exibe a hora da última atualização e a fonte.
- Passado um limite definido por tipo de dado, o indicador é marcado como desatualizado.
- Quando uma fonte não tem integração automática, a equipe consegue lançar ou importar o dado, e o registro guarda a hora.
- Sem dado, a tela mostra "Dados insuficientes" e a fonte que falta, nunca zero nem "baixo" (RN-01, RN-02).

### Limitação importante

Os dados de saúde em tempo real são o maior desejo do cliente e provavelmente a integração mais difícil. Os dados de saúde hoje integrados são semanais (InfoDengue e SINAN), e para animais peçonhentos e atendimento nos abrigos ainda não há fonte. O painel mostra o dado tão atual quanto a fonte permitir, sempre com a hora. Essa expectativa precisa ser alinhada com o cliente.

## 10. Requisitos não funcionais

Segurança de dados e integração com os sistemas existentes são os critérios que mais pesam para o cliente, segundo as duas entrevistas.

| ID | Área | Requisito |
| --- | --- | --- |
| RNF-01 | Segurança | Autenticação com sessão no servidor (ADR 0007), papéis de analista, revisor, coordenação e administrador, e registro de quem acessou ou alterou o quê. |
| RNF-02 | Segurança | O cliente relatou que uma falha em PHP deixou todos sem acesso aos sistemas da prefeitura. A plataforma deve funcionar de forma independente desses sistemas, com hospedagem segura e sem depender de PHP exposto. |
| RNF-03 | LGPD | Só dados agregados, sem registros individuais na interface ou na API (RN-13). Dados de pessoas vulneráveis (deficiência, idosos, crianças) com acesso restrito, e uso limitado ao planejamento de resgate e da resposta. |
| RNF-04 | Integração | Integrar com as fontes do COP, da Assistência Social, da Defesa Civil e do centro de vigilância epidemiológica; ter importação manual como alternativa. |
| RNF-05 | Frescor | Atualização automática das telas e indicação de dado desatualizado (RF-10 e RF-19). |
| RNF-06 | Desempenho | Carregar a tela principal e recalcular o simulador em segundos, mesmo durante um evento. |
| RNF-07 | Disponibilidade | Disponível durante eventos de chuva, quando o uso é maior; meta de disponibilidade a definir. |
| RNF-08 | Usabilidade | Telas e funcionalidades intuitivas e simples de usar, para duas usuárias que só consomem dados; funcionar no celular. |
| RNF-09 | Explicabilidade | Cada previsão do modelo mostra seus motivos principais e seu nível de confiança. |
| RNF-10 | Dados reais | Nenhum dado simulado no produto (ADR 0008, RF-12.10). Dados de exemplo só em testes automatizados, nunca no banco do produto. |
| RNF-11 | Qualidade | O CI existente (gitleaks, ruff, pytest, lint, testes e build do frontend) deve passar antes de qualquer integração. |
| RNF-12 | Hospedagem | MongoDB Atlas e Neon são serviços de terceiros: adequados a dados públicos. A hospedagem definitiva deve ser decidida antes de qualquer dado não público do cliente. |

## 11. Roadmap por fases

As fases não têm datas porque as fontes de dados ainda não foram confirmadas. Parte da fase 1 já existe no repositório.

| Fase | Nome | Conteúdo |
| --- | --- | --- |
| 1 | Base | Mapa e estágios por bairro; abrigos e desabrigados; ações e relatório; alertas e mensagem pronta de WhatsApp; simulador por regras; importação manual de dados |
| 2 | Saúde e ML experimental | Dados de saúde atuais; leptospirose e animais peçonhentos; atendimento nos abrigos; unidades danificadas; ML só se superar a regra simples; confiança e explicação |
| 3 | Evolução | Recalibração após cada evento; apoio à reconstrução; novos pedidos do cliente |

Gates entre as fases:

- **Gate 1 (fase 1 para 2):** fontes do COP integradas e painel validado pelas duas usuárias.
- **Gate 2 (fase 2 para 3):** dados de saúde com frescor definido, e o ML publicado apenas se cumprir os critérios da seção 8.4.

A fase 1 entrega o painel com os dados que o COP e a Assistência Social conseguem fornecer. A fase 2 depende de integrações mais pesadas de saúde; o ML entra só se superar a regra simples. A fase 3 melhora o modelo e inclui o que o cliente ainda vai pedir.

## 12. Riscos e mitigações

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Fontes de saúde integradas são semanais ou inexistentes | O painel não fica em tempo real, a maior expectativa do cliente | Alinhar a expectativa desde já; mostrar sempre a hora do dado; "Dados insuficientes" quando não houver fonte; importação manual como alternativa |
| ML não superar a regra simples (caso do estudo atual) | Previsão sem ganho sobre a regra de chuva | Regras na frente; ML experimental com critérios de publicação; recalibração após cada evento |
| Sistemas da prefeitura inacessíveis por falha em PHP | Integrações bloqueadas ou atrasadas | Plataforma independente e segura; entrada manual de dados; definir cedo o acesso às fontes |
| COP depende de dados de várias secretarias | Atraso ou inconsistência nos dados de abrigos | Marcar dado desatualizado; combinar com o COP o formato e a frequência |
| Estágio por bairro sem validade oficial | A equipe não sabe se pode agir com base nele | Mostrar como sugestão ao lado do estágio oficial; a declaração é humana e auditada; definir quem a oficializa |
| Exposição de dados pessoais de pessoas vulneráveis | Risco legal e de segurança (LGPD) | Só dados agregados, acesso restrito e registro de acessos |
| Landing pública e comunicados já construídos | Superfície pública que o cliente não pediu | Desligar por chave de funcionalidade e remover o link do menu, sem apagar o código |
| Mais de um documento de requisitos | Instruções conflitantes para pessoas e agentes | Este PRD vale; avisar no topo de `specs/requirements.md` e `specs/foco-chuvas.md` |
| Equipe de apenas duas usuárias | Dependência de pessoas; falta de uso se uma estiver ausente | Interface simples; perfis de acesso que permitam incluir outras pessoas depois |
| Escopo crescer além do pedido | Perda de simplicidade, que o cliente quer | Manter a lista fora do escopo (seção 5) e só incluir o que o cliente solicitar |

## 13. Perguntas em aberto e próximos passos

### Perguntas para o cliente

- [ ] Por onde os dados de saúde chegam hoje (sistema, planilha, e-mail) e com que atraso? A vigilância tem algo mais atual que o SINAN semanal?
- [ ] Os abrigos abertos já vêm do feed do COP. O COP consegue disponibilizar também ocupação e desabrigados?
- [ ] Existe fonte estruturada para animais peçonhentos e para consultas, vacinas e medicamentos dos abrigos, ou o registro é manual?
- [ ] Existem ocorrências de deslizamento com bairro e data?
- [ ] Existe mapeamento oficial de áreas de risco por bairro ou setor? A base territorial atual só tem geometria de distrito.
- [ ] Quem pode oficializar o estágio de ativação por bairro? Hoje essa decisão é do COP. Quais gatilhos e limiares o cliente aceita para cada estágio?
- [ ] Onde a plataforma pode ser hospedada, dada a falha em PHP que deixou todos sem acesso?
- [ ] O relatório executivo tem modelo obrigatório? O Boletim atual atende?
- [ ] A mensagem pronta de WhatsApp atende à dor da comunicação, ou o cliente espera algo a mais?
- [ ] Resposta 9 do primeiro grupo: o cliente ficou de completar depois os indicadores e painéis que quer ter.

### Próximos passos

1. Validar este PRD com o cliente, em especial o escopo (seção 5) e as premissas do simulador (seção 8.1).
2. Montar a matriz de requisitos contra o código atual (manter, adaptar ou remover), em `docs/matriz-prd-codigo.md`.
3. Avisar no topo de `specs/requirements.md` e `specs/foco-chuvas.md` que, em conflito, vale este PRD.
4. Desligar a landing pública e os comunicados por chave de funcionalidade.
5. Mapear as fontes de dados e a frequência de atualização de cada uma (seção 9).
6. Definir com o cliente os gatilhos e os limiares de cada estágio de ativação.
7. Demonstrar o painel atual às duas usuárias e registrar o que elas mudariam.
