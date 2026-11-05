# Saúde e chuva: arboviroses, leptospirose e outros agravos

> Pesquisa de 05/11/2026 para o Vigidesastres (Vigilância em Saúde do Recife). Responde à pergunta do cliente:
> **como ligar a chuva e o alagamento aos agravos à saúde de um jeito útil para agir depois do evento?**
> Complementa `specs/foco-chuvas.md` (seção 7, linha "SINAN") e `docs/funcionalidades-equipe.md` (seção 4).
> Toda afirmação marcada como **[testado]** foi verificada com chamada real (curl ou Python) nesta data; o resto
> vem da literatura ou de páginas oficiais, com a URL ao lado.

## Resumo

| Agravo | Melhor fonte pública | Granularidade | Atraso medido | Bairro ou distrito? |
|---|---|---|---|---|
| Dengue, chikungunya | InfoDengue `alertcity` | Município, semana epidemiológica | ~1 semana (SE 43 disponível em 05/11) **[testado]** | Não |
| Zika | InfoDengue | Município, semana | **Série parou em 2024-SE07** **[testado]** | Não |
| Dengue, chik, zika (histórico) | Dados Abertos Recife, `casos-de-dengue-zika-e-chikungunya` | Caso individual, com distrito e bairro | Anual; 2025 publicado em 03/2026, **2026 ainda não existe** **[testado]** | **Sim** |
| Leptospirose | DATASUS FTP, SINAN `LEPTBR26.dbc` (preliminar) | Caso individual, só **município** de residência | ~2 semanas do arquivo; casos recentes ainda sem encerramento **[testado]** | Não |
| Animais peçonhentos | DATASUS FTP, SINAN `ANIMBR26.dbc` | Caso individual, só município | ~3 semanas **[testado]** | Não |
| Diarreias (MDDA) | SIVEP-DDA | Unidade sentinela, semana | Sem download público localizado | Não verificado |

Conclusão curta: **a decisão por bairro após um alagamento não pode vir de dado de caso público em tempo útil.**
O que dá para fazer bem é (1) uma **janela de vigilância** disparada pelo próprio evento (que o ClimaSense já registra),
(2) um **acompanhamento municipal semanal** de leptospirose e arboviroses com as lacunas à vista, e (3) um **retrato
histórico por distrito e bairro** das arboviroses para planejamento. O dado de leptospirose por bairro precisa vir da
própria Vigilância (extrato do SINAN local), como já previsto na spec.

---

## 1. InfoDengue (dengue, chikungunya, zika)

### 1.1 API pública `info.dengue.mat.br/api/alertcity` **[testado]**

```
GET https://info.dengue.mat.br/api/alertcity
    ?geocode=2611606&disease=dengue|chikungunya|zika&format=json|csv
    &ew_start=30&ew_end=44&ey_start=2026&ey_end=2026
```

- Sem chave, HTTP 200, JSON ou CSV. Uma linha por semana epidemiológica (SE), mais recente primeiro.
- **Dengue Recife:** série de 2010-SE01 até 2026-SE43 (878 semanas), `versao_modelo` 2026-11-03.
- **Chikungunya Recife:** mesma estrutura, até 2026-SE43.
- **Zika Recife:** 424 semanas, de 2016-SE01 a **2024-SE07**; nada depois. Tratar como série encerrada (mostrar
  "sem dados desde 02/2024", nunca zero).

Trecho real da resposta (dengue, SE 2026-43, semana iniciada em 25/10/2026):

```json
{"SE": 202643, "data_iniSE": 1792886400000, "municipio_nome": "Recife",
 "casos": 36, "casos_est": 221.0, "casos_est_min": 123, "casos_est_max": 414,
 "Rt": 1.024722, "p_rt1": 0.6007913, "p_inc100k": 14.786703,
 "nivel": 2, "nivel_inc": 1, "receptivo": 1, "transmissao": 0,
 "tempmin": "24.4099", "tempmed": "27.2680666666667", "tempmax": "31.4115666666667",
 "umidmin": "52.3786333333333", "umidmed": "71.8578333333333", "umidmax": "86.3759666666667",
 "pop": "1494586", "notif_accum_year": 3091, "versao_modelo": "2026-11-03"}
```

Note a diferença entre `casos` (36 notificados até agora) e `casos_est` (221, IC 123–414): é o *nowcasting*, que
corrige o atraso de notificação. Na semana mais recente o número notificado é sempre baixo e **não é queda**.

### 1.2 Campos (dicionário em https://info.dengue.mat.br/services/api)

| Campo | Significado |
|---|---|
| `SE`, `data_iniSE` | Semana epidemiológica (AAAASS) e seu domingo inicial (epoch ms) |
| `casos` | Casos notificados na semana (revisado retroativamente) |
| `casos_est`, `_min`, `_max` | Estimativa por nowcasting e intervalo de credibilidade de 95% |
| `casprov*`, `casconf` | Casos prováveis e confirmados em laboratório (vieram `null` para o Recife) |
| `p_inc100k` | Incidência estimada por 100 mil |
| `Rt`, `p_rt1` | Número reprodutivo e probabilidade de Rt > 1 (alerta laranja exige p_rt1 > 0,95 por 3 semanas) |
| `nivel` | Nível de alerta 1 verde, 2 amarelo, 3 laranja, 4 vermelho |
| `nivel_inc` | Incidência abaixo do limiar pré-epidêmico, acima dele ou acima do epidêmico |
| `receptivo` | Receptividade climática ao vetor (0–3) |
| `transmissao` | Evidência de transmissão sustentada (0–3) |
| `temp*`, `umid*` | Médias semanais de temperatura e umidade (estações de aeroporto, REDEMET) |
| `Localidade_id` | Subdivisão municipal, **só implementada para o Rio de Janeiro**; no Recife é 0 |
| `notif_accum_year` | Notificações acumuladas no ano |

**Não há chuva** nos campos do InfoDengue; a chuva viria do próprio ClimaSense (APAC ou Open-Meteo).

### 1.3 Mosqlimate `api.mosqlimate.org/api/datastore/infodengue/` **[testado: 401]**

Mesmos campos, paginado (`page`, `per_page` até 100, `disease`, `start`, `end`, `geocode`), mas exige o cabeçalho
`X-UID-Key` (cadastro gratuito). Sem chave a resposta é `{"detail": "Unauthorized. See documentation"}`.
Documentação: https://api.mosqlimate.org/docs/datastore/GET/infodengue/. Não traz vantagem para uma cidade só;
**usar a API pública do InfoDengue**.

### 1.4 Licença e limites

- Código do AlertaDengue: **GPL-3.0** (https://github.com/AlertaDengue/AlertaDengue). Para os **dados**, não encontrei
  licença explícita nem limite de requisições publicado (página da API e documentação do Mosqlimate não citam).
  Os dados de casos vêm do SINAN e o clima da REDEMET.
- Recomendação: uma chamada por dia por doença (a série muda uma vez por semana), citar "InfoDengue (Fiocruz/FGV)"
  e o artigo de método (Codeço et al., InfoDengue, https://www.biorxiv.org/content/10.1101/046193v1), e pedir
  confirmação de uso à equipe do InfoDengue se o produto for além do piloto acadêmico. **Não verificado:** termos de uso.

---

## 2. Leptospirose (e peçonhentos) no SINAN

### 2.1 Microdados no FTP do DATASUS **[testado]**

```
ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/FINAIS/LEPTBR00.dbc … LEPTBR24.dbc
ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/PRELIM/LEPTBR25.dbc, LEPTBR26.dbc
(o mesmo para ANIMBR = peçonhentos, DENGBR, CHIKBR)
```

| Arquivo | Última modificação | Tamanho |
|---|---|---|
| `FINAIS/LEPTBR24.dbc` | 15/07/2026 | 1,9 MB |
| `PRELIM/LEPTBR25.dbc` | 03/11/2026 | 1,4 MB |
| `PRELIM/LEPTBR26.dbc` | 03/11/2026 | 1,1 MB |
| `PRELIM/ANIMBR26.dbc` | 29/10/2026 | 12 MB |

O `.dbc` é um DBF comprimido (PKWare implode). Sem instalar nada, decodifiquei com uma porta em Python puro do
`blast.c` do zlib (o PySUS faz o mesmo com `pyreaddbc`). Achados reais no `LEPTBR26.dbc`:

- 14.848 notificações no Brasil; **331 de residentes no Recife** (`ID_MN_RESI = 261160`, código IBGE de 6 dígitos):
  129 confirmadas (`CLASSI_FIN=1`), 194 descartadas, 7 sem encerramento. 19 óbitos entre confirmados.
- **Exposição a água ou lama de enchente** (`ANT_CB_LAM`, nos 30 dias antes dos sintomas): 75 de 129 confirmados (58%)
  responderam "sim"; 27 "ignorado". Em 2025, 66 de 113.
- **Não há bairro nem distrito** no arquivo público: só município de notificação e de residência, regional
  (`ID_REGIONA` 1497) e a unidade notificadora (`ID_UNIDADE`, CNES). A unidade **não** é o local de residência nem
  de exposição; não serve como proxy de bairro.
- Datas disponíveis: notificação, primeiros sintomas (`DT_SIN_PRI`, `SEM_PRI`), investigação, encerramento, digitação,
  e até 4 datas e municípios de situação de risco (`DT_RISCO1..4`, `CO_MUN_R1..4`).
- **Atrasos medidos (Recife, 2026):** sintomas → notificação, mediana 5 dias (Q1 3, Q3 8); notificação →
  encerramento, mediana 18 dias (Q3 36). Última notificação do Recife no arquivo: 10/10/2026; última digitação no
  Brasil: 23/10/2026; arquivo publicado em 03/11/2026. Ou seja, **o arquivo chega ~2 semanas atrás** e as últimas
  4–6 semanas ainda têm casos sem confirmação.

Série semanal (sintomas) em 2026, ao lado da chuva semanal do Open-Meteo Archive (ERA5, ponto do Recife):

| Semana (domingo) | Chuva (mm) | Notificados | Confirmados |
|---|---|---|---|
| 26/04 | 92 | 21 | 10 |
| 03/05 | 70 | 18 | 7 |
| **10/05** | **167** | **33** | **20** |
| 17/05 | 23 | 22 | 8 |
| 24/05 | 64 | 18 | 5 |
| 31/05 | 53 | 20 | 10 |
| 07/06 | 66 | 7 | 2 |
| 14/06 | 28 | 12 | 4 |
| **21/06** | **154** | 7 | 4 |
| 28/06 | 24 | 8 | 3 |
| 05/07 | 12 | 4 | 2 |

Leitura descritiva, sem modelo: o pico de maio coincide com as semanas mais chuvosas e se mantém por 3 semanas; a
chuva de 21/06, quase igual, **não** foi seguida de alta. Chuva sozinha não explica os casos; o que importa é quem teve
contato com água de alagamento, e isso depende de onde alagou. Reforça a ideia de disparar a vigilância pelo
**evento registrado** (estágio, ocorrência, abrigo), não por um limiar de chuva.

**Peçonhentos** (`ANIMBR26.dbc`): 1.768 notificações de residentes no Recife em 2026, 87% escorpião (`TP_ACIDENT=3`),
de 150 a 210 por mês sem pico claro na chuva. Mesma limitação: só município. Baixa prioridade para a relação com chuva;
pode entrar no boletim como contexto (escorpiões e serpentes desalojados após enchentes são orientação clássica).

### 2.2 TabNet **[testado: página no ar]**

http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/leptobr.def traz **casos confirmados** por município de
notificação ou residência, de 2007 a 2026, com linha por **mês** (ano/mês de sintomas ou notificação), não por semana.
Bom para conferência manual; o FTP é melhor para o sistema.

### 2.3 Outras fontes procuradas

- **OpenDataSUS:** não achei conjunto CSV de leptospirose; o caminho oficial de microdados é a transferência de arquivos
  do DATASUS (https://datasus.saude.gov.br/transferencia-de-arquivos/), o mesmo FTP. **Não verificado** em detalhe.
- **Painel do Ministério:** casos e óbitos 2000–2025 (PDF),
  https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/l/leptospirose/situacao-epidemiologica/casos-e-obitos-2000-a-2025.pdf.
- **SES-PE / CIEVS-PE:** não encontrei painel ou boletim com leptospirose por município em 2026; só notícia citando a
  SES-PE (Diario de Pernambuco, 05/2026,
  https://www.diariodepernambuco.com.br/vida-urbana/2026/05/11713692-leptospirose-o-perigo-silencioso-trazido-pelas-chuvas-e-alagamentos.html).
- **Secretaria de Saúde do Recife:** não encontrei boletim público de leptospirose por distrito sanitário.
  O SINAN **municipal** (base local da Vigilância) tem bairro e logradouro; é o mesmo pedido já registrado na spec:
  **extrato por bairro e semana fornecido pela própria Vigilância**, agregado, sem identificação.

---

## 3. Dados Abertos do Recife (CKAN) **[testado]**

Busca em `https://dados.recife.pe.gov.br/api/3/action/package_search` por dengue, chikungunya, zika, arbovirose,
leptospirose, aedes, notificação, agravo, vigilância, zoonoses e escorpião.

- **leptospirose:** 0 conjuntos. **Peçonhentos:** nenhum conjunto de casos (só a unidade do Centro de Vigilância de
  Zoonoses).
- **`casos-de-dengue-zika-e-chikungunya`** (Secretaria de Saúde, licença ODbL, metadados modificados em 20/05/2026):
  https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya

| Recurso | Anos | Última atualização do recurso |
|---|---|---|
| Casos de Dengue (CSV, um por ano) | 2013–2025 | 2025: 07/03/2026 |
| Casos confirmados de Chikungunya (CSV) | 2015–2025 | 2025: 04/03/2026 |
| Casos confirmados de Zika (CSV) | 2015–2025 | 2025: 04/03/2026 |
| Tabela de Bairros, Tabela Distrito, Tabela dos Agravos, Tabela Municípios, Tabela UF (CSV) | — | 07/03/2026 |
| Metadados (JSON) de cada tabela | — | 07/03/2026 |

Os downloads redirecionam para `ckan-storage-download.app.emprel.gov.br` (URL assinada de 1 h); é preciso seguir o
redirecionamento (`curl -L`). Perfil real dos arquivos de 2025 (UTF-8, separador `;`, 130 colunas, layout do SINAN):

- **Dengue 2025:** 9.187 notificações de residentes; `CLASSI_FIN`: 5.002 dengue (10), 99 com sinais de alarme (11),
  9 grave (12), 3.533 descartados (5), 255 em branco. Datas de 01/01 a 31/12/2025.
- **Chikungunya 2025:** 1.942 linhas; apesar do nome "casos confirmados", 1.072 são **descartados** (5) e 863
  confirmados (13). Filtrar por `CLASSI_FIN` sempre.
- **Território:** `ID_DISTRIT` preenchido em 98% (dengue); 8 códigos (117–122, 546, 547), mas a "Tabela Distrito" só
  descreve 117–122 (6 distritos antigos). Os códigos 546 e 547 precisam de confirmação com a Vigilância (provavelmente
  os distritos VII e VIII). `ID_BAIRRO`/`NM_BAIRRO` preenchidos em 99%; 116 grafias distintas para 94 bairros oficiais
  (precisa de normalização).
- **Sensível:** os arquivos trazem **logradouro (`NM_LOGRADO`) e CEP** de cada caso. Mesmo sendo público, o ClimaSense
  deve **descartar logradouro, CEP e número da notificação na carga bronze** e guardar só contagens por bairro e semana
  (LGPD, minimização).
- **Atraso:** publicação anual. Em novembro de 2026 **não há nenhum dado de 2026**. Serve para histórico e
  planejamento, não para o pós-evento.

---

## 4. Literatura: defasagens e uso pela vigilância

### 4.1 Leptospirose

- **Incubação de 1 a 30 dias, média de 5 a 14 dias** após a exposição: Nota Técnica nº 138/2022-CGZV/DEIDT/SVS/MS,
  "Estratégias para enfrentamento da leptospirose durante inundações",
  https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/notas-tecnicas/2022/nota-tecnica-138-2022-estrategias-para-enfrentamento-da-leptospirose-durante-inundacoes.pdf
  (o link hoje serve o fluxograma clínico SVS/2014 anexo, que define o critério "contato com áreas alagadas, lama ou
  esgoto **nos 30 dias antes** do início dos sintomas"); mesma faixa no Guia de Vigilância em Saúde 2017
  (https://www.saude.sp.gov.br/resources/cve-centro-de-vigilancia-epidemiologica/areas-de-vigilancia/doencas-de-transmissao-por-vetores-e-zoonoses/doc/lepto/lepto_gvs_vol_unico_2017.pdf).
- **O que a vigilância faz após inundação** (NT 138/2022 e o alerta do MS reproduzido pelo CVE-SP,
  https://www.saude.sp.gov.br/resources/cve-centro-de-vigilancia-epidemiologica/areas-de-vigilancia/doencas-de-transmissao-por-vetores-e-zoonoses/doc/lepto/alerta_epidemiologicoms_lepto_inundacoes.pdf):
  alertar a rede assistencial; considerar suspeito todo exposto à enchente com febre, mialgia ou cefaleia; iniciar
  antibiótico sem esperar o laboratório; orientar a população exposta a procurar atendimento se tiver sintomas
  **em até 30 dias**; manter vigilância ativa nesse período; registrar a exposição na ficha. Exemplos municipais de
  alerta por região após chuva: São Paulo (https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/alerta_leste2019.pdf).
- **Defasagem chuva → casos:** revisão sistemática de 22 estudos ecológicos (F1000Research, 2026,
  https://f1000research.com/articles/15-1040): 7 estudos acharam defasagem curta de **1 a 3 semanas** (ex.: 14–18
  dias em Coelho & Massad, pico em 2 semanas em Matsushita et al. 2018, 1–2 semanas em Cunha et al. 2022), outros de
  0–1 mês e de 1–3 meses. Preprint de Salvador com dados semanais: 1–2 semanas (medRxiv 2026, só o resumo; não acessei
  o texto completo).
- **Recife:** estudo de séries temporais e regressão beta, 2007–2016, chuva da APAC (6 postos), concluindo que a
  chuva ajuda a antecipar casos (Sigmae/Unifal,
  https://publicacoes.unifal-mg.edu.br/revistas/index.php/sigmae/article/download/1075/1093/6337). **Não consegui
  extrair do PDF a defasagem estimada.** Os dados de 2026 da seção 2.1 são coerentes com 0–2 semanas entre a semana
  de chuva forte e a semana dos sintomas.

**Regra prática para o produto:** janela de 30 dias a partir do dia do alagamento, com atenção maior entre o 5º e o
14º dia (média de incubação) e lembrando que a notificação chega ~5 dias depois dos sintomas.

### 4.2 Arboviroses

- Brasil, 558 microrregiões, 2001–2019: risco de dengue aumenta **0 a 3 meses após condições extremamente úmidas**
  (máximo em 1 mês, RR 1,56) e **3 a 5 meses após seca** (máximo em 4 meses), com o efeito da seca maior em áreas
  urbanas e com falta de água (armazenamento doméstico). Lowe et al., Lancet Planet Health 2021,
  https://doaj.org/article/d2ea395f9ec648febde65cdd1d984491.
- Recife, 2001–2019: casos em geral acompanham a estação chuvosa, mas **4 de 6 grandes surtos ocorreram em meses mais
  secos**; o sorotipo circulante explicou muito mais que a chuva (correlação de 0,37 para 0,88 ao incluir sorotipo).
  O ciclo vetor-vírus é estimado em ~26 dias. Borges et al., Front Public Health 2024,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11537940/.
- Chuva extrema pode **reduzir** a incidência por lavagem de criadouros (*washout*), conforme estudo SARIMAX de
  2018–2021 para o Recife (https://publicacoes.unifal-mg.edu.br/revistas/index.php/sigmae/article/download/930/676/3912).
- Tese UFPE sobre dengue e El Niño na RMR com correlação cruzada por defasagem
  (https://attena.ufpe.br/bitstream/123456789/43004/1/TESE%20Henrique%20dos%20Santos%20Ferreira.pdf); não extraí o valor.

**Regra prática:** para arboviroses a escala é de **semanas a meses** e a chuva é só um dos fatores; o nível do
InfoDengue já incorpora clima, Rt e incidência. O papel do ClimaSense é **lembrar** a ação pós-chuva (eliminação de
criadouros, recolhimento de entulho, inspeção de abrigos) 2 a 8 semanas depois, e mostrar o nível do InfoDengue, não
inventar um índice próprio.

### 4.3 Diarreias

Doença diarreica aguda é monitorada pelo SIVEP-DDA (unidades sentinela, por semana), mas **não encontrei download
público por município** (https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dda/vigilancia-epidemiologica).
Fica como pedido à Vigilância; não entra nesta onda.

---

## 5. Funcionalidades propostas

Todas seguem as regras do projeto: falta de dado não é zero (RN-01), prioridade não é probabilidade (RN-06),
precisão espacial honesta (RN-07), experimental até validar (RN-11), só dados reais e decisão humana por último.
Rotas sob `/api/v1`, autenticadas, no padrão `RespostaDados`.

### S1. Janela de vigilância de leptospirose pós-alagamento (prioridade 1)

- **Pergunta:** "Em quais territórios houve alagamento recente, em que dia da janela de risco estamos e o que falta
  fazer?"
- **Fonte:** dados que o ClimaSense já tem: declaração de estágio `alerta` ou `critico` (F1), abrigo aberto (F3),
  ocorrência de alagamento da Defesa Civil e chuva medida da APAC. Referência técnica: NT 138/2022.
- **Rotas:** `GET /saude/janelas-leptospirose?ativa=true&distrito_id=` → `{territorio_id, nivel, aberta_em,
  origem: estagio|abrigo|ocorrencia|manual, dia_da_janela, fecha_em, acoes_vinculadas}`;
  `POST /saude/janelas-leptospirose` (a equipe abre ou confirma a janela sugerida, com autor e hora);
  `PATCH /saude/janelas-leptospirose/{id}` (encerrar ou ajustar). As ações usam o tipo existente
  "vigilância de agravo" de `/acoes`.
- **Granularidade:** o território do evento (bairro ou distrito, o mesmo que foi declarado). Se a origem for a chuva do
  distrito, a janela é do distrito e a tela diz isso.
- **Na tela:** "Ibura: dia 9 de 30 desde o alagamento de 27/10; período de maior atenção até o dia 14; 2 de 4 ações
  feitas (alerta às unidades, orientação nos abrigos, …)", com checklist da NT 138/2022 e texto pronto para o
  WhatsApp dos distritos (reuso de F2).
- **Não podemos afirmar:** que haverá casos, quantos, nem uma "probabilidade de leptospirose"; a janela é um
  **lembrete de vigilância** baseado na incubação, não um risco calculado. Território sem evento registrado não é
  "sem risco": pode ter alagado sem registro.

### S2. Leptospirose no Recife por semana de sintomas (prioridade 2)

- **Pergunta:** "Os casos de leptospirose no Recife estão subindo depois das últimas chuvas?"
- **Fonte:** SINAN preliminar do DATASUS, `ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/PRELIM/LEPTBR{AA}.dbc`
  (e `FINAIS` para o histórico), filtrado por `ID_MN_RESI = 261160`, carga semanal; leitura do `.dbc` com
  `pyreaddbc` ou o decodificador próprio. Chuva semanal da APAC ao lado.
- **Rota:** `GET /saude/leptospirose/serie?desde=&ate=` → por SE: `notificados, confirmados, em_investigacao,
  expostos_enchente, chuva_mm, completa: bool`, mais `arquivo_atualizado_em`.
- **Granularidade:** município, semana epidemiológica de início dos sintomas.
- **Na tela:** barras de notificados e confirmados por semana sobre a chuva semanal, com as últimas 6 semanas
  hachuradas como "incompletas, dado em atualização" e a data do arquivo do DATASUS.
- **Não podemos afirmar:** nada por bairro ou distrito; que uma semana recente baixa é queda (é atraso); que a chuva
  causou os casos (é coincidência temporal descritiva). Semana sem linha no arquivo aparece como "sem notificação
  registrada até DD/MM", não como zero definitivo.

### S3. Situação das arboviroses (InfoDengue) no painel e no boletim (prioridade 2)

- **Pergunta:** "Como estão dengue e chikungunya no Recife nesta semana, para incluir no boletim pós-chuva?"
- **Fonte:** `GET https://info.dengue.mat.br/api/alertcity?geocode=2611606&disease={dengue|chikungunya}&format=json`
  (carga diária, bronze no Atlas, silver no Neon). Zika fora: série sem dados desde 02/2024.
- **Rota:** `GET /saude/arboviroses?doenca=dengue|chikungunya&semanas=12` → `{se, data_ini, casos, casos_est,
  casos_est_min, casos_est_max, rt, p_rt1, nivel, nivel_inc, receptivo, versao_modelo}`; um item resumido em
  `/boletim`.
- **Granularidade:** município, semana.
- **Na tela:** cartão "Dengue: nível amarelo (InfoDengue), ~221 casos estimados na semana de 25/10 (faixa 123–414),
  Rt 1,02", e, quando houver estágio de alerta recente, o lembrete "2 a 8 semanas após chuva forte: revisar
  criadouros e entulho nos territórios afetados".
- **Não podemos afirmar:** que o nível é do ClimaSense (é do InfoDengue, citado como tal); que o número estimado é
  contagem; qualquer relação causal da chuva com a semana atual; recorte por bairro.

### S4. Retrato histórico de arboviroses por distrito e bairro (prioridade 3)

- **Pergunta:** "Quais bairros concentraram mais dengue e chikungunya nos anos anteriores, para planejar a estação de
  chuvas?"
- **Fonte:** CKAN Recife, `casos-de-dengue-zika-e-chikungunya`, recursos anuais 2013–2025; carga anual; descartar
  logradouro, CEP e número da notificação na bronze; normalizar `NM_BAIRRO` para os 94 bairros; população do
  Censo 2022 para taxa.
- **Rota:** `GET /saude/arboviroses/historico?doenca=&ano=&nivel=distrito|bairro` → `{territorio_id, ano,
  casos_confirmados, taxa_100k, ignorados, ultima_atualizacao_fonte}`.
- **Granularidade:** distrito e bairro de residência, por ano (mês como detalhe).
- **Na tela:** mapa coroplético de taxa por 100 mil no último ano publicado, com o aviso "dados de 2025, publicados
  em 03/2026; 2026 ainda não disponível".
- **Não podemos afirmar:** situação atual; local de infecção (é o endereço de residência); ranking firme em bairros
  pequenos (mostrar intervalo ou "poucos casos"); casos com bairro ignorado somem do mapa, mas aparecem no total.

### Pedido à Vigilância (desbloqueia S1 e S2 por bairro)

Extrato semanal agregado do SINAN local (leptospirose, dengue, chikungunya, peçonhentos e, se houver, MDDA) por
bairro de residência e semana de sintomas, sem identificação, com a data de extração. Com isso S2 e S3 ganham recorte
por distrito e S1 pode mostrar "casos notificados no território durante a janela".

---

## 6. O que foi testado e o que não foi

| Item | Situação |
|---|---|
| InfoDengue `alertcity` dengue, chik, zika para 2611606, JSON e CSV | **Testado** (HTTP 200; zika termina em 2024-SE07) |
| Mosqlimate datastore | **Testado**: exige `X-UID-Key` (401 sem chave) |
| Licença dos dados e limite de uso do InfoDengue | **Não encontrado** (só GPL-3.0 do código) |
| FTP DATASUS SINAN lepto, peçonhentos, dengue, chik (lista, datas, download) | **Testado** |
| Leitura do `.dbc` de leptospirose e peçonhentos 2025–2026, colunas, contagens e atrasos do Recife | **Testado** |
| TabNet leptospirose (mensal, 2007–2026) | **Testado** (página no ar; não gerei tabela) |
| CKAN Recife: busca, conjuntos, recursos, download e perfil dos CSV de 2025 | **Testado** |
| Significado dos códigos de distrito 546 e 547 | **Não verificado** |
| Boletim de leptospirose da SES-PE ou da SMS Recife por distrito | **Não encontrado** |
| Dados abertos do SIVEP-DDA (diarreias) | **Não encontrado** |
| Texto completo da NT 138/2022 | Parcial: o PDF servido é o fluxograma anexo; números de incubação confirmados em fontes que a reproduzem |
| Defasagem estimada nos estudos do Recife (Sigmae, tese UFPE) | **Não extraída** (PDF ilegível sem biblioteca) |
| Correlação chuva × leptospirose 2026 | Só tabela descritiva com ERA5; nenhum modelo foi ajustado |
