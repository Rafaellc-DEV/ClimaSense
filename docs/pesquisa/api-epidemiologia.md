# Epidemiologia e saúde durante o evento: o que existe como dado público

> Pesquisa de 06/11/2026 para o Vigidesastres (Vigilância em Saúde do Recife). Pergunta do cliente: **dá para acompanhar
> a saúde DURANTE um evento de chuva e comparar ANTES, DURANTE e DEPOIS?**
> Complementa `docs/pesquisa/saude-e-chuva.md` (05/11/2026), que já cobre InfoDengue, SINAN leptospirose e o CKAN de
> arboviroses; aqui só repito o que muda a conclusão. Dicionários existentes: `docs/dicionario-dados/infodengue.md`,
> `sinan-leptospirose.md`, `recife-arboviroses.md`.
> **[testado]** = chamada real (curl/Python, só GET públicos) feita em 06/11/2026. O resto vem de página oficial citada
> ou é marcado **[não verificado]**. Nenhum dado pessoal foi gravado; as amostras abaixo são contagens.
> Itens ligados a PRD: RF-12.10 (dado real), RN-01 (ausência não é zero), RN-11 (experimental), RN-13 (agregado), RF-19.

## Resposta curta

1. **Tempo oportuno (dias):** quase nada de saúde pública sai em dias. O mais rápido que **achei e testei** são dois
   conjuntos que ainda não estão no ClimaSense: **SAMU Recife** (chamados por dia e bairro, com subtipos como
   diarreia, desidratação, febre, mialgia; publicação mensal, dado até 31/10 em 06/11) e **SISAGUA** (análises da água de
   abastecimento por bairro, defasagem de ~1 semana). Nenhum dos dois é caso de doença: são sinal de demanda de
   urgência e de qualidade da água.
2. **Casos de doença:** semanas (InfoDengue ~1 semana; SINAN ~2 semanas e incompleto por mais 4 a 6) ou anos
   (arboviroses por bairro, hepatite A). Nada disso mostra o que acontece "durante" um evento de 1 a 3 dias.
3. **Comparativo antes/durante/depois:** só é honesto como **janela semanal** com municipal (ou por distrito/bairro
   onde há dado diário: SAMU e SISAGUA), com cada indicador mostrando a própria defasagem e as semanas incompletas.
4. **Precisa de convênio com a Vigilância/SESAU:** atendimentos em UPAs/UBS/SPAs por causa (diarreia, leptospirose
   suspeita, peçonhentos) por dia e bairro, MDDA/SIVEP-DDA, extrato do SINAN municipal por bairro e semana,
   hepatite A recente, internações com menos de ~6 semanas.

---

## 1. Panorama por fonte

| Fonte | O que traz | Granularidade | Defasagem medida | Serve DURANTE o evento? |
|---|---|---|---|---|
| **SAMU Recife (CKAN)** | chamados com tipo/subtipo | **dia e bairro** | mensal; em 06/11 ia até 31/10 | Só como retrospectiva em semanas |
| **SISAGUA (API MS)** | análises de água (E. coli, cloro, turbidez) | amostra, **bairro**, dia da coleta | ~1 semana (coleta 28/10, registro 03/11) | Sim, como contexto de água; não é doença |
| **InfoDengue** | dengue/chik: casos, nowcast, Rt, nível | município, semana | ~1 semana | Parcial (semana, município) |
| **SINAN lepto (FTP)** | notificações com data de sintomas | município, semana | ~2 semanas + 4 a 6 sem. incompletas | Não (lento); sim para janela de 30 dias |
| **SINAN peçonhentos `ANIMBR26`** | acidentes por animal | município, semana | ~3 semanas | Não |
| **SINAN hepatite A `HEPABR`** | hepatites virais | município | **parou em 2023** (arquivo de 03/2025) | Não |
| **API Dados Abertos MS `/arboviroses/*`** | microdado de dengue/chik/zika | caso individual | semanas (digitação) | Não; replica o SINAN |
| **SIH/SUS (FTP `RDPE`)** | internações (AIH) PE | município de residência, mês | `RDPE2608` publicado em 16/10 (~6 a 8 semanas) | Não |
| **SIA/SUS (FTP `PAPE`)** | produção ambulatorial PE | estabelecimento, mês | `PAPE2608` publicado em 30/10 | Não (e não traz diagnóstico de UPA por dia) |
| **CKAN Recife, arboviroses** | casos por bairro/ano | bairro, ano | anual (2025 em 03/2026) | Não |
| **SIVEP-DDA/MDDA** | diarreia por faixa etária, sentinela | unidade/semana | sem download público | Não existe público |
| **e-SUS Notifica** | síndrome gripal, notificações | — | sem dado municipal público achado | Não existe público |

---

## 2. Fontes novas (não estão no ClimaSense)

### 2.1 SAMU Recife (Dados Abertos do Recife) **[testado]**

- **URL do conjunto:** https://dados.recife.pe.gov.br/dataset/servico-de-atendimento-movel-de-urgencia-samu-2026
  (um conjunto por ano, 2011 a 2026). Descoberta por
  `https://dados.recife.pe.gov.br/api/3/action/package_show?id=servico-de-atendimento-movel-de-urgencia-samu-2026`.
- **Recurso:** CSV "Solicitações de Atendimento 2026" + dicionário JSON. O download redireciona; usar `curl -L`.
- **Autenticação:** nenhuma. **Licença:** ODbL (`odc-odbl`). **Responsável:** Secretaria de Saúde, publicação Emprel.
  **Frequência declarada:** mensal.
- **Formato:** CSV `;`, UTF-8, 26 MB, 162.524 linhas em 2026. Colunas: `data`, `hora_minuto`, `municipio`, `bairro`,
  `endereco`, `origem_chamado`, `tipo`, `subtipo`, `sexo`, `idade`, `motivo_finalizacao`, `motivo_desfecho`.
- **Cobertura:** a central regula o Recife e 17 municípios da região metropolitana. Filtrar `municipio = RECIFE`:
  62.926 chamados em jan-out/2026 (~6.000 a 6.700 por mês, ~210 por dia), 103 grafias de bairro.
- **Defasagem real:** em 06/11/2026 o arquivo ia **até 31/10/2026** (último dia completo), e o conjunto foi
  modificado em 06/11. Ou seja, o mês fecha e sobe em dias; **um evento no dia 10 só aparece no início do mês
  seguinte**. Só vi um ponto de publicação; o ritmo mensal vem da metadata e **não foi verificado em mais de um mês**.
- **Exemplo real (Recife, semana a partir do domingo, 2026):**

| Semana | Chuva (ERA5, mm, da pesquisa anterior) | Tipo gastrointestinal | Diarreia+desidratação+infecção GI | Febre+mialgia+síndrome viral | Total de chamados |
|---|---|---|---|---|---|
| 03/05 | 70 | 74 | 15 | 24 | 1.512 |
| **10/05** | **167** | 84 | 11 | 24 | 1.515 |
| 17/05 | 23 | 75 | 21 | 23 | 1.582 |
| 07/06 | 66 | 76 | 20 | 45 | 1.696 |
| 14/06 | 28 | 88 | 29 | 25 | 1.506 |

  Leitura honesta: **não há sinal visível** na semana de 167 mm; os subtipos de interesse têm 10 a 30 chamados por
  semana na cidade inteira (diarreia: 229 no ano; desidratação: 282; febre: 416; mialgia: 323). Por bairro seria 0 a 2
  por semana: ruído. Útil só agregado (cidade ou distrito) e como curva de contexto.
- **Limites:** é **solicitação de atendimento**, não diagnóstico. `subtipo = OUTROS` é 40% (25.421), `GERAIS/OUTROS` e
  `CAUSAS EXTERNAS` dominam. O bairro é o do chamado, não necessariamente da residência. O dicionário do recurso
  descreve 2025 em um campo de 2026 (erro de texto).
- **Úteis ao evento:** `CHOQUE ELETRICO` (48), `ACIDENTE COM ANIMAIS TERRESTRES` (142), `QUEDA DE NIVEL`
  (907); afogamento não apareceu entre os subtipos que listei (não conferi a lista inteira).
- **Dado pessoal (LGPD, RN-13):** cada linha traz **endereço, sexo e idade**. Conector deve agregar na leitura
  (como `recife-arboviroses`): guardar só contagem por data × bairro oficial × tipo/subtipo, descartar `endereco`,
  `sexo`, `idade`, `hora_minuto` (ou reduzir a faixa horária).
- **Esforço de integração:** **baixo** (mesmo CKAN, mesmo padrão do conector de arboviroses; um arquivo por ano,
  atualização mensal; normalização de bairro já existe). Para linha de base: os anos 2011-2025 estão no mesmo CKAN.

### 2.2 SISAGUA, vigilância da qualidade da água (API de Dados Abertos do MS) **[testado]**

- **URL:** `GET https://apidadosabertos.saude.gov.br/sisagua/vigilancia-parametros-basicos?codigo_ibge=261160&ano=2026&limit=1000&offset=0`
  (Swagger em https://apidadosabertos.saude.gov.br/v1/; especificação em `/static/swagger.json`). Sem autenticação.
  Outros: `/sisagua/controle-mensal-amostras-fora-do-padrao` (controle pela companhia de água).
- **Formato:** JSON paginado (`limit`, `offset`; resposta na chave `parametros`). Licença: dado aberto do MS, termo
  não localizado na API **[não verificado]**.
- **Dados reais do Recife em 2026:** 5.680 linhas até 28/10 (478 a 729 por mês). Parâmetros: cloro residual livre
  (3.065), coliformes totais (1.120), **Escherichia coli (1.120: 1.071 AUSENTE, 49 PRESENTE)**, turbidez (341).
  87 bairros em `area`. Campos: `data_da_coleta`, `data_do_laudo`, `data_de_registro_no_sisagua`, `area` (bairro),
  `local`, `motivo_da_coleta` (rotina ou outro), `resultado`.
- **Defasagem real:** última coleta 28/10, último registro 03/11 em 06/11: **cerca de 1 semana**, a mais curta entre
  as fontes de saúde que achei.
- **Uso:** contexto de doença de transmissão hídrica (coliforme/E. coli presente em bairro afetado por alagamento)
  e prova de que há vigilância ativa. **Não é caso de doença** e a amostragem é de rotina (não dirigida pelo evento).
  Sem amostra no bairro/semana é "sem coleta", nunca "água boa".
- **Cuidado:** `descricao_do_local` traz endereço (logradouro) do ponto de coleta: descartar, guardar bairro e
  resultado. Ponto de coleta não é dado pessoal, mas não precisa ir para o produto.
- **Esforço:** **baixo a médio** (API simples; paginar 6.000 linhas/ano; casar bairro; definir "presença de E. coli"
  como dado e não como risco).

---

## 3. Fontes já mapeadas, com o que mudou nesta pesquisa

### 3.1 InfoDengue **[testado]**
`GET https://info.dengue.mat.br/api/alertcity?geocode=2611606&disease=dengue|chikungunya&format=json&ew_start=43&ew_end=44&ey_start=2026&ey_end=2026`
devolveu em 06/11 só a **SE 43/2026** (36 notificados, nível 2). Município, semana, sem bairro, defasagem ~1 semana,
a mais recente sempre baixa. Já integrado. Zika: série parou em 2024-SE07 (ver `saude-e-chuva.md`).

### 3.2 SINAN no FTP do DATASUS **[testado]**
`ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/{FINAIS|PRELIM}/`. Arquivos de 2026 existentes:
`LEPTBR26` (03/11), `ANIMBR26` (29/10), `DENGBR26`, `CHIKBR26`, `ZIKABR26`, `HANTBR26` (15/05). **Hepatite A:**
`HEPABR` só vai até **`HEPABR23.dbc` (atualizado em 26/03/2025)**; não há 2024, 2025 nem 2026. Logo, hepatite A como
indicador do evento **não existe** em fonte pública atual. Não há arquivo de DDA no SINAN (a DDA fica no SIVEP-DDA;
só surto vai ao SINAN). Defasagem e minimização: ver dicionário `sinan-leptospirose.md`.

### 3.3 API de Dados Abertos do MS, `/arboviroses/{dengue,chikungunya,zikavirus}` **[testado]**
`GET https://apidadosabertos.saude.gov.br/arboviroses/dengue?limit=&offset=&id_municip=261160&nu_ano=2026&campos=...`
(o filtro de município é `id_municip`; com outro nome o parâmetro é ignorado e vem o Brasil). Devolve **a ficha
individual** do SINAN (idade, sexo, raça, gestante, ocupação, sintomas). Os registros do Recife de 2026 que vi tinham
`dt_digita` de semanas depois da notificação. **Não recomendado:** repete o FTP, expõe dado pessoal e não traz bairro.
Se usado, passar `campos` com só `dt_notific, sem_pri, classi_fin` e agregar na memória.

### 3.4 Dados Abertos do Recife (CKAN) **[testado]**
Busca em `https://dados.recife.pe.gov.br/api/3/action/package_search`: **não há** conjunto de leptospirose, DDA,
diarreia, hepatite, internação ou atendimento em UPA/SPA. O que existe de saúde com dado:
- `casos-de-dengue-zika-e-chikungunya` (anual, já usado);
- SAMU por ano (seção 2.1);
- `consultas-e-procedimentos-de-saude`: **só 2022 e 2023** (consultas, produção ambulatorial, internamentos);
- `servico-de-pronto-atendimento-spa`: apenas **cadastro das unidades** (CSV de unidades, 03/2026), sem atendimento;
- `registro-de-atendimentos-da-defesa-civil` (já tratado em outro dicionário).

### 3.5 SIH/SUS e SIA/SUS no FTP **[testado a existência; conteúdo não lido]**
`ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RDPE2608.dbc` (4,4 MB, publicado 16/10/2026) e
`.../SIASUS/200801_/Dados/PAPE2608.dbc` (80 MB, 30/10/2026). Mensal, por UF, `.dbc` (já temos o leitor). A AIH traz
CID principal (A00-A09 diarreias, A27 leptospirose, A90 dengue) e município de residência, mas **não bairro**, e o
arquivo traz CEP e data de nascimento (agregar na leitura). Defasagem de 6 a 8 semanas, só internação pública:
serve para balanço do trimestre, não para o evento. **Não li as colunas** para esta pesquisa **[não verificado]**.

### 3.6 TabNet **[testado: página no ar]**
http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/hepabr.def abre (hepatites, mensal, município). Útil para
conferência manual; não é fonte para o sistema (sem API, HTML).

---

## 4. O que procurei e **não** achei como dado público utilizável

| Item | Resultado |
|---|---|
| SIVEP-DDA/MDDA por município | Só formulários e manual em https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dda/vigilancia-epidemiologica; os informes da Sala Nacional de Emergências Climáticas citam extrações do SIVEP-DDA por semana, mas o informe testado exigiu login ("Conteúdo restrito"). Nenhum conjunto no dados.gov.br ou na API do MS. |
| Painel de Monitoramento das Arboviroses (MS) | Existe painel (informes semanais PDF citam fonte Sinan Online e e-SUS VS), **sem API nem download documentado** nos resultados. Não foi acessado. Equivalente programático: InfoDengue. |
| SES-PE / CIEVS-PE | Boletins de arboviroses estaduais circulam em notícias (6.292 notificações de arbovirose até 29/08 segundo reportagem; "Boletim nº 15" cobrindo 04/01 a 18/04), mas **não localizei painel nem dado estruturado** e **não confirmei a URL oficial** (o site saude.pe.gov.br respondeu, sem links de boletim extraídos). **[não verificado]**. Estado, não Recife. |
| Prefeitura do Recife: boletim epidemiológico, atendimentos nas UPAs/SPAs | Nenhum conjunto aberto; CKAN só tem cadastro de unidades. |
| e-SUS Notifica / SRAG (OpenDataSUS) | O portal OpenDataSUS respondeu, mas não analisei SRAG: é respiratório e fora do tema; sem recorte municipal diário útil. Não pesquisado a fundo. |
| Vigilância Climática / Observatório Clima e Saúde (Fiocruz) | https://climaesaude.icict.fiocruz.br/ no ar; páginas de indicadores (ar, água, vetores, eventos extremos) e "Áreas de Vigilância" (Manaus, Porto Velho, Rio, semiárido, Amapá); **sem API e sem Recife** na página principal. |
| InfoGripe (Fiocruz) | https://infogripe.fiocruz.br/ não respondeu no teste (timeout). SRAG é fora do tema; não insistido. |
| Hepatite A recente | Arquivo do SINAN parou em 2023 (seção 3.2). |
| Atendimento relacionado à chuva (CID, causa) | Não existe público. |

---

## 5. Respostas às três perguntas

### (a) O que existe em tempo oportuno para acompanhar saúde DURANTE o evento

Com honestidade: **nenhuma fonte pública mostra casos de doença nos dias do evento.** O que há de mais próximo:

| Indicador | Atraso | Dá para dizer durante o evento? |
|---|---|---|
| Qualidade da água por bairro (SISAGUA) | ~1 semana | Não "durante", mas "na semana seguinte", com bairro |
| Dengue/chik no município (InfoDengue) | ~1 semana (estimado) | Nível e Rt da semana anterior |
| Chamados do SAMU por subtipo | fim do mês + dias | Só retrospectiva |
| Leptospirose (SINAN) | ~2 semanas, 4 a 6 incompletas | Só janela de 30 dias |
| Peçonhentos | ~3 semanas | Não |

O que o sistema pode mostrar **durante** o evento é o que o ClimaSense já tem: chuva, alagamentos, estágio. A saúde
entra como "janela de vigilância aberta" (lembrete, NT 138/2022) e como linha de base, com cada indicador indicando
"dados até DD/MM" (RF-19).

### (b) Como montar o comparativo antes/durante/depois

**Definição proposta** (descritiva, sem causalidade; RN-06, RN-11):

- **Evento** = o que a equipe registrou (estágio, ocorrência de alagamento), com data de início e fim.
- **Antes:** as 4 semanas epidemiológicas anteriores à semana do evento (referência), mais, quando houver, a mediana
  da mesma semana do ano em 2 a 5 anos anteriores (sazonal).
- **Durante:** a semana epidemiológica do evento (ou duas, se cruzar domingo).
- **Depois:** semanas +1 a +4 para SISAGUA, SAMU e dengue; **semanas +1 a +6** para leptospirose (incubação média 5 a
  14 dias, até 30; notificação ~5 dias depois do sintoma; encerramento ~18 dias).
- **Granularidade por indicador:** município e semana para InfoDengue e SINAN; **distrito sanitário ou bairro e
  semana** para SISAGUA e SAMU (bairros pequenos têm 0 a 2 chamados por semana: usar distrito ou cidade).
- **Regras de tela:**
  - cada coluna "antes/durante/depois" traz a data de corte da fonte; semanas depois do corte aparecem como
    "ainda sem dado" e semanas incompletas hachuradas (as últimas 4 do InfoDengue; 4 a 6 do SINAN);
  - **sem cálculo de variação percentual enquanto "depois" estiver incompleto**; mostrar contagem e a faixa do
    nowcast (InfoDengue), nunca "queda de X%" sobre semana incompleta;
  - sem evento registrado não há comparativo ("sem evento declarado": não é "sem impacto");
  - selo "Experimental" enquanto não houver validação (RN-11), e texto fixo: "coincidência temporal descritiva, não
    prova de causa".

### (c) O que NÃO existe público e precisa de convênio com a Vigilância/SESAU

| Dado que o cliente quer | Por que não existe público | Pedido |
|---|---|---|
| Atendimentos nas UPAs/SPAs/UBS relacionados à chuva | Só cadastro das unidades no CKAN; prontuário/BPA não é publicado por dia | Contagem diária por unidade ou distrito e por grupo de causa (CID A00-A09, A27, A90-A92, T63, W-chuva), sem identificação |
| DDA diária | MDDA/SIVEP-DDA é interno; sem download | Extrato semanal (ou diário em evento) do MDDA do Recife, por unidade sentinela e faixa etária |
| Leptospirose e peçonhentos por bairro/semana | SINAN público só tem município | Extrato agregado do SINAN municipal |
| Hepatite A e outras hídricas recentes | Arquivo público parou em 2023 | Extrato do SINAN local |
| Internações por causa com menos de 6 semanas | SIH tem 6 a 8 semanas de atraso | Extrato mensal ou semanal das AIH pela SESAU |
| Arboviroses 2026 por bairro | CKAN anual (2025 em 03/2026) | Extrato semanal do SINAN municipal |

**Como a tela deve dizer** (RN-01, RN-02): em vez de gráfico vazio ou zero, um cartão por indicador:

> **Atendimentos nas UPAs por diarreia: Dados insuficientes.** Fonte que falta: registro de atendimento da Secretaria
> de Saúde do Recife (não publicado). Última atualização: sem dado. Pedido enviado à Vigilância em: __ (ou "ainda não
> solicitado").

E para indicadores com dado atrasado: "Leptospirose (SINAN/DATASUS), dados até 10/10; as últimas 6 semanas ainda
estão em atualização". **Zero medido** (ex.: nenhuma notificação de residente em semana coberta pelo arquivo) é
mostrado como 0; **semana depois do corte** é "sem dado até DD/MM" (RN-02).

---

## 6. Recomendação priorizada

| # | Ação | Valor | Esforço | Observação |
|---|---|---|---|---|
| 1 | **Comparativo antes/durante/depois semanal** com o que já existe (InfoDengue + SINAN leptospirose + chuva), com semanas incompletas e data de corte explícitas | Alto | Baixo (dados já integrados) | Nada novo de fonte; depende de evento registrado |
| 2 | **Pedir à Vigilância** o extrato semanal agregado (SINAN municipal por bairro; MDDA; atendimentos de UPA por causa) | Muito alto | Político, não técnico | Só isso entrega "durante o evento" de verdade; ver perguntas |
| 3 | **SISAGUA** (água por bairro, ~1 semana) | Médio | Baixo a médio | Único dado de saúde com bairro e atraso curto; contexto, não doença |
| 4 | **SAMU Recife** (chamados por subtipo, por distrito) | Médio-baixo | Baixo | Mensal; usar só agregado e como contexto; valor limitado pelo número pequeno |
| 5 | SIH/SIA, hepatite A, API de arboviroses do MS, painéis estaduais | Baixo | Médio | Não trazem valor em tempo oportuno ou repetem fonte já integrada |
| – | Painel MS de arboviroses, SIVEP-DDA público, UPA | – | – | Não existem como dado utilizável; registrar como lacuna na tela |

Antes de construir 3 e 4, confirmar no PRD que cabem (CLAUDE.md: "se não está no PRD, não construa"); se não cabem,
registrar em `docs/perguntas-abertas.md`.

---

## 7. Perguntas para levar ao cliente

1. A Vigilância/SESAU consegue fornecer **extrato semanal agregado** (sem identificação) do SINAN municipal
   (leptospirose, dengue, chikungunya, peçonhentos, hepatite A) por bairro e semana de sintomas? Em que formato e
   com que periodicidade? Durante o evento, poderia ser diário?
2. A MDDA/SIVEP-DDA do Recife pode ser compartilhada por unidade sentinela e semana? Quais unidades notificam?
3. Há contagem de atendimentos nas UPAs/SPAs/UBS por grupo de causa (diarreia, febre, mialgia, acidente com animal)?
   Quem é o responsável (CIEVS Recife, Gerência de Informação, Emprel) e qual é o fluxo formal (ofício, convênio, LGPD)?
4. Que janelas a Vigilância usa de fato para "depois do evento" (30 dias de leptospirose? 2 a 8 semanas de
   arboviroses?) e quais agravos ela quer ver na comparação?
5. O que conta como "evento" para o comparativo: estágio declarado, ocorrência de alagamento por bairro, ou um limiar
   de chuva? Quem declara o fim do evento?
6. O SAMU (dado público, mensal) é aceitável como indicador de contexto, sabendo que é chamado e não diagnóstico?
   O SISAGUA (água por bairro) interessa à Vigilância ou é da Vigilância Ambiental, com outro fluxo?
7. Os códigos de distrito 546 e 547 dos arquivos de arboviroses (pergunta aberta desde 05/11) correspondem a quais
   distritos?
8. O ClimaSense pode citar publicamente InfoDengue, SINAN e SISAGUA? (Para o InfoDengue, termos de uso de dados
   não encontrados.)

---

## 8. O que foi testado e o que não foi

| Item | Situação |
|---|---|
| CKAN Recife: busca de conjuntos de saúde (73 resultados para "saúde"), SAMU 2026 baixado e perfilado, SPA, consultas e procedimentos, zoonoses | **Testado** |
| SAMU 2026: período, contagem Recife, tipos e subtipos, série semanal | **Testado** |
| Ritmo de publicação mensal do SAMU | **Não verificado** (um único ponto de observação) |
| SISAGUA via API do MS: Recife 2026 completo (5.680 linhas), parâmetros, bairros, defasagem | **Testado** |
| API MS `/arboviroses/dengue` com filtro de município | **Testado** (ficha individual; não recomendado) |
| InfoDengue (SE 43/2026) | **Testado** |
| FTP SINAN, SIH, SIA: listas e datas (incluindo ausência de hepatite A após 2023) | **Testado** |
| Conteúdo das colunas de SIH e SIA | **Não lido** |
| Painel MS de arboviroses, SIVEP-DDA, SES-PE/CIEVS, e-SUS Notifica | **Não encontrado como dado utilizável** |
| Observatório Clima e Saúde (Fiocruz) | Página principal lida; sem API e sem Recife na página |
| InfoGripe | Timeout no teste |
| Licença dos dados do SISAGUA e do InfoDengue | **Não encontrada** |
