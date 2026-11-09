---
title: PRD — Plataforma ClimaSense (Vigidesastres Recife)
version: 4
date: 2026-11-06
language: pt-BR
status: rascunho para validação com o cliente, alinhado ao repositório existente (v3 aguarda aprovação do dono, D-13; v4 aguarda D-16)
product: ClimaSense
client: Vigidesastres, Secretaria de Saúde do Recife
sources: entrevistas com a equipe do Vigidesastres (grupo 1 e grupo 3), specs/foco-chuvas.md, docs/adr/, docs/funcionalidades-equipe.md, docs/pesquisa/api-*.md (06/11/2026)
---

# PRD — Plataforma ClimaSense (Vigidesastres Recife)

## Resumo para leitura rápida (para IA)

- **O que é:** painel de gestão que antecipa o impacto das chuvas por bairro e acompanha a resposta durante e depois do evento.
- **Foco (v3, 06/11/2026):** chuva, nível da maré, o cenário em que as áreas são mais afetadas e, com o aumento das chuvas, qual distrito sanitário é mais impactado e com quais arboviroses (dengue, chikungunya, zika). **Abrigos estão fora do escopo** (ADR 0016).
- **Ponto de partida:** o repositório ClimaSense já existe (FastAPI, React com TypeScript, Leaflet, ECharts, MongoDB Atlas e Postgres). Não reescrever do zero; marcar cada requisito como manter, adaptar ou remover contra o código atual.
- **Quem usa:** 2 pessoas da equipe do Vigidesastres (Mariana Siqueira e Mariana Lima). Elas só consomem dados.
- **Prioridade nº 1:** dados o mais atualizados possível, com fonte e hora da última atualização em cada indicador.
- **Princípio de UX:** telas e funcionalidades intuitivas e simples de usar; só o que o cliente pediu.
- **Regras herdadas do projeto (valem para todo código):** somente dados reais, sem dado simulado; ausência de dado não é risco baixo; prioridade não é probabilidade; previsão experimental leva selo até validar; a decisão final é sempre humana.
- **Ampliação (v4, 06/11/2026, ADR 0017):** nível dos rios do Capibaribe com limiares oficiais, chuva medida por distrito, cobertura territorial dos 94 bairros, cruzamento de camadas, saúde antes, durante e depois do evento, central de alertas, histórico de eventos com relatório executivo e metadados de cada dado (RF-35 a RF-42). Só com fontes reais confirmadas; o que não existe aparece como "Dados insuficientes". Abrigos continuam fora.
- **Telas:** (1) Mapa, (2) Situação do evento, (3) Saúde, (4) Ações, (5) Simulador de cenário. A v4 não cria tela nova.
- **Critérios que mais pesam:** segurança de dados e integração com sistemas existentes.
- **Preferência de alerta:** melhor alerta que não se confirma do que alerta que falta.
- **Entrega em 3 fases:** Base, Saúde e ML experimental, Evolução.
- **Em caso de conflito** com `specs/requirements.md` ou `specs/foco-chuvas.md`, vale este PRD.
- **Convenção de IDs:** `RF-xx` = requisito funcional deste PRD; `RNF-xx` = requisito não funcional; `RN-xx` = regra de negócio de `specs/requirements.md`.

## 1. Visão geral

A ClimaSense é um painel de gestão para a equipe do Vigidesastres, da Secretaria de Saúde do Recife, que antecipa o impacto das chuvas por bairro e acompanha a resposta durante e depois do evento, com os dados mais atualizados que as fontes permitirem.

O documento reúne as respostas de duas entrevistas com a equipe do Vigidesastres (grupo 1 e grupo 3) e as decisões já tomadas no repositório. O painel é deliberadamente simples e contém apenas o que o cliente pediu.

**Em uma frase:** um painel único que mostra quanto chove e como está a maré, onde a chuva vai pesar mais, quem está mais exposto, quais distritos pedem mais atenção pelas arboviroses, e o que a equipe já fez.

### 1.1 Ponto de partida

A ClimaSense já existe como projeto acadêmico (Grupo 3, AVD 2026.2, CESAR School). Este PRD guia a próxima etapa; não é um projeto novo.

- **Stack decidida em ADR:** FastAPI (ADR 0002), React com TypeScript (0004), ECharts (0005), Leaflet (0006), MongoDB Atlas na camada bronze e Postgres em silver e gold (0003), sessão no servidor (0007).
- **Funcionalidades da equipe já descritas** em `docs/funcionalidades-equipe.md` (05/11/2026): Painel, Estágios, Abrigos, Ações, Boletim, Saúde depois da chuva, Territórios, Comunicados, Análise e Administração. Abrigos saiu do produto em 06/11/2026 (ADR 0016).
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
2. **Acompanhar:** mostrar em um só painel o estágio oficial, a chuva, a maré, a saúde (arboviroses e leptospirose) e as ações em curso.
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
| Assistência Social | Órgão com quem a equipe mais trabalha, em segundo lugar | Possível fonte de agregados de população vulnerável (P-12); abrigos e desabrigados estão fora do escopo do painel (ADR 0016) |
| Defesa Civil | Terceiro órgão mais próximo; contato direto diário por WhatsApp, telefone, e-mail ou pessoalmente | Fonte de alertas e ocorrências |
| APAC | Sem contato direto; só envia comunicados, e o COP faz a ponte | Fonte de previsão, via COP |
| Centro de vigilância epidemiológica | Opera os sistemas de saúde | Fonte dos dados de saúde |
| Secretaria de Saúde | Destinatária do relatório executivo | Consome o relatório |

O cliente não relatou resistência a novas ferramentas. A ordem de proximidade com os órgãos é COP, Assistência Social e Defesa Civil.

No sistema, as pessoas da equipe têm papel de analista, revisor, coordenação ou administrador, e ninguém aprova o próprio conteúdo (RN-05).

## 5. Escopo

O produto cobre as cinco telas da seção 7 e o simulador de cenário, entregues em fases (seção 11). Tudo o que o cliente não pediu fica fora.

### Dentro do escopo

- Mapa com estágios de ativação por bairro e distrito sanitário, áreas de risco, população vulnerável e equipamentos de saúde.
- Estágio operacional por território: o sistema sugere e a equipe declara, com justificativa.
- Mensagem pronta de WhatsApp para a mudança de estágio, para copiar ou abrir no WhatsApp, sem envio automático.
- Situação do evento: estágio oficial da cidade dado pelo COP, chuva medida e prevista e nível da maré.
- Saúde: dados de saúde disponíveis, doenças ligadas à chuva (leptospirose, arboviroses) e consultas, vacinas e medicamentos em eventos de chuva (quando houver fonte).
- Monitoramento de ações por cidade, distrito ou bairro (com exclusão auditada) e relatório executivo, com o boletim situacional de uma página como ponto de partida.
- Simulador de cenário com previsão de áreas mais afetadas, mapa interativo e, por distrito, as arboviroses (dengue, chikungunya, zika) como contexto e a ordem de atenção.
- Alertas oficiais disponíveis no painel, com fonte, hora e território.
- Atualização automática dos dados e indicação da hora da última atualização.
- Entrada manual ou importação de dados quando uma fonte não tiver integração.

### Fora do escopo

- Central de mensagens e comunicação entre órgãos, apesar de a comunicação ser a maior frustração do cliente. (A central de alertas do RF-40 só organiza avisos oficiais e sinalizações internas; não troca mensagens nem envia nada.)
- Notificações push e envio automático por WhatsApp.
- Landing pública e fluxo de comunicados à população: já construídos, mas fora do escopo do cliente. Ficam desligados por chave de funcionalidade e sem link no menu, sem apagar o código.
- Lições aprendidas. (v4: o histórico de eventos com relatório executivo entra como RF-41, dentro da tela de Ações; deixa de ser "módulo separado".)
- Comparação de cenários lado a lado e aprendizado contínuo do modelo.
- **Abrigos** (v3, 06/11/2026): locais, abertos, ocupação, pessoas abrigadas, desabrigados, capacidade, camada do mapa, ETL e pressão nos abrigos no simulador. Removidos do código e do banco (migração 0019); o dado de abrigos deixa de ser tratado (ADR 0016).
- Previsão de casos de arboviroses: o simulador mostra arboviroses como contexto (casos recentes notificados), nunca como efeito previsto da chuva.
- **Fontes que não entram** (v4, ADR 0017): raspagem de rede social e de portais sem API; S2iD direto (o Atlas Digital é a versão aberta); EM-DAT; microdados individuais (SINAN, SIH, SAMU linha a linha); base da Celpe com nome de cliente; CadÚnico individual; API `/arboviroses` do Ministério da Saúde (ficha individual).
- Emitir alerta em nome da APAC, da Defesa Civil ou do COP, ou reclassificar aviso oficial (v4, RF-40).
- Estimar pessoas com deficiência por bairro sem decisão do cliente (P-41).

### Ampliação de escopo (v4, 06/11/2026)

O dono do projeto pediu foco em funcionalidades novas a partir de cinco dores do cliente: informação urgente espalhada (rios, chuva por distrito, avisos), mapa de risco incompleto, falta de dado de saúde durante o evento, desconfiança de alerta automático e falta de memória dos eventos para o relatório. Entram, nas telas que já existem:

- Hidrologia: nível dos rios e reservatórios do Capibaribe com limiares oficiais (RF-35).
- Meteorologia observada: chuva medida em 24 h e 72 h por distrito, série horária a partir do início da coleta, temperatura e umidade do solo como previsão ou modelo (RF-36).
- Cobertura territorial dos 94 bairros (RF-37) e cruzamento de camadas por território (RF-38).
- Saúde durante o evento: comparativo antes, durante e depois (RF-39).
- Central de alertas (RF-40).
- Histórico de eventos e relatório executivo (RF-41). Muda o item "Fora do escopo" sobre registro do evento: o histórico entra; lições aprendidas continuam fora.
- Metadados de cada dado (RF-42).

O texto do pedido também citava abrigos; essa parte não vale (ADR 0016 prevalece).

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
| RF-02 | 1 | Camadas ativáveis: áreas de risco (deslizamento e alagamento), população vulnerável e equipamentos de saúde. (v3: a camada de abrigos saiu, ADR 0016.) |
| RF-03 | 1 | A camada de população vulnerável separa pessoas com deficiência, idosos e crianças, para planejar resgate, sempre com dados agregados. |
| RF-04 | 1 | Cruzar equipamentos de saúde com as populações vulneráveis do território. |
| RF-05 | 1 | Mostrar os alertas oficiais disponíveis (COP, APAC via COP, Defesa Civil) com data e hora. |
| RF-06 | 1 | Destacar os distritos e bairros mais vulneráveis, como o distrito sanitário 7. |
| RF-07 | 1 | Ao clicar num bairro, mostrar estágio, população vulnerável e equipamentos de saúde. (v3: abrigos próximos saíram, ADR 0016.) |

### 7.2 Situação do evento

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-08 | — | **Removido na v3 (ADR 0016).** Era: mostrar o número de abrigos abertos e de desabrigados. O ID não é reutilizado. |
| RF-09 | 1 | Mostrar o estágio oficial da cidade dado pelo COP, a chuva medida nas últimas 24 h, a chuva prevista nas próximas 24 h e o nível da maré, cada um com fonte e hora. Na cidade, a chuva é o maior valor entre os distritos; o recorte por distrito e bairro fica no Mapa e no Simulador. |
| RF-10 | 1 | Atualizar automaticamente, sem recarregar a página, e exibir a hora da última atualização. |

### 7.3 Saúde

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-11 | 2 | Mostrar dados de saúde sobre o que se desenrola durante o evento, na maior atualização que a fonte permitir. |
| RF-12 | 2 | Acompanhar doenças e agravos ligados às chuvas, como leptospirose, arboviroses (dengue, chikungunya, zika) e acidentes por animais peçonhentos, por território, nas semanas após o evento. |
| RF-13 | 2 | Acompanhar consultas, vacinas e medicamentos dispensados em eventos de chuva. (v3: a parte "nos abrigos" saiu, ADR 0016.) |
| RF-14 | 2 | Mostrar unidades de saúde fechadas ou danificadas, para apoiar a recuperação no pós-evento. |

### 7.4 Ações

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-15 | 1 | Registrar as ações na cidade toda, por distrito ou por bairro, com responsável, status e horário. Uma ação pode ser excluída em qualquer situação; a exclusão é auditada (quem, quando e o que) e a linha do tempo da ação fica guardada (ADR 0016, P-30). |
| RF-16 | 1 | Mostrar o andamento das ações em curso. |
| RF-17 | 1 | Gerar o relatório executivo para a Secretaria de Saúde a partir das ações e dos indicadores, partindo do Boletim atual. |
| RF-18 | 3 | No pós-evento, consolidar tudo o que foi feito para apoiar a reconstrução. |

### 7.5 Simulador de cenário

Ver seção 8 (RF-23 a RF-28, RF-33 e RF-34).

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

### 7.8 Ampliação de escopo (v4, ADR 0017)

Os requisitos abaixo entram nas cinco telas existentes; a coluna Tela diz onde (proposta, D-17). Valem para todos: dado real (ADR 0008), "Dados insuficientes" com a fonte que falta quando não há dado (RN-01), zero medido diferente de ausente (RN-02), classe e nunca percentual (RN-06), selo "Experimental" para inferência não validada (RN-11), só agregado (RN-13) e metadados do RF-42.

| ID | Fase | Tela | Requisito |
| --- | --- | --- | --- |
| RF-35 | 1 (inundação por território: 2) | Situação do evento; camada no Mapa | **Hidrologia.** Mostrar o nível dos rios e a situação dos reservatórios da bacia do Capibaribe (Tapacurá, Goitá, Carpina) com os **limiares oficiais** de cada estação (pré-alerta, alerta, enchente), em classe e com a leitura em cm, fonte e hora. Fontes: APAC (`/estacoes_rios`, `/historico_rios`, `/reservatorio`) e ANA (serviço legado, como segunda fonte). **Não há estação pública de nível dentro do Recife**: a tela diz que a estação de referência (São Lourenço da Mata) fica a montante da cidade, e os rios Beberibe, Tejipió, Jordão e Pina mostram "Dados insuficientes. Falta: estação de nível no rio". A possibilidade de inundação por território (rio de referência + reservatórios + chuva) só aparece como **Experimental** e depende do mapeamento bairro → rio (P-49). |
| RF-36 | 1 | Situação do evento; Mapa; premissas do Simulador | **Meteorologia observada.** Chuva medida em 24 h e 72 h por distrito (APAC/Cemaden, `24_horas` e `72_horas`), com o número de estações válidas e a hora da última leitura; distrito sem estação válida mostra "Dados insuficientes". Série horária de chuva medida **a partir do início da coleta** (dito na tela; o passado nunca é preenchido com modelo). Temperatura só como **previsão ou modelo** (INMET, APAC, Open-Meteo) enquanto não houver token do INMET (P-36). Umidade do solo só como **estimativa de modelo** (Open-Meteo), com selo Experimental. |
| RF-37 | 1 (alagamento de 2026: depois de P-32) | Mapa (camadas e painel do bairro) | **Cobertura territorial dos 94 bairros.** (a) Suscetibilidade a deslizamento do SGB/CPRM, rotulada "suscetibilidade do terreno (SGB, 2012 a 2014)", nunca "risco"; os setores R1 a R4 da Sedec seguem onde existem. (b) Atendimentos da Defesa Civil com grau R3 ou R4 por bairro, como fato com data ("atendimentos com grau R3/R4 de 2014 a 2024"), nunca "bairro de risco". (c) Alagamento de 2026 agregado por bairro (comunidades, trechos de rua e lotes atingidos, só contagem), sem lote, endereço ou CEP. Cada camada diz quantos dos 94 bairros cobre. Pessoas com deficiência por bairro não existem em fonte pública: total municipal real e "Dados insuficientes" no bairro (P-41). |
| RF-38 | 1 | Mapa (painel do bairro); Simulador | **Cruzamento de camadas por território.** Para cada bairro, lado a lado: chuva prevista, suscetibilidade, população vulnerável (idosos e crianças, Censo 2022), equipamentos de saúde próximos (CNES) e ocorrências (Defesa Civil), cada uma com fonte, data de referência e cobertura. Sem índice composto nem peso entre camadas até o cliente decidir (P-22). O cruzamento é por geometria, não por nome de bairro. |
| RF-39 | 2 | Saúde | **Saúde durante o evento.** Comparativo antes, durante e depois de um evento registrado (RF-41), por semana epidemiológica: dengue e chikungunya (InfoDengue), leptospirose (SINAN, janela de até 6 semanas depois), **SAMU** como demanda de urgência agregada por distrito ou cidade (nunca caso de doença) e **SISAGUA** como qualidade da água por bairro ("sem coleta" não é "água boa"). Cada coluna mostra a data de corte da fonte; semanas incompletas marcadas; sem variação percentual enquanto o "depois" estiver incompleto. Texto fixo: **"Coincidência temporal, não prova de causa."** Selo Experimental. Atendimentos de UPA, DDA e SINAN por bairro só com convênio (P-38 a P-40): até lá, "Dados insuficientes" com a fonte que falta. |
| RF-40 | 1 | Situação do evento (bloco Alertas); painel do bairro | **Central de alertas.** (a) Alertas oficiais organizados (APAC, INMET, Cemaden, IDAP; COP e Defesa Civil do Recife por registro da equipe), com origem, nível, emissão, validade, território e link, e **histórico guardado** a partir da coleta. (b) Sinalizações internas de apoio à análise (ex.: rio de referência acima do pré-alerta, chuva de 72 h acima do gatilho, estação parada), com fonte, hora, confiança e justificativa, rotuladas "sinalização interna, não é alerta oficial" e visualmente separadas. O sistema **nunca emite alerta em nome da APAC, da Defesa Civil ou do COP**, não reclassifica aviso e não envia nada. Amplia RF-05 e RF-32. |
| RF-41 | 2 | Ações (Histórico de eventos e Relatório executivo) | **Histórico de eventos e relatório executivo.** Cada evento guarda início e fim, comunicados (registrados pela equipe com órgão, hora e link), distritos afetados, evolução (linha do tempo de alertas, estágios e ações), indicadores, ações, situação final e pendências. Campo sem fonte mostra "Dados insuficientes". A situação final e o relatório são aprovados por **outra pessoa** (RN-05). Eventos antigos entram como **retrospectivos**: Atlas Digital de Desastres (danos oficiais, 1991 a 2025) e episódios dos atendimentos da Defesa Civil (2014 a 2024), sem estágio nem comunicados ("não disponível nesta fonte"). A regra de início e fim e quem registra e aprova dependem do cliente (P-43, P-44). Amplia RF-17 e prepara RF-18. |
| RF-42 | 1 | Todas; tela Fontes | **Metadados de cada dado.** Todo indicador mostra fonte, hora da última atualização, data de referência (até quando o dado vai), frequência da fonte, situação da integração (integrada, registro manual, planejada, com falha, sem fonte) e confiabilidade quando houver (medido, previsão, modelo, oficial; número de estações válidas). Amplia RF-19. |

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

A premissa "Resposta disponível" (abrigos abertos e capacidade) saiu na v3 (ADR 0016).

### 8.2 O que o simulador devolve

- Classe de risco de deslizamento e de alagamento por bairro, nunca apresentada como probabilidade (RN-06).
- Índice de impacto em pessoas, que combina o risco do local com a vulnerabilidade: pessoas com deficiência, idosos, crianças e equipamentos de saúde expostos.
- Estágio de ativação sugerido por bairro, como apoio à decisão e não como estágio oficial.
- Nível de confiança de cada previsão.
- Explicação do motivo do risco de cada bairro.
- Selo "Experimental" enquanto a estimativa não for validada (RN-11).
- Por distrito sanitário, as arboviroses (dengue, chikungunya e zika) como **contexto**: casos recentes notificados, nunca previsão causal da chuva (RF-33).
- A ordem de atenção dos distritos: qual distrito é mais impactado com o aumento da chuva simulada e com quais arboviroses (RF-34).

### 8.3 Mapa interativo

| ID | Fase | Requisito |
| --- | --- | --- |
| RF-23 | 1 | Colorir bairros e distritos pelo risco previsto, com legenda e nível de confiança. |
| RF-24 | 1 | Atualizar o mapa quando a usuária alterar uma premissa, sem recarregar a página. |
| RF-25 | 1 | Ao clicar num bairro, mostrar a explicação do risco e a população vulnerável exposta. |
| RF-26 | 1 | Permitir ligar e desligar as mesmas camadas do mapa principal. |
| RF-27 | 1 | Salvar o cenário com suas premissas, para consulta depois e uso no relatório. |
| RF-28 | 1 | Devolver o resultado em segundos ou poucos minutos, porque os cenários mudam rápido. |
| RF-33 | 1 | Para cada distrito, mostrar dengue, chikungunya e zika como contexto do cenário: a série semanal recente (hoje só do município, InfoDengue), o total anual de confirmados do distrito (Prefeitura do Recife) e uma classe baixa, média ou alta que compara os distritos entre si (critério provisório: terços do total anual, P-29). Sem série, "Dados insuficientes" e a fonte que falta (hoje, zika). Nunca percentual nem probabilidade (RN-06); contagens pequenas suprimidas (RN-13); selo "Experimental" (RN-11). |
| RF-34 | 1 | Ordenar os distritos do mais para o menos afetado pela chuva simulada (estágio sugerido) e, no empate, pela classe de arboviroses, dizendo quais agravos estão em destaque. É ordem de atenção, não probabilidade (RN-06); o critério precisa de validação do cliente (P-29). |

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
| Estágio oficial da cidade | Registro auditado da equipe (o COP não publica em formato legível, P-21) | A cada mudança |
| Ocorrências de alagamento e deslizamento | Dados Abertos do Recife (atendimentos da Defesa Civil) | Diária, com defasagem |
| Dengue, chikungunya e leptospirose | InfoDengue e SINAN (DATASUS): semanal, só do município; Dados Abertos do Recife: anual, por bairro (somado por distrito no simulador) | O mais próximo do tempo real que a fonte permitir; hoje, semanal no município e anual por distrito (P-28) |
| Zika | Sem série integrada (a série do InfoDengue para o Recife parou em 2024) | "Dados insuficientes" até haver fonte (P-27) |
| Animais peçonhentos; consultas, vacinas e medicamentos em eventos de chuva | Sem fonte integrada | "Dados insuficientes" até haver fonte |
| Ações em andamento | Registro da própria equipe | Imediata |
| Áreas de risco, população vulnerável e equipamentos de saúde | Base territorial oficial e cadastros | Estáticos, revisados periodicamente |

Abrigos (locais, abertos, ocupação e desabrigados) deixaram de ser fonte do produto na v3 (ADR 0016).

### Fontes novas da v4 (ADR 0017)

Cadência e atraso medidos nas pesquisas de 06/11/2026 (`docs/pesquisa/api-*.md`). "A confirmar" quer dizer que a fonte não declara termos ou que só houve um ponto de observação.

| Dado | Fonte | Cadência real | Requisito |
| --- | --- | --- | --- |
| Nível de rio com limiares oficiais | APAC `/estacoes_rios` e `/historico_rios` (sem cadastro, JSON; termos não declarados, P-33) | Leitura a cada 15 min (ANA) a 30–60 min (Cemaden); atraso visto de 7 h a cerca de 30 h | RF-35 |
| Nível de rio (segunda fonte) | ANA `ServiceANA.asmx` (legado, sem token, XML) | 15 min; atraso de cerca de 7 h no teste; pode ser desligado | RF-35 |
| Reservatórios do Capibaribe | APAC `/reservatorio` | Leitura diária | RF-35 |
| Risco hidrológico por município | Cemaden `wsAlertas2` (já integrado) | Lista de alertas ativos | RF-35, RF-40 |
| Chuva medida 24 h e 72 h por estação | APAC `/precipitacao_acumulada` (conector `apac-chuva`, já integrado) | 10–15 min; cerca de 15 das 40 estações cadastradas no Recife em dia | RF-36 |
| Série horária de chuva medida | Gravação das leituras da APAC pelo próprio ETL | A partir do início da coleta; não há série histórica horária aberta | RF-36 |
| Temperatura | INMET `apiprevmet3` (previsão por período), APAC `/previsao_municipio` (previsão horária; código de município a validar, P-33), Open-Meteo (modelo horário) | Por rodada de previsão | RF-36 |
| Umidade do solo | Open-Meteo (modelo; arquivo ERA5-Land com 5–7 dias de atraso) | Horária (modelo) | RF-36 |
| Suscetibilidade a deslizamento | SGB/CPRM 2015, camada `Hosted/Suscebilidade_Deslizamento` da Prefeitura (licença não declarada, P-32) | Estática (campo de 2012 a 2014) | RF-37 |
| Atendimentos com grau R3/R4 | Atendimentos da Defesa Civil, coluna `Grau_de_Risco` (CKAN, ODbL, já integrado) | 2014 a 2024; o arquivo de 2025 está vazio e não há 2026 (P-42) | RF-37, RF-41 |
| Alagamento de 2026 por bairro | Camadas ArcGIS da Prefeitura (comunidades, logradouros, lotes; licença e método a confirmar, P-32) | Retrato único, sem data por registro | RF-37, RF-41 |
| Demanda de urgência | SAMU Recife (CKAN, ODbL), agregado na leitura | Mensal (dado até o último dia do mês anterior; ritmo a confirmar) | RF-39 |
| Qualidade da água por bairro | SISAGUA (API de Dados Abertos do Ministério da Saúde; termos a confirmar, P-51) | Cerca de 1 semana de atraso | RF-39 |
| Peçonhentos | SINAN `ANIMBR` (FTP do DATASUS), só município | Cerca de 3 semanas de atraso | RF-12, RF-39 |
| Histórico dos alertas oficiais | `silver.alertas_oficiais` (o IDAP guarda cerca de 12 h; a APAC, cerca de 14 avisos) | A partir do início da coleta | RF-40, RF-41 |
| Eventos retrospectivos com danos | Atlas Digital de Desastres (Sedec/MIDR, CSV latin-1; termos a confirmar, P-34) | Anual (versão de 06/08/2026 cobre até 2025; 16 registros do Recife) | RF-41 |
| Estágio do COP, comunicados, consequências e situação final | Registro da equipe, com autor, hora e link de evidência | Durante o evento | RF-40, RF-41 |

### O que não existe (confirmado nas pesquisas)

| Pedido | Situação | Como a tela fica |
| --- | --- | --- |
| Estação pública de nível dentro do Recife (Capibaribe urbano, Beberibe, Tejipió, Jordão, Pina) | Não existe; sensores do COP não são públicos (P-35) | "Dados insuficientes. Falta: estação de nível no rio X" |
| Sistema de alerta hidrológico do SGB para o Capibaribe | Não existe (o SACE em PE cobre só o Mundaú) | Não aparece |
| Mancha de inundação por bairro | Não existe; só nível em ponto de rio | Indicador Experimental (RF-35) |
| Série horária histórica de chuva medida no Recife | A rota horária da APAC vem vazia para a cidade | Série só a partir do início da coleta |
| Temperatura medida sem token; umidade do solo medida | INMET A301 exige token (P-36); não há sensor de solo público | Previsão ou modelo, rotulados |
| API pública das PCDs do Cemaden | Não encontrada (P-37) | Cemaden só via APAC |
| Pessoas com deficiência por bairro | O IBGE publica só por município | Total municipal e "Dados insuficientes" no bairro (P-41) |
| Setorização de risco do SGB (R3/R4) para o Recife | Não publicada; quem setoriza é a Sedec | Setores da Sedec onde existem (P-25) |
| Atendimentos da Defesa Civil de 2025 e 2026 | Arquivo de 2025 vazio; 2026 ausente (P-42) | Data da última ocorrência disponível; nunca "sem ocorrência" |
| Casos de doença durante o evento | Nenhuma fonte pública sai em dias; atendimentos de UPA e DDA só com convênio (P-38, P-39) | "Dados insuficientes" com a fonte que falta |
| Hepatite A recente | O arquivo do SINAN parou em 2023 | "Dados insuficientes" |
| Feed de estágio ou de comunicados do COP | Não existe (P-21) | Registro da equipe |
| Histórico público de alertas | Não existe | Só o que o ETL guardou |

### Regras de frescor

- Cada indicador exibe a hora da última atualização e a fonte.
- Passado um limite definido por tipo de dado, o indicador é marcado como desatualizado.
- Quando uma fonte não tem integração automática, a equipe consegue lançar ou importar o dado, e o registro guarda a hora.
- Sem dado, a tela mostra "Dados insuficientes" e a fonte que falta, nunca zero nem "baixo" (RN-01, RN-02).

### Limitação importante

Os dados de saúde em tempo real são o maior desejo do cliente e provavelmente a integração mais difícil. Os dados de saúde hoje integrados são semanais e só do município (InfoDengue e SINAN) ou anuais por bairro (Prefeitura do Recife); para zika, animais peçonhentos e atendimentos em eventos de chuva ainda não há fonte. O painel mostra o dado tão atual quanto a fonte permitir, sempre com a hora. Essa expectativa precisa ser alinhada com o cliente.

Na v4, o mais rápido que existe em fonte aberta é o SISAGUA (cerca de 1 semana, qualidade da água) e o SAMU (mensal, demanda de urgência); nenhum dos dois é caso de doença. Acompanhar a saúde **durante** o evento só será possível com extrato da Vigilância/SESAU (P-38 a P-40).

## 10. Requisitos não funcionais

Segurança de dados e integração com os sistemas existentes são os critérios que mais pesam para o cliente, segundo as duas entrevistas.

| ID | Área | Requisito |
| --- | --- | --- |
| RNF-01 | Segurança | Autenticação com sessão no servidor (ADR 0007), papéis de analista, revisor, coordenação e administrador, e registro de quem acessou ou alterou o quê. |
| RNF-02 | Segurança | O cliente relatou que uma falha em PHP deixou todos sem acesso aos sistemas da prefeitura. A plataforma deve funcionar de forma independente desses sistemas, com hospedagem segura e sem depender de PHP exposto. |
| RNF-03 | LGPD | Só dados agregados, sem registros individuais na interface ou na API (RN-13). Dados de pessoas vulneráveis (deficiência, idosos, crianças) com acesso restrito, e uso limitado ao planejamento de resgate e da resposta. (v4: fontes com linha individual, como SAMU, lotes e logradouros alagados, são agregadas na leitura e a linha não é guardada; a base da Celpe com nome de cliente não é lida.) |
| RNF-04 | Integração | Integrar com as fontes do COP, da Defesa Civil e do centro de vigilância epidemiológica (e da Assistência Social para agregados de população vulnerável, P-12); ter importação manual como alternativa. |
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
| 1 | Base | Mapa e estágios por bairro; situação do evento com estágio oficial, chuva e maré; ações e relatório; alertas e mensagem pronta de WhatsApp; simulador por regras com arboviroses por distrito como contexto; importação manual de dados. **v4:** nível dos rios e reservatórios (RF-35); chuva medida em 24 h e 72 h por distrito e série horária a partir da coleta (RF-36); suscetibilidade do SGB e atendimentos R3/R4 nos 94 bairros (RF-37); cruzamento de camadas lado a lado (RF-38); central de alertas com histórico e sinalizações internas (RF-40); metadados de cada dado (RF-42) |
| 2 | Saúde e ML experimental | Dados de saúde atuais; leptospirose, arboviroses por território e animais peçonhentos; consultas, vacinas e medicamentos em eventos de chuva; unidades danificadas; ML só se superar a regra simples; confiança e explicação. **v4:** possibilidade de inundação por território, Experimental (parte de RF-35, depois de P-49); alagamento de 2026 por bairro (parte de RF-37, depois de P-32); comparativo de saúde antes, durante e depois com SAMU e SISAGUA (RF-39); histórico de eventos com retrospectivos do Atlas e relatório executivo aprovado por outra pessoa (RF-41, depois de P-43 e P-44) |
| 3 | Evolução | Recalibração após cada evento; apoio à reconstrução; novos pedidos do cliente. **v4:** comparação entre eventos do histórico (RF-41) e dados de saúde por convênio, quando existirem (RF-39) |

Gates entre as fases:

- **Gate 1 (fase 1 para 2):** fontes do COP integradas e painel validado pelas duas usuárias.
- **Gate 2 (fase 2 para 3):** dados de saúde com frescor definido, e o ML publicado apenas se cumprir os critérios da seção 8.4.
- **v4:** nenhuma fonte nova sem termos declarados (APAC, ArcGIS da Prefeitura, Atlas, SISAGUA) vai a produção antes da resposta às perguntas de licença (P-32 a P-34, P-51), salvo decisão do dono.

A fase 1 entrega o painel com os dados que as fontes públicas e o COP conseguem fornecer. A fase 2 depende de integrações mais pesadas de saúde; o ML entra só se superar a regra simples. A fase 3 melhora o modelo e inclui o que o cliente ainda vai pedir.

## 12. Riscos e mitigações

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Fontes de saúde integradas são semanais ou inexistentes | O painel não fica em tempo real, a maior expectativa do cliente | Alinhar a expectativa desde já; mostrar sempre a hora do dado; "Dados insuficientes" quando não houver fonte; importação manual como alternativa |
| ML não superar a regra simples (caso do estudo atual) | Previsão sem ganho sobre a regra de chuva | Regras na frente; ML experimental com critérios de publicação; recalibração após cada evento |
| Sistemas da prefeitura inacessíveis por falha em PHP | Integrações bloqueadas ou atrasadas | Plataforma independente e segura; entrada manual de dados; definir cedo o acesso às fontes |
| COP depende de dados de várias secretarias | Atraso ou inconsistência no estágio oficial e nos alertas | Marcar dado desatualizado; combinar com o COP o formato e a frequência |
| Arboviroses lidas como efeito previsto da chuva | Decisão baseada em causalidade que o dado não sustenta | Rótulo "contexto, não previsão", selo "Experimental", classe relativa sem percentual; validar o critério com o cliente (P-29) |
| Arboviroses por distrito só anuais | O contexto do cenário não reflete a semana corrente no distrito | Mostrar ano e fonte; série semanal só do município, dita na tela; pedir fonte semanal por distrito (P-28) |
| Exclusão de ação | Perda do registro ou guarda indevida de dado | Exclusão auditada sem texto livre; linha do tempo guardada; confirmar a guarda com o cliente (P-30) |
| Estágio por bairro sem validade oficial | A equipe não sabe se pode agir com base nele | Mostrar como sugestão ao lado do estágio oficial; a declaração é humana e auditada; definir quem a oficializa |
| Exposição de dados pessoais de pessoas vulneráveis | Risco legal e de segurança (LGPD) | Só dados agregados, acesso restrito e registro de acessos |
| Landing pública e comunicados já construídos | Superfície pública que o cliente não pediu | Desligar por chave de funcionalidade e remover o link do menu, sem apagar o código |
| Mais de um documento de requisitos | Instruções conflitantes para pessoas e agentes | Este PRD vale; avisar no topo de `specs/requirements.md` e `specs/foco-chuvas.md` |
| Equipe de apenas duas usuárias | Dependência de pessoas; falta de uso se uma estiver ausente | Interface simples; perfis de acesso que permitam incluir outras pessoas depois |
| Escopo crescer além do pedido | Perda de simplicidade, que o cliente quer | Manter a lista fora do escopo (seção 5) e só incluir o que o cliente solicitar. v4: os RF-35 a RF-42 entram nas cinco telas existentes, sem tela nova |
| Nível do rio a montante lido como nível do bairro (v4) | Falsa sensação de segurança ou alarme no bairro errado | Texto fixo "estação a montante do Recife"; aplicar a bairros só com o mapeamento de P-49; inundação por território só Experimental |
| Atraso variável da APAC e serviço legado da ANA (v4) | Leitura velha mostrada como atual | Idade da leitura sempre visível; ANA como segunda fonte; selo de desatualizado (RF-42) |
| Licença não declarada nas fontes novas (v4) | Uso ou redistribuição indevidos | Perguntas P-32 a P-34 e P-51; citar sempre a fonte; uso interno até a resposta |
| Open-Meteo gratuito só para uso não comercial (v4) | Previsão, maré, temperatura e umidade do solo sem base de uso | Confirmar o enquadramento (P-46); plano pago ou fonte oficial como alternativa |
| SAMU e SISAGUA lidos como casos de doença (v4) | Conclusão causal sem base | Rótulos "demanda de urgência" e "qualidade da água"; texto "coincidência temporal, não prova de causa"; selo Experimental |
| Sinalização interna confundida com alerta oficial (v4) | A equipe age como se a APAC, a Defesa Civil ou o COP tivessem alertado | Rótulo e cor próprios; nunca emitir em nome de órgão; nada enviado |
| Dado pessoal em fontes públicas (Celpe, lotes, SAMU) (v4) | Risco legal (LGPD) | Agregar na leitura; não ler a base da Celpe; avisar o cliente do possível vazamento (P-45) |
| Histórico de eventos sem regra de início e fim (v4) | Eventos montados de forma arbitrária | Regra e responsáveis definidos com o cliente (P-43, P-44); campos sem fonte em "Dados insuficientes" |

## 13. Perguntas em aberto e próximos passos

### Perguntas para o cliente

- [ ] Por onde os dados de saúde chegam hoje (sistema, planilha, e-mail) e com que atraso? A vigilância tem algo mais atual que o SINAN semanal?
- [x] ~~Os abrigos abertos já vêm do feed do COP. O COP consegue disponibilizar também ocupação e desabrigados?~~ Não se aplica: abrigos saíram do escopo (v3, ADR 0016).
- [ ] Existe fonte estruturada para animais peçonhentos e para consultas, vacinas e medicamentos em eventos de chuva, ou o registro é manual?
- [ ] Zika não tem série integrada. A vigilância tem casos de zika por semana ou por distrito? (P-27)
- [ ] Arboviroses por distrito existem só como total anual. Basta, ou é preciso fonte semanal por distrito? (P-28)
- [ ] O critério da classe de arboviroses (terços do total anual entre distritos) e a ordem de atenção (estágio sugerido, depois arboviroses) servem? (P-29)
- [ ] A ação excluída some da lista, mas a auditoria e a linha do tempo ficam guardadas. Isso atende ao cliente e ao encarregado de dados (LGPD)? (P-30)
- [ ] Existem ocorrências de deslizamento com bairro e data?
- [ ] Existe mapeamento oficial de áreas de risco por bairro ou setor? A base territorial atual só tem geometria de distrito.
- [ ] Quem pode oficializar o estágio de ativação por bairro? Hoje essa decisão é do COP. Quais gatilhos e limiares o cliente aceita para cada estágio?
- [ ] Onde a plataforma pode ser hospedada, dada a falha em PHP que deixou todos sem acesso?
- [ ] O relatório executivo tem modelo obrigatório? O Boletim atual atende?
- [ ] A mensagem pronta de WhatsApp atende à dor da comunicação, ou o cliente espera algo a mais?
- [ ] Resposta 9 do primeiro grupo: o cliente ficou de completar depois os indicadores e painéis que quer ter.

Perguntas da v4 (detalhe em `docs/perguntas-abertas.md`, P-32 a P-54):

- [ ] Licença e termos: camadas ArcGIS da Prefeitura (P-32), API da APAC (P-33), Atlas Digital de Desastres (P-34), InfoDengue e SISAGUA (P-51); Open-Meteo gratuito é só para uso não comercial (P-46).
- [ ] Acesso: sensores de nível de canal do COP (P-35), token do INMET (P-36), PCDs do Cemaden (P-37).
- [ ] Saúde: extratos da Vigilância/SESAU para atendimentos (P-38), DDA (P-39) e SINAN local por bairro (P-40); janelas e agravos do comparativo e uso de SAMU e SISAGUA (P-50); códigos de distrito 546 e 547 (P-52).
- [ ] Território: deficiência por bairro pela Assistência Social, ou estimativa rotulada (P-41); onde estão os atendimentos da Defesa Civil de 2025 e 2026 (P-42); bairros de referência de cada rio (P-49); camadas complementares (P-54).
- [ ] Eventos e alertas: quem registra e quem aprova (P-43); o que define início e fim (P-44); estágios retrospectivos do COP (P-47); canal oficial de comunicados e balanços (P-48); quais sinalizações internas a equipe quer (P-53).
- [ ] LGPD: possível vazamento da base da Celpe com nome de cliente no portal da Prefeitura (P-45).

### Próximos passos

1. Validar este PRD com o cliente, em especial o escopo (seção 5) e as premissas do simulador (seção 8.1).
2. Montar a matriz de requisitos contra o código atual (manter, adaptar ou remover), em `docs/matriz-prd-codigo.md`.
3. Avisar no topo de `specs/requirements.md` e `specs/foco-chuvas.md` que, em conflito, vale este PRD.
4. Desligar a landing pública e os comunicados por chave de funcionalidade.
5. Mapear as fontes de dados e a frequência de atualização de cada uma (seção 9).
6. Definir com o cliente os gatilhos e os limiares de cada estágio de ativação.
7. Demonstrar o painel atual às duas usuárias e registrar o que elas mudariam.

## 14. Histórico de mudanças

| Versão | Data | O que mudou | Decisão |
| --- | --- | --- | --- |
| 1 | — | Primeira versão, a partir das entrevistas com a equipe do Vigidesastres | — |
| 2 | 06/11/2026 | Alinhada ao repositório existente: manter, adaptar ou remover contra o código; regras herdadas; estágio por território e mensagem de WhatsApp (RF-29 a RF-32) | Onda 0 |
| 3 | 06/11/2026 | Mudança de escopo pedida pelo dono do projeto. **Sai:** tudo de abrigos (RF-08 removido; camada de abrigos de RF-02; abrigos próximos de RF-07; "nos abrigos" de RF-13; premissa "Resposta disponível" e pressão nos abrigos do simulador; fontes de abrigos da seção 9; pergunta sobre ocupação e desabrigados). **Muda:** RF-09 (Situação do evento com estágio oficial do COP, chuva e maré), RF-12 (inclui arboviroses), RF-15 (ação na cidade, no distrito ou no bairro, com exclusão auditada em qualquer situação). **Entra:** RF-33 (arboviroses por distrito como contexto do simulador) e RF-34 (ordem de atenção dos distritos). Riscos e perguntas novas (P-27 a P-31). | ADR 0016 (proposta; aprovação em D-13) |
| 4 | 06/11/2026 | Ampliação de escopo pedida pelo dono, a partir de cinco dores do cliente e de cinco pesquisas de fontes reais (`docs/pesquisa/api-*.md`). **Entra:** RF-35 (hidrologia), RF-36 (meteorologia observada), RF-37 (cobertura territorial dos 94 bairros), RF-38 (cruzamento de camadas), RF-39 (saúde antes, durante e depois do evento), RF-40 (central de alertas), RF-41 (histórico de eventos e relatório executivo), RF-42 (metadados de cada dado), todos nas cinco telas existentes. **Muda:** §5 (o histórico de eventos entra; lições aprendidas continuam fora; lista de fontes que não entram), §9 (fontes novas com cadência real e o que não existe), RNF-03 (agregação na leitura), §11, §12 e §13. **Não muda:** abrigos continuam fora (ADR 0016), mesmo citados no pedido. Perguntas novas P-32 a P-54. | ADR 0017 (proposta; aprovação em D-16) |
