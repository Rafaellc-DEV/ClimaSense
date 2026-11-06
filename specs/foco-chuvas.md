> **Em conflito, vale `docs/PRD.md`.** Este documento é anterior ao PRD (06/11/2026) e fica como histórico.

# Foco: chuvas, decisão rápida e o dia a dia do Vigidesastres

> Revisão de escopo de 04/11/2026, a partir do desafio da SEVS (Projeto 5), da entrevista de 23/10/2026 com a equipe
> do Vigidesastres (Mari Siqueira e Mari Lima) e do mapa de empatia atualizado. Complementa `requirements.md`; onde
> houver conflito de prioridade, este documento vale para a próxima onda de trabalho.

## 1. A dor real

A equipe tem **duas pessoas** e já usa painéis (o do COP). O problema não é resistência à tecnologia:

1. **O alerta é da cidade inteira, a decisão é por bairro.** O COP declara o estágio para o Recife; a equipe precisa
   saber *onde* agir. Distritos historicamente vulneráveis às vezes nada sofrem, e outras áreas colapsam.
2. **A comunicação é manual.** Mudança de estágio vai para os distritos por grupos de WhatsApp, digitada na hora.
3. **Não há como acompanhar as ações em campo** durante o evento, nem consolidar depois (as "lições aprendidas"
   ficam em planilha).
4. **No pico, as primeiras métricas são abrigos abertos e desabrigados**, e hoje não estão em lugar nenhum integrado.
5. **Desconfiança de alerta automático** com localização errada (ex.: Petrolina encaminhado como Recife). Validam
   manualmente na APAC e no Cemaden.
6. **Segurança e integração** são os critérios de adoção (houve uma falha de PHP que deixou todos sem acesso).

Princípios que já existem e continuam valendo: dado ausente não é risco baixo (RN-01), prioridade não é probabilidade
(RN-06), precisão espacial honesta (RN-07), experimental até validar (RN-11), só dados reais (RF-12.10), decisão
humana sempre por último.

**Preferência declarada:** alerta não confirmado é melhor que evento não avisado. Antecedência útil: de algumas horas
a um dia.

## 2. O que sai do centro

- **Vacinação** não foi pedida pelo cliente e foi **removida** do produto: ETL, API, telas, mapa e o estudo de ML
  (migração `0009`). Só o legado do projeto antigo no Neon continua intocado (seção 6).
- O ML do produto passa a ser **chuva e alagamento** (`docs/ml/risco-alagamento.md`).

## 3. Funcionalidades da próxima onda

| ID | Funcionalidade | Responde à dor |
|---|---|---|
| F1 | **Estágio operacional por território** com gatilhos parametrizados e confirmação humana | 1, 5 |
| F2 | **Mensagem pronta para WhatsApp** da mudança de estágio (copiar ou abrir `wa.me`) | 2 |
| F3 | **Abrigos e desabrigados** (registro manual pela equipe, com hora e autor) | 4 |
| F4 | **Ações de resposta** com situação e linha do tempo por território | 3 |
| F5 | **Boletim situacional** de uma página, imprimível em PDF e resumível para WhatsApp | 2, 3 |
| F6 | **Risco de alagamento por bairro (ML)**, experimental, alimentando o gatilho de F1 | 1 |
| F7 | **Origem e localização em todo alerta** (fonte, hora, território exato, "confira na APAC/Cemaden") | 5 |

### F1. Estágio operacional por território

- Estágios: `sem_dados`, `observacao`, `atencao`, `alerta`, `critico` (os quatro últimos seguem a seção 6.1 de
  `requirements.md`, ainda pendente de validação, P5).
- O sistema **sugere** um estágio por distrito e por bairro a partir de gatilhos configuráveis:
  - chuva prevista nas próximas 24 h e 72 h (mm), da `open-meteo-previsao`;
  - chuva acumulada nas últimas 24 h (mm);
  - maré alta coincidindo com o pico de chuva, da `open-meteo-mare`;
  - risco do modelo de F6, quando houver (sempre rotulado experimental);
  - histórico de alagamento do bairro, quando houver ocorrências carregadas.
- A previsão é por distrito. Um bairro herda a chuva do distrito e isso fica explícito na tela (RN-07).
- Faltando insumo → `sem_dados`, nunca `observacao` (RN-01).
- **Declarar** o estágio é ato humano (analista ou acima), com justificativa curta, autor e hora, auditado.
  A sugestão nunca muda o estágio sozinha.
- Parâmetros (limiares) editáveis pela coordenação e pelo administrador, com histórico.

### F2. Mensagem para WhatsApp

- Ao declarar ou mudar o estágio, a tela oferece um texto curto e padronizado: estágio, territórios, motivo,
  orientações, hora, "fonte: ClimaSense / Vigidesastres". Botões: **Copiar** e **Abrir no WhatsApp** (`wa.me/?text=`).
- Nada é enviado automaticamente. Sem integração com a API do WhatsApp nesta onda.

### F3. Abrigos e desabrigados

- Cadastro de abrigo: nome, bairro, endereço, capacidade, aberto (sim/não), pessoas abrigadas, desabrigados atendidos,
  observação, atualizado em, por quem. Cada atualização guarda histórico.
- O painel mostra no topo: **abrigos abertos** e **desabrigados**, com a hora da última atualização.

### F4. Ações de resposta

- Registro: território, tipo (orientação, visita, distribuição de insumos, vigilância de agravo, articulação, outro),
  descrição, órgão ou responsável, situação (`planejada`, `em_andamento`, `concluida`, `cancelada`), horários.
- Linha do tempo por território e por período; filtro "em andamento agora".
- Campo opcional "lição aprendida" ao concluir, para a reunião pós-evento.

### F5. Boletim situacional

- Uma página com: estágio por distrito, territórios em atenção, chuva das últimas 24 h e prevista, maré, abrigos e
  desabrigados, ações em andamento, fontes e horários. Imprimível (CSS de impressão, "Salvar como PDF" do navegador)
  e com um resumo em texto para WhatsApp.

### F6. Risco de alagamento por bairro (ML)

- Reaproveita o método do estudo da disciplina (árvore de decisão, validação cruzada, relatório em `docs/ml`), agora
  com rótulo = ocorrência de alagamento por bairro e dia, e atributos de chuva (ERA5) e maré.
- Validação **temporal** (treina no passado, testa no futuro), comparada com uma referência simples (limiar de chuva).
- Saída por bairro: classe de risco e explicação dos fatores. Selo experimental (RN-11). Nunca "% de chance" (RN-06).
- Sem ocorrências reais suficientes → o modelo não é publicado e o gatilho de F1 ignora este insumo.

## 4. Contratos de API (base `/api/v1`)

Todos autenticados, exceto quando dito. Respostas seguem o padrão já usado (`RespostaDados`, problema RFC 7807 em erro).

```
GET   /estagios                         → estágio declarado e sugerido de cada território
        ?nivel=distrito|bairro
        item: { territorio_id, territorio_nome, nivel, distrito_id,
                sugerido: { estagio, motivos: [str], insumos: {chuva_24h_mm, chuva_prev_24h_mm,
                            chuva_prev_72h_mm, mare_max_m, risco_ml, ...}, calculado_em },
                declarado: { estagio, justificativa, autor_nome, declarado_em } | null }
POST  /estagios                         ← { territorio_ids: [str], estagio, justificativa }  → declarações criadas
GET   /estagios/historico?territorio_id=&desde=&ate=
GET   /estagios/parametros              → limiares atuais
PUT   /estagios/parametros              ← limiares (coordenacao/administrador)
POST  /estagios/mensagem                ← { territorio_ids, estagio, justificativa? } → { texto, wa_me_url }

GET   /abrigos?aberto=&distrito_id=     → lista com totais { abrigos_abertos, pessoas_abrigadas, desabrigados,
                                           atualizado_em }
POST  /abrigos                          ← cadastro
PATCH /abrigos/{id}                     ← atualização (gera histórico)
GET   /abrigos/{id}/historico

GET   /acoes?territorio_id=&situacao=&desde=&ate=
POST  /acoes
PATCH /acoes/{id}                       ← situação, descrição, lição aprendida

GET   /boletim?territorio_id=recife     → retrato consolidado para a página do boletim
GET   /boletim/texto                    → { texto, wa_me_url } (resumo para WhatsApp)

GET   /risco-alagamento?nivel=bairro    → { disponivel: bool, motivo?, modelo: {versao, treinado_em,
                                           validacao}, itens: [{territorio_id, classe, fatores: [str]}] }
```

## 5. Quem mexe em quê (para trabalho em paralelo)

| Área | Dono |
|---|---|
| `backend/climasense/{dominio,servicos,api,infra}`, `backend/migrations`, `backend/tests` (exceto `tests/unit/ml`) | Backend |
| `backend/climasense/ml`, `backend/climasense/modelos`, `backend/tests/unit/ml`, `docs/ml`, `api/routers/risco_alagamento.py` | ML |
| `frontend/` | Frontend |
| `specs/`, `docs/` (exceto `docs/ml`) | Coordenação (Claude principal) |

Nenhum agente faz commit, `git stash`, `git checkout` ou reverte arquivos alheios: a árvore de trabalho tem
alterações em andamento do time.

## 6. Decisões registradas (04/11/2026)

| Decisão | Motivo |
|---|---|
| **Vacinação removida do produto**, incluindo ETL, API, telas e o estudo acadêmico de ML | Não foi pedida pela gestão: o desafio da SEVS e a entrevista tratam de desastres. A menção a "vacinas nos abrigos" é estoque de insumo do abrigo, outro assunto. |
| Tabela `public.silver_vacinados_legado_etl_avd` e view `public.silver_vacinados` no Neon **ficam como estão** | São do projeto antigo `Projeto-ETL_AVD`; o ClimaSense só deixa de usá-las. |
| **Modelo de risco de alagamento (F6) não é exibido** (`disponivel: false`) | Na validação temporal (treino 2014–2023, teste 2024) a árvore não superou o limiar simples de chuva em AUC-PR (0,046 × 0,050). Rótulo fraco: data da vistoria da Defesa Civil, 461 bairro-dias em 10 anos. Detalhes em `docs/ml/risco-alagamento.md`. Reavaliar com os pluviômetros da APAC. |
| Declarar estágio é ato de **uma** pessoa, auditado, sem revisão | Equipe de duas pessoas; a revisão em dupla fica só para o aviso público. |
| Desenvolvimento **local** primeiro (`dev-local.ps1`: Postgres 55433 e Mongo 27018 em Docker) | Neon e Atlas do time só recebem as migrações e cargas depois da aprovação, seguindo bronze no Atlas → silver/gold no Neon. |

## 7. Fontes verificadas (pesquisa de 04/11/2026)

| Fonte | Uso | Situação |
|---|---|---|
| API APAC (`api.apac.pe.gov.br`, sem login) | Chuva por pluviômetro a cada 10 min (19 estações no Recife, inclui Cemaden), histórico diário desde 2022, avisos, maré | Conector `apac-chuva` em implementação |
| IDAP (CAP), INMET avisos, Cemaden `wsAlertas2`, APAC `/alertas` | Alerta oficial ao lado da sugestão, filtrado para o Recife (código IBGE 2611606 ou polígono) | Conector `alertas-oficiais` em implementação |
| CKAN Recife, atendimentos da Defesa Civil | Ocorrências de alagamento 2014–2024 (rótulo fraco) | Conector `recife-alagamento` em implementação |
| CKAN Recife, `abrigos-temporarios-disponiveis` + pesquisa curada | Locais de abrigo para a landing e o cadastro da equipe | Conector `recife-abrigos` em implementação |
| SINAN (DATASUS) leptospirose | Município, semana de sintomas, ~2 semanas de atraso | Conector `sinan-leptospirose` (05/11/2026, §9); por bairro só com extrato da Vigilância |
| InfoDengue (dengue, chikungunya) | Município, semana, nowcasting e nível de alerta | Conector `infodengue` (05/11/2026, §9) |
| CKAN Recife, `casos-de-dengue-zika-e-chikungunya` | Bairro × ano, publicação anual (2026 ainda não existe) | Conector `recife-arboviroses` (05/11/2026, §9) |
| SINAN peçonhentos | Só município | Depois (baixa relação com a chuva) |
| Censo 2022 (PcD) | Não há deficiência por bairro | Depois; idade e domicílio por bairro, favelas |
| Marinha (tábua) e ANA | Sem acesso programático / sem estação no Recife | Descartadas |

## 8. Métricas do piloto (medidas no próprio sistema)

1. Tempo da sugestão de atenção ou mais até a declaração do estágio (meta: menos de 60 min).
2. % de declarações com mensagem de WhatsApp copiada ou aberta em até 15 min.
3. Antecedência entre a primeira sugestão e o primeiro abrigo aberto ou ação no território (meta: 6 h ou mais).
4. Eventos não avisados: território com abrigo aberto ou ação sem estágio de atenção nas 24 h anteriores (meta: 0).
5. Concordância entre estágio sugerido e declarado, com as divergências justificadas (calibra os limiares).
6. % de abrigos abertos atualizados há menos de 2 h durante o evento.
7. % de ações encerradas com lição aprendida.
8. Tempo para gerar e imprimir o boletim (meta: menos de 10 min).
9. Uso pelas duas usuárias por dia útil, disponibilidade da API, zero incidente de acesso.
10. % de alertas exibidos com fonte, hora e território dentro do Recife.

## 9. Saúde depois da chuva (05/11/2026)

Pesquisa das fontes em `docs/pesquisa/saude-e-chuva.md`; dicionário em `docs/dicionario-dados/infodengue.md`,
`sinan-leptospirose.md`, `recife-arboviroses.md` e `recife-alagamento.md` (deslizamento). Migração `0011`.

O que a equipe pergunta depois de uma chuva forte, e o que o sistema responde:

| Pergunta | Resposta | Fonte |
|---|---|---|
| "Estamos dentro da janela de leptospirose? Desde quando, até quando, onde?" | Janela de 30 dias (NT 138/2022) aberta por estágio declarado Alerta ou Crítico, atendimento de alagamento da Defesa Civil ou chuva **medida** em 24 h acima do limiar de Alerta dos estágios (`chuva_24h_alerta_mm`). Gatilhos encadeados estendem a janela. | registros do próprio ClimaSense |
| "Os casos de leptospirose estão subindo depois das chuvas?" | Série semanal (semana de sintomas) com notificados e confirmados, semanas recentes marcadas como incompletas, e a chuva semanal ao lado. | SINAN (DATASUS) |
| "Como estão dengue e chikungunya nesta semana?" | Casos notificados, estimativa com IC 95% (nowcasting) e o nível de alerta **do InfoDengue**. | InfoDengue |
| "Que bairros concentraram dengue e chikungunya nos anos anteriores?" | Casos confirmados por bairro de residência e ano, para planejar a estação de chuvas. | Secretaria de Saúde (Dados Abertos) |
| "Onde já houve alagamento ou deslizamento?" | Atendimentos da Defesa Civil por bairro: quantos, em quantos dias, primeiro e último registro. O deslizamento alimenta a prevenção nos morros. | Defesa Civil (Dados Abertos) |

Regras: falta de dado não é zero (agravo sem carga vem com `ultima_semana: null`; semana depois da última notificação
não existe); semana recente baixa é atraso, não queda (`incompleta: true`); o nível de alerta é do InfoDengue; a
janela é lembrete de vigilância, não risco calculado (RN-06); casos semanais só por município, bairro só no retrato
anual (RN-07); nenhum dado pessoal: as linhas com endereço, CEP ou nascimento são agregadas em memória e só as
contagens chegam à bronze.

Zika fica de fora (a série do InfoDengue parou em 2024-SE07). Peçonhentos e diarreias ficam para depois.

### 9.1 Contrato das rotas (base `/api/v1`, área da equipe, `Permissao.CONSULTAR`, envelope `RespostaDados`)

```
GET /saude/resumo
  dados: { agravos: [{ agravo: "dengue"|"chikungunya"|"leptospirose", nome, fonte_id,
                       ultima_semana: {ano, semana, inicio} | null,
                       casos, casos_estimados, confirmados, rt,
                       variacao_4s_pct,          # 4 últimas semanas utilizáveis x 4 anteriores; null sem base
                       nivel_alerta (1-4 | null), incompleta }],
           janela_leptospirose: { ativa, inicio, fim, dia_da_janela, atencao_maior, motivo,
                                  origens: ["estagio"|"ocorrencia"|"chuva"], territorios: [{id, nome}] } | null,
           gerado_em }
  # janela: ativa até 30 dias depois do último gatilho; de 30 a 60 dias volta com ativa=false; depois, null.
  # atencao_maior: do 5º ao 14º dia desde o último gatilho (incubação média).
  # variacao_4s_pct: com nowcasting usa casos_estimados; na leptospirose ignora as semanas incompletas.

GET /saude/semanal?agravo=dengue|chikungunya|leptospirose&desde=AAAA-MM-DD   (padrão: 104 semanas)
  dados: { agravo, desde,
           itens: [{ano, semana, inicio, casos, confirmados, casos_estimados, ic_inf, ic_sup, nivel_alerta,
                    incompleta}],
           chuva: [{inicio, chuva_mm, dias_com_dado}] }
  # chuva: reanálise ERA5 (open-meteo-historico), média dos distritos, domingo a sábado; sem dado, chuva_mm null

GET /saude/bairros?agravo=dengue|chikungunya&ano=2025   (padrão: último ano publicado)
  dados: { agravo, ano, itens: [{bairro_id, bairro_nome, distrito_id, casos, notificados}],   # os 94 bairros
           anos_disponiveis: [...], total_confirmados, confirmados_sem_bairro, total_notificados,
           fonte_atualizada_em }
  # casos = confirmados de residentes; ano não publicado: itens [] e meta.dados_insuficientes = true

GET /ocorrencias/historico?tipo=alagamento|deslizamento
  dados: { tipo, itens: [{bairro_id, bairro_nome, distrito_id, registros, dias_com_registro,
                          primeiro_registro, ultimo_registro}],
           total_registros, bairros_com_registro, periodo_inicio, periodo_fim }
```

`meta.fontes` traz `infodengue`, `sinan-leptospirose`, `recife-arboviroses`, `recife-alagamento`, `apac-chuva` ou
`open-meteo-historico` conforme a rota; `meta.avisos` traz prontos para a tela os avisos de atraso, de nível do
InfoDengue e de precisão espacial.

### 9.2 Cargas

`python -m climasense.etl run infodengue | sinan-leptospirose | recife-arboviroses | recife-alagamento`;
`python -m climasense.etl semanal` (InfoDengue e SINAN). No `atualizar`: InfoDengue sempre, SINAN no máximo a cada
6 dias, arboviroses a cada 30 dias, Defesa Civil a cada 7 dias.
