# Arboviroses e leptospirose: fontes de dados e indicadores para o cartão de Saúde e o painel do bairro

> Proposta de 26/11/2026 (SE 47/2026, de 22/11 a 28/11). Só pesquisa e leitura: nada foi alterado no código nem no banco
> (consultas só com `SELECT`, em transação somente leitura). Complementa `docs/pesquisa/saude-e-chuva.md` (05/11) e
> `docs/pesquisa/api-epidemiologia.md` (06/11); aqui não se repete o que já está lá, só o que muda a decisão.
>
> Itens do PRD: RF-12 (agravos ligados à chuva por território), RF-19 (fonte e hora), RF-33 e RF-34 (arboviroses por
> distrito no simulador), RF-39 (saúde antes, durante e depois). Regras: RN-01 e RN-02 (sem dado não é zero), RN-06
> (classe, não percentual), RN-11 (experimental), RN-13 e RNF-03 (só agregado, contagens pequenas suprimidas).
>
> **[banco]** = consultado no banco em 26/11/2026. **[web]** = página oficial ou notícia citada, lida nesta data.
> **[não verificado]** = não conferido na fonte primária.

## Resposta curta às quatro perguntas da equipe

| Pergunta | Resposta com o dado que existe hoje |
|---|---|
| **A dengue está subindo?** | **Não, até a última semana carregada (SE 43/2026, 25/10 a 31/10).** Nível de alerta 2 (amarelo) do InfoDengue desde a SE 37, estimativa estável de 209 a 232 casos por semana nas SE 39 a 43, Rt entre 0,83 e 1,08. Nas últimas 4 semanas já completas (SE 35 a 38) foram 1.008 notificados, contra 1.694 no mesmo período de 2025 e 463 em 2024. Chikungunya cai (Rt abaixo de 1 desde a SE 39). **Mas o dado está 4 semanas atrasado** (seção 2): hoje o cartão de Saúde mostra "Dados insuficientes", corretamente. |
| **Onde (distrito/bairro)?** | **Só no histórico anual.** Em 2025 (último ano publicado pela Prefeitura), a maior incidência de dengue confirmada foi no **DS VIII (643 por 100 mil hab.)**, depois DS VI (418), DS I (396), DS II (393) e DS VII (385); a menor no DS V (215). Para 2026 **não existe dado público por bairro ou distrito**: InfoDengue e SINAN do DATASUS só têm o município. Precisa do extrato agregado do SINAN local (P-28, P-40). |
| **Tem relação com a chuva?** | **Dengue: não de semana para semana.** A literatura acha efeito de 0 a 3 meses e dominado por sorotipo e armazenamento de água; nos dados do próprio banco (2021 a 2026), depois de tirar a sazonalidade, a correlação entre chuva semanal e casos de dengue é nula (–0,03 a 0,01, defasagens de 0 a 8 semanas). **Leptospirose: sim, fraca e curta**: correlação de 0,16 a 0,20 com defasagem de 0 a 3 semanas, caindo para 0,07 na 4ª semana; após as semanas de maio de 2022 (268 mm) vieram 252 notificações em 3 semanas. É coincidência temporal descritiva, não modelo. |
| **Qual a janela de vigilância depois de um alagamento?** | **Leptospirose: 30 dias a partir do alagamento**, com maior atenção do 5º ao 14º dia (incubação, NT 138/2022). Como a notificação chega ~5 dias depois dos sintomas e o encerramento ~18 dias depois, o efeito aparece na série do SINAN de 2 a 6 semanas depois (RF-39 já fala em "até 6 semanas"). **Arboviroses: 2 a 8 semanas** para ação sobre criadouros e entulho (ciclo vetor-vírus de ~26 dias), como lembrete de ação, não como alerta de casos. A janela de leptospirose **já está implementada** em `/saude/resumo`. |

---

## 1. O que o projeto já tem

### 1.1 Conectores e serviços

| Peça | Arquivo | O que faz | Granularidade |
|---|---|---|---|
| Conector `infodengue` | `backend/climasense/etl/conectores/infodengue.py` | API `alertcity`, dengue e chikungunya desde 2015; casos, nowcast com IC 95%, Rt, `p_rt1`, `p_inc100k`, nível 1 a 4, `nivel_inc`, `receptivo`, `transmissao`; marca semana incompleta (4 mais recentes ou estimativa > 1,1 × notificado) | município × semana |
| Conector `recife-arboviroses` | `backend/climasense/etl/conectores/arboviroses.py` | CKAN da Prefeitura, um CSV por agravo e ano (dengue 2013–2025, chikungunya 2015–2025); agrega na leitura por bairro × classificação e descarta logradouro, CEP, nascimento e nº de notificação | bairro de residência × ano |
| Conector `sinan-leptospirose` | `backend/climasense/etl/conectores/leptospirose.py` + `dbc.py` | FTP do DATASUS, `LEPTBR15` a `LEPTBR26` (.dbc lido em Python puro), filtra residentes do Recife e agrega por semana de sintomas × classificação × evolução × exposição a enchente | município × semana de sintomas |
| Serviço de saúde | `backend/climasense/servicos/saude_agravos.py` | resumo por agravo com regra de frescor (`semana_utilizavel`), variação 4 × 4 semanas (sobre o nowcast no InfoDengue), série com chuva ERA5, bairros com supressão de 1 a 4, janela de leptospirose (gatilhos: estágio, ocorrência da Defesa Civil, chuva APAC acima do limiar de Alerta) | — |
| Contexto do simulador | `backend/climasense/servicos/arboviroses_cenario.py` | por distrito: série semanal do município + total anual confirmado do distrito + classe baixa/média/alta (terços); zika sempre "Dados insuficientes" | distrito |
| Regra da janela | `backend/climasense/dominio/janela_leptospirose.py` | 30 dias, atenção 5–14, encadeia gatilhos | território do gatilho |

### 1.2 Rotas

| Rota | Entrega | Fontes no `meta` |
|---|---|---|
| `GET /saude/resumo` | por agravo: última semana com dado, casos, estimados, confirmados, Rt, `variacao_4s_pct`, nível, `utilizavel`, `motivo`; janela de leptospirose ativa | infodengue, sinan-leptospirose, apac-chuva, recife-alagamento |
| `GET /saude/semanal?agravo=&desde=` | série semanal (104 semanas por padrão) com chuva semanal ERA5 ao lado; zika vazio com motivo | infodengue ou sinan-leptospirose, open-meteo-historico |
| `GET /saude/bairros?agravo=&ano=` | confirmados e notificados por bairro num ano, supressão de 1 a 4, total e "sem bairro" | recife-arboviroses |
| `GET /cenarios/impacto-previsto` | bloco de arboviroses por distrito (RF-33, RF-34) | infodengue, recife-arboviroses |

### 1.3 Tabelas e cobertura **[banco]**

| Tabela | Cobertura | Observação |
|---|---|---|
| `silver.infodengue_semanal` | dengue e chikungunya, 617 semanas cada, **04/01/2015 a 25/10/2026 (SE 43)**; `versao_modelo` 2026-11-03; coletado em 05/11/2026 | 5 semanas marcadas incompletas por agravo; nenhuma semana com `casos` nulo. Tem `p_rt1`, `p_inc100k`, `receptivo`, `transmissao`, `nivel_inc`, que **não chegam à gold** |
| `silver.leptospirose_semanal` | 616 semanas, **04/01/2015 a 18/10/2026 (SE 42)**; última notificação 23/10/2026; versão "FINAIS LEPTBR15–24 (15/07/2026); PRELIM LEPTBR25–26 (03/11/2026)" | 6 semanas incompletas. Tem `obitos` e `expostos_enchente`, que **não chegam à gold** |
| `gold.saude_semanal` | as três séries acima, colunas `casos, confirmados, casos_estimados, ic_inf, ic_sup, nivel_alerta, rt, incompleta` | é o que as rotas leem |
| `silver/gold.arboviroses_bairro_ano` | dengue 2013–2025, chikungunya 2015–2025; 2025 atualizado na fonte em 07/03/2026 (dengue) e 04/03/2026 (chik) | dengue 2025: 5.110 confirmados, 9.187 notificados, 14 sem bairro, 93 bairros. **Zika não carregada**, embora o CKAN tenha zika 2015–2025 |
| `silver.populacao_bairro` | Censo 2022, 94 bairros, faixas total, 0-4, 0-14, 60+, 70+ (1.482.654 hab.) | permite incidência por 100 mil por bairro e distrito **sem fonte nova** |
| `silver/gold.samu_demanda_semana` | **vazia** | o conector `samu-recife` nunca concluiu |
| SISAGUA | **nenhuma tabela com dado** | o conector `sisagua` nunca concluiu |

Série recente de dengue no banco (gold), para referência:

| SE (início) | Notificados | Estimados (IC 95%) | Nível | Rt | Incompleta |
|---|---|---|---|---|---|
| 43 (25/10) | 36 | 221 (123–414) | 2 | 1,02 | sim |
| 42 (18/10) | 107 | 232 (163–334) | 2 | 1,08 | sim |
| 41 (11/10) | 121 | 209 (163–294) | 2 | 0,91 | sim |
| 40 (04/10) | 159 | 212 (184–263) | 2 | 0,85 | sim |
| 39 (27/09) | 183 | 217 (199–249) | 2 | 0,83 | sim |
| 38 (20/09) | 241 | 264 | 2 | 1,00 | não |
| 37 (13/09) | 251 | 268 | 2 | 1,01 | não |

Em 2026 (SE 1 a 43) a dengue ficou 12 semanas no nível 1, 27 no nível 2 e 4 no nível 3; nunca no 4. Notificados acumulados
SE 1–43: 10.631 (2026), 12.667 (2025), 14.247 (2024). Leptospirose SE 1–43: 322 notificados (2026), 308 (2025), 212 (2024),
com as 6 últimas semanas ainda em atualização.

---

## 2. O que está desatualizado hoje e por quê **[banco]**

### 2.1 Execuções de ETL abandonadas desde 13/11 (confirmado)

- Em `app.etl_execucoes` há **180 execuções com `status = 'em_andamento'` e `fim` nulo**: **9 por fonte, em 20 fontes**,
  todas criadas entre **13/11/2026 23:01:18 e 23:01:45 UTC (20:01 de Recife)**, todas disparadas pela rota de
  administrador `POST /etl/execucoes` (campo `disparado_por` preenchido, um único usuário), com `lidos = 0` e
  `gravados = 0`. Nenhuma tem erro registrado. Não há trava ativa no banco (`pg_locks` sem travas de relação de outras
  sessões); o bloqueio é só a linha "em andamento".
- Fontes afetadas: `infodengue`, `sinan-leptospirose`, `recife-arboviroses`, `samu-recife`, `sisagua`,
  `open-meteo-historico`, `alertas-oficiais`, `apac-previsao`, `apac-rios`, `apac-reservatorios`, `atlas-desastres`,
  `cnes-equipamentos`, `ibge-censo-2022-bairro`, `open-meteo-solo`, `open-meteo-temperatura`, `recife-alagamento`,
  `recife-alagamento-2026`, `recife-areas-risco`, `recife-atendimentos-grau-risco`, `sgb-suscetibilidade-deslizamento`.
- **Por que trava:** `execucao.reservar()` (`backend/climasense/etl/execucao.py`) recusa uma nova carga quando existe
  qualquer linha `em_andamento` da fonte ("Esta fonte já tem uma execução em andamento"), e o código diz de propósito que
  execução abandonada exige **recuperação explícita, nunca expiração automática**. Tanto o botão da API (409) quanto o
  `etl atualizar`/`etl semanal` pelo terminal (`iniciar()` chama `reservar()`) param aí. Por isso **nenhuma dessas 20
  fontes teve carga bem-sucedida depois de 13/11**; as únicas com sucesso recente são `apac-chuva`, `open-meteo-mare` e
  `open-meteo-previsao` (26/11), que não estão na lista.
- **Causa provável [não verificado]:** a tarefa em segundo plano (`BackgroundTasks`) não chegou a rodar ou o processo da
  API foi encerrado antes de chamar `_registrar()`; o padrão de 20 fontes × 9 disparos em 27 segundos sugere um
  "atualizar tudo" repetido ou um script. A reserva foi gravada e confirmada antes de a tarefa começar, então a linha
  ficou órfã.
- **O que destrava (não feito aqui):** o operador marcar essas 180 linhas como `falha` com motivo "abandonada" (com
  registro em auditoria) e rodar de novo as cargas. É decisão do dono; o agente de ETL pode propor um comando
  `etl recuperar` com confirmação, coerente com a regra "recuperação explícita".

### 2.2 Efeito nos dados de saúde

| Fonte | Último sucesso | Dado vai até | Limite de frescor (`etl/frescor.toml`) | O que a tela mostra hoje |
|---|---|---|---|---|
| `infodengue` | 05/11/2026 21:06 UTC | SE 43 (termina 31/10) | 192 h | fim da semana tem 26 dias (624 h) → `utilizavel = false` → **"Dados insuficientes"** para dengue e chikungunya, com o motivo. A API do InfoDengue já deve ter as SE 44 a 46 **[não verificado nesta data]** |
| `sinan-leptospirose` | 05/11/2026 21:10 UTC | SE 42 (termina 24/10); arquivo PRELIM de 03/11 | 360 h | 33 dias (792 h) → **"Dados insuficientes"**. O DATASUS republica a cada 1 a 3 semanas |
| `open-meteo-historico` (chuva semanal ao lado da série) | 05/11/2026 02:33 UTC | semana de 25/10 | — | gráfico de `/saude/semanal` sem chuva depois de 25/10 |
| `recife-arboviroses` | 05/11/2026 | 2025 (publicado em 03/2026) | 13.140 h | ainda "em dia": a fonte é anual e 2026 não foi publicado; a trava só impediria pegar uma eventual republicação |
| `samu-recife`, `sisagua` (RF-39) | **nunca** | — | — | sem dado; o comparativo antes/durante/depois não tem essas colunas |

Ou seja: a regra RN-01 está funcionando (o cartão não mostra número velho como atual), mas o cartão de Saúde está vazio
por causa da trava, não por falta de fonte.

---

## 3. Fontes de dados

### 3.1 Tabela geral

| Fonte | URL | O que traz | Granularidade | Frequência e atraso | Formato e acesso | Licença | Usa hoje? | Esforço |
|---|---|---|---|---|---|---|---|---|
| **InfoDengue (Fiocruz/FGV)** | https://info.dengue.mat.br/api/alertcity (doc: https://info.dengue.mat.br/services/api/doc) | dengue, chikungunya, zika: notificados, nowcast com IC, Rt, `p_rt1`, incidência/100 mil, nível 1–4, receptividade climática, transmissão | **município** (geocódigo 2611606); recorte intramunicipal só no Rio | semanal, ~1 semana; semanas recentes revisadas | API JSON/CSV sem chave; parâmetros obrigatórios `geocode, disease, format, ew_start, ew_end, ey_start, ey_end` **[web]** | dados sem licença declarada; código GPL-3.0 (P-51) | **sim** (dengue, chik) | — (só destravar e expor campos que já estão na silver) |
| **Mosqlimate (mesmos dados do InfoDengue)** | https://api.mosqlimate.org/docs/datastore/GET/infodengue/ | idem, paginado | município | idem | API com chave `X-UID-Key` (cadastro) | não declarada | não | não vale: a API pública basta |
| **SINAN no FTP do DATASUS** | ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/ (`FINAIS`, `PRELIM`); página: https://datasus.saude.gov.br/transferencia-de-arquivos/ | microdado: `LEPTBR`, `DENGBR`, `CHIKBR`, `ZIKABR`, `ANIMBR`; classificação, evolução, semana de sintomas, exposição a enchente (lepto) | **município** de residência (sem bairro) | PRELIM republicado a cada 1–3 semanas; ~2 semanas de atraso e 4–6 semanas incompletas | .dbc (DBF comprimido); leitor próprio em `dbc.py` | dado público do MS, sem licença explícita | **sim** (só `LEPTBR`) | dengue/chik pelo SINAN: médio (arquivos nacionais grandes; repete o InfoDengue, mas daria confirmados, sinais de alarme, graves e óbitos) |
| **TabNet (DATASUS)** | http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/leptobr.def (leptospirose; a página de dengue segue o mesmo padrão, endereço não conferido) | tabulação de casos por município e mês | município × mês | segue o SINAN | HTML, sem API | público | não | só conferência manual |
| **Painel / Observatório de Arboviroses (MS)** | https://www.gov.br/saude/pt-br/composicao/svsa/cnie/observatorio-de-arboviroses e https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/a/aedes-aegypti/monitoramento-das-arboviroses | casos prováveis, óbitos, informes semanais | nacional, estadual e **municipal** **[web]** | painel diário, informe semanal | painel interativo; **sem download ou API documentados** **[web]** | público | não | só conferência; não integrar (sem acesso programático) |
| **Informe semanal de arboviroses (MS)** | https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/a/arboviroses/informe-semanal | situação nacional e por UF | UF | semanal | PDF | público | não | não integrar |
| **API de Dados Abertos do MS `/arboviroses/*`** | https://apidadosabertos.saude.gov.br/v1/ | ficha individual do SINAN | caso | semanas | JSON | público | não | **fora do escopo**: PRD §5 / ADR 0017 excluem (ficha individual) |
| **Dados Abertos do Recife: dengue, chikungunya e zika** | https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya | caso a caso no layout SINAN, com **bairro e distrito de residência**, **semana de sintomas** (`ds_semana_sintoma`/`SEM_PRI`) e classificação; tabelas de bairros e distritos | **bairro e distrito** × ano (e semana dentro do ano) | anual; frequência declarada "trimestral", mas 2025 saiu em 03/2026 e **não há 2026** **[web]** | CSV via CKAN (URL assinada) | **ODbL** | **sim** (dengue, chik por bairro × ano) | zika: baixo (P-27). Semana × distrito histórica: baixo a médio (mesmo arquivo, mudar a agregação) |
| **LIRAa (índice de infestação predial do Aedes) do Recife** | sem conjunto aberto: busca por "aedes" no CKAN devolve 0 conjuntos **[web]**; resultado divulgado pela Prefeitura na imprensa, ex.: https://www.diariodepernambuco.com.br/vida-urbana/2026/01/11705684-recife-entra-em-2026-com-risco-medio-por-conta-de-focos-de-mosquito-da-dengue.html; boletim antigo com LIRAa por distrito e bairro: https://www2.recife.pe.gov.br/sites/default/files/boletim_de_arboviroses_recife_se_49.pdf | IIP e IB por estrato/bairro; 1º ciclo 2026: IIP 1,3% (médio), risco muito alto (≥ 4%) em Brasília Teimosa, Ibura, Cohab e Vasco da Gama | **bairro / estrato** | 4 a 6 ciclos por ano | sem dado estruturado público | — | não | precisa de pedido à Vigilância Ambiental (GVACZ/SESAU) e de entrar no PRD; carga por importação manual |
| **Resultado nacional do LIRAa (MS)** | https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/estudos-e-notas-informativas/2026/nota-informativa-no-11-resultado-lira.pdf | classificação por município por ciclo (67% dos municípios informaram o 2º ciclo de 2026) | **município** | por ciclo | PDF | público | não | baixo valor (só o Recife inteiro) |
| **SES-PE: boletim de arboviroses** | portal: https://portal.saude.pe.gov.br/ (boletim nº 45, de 18/11/2026, cobre até 14/11, segundo a imprensa: https://www.diariodepernambuco.com.br/vida-urbana/2026/11/11729435-morte-de-adolescente-de-13-anos-por-dengue-e-a-oitava-registrada-em-pernambuco-em-2026.html) | estado: 55.119 notificações de dengue em 2026 (+29% sobre 2025), 7.955 de chikungunya | estado (municípios citados no texto) | semanal | PDF; **URL oficial do boletim não confirmada** **[não verificado]** | público | não | só contexto estadual e conferência |
| **SINAN `LEPTBR` + janela por evento** | igual ao FTP acima | leptospirose com `ANT_CB_LAM` (exposição a enchente nos 30 dias antes) | município | idem | .dbc | público | **sim** | expor `expostos_enchente` e `obitos` na gold: baixo |
| **Extrato agregado do SINAN local (SESAU Recife)** | sem URL: pedido formal (P-28, P-40) | dengue, chik, zika e lepto por **bairro/distrito × semana** do ano corrente | bairro, distrito | o que a Vigilância conseguir (semanal) | importação manual (planilha agregada) | convênio | não | técnico baixo; depende do cliente |
| **Chuva semanal** (para comparar) | APAC (já integrada) e Open-Meteo Archive ERA5 (já integrada) | mm por semana | distrito / cidade | diário | API | APAC: P-33; Open-Meteo: P-46 | **sim** | — |

### 3.2 Leituras importantes da pesquisa web

- **InfoDengue:** a documentação oficial lista os parâmetros obrigatórios e mostra exemplos de campos, mas **não define o
  significado dos níveis nem traz licença, frequência ou limite de uso** (https://info.dengue.mat.br/services/api/doc).
  A leitura dos níveis (1 verde, 2 amarelo, 3 laranja, 4 vermelho; laranja exige `p_rt1 > 0,95` por 3 semanas) vem do
  dicionário já registrado em `docs/dicionario-dados/infodengue.md` e de guias de terceiros
  (https://lac.tghn.org/recursos/infodengue-glossary, https://prefeitura.poa.br/sms/onde-esta-o-aedes/dados-de-porto-alegre).
- **CKAN do Recife:** 49 recursos no conjunto de arboviroses; **zika 2015–2025 existe** (não carregada pelo conector);
  metadados dos casos de dengue a partir de 2016 trazem `ds_semana_sintoma`, `ds_semana_notificacao`,
  `co_distrito_residencia` e `co_distrito_infeccao` (conferido no JSON de metadados). Nenhum recurso de 2026, nenhum de
  LIRAa (https://dados.recife.pe.gov.br/api/3/action/package_show?id=casos-de-dengue-zika-e-chikungunya).
- **Classificação do LIRAa (MS):** IIP abaixo de 1% satisfatório, 1% a 3,9% alerta (médio risco), 4% ou mais risco de
  surto (manual: https://edisciplinas.usp.br/pluginfile.php/5413329/mod_resource/content/1/manual_liraa_2013.pdf). Já é
  classe, combina com RN-06.
- **Recife na imprensa:** 3.048 casos prováveis de dengue até setembro de 2026 contra 3.186 no mesmo período de 2025
  **[não verificado na fonte primária]**; o estado sobe enquanto o Recife fica estável ou cai, coerente com o InfoDengue.

---

## 4. Chuva e agravos: literatura e o que os nossos dados mostram

### 4.1 Literatura

| Agravo | Achado | Fonte |
|---|---|---|
| Leptospirose | incubação de 1 a 30 dias (média 5 a 14); orientar expostos por 30 dias; vigilância ativa nesse período | NT 138/2022-CGZV/DEIDT/SVS/MS: https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/notas-tecnicas/2022/nota-tecnica-138-2022-estrategias-para-enfrentamento-da-leptospirose-durante-inundacoes.pdf |
| Leptospirose | revisão de 22 estudos ecológicos: 7 com defasagem curta de **1 a 3 semanas** entre chuva e casos; outros 0–1 mês ou 1–3 meses | F1000Research 2026: https://f1000research.com/articles/15-1040 |
| Leptospirose (Recife) | chuva melhora a previsão de casos (2007–2016, regressão beta), sem defasagem extraída | Sigmae/Unifal: https://publicacoes.unifal-mg.edu.br/revistas/index.php/sigmae/article/download/1075/1093/6337 |
| Leptospirose (Salvador/Recife) | chuva e fatores meteorológicos como motores da transmissão urbana | Cunha et al., PLoS NTD 2022: https://doaj.org/article/05ea7056243e4414a0bf1792c5a6ab4a |
| Dengue (Brasil) | risco sobe **0 a 3 meses após condições extremamente úmidas** (máximo em 1 mês) e 3 a 5 meses após seca | Lowe et al., Lancet Planet Health 2021: https://doaj.org/article/d2ea395f9ec648febde65cdd1d984491 |
| Dengue (Recife) | 4 de 6 grandes surtos em meses mais secos; sorotipo explica muito mais que a chuva; ciclo vetor-vírus ~26 dias | Borges et al., Front Public Health 2024: https://pmc.ncbi.nlm.nih.gov/articles/PMC11537940/ |
| Dengue (Recife) | chuva extrema pode reduzir casos por lavagem de criadouros | Sigmae/Unifal: https://publicacoes.unifal-mg.edu.br/revistas/index.php/sigmae/article/download/930/676/3912 |

### 4.2 Análise descritiva com o banco (não é modelo; RN-11)

Chuva semanal ERA5 do Recife (`gold.chuva_diaria`, só semanas com 7 dias, 305 semanas de 27/12/2020 a 25/10/2026) contra
casos das semanas completas (`gold.saude_semanal`). Correlação de Spearman.

| Agravo | Bruta, defasagem 0 a 4 semanas | Sem sazonalidade (desvio da mediana da mesma semana do ano), defasagem 0 a 4 semanas |
|---|---|---|
| Dengue | 0,27 a 0,31 (cai a 0,01 em 12 semanas) | **–0,03 a 0,01** (também nas defasagens de 6 e 8) |
| Chikungunya | 0,30 a 0,33 | não calculado |
| Leptospirose | 0,32 a 0,45 (pico em 1 semana) | **0,16 / 0,16 / 0,20 / 0,18 / 0,07** (pico em 2 semanas) |

Leitura: a correlação bruta da dengue é só a estação (chuva e casos sobem juntos no meio do ano); tirada a estação, não
sobra relação semana a semana. A leptospirose mantém sinal fraco de 0 a 3 semanas, coerente com a literatura e com a
janela de 30 dias. Semanas com 100 mm ou mais e leptospirose nas 3 semanas seguintes (notificados): 22/05/2022 (268 mm):
252; 25/06/2023 (133 mm): 47; 26/04/2026 (110 mm): 73; 21/06/2026 (148 mm): 21. **Chuva sozinha não explica**: o que
importa é onde alagou e quem teve contato com a água, por isso a janela é disparada pelo evento registrado.

**Para a tela:** manter a frase fixa "Coincidência temporal, não prova de causa" (RF-39) e não desenhar linha de
tendência chuva → casos.

---

## 5. Indicadores recomendados

Ordem de prioridade para o cartão de Saúde (Dashboards, I-10 de `dashboards-indicadores.md`) e para o painel do bairro.
"Já dá" = dado e rota existem; só falta destravar o ETL (seção 2).

| # | Indicador | Onde | Como mostrar (regras) | Dado | Situação |
|---|---|---|---|---|---|
| 1 | **Nível de alerta do InfoDengue com tendência** (dengue e chikungunya) | cartão de Saúde | selo de cor do nível (1–4, "nível do InfoDengue") + seta sobe/estável/cai a partir de `variacao_4s_pct` (nowcast); sem número percentual; semana e fonte | `/saude/resumo` | **Já dá** (após destravar `infodengue`) |
| 2 | **Casos estimados da semana com faixa e Rt** | cartão de Saúde (detalhe) | "~221 casos estimados na semana de 25/10 (faixa 123–414)"; Rt com a frase "acima de 1 = transmissão crescendo"; notificado da semana incompleta nunca como queda | `/saude/resumo`, `/saude/semanal` (`casos_estimados, ic_inf, ic_sup, rt`) | **Já dá**. `p_rt1` ("chance de Rt > 1") está na silver, não na gold; se entrar, mostrar como classe ("provável"/"incerto"), não como % (RN-06): ajuste pequeno na gold e na rota |
| 3 | **Últimas 4 semanas completas contra o mesmo período do ano anterior** (e mediana de 3 a 5 anos) | cartão de Saúde | "1.008 notificados nas SE 35–38, abaixo de 2025 (1.694)"; rótulo acima/semelhante/abaixo; só semanas completas | série desde 2015 em `gold.saude_semanal` | **Dado já existe; falta cálculo** (campo novo em `/saude/resumo` ou rota nova). Esforço baixo |
| 4 | **Incidência anual por 100 mil hab. por distrito e bairro** (dengue, chikungunya) | painel do bairro e mapa | "Dengue em 2025: 643 por 100 mil no DS VIII"; ano e data de publicação sempre visíveis ("retrato anual, não situação atual"); supressão de contagens 1–4; aviso de bairro pequeno | `gold.arboviroses_bairro_ano` + `silver.populacao_bairro` (Censo 2022) | **Dado já existe; falta cálculo na rota** `/saude/bairros` (taxa ao lado da contagem). Esforço baixo |
| 5 | **Janela de leptospirose de 30 dias após alagamento** | cartão de Saúde e painel do bairro/distrito | "Dia 9 de 30 desde o alagamento de 27/10; maior atenção até o dia 14"; território do gatilho; "sem registro não é sem risco" | `/saude/resumo` (`janela_leptospirose`) | **Já dá** (gatilhos vêm de estágio, Defesa Civil e APAC; não dependem do SINAN) |
| 6 | **Leptospirose por semana de sintomas, com expostos a enchente e óbitos** | cartão de Saúde (detalhe) e comparativo RF-39 | barras de notificados e confirmados, 6 últimas semanas hachuradas; "X de Y confirmados relataram contato com enchente" (contagem, não %) | silver tem `expostos_enchente` e `obitos`; gold não | **Parcial**: notificados e confirmados já em `/saude/semanal`; exposição e óbitos pedem ajuste na gold e na rota (baixo). Contagens pequenas suprimidas |
| 7 | **Zika anual por bairro** | painel do bairro | igual ao 4; substitui "Dados insuficientes" no histórico (a semanal continua sem fonte) | CSV de zika 2015–2025 no mesmo conjunto do CKAN | **Conector existente com ajuste** (incluir zika no filtro e confirmar o código de confirmado no dicionário do SINAN); responde P-27. Esforço baixo |
| 8 | **LIRAa por bairro** (IIP com a classe do MS) | painel do bairro e mapa | classe satisfatório / alerta / risco com ciclo e data; bairro sem levantamento = "sem dado do ciclo" | não há dado aberto | **Precisa de fonte e de PRD**: pedido à Vigilância Ambiental, importação manual por ciclo. **Não está no PRD**: registrar pergunta antes de construir |

Fica fora da lista, mas vale como passo seguinte: **"canal endêmico" por distrito** (casos por semana de sintomas e
distrito em 2013–2025, a partir dos mesmos CSVs do CKAN, para dizer "esta época do ano costuma ser pior no DS VIII").
Esforço baixo a médio (mudar a agregação do conector para incluir a semana); só histórico.

### 5.1 O que dá para fazer já

1. **Destravar o ETL** (seção 2.1) e rodar `infodengue`, `sinan-leptospirose` e `open-meteo-historico`: com isso os
   indicadores 1, 2, 5 e parte do 6 voltam ao cartão sem uma linha de código nova.
2. **Indicadores 3 e 4**: só SQL sobre tabelas que já existem (agente backend-api; RF-12, RF-19).
3. **Expor na gold** `p_rt1`, `p_inc100k` (InfoDengue) e `expostos_enchente`, `obitos` (leptospirose) (agente etl-dados).

### 5.2 O que falta

| Falta | Por quê | Caminho |
|---|---|---|
| Dengue/chik/lepto **2026 por bairro ou distrito** | nenhuma fonte pública tem recorte intramunicipal no ano corrente | extrato agregado do SINAN local (P-28, P-40) por importação manual |
| **LIRAa por bairro** | sem conjunto aberto; não está no PRD | pergunta nova ao cliente (abaixo) |
| **Zika semanal** | InfoDengue parou em 2024-SE07 | extrato do SINAN local ou `ZIKABR` (município) |
| Termos de uso do InfoDengue | não publicados | P-51 |

### 5.3 Perguntas a registrar em `docs/perguntas-abertas.md` (este agente só escreve em `docs/propostas/`)

- **LIRAa por bairro.** O LIRAa do Recife (IIP por bairro/estrato, a cada ciclo) pode ser enviado pela Vigilância
  Ambiental (GVACZ) para importação manual? Interessa à equipe ver a classe de infestação no painel do bairro? (Hoje não
  está no PRD; ligaria a RF-12 por território e RF-37/RF-38.)
- **Destravar execuções.** O dono autoriza encerrar as 180 execuções abandonadas de 13/11 e ter um comando de
  recuperação explícita com auditoria?
- **Comparação com o ano anterior.** A equipe prefere comparar com o mesmo período do ano anterior, com a mediana de 3
  a 5 anos, ou com o limiar do próprio InfoDengue (`nivel_inc`)?

---

## 6. O que foi testado e o que não foi

| Item | Situação |
|---|---|
| Tabelas de saúde, períodos, última semana, lacunas | **Testado** no banco (só `SELECT`, transação somente leitura) |
| Execuções abandonadas de 13/11 (contagem, horário, origem, ausência de travas) | **Testado** no banco |
| Incidência por distrito 2025 com Censo 2022 | **Testado** no banco |
| Correlação chuva × casos (bruta e sem sazonalidade) | **Calculado** no banco; descritivo, sem validação |
| Parâmetros da API InfoDengue | **Lido** na documentação oficial |
| SE mais recente disponível hoje no InfoDengue e no DATASUS | **Não verificado** nesta data |
| CKAN do Recife: recursos, zika, ausência de 2026 e de LIRAa, campos de semana e distrito | **Testado** (API do CKAN e JSON de metadados) |
| Painel de Arboviroses do MS | página lida; **sem download/API documentados** |
| Boletim da SES-PE | só pela imprensa; **URL oficial não confirmada** |
| LIRAa do Recife (2º e 3º ciclos de 2026) | **Não encontrado** |
| Código de "confirmado" de zika no SINAN | **Não verificado** |
