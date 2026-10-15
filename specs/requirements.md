# ClimaSense — Especificação de Requisitos (`requirements.md`)

> **Antecipar riscos. Orientar decisões. Cuidar do território.**

| Campo | Valor |
|---|---|
| Fase SDD | 1 de 4 — Especificação (o quê e por quê) |
| Versão | 0.3 — revisada em 15/10/2026: somente dados reais (P3) |
| Data | 15/10/2026 |
| Próximas fases | `design.md` (como) → `tasks.md` (passos) → execução |
| Documentos-base | `ClimaSense-contexto-completo.md` v1.0; Atividade de Arquitetura de Software (template preenchido); Planejamento CRISP-DM (AVD); código das pastas `Projetos/AVD`, `Desktop/AVD` e `Desktop/Projeto-ETL_AVD` |

Convenções deste documento:

- **DEVE** = obrigatório no MVP. **DEVERIA** = desejável no MVP, pode ir para a evolução. **PODE** = evolução.
- Critérios de aceite no formato EARS: *QUANDO / SE / ENQUANTO … ENTÃO o sistema DEVE …*.
- IDs: `RF` (funcional), `RNF` (não funcional), `RN` (regra de negócio), `J` (jornada), `CA` (critério de aceite).
- Este documento descreve **o quê**. Stack, contratos de API e estrutura de pastas ficam no `design.md`.

---

## 1. Visão do produto

O ClimaSense reúne dados de clima, território e saúde do Recife para ajudar as equipes de Vigilância em Saúde a responder uma pergunta:

> **Diante das condições previstas, quais territórios precisam de atenção primeiro, por quais motivos e com qual nível de confiança?**

O produto tem duas faces:

1. **Área pública (landing page):** informa a população sobre avisos aprovados pela equipe e explica o que é o ClimaSense. Não exige login. Seu objetivo principal é **comunicar com clareza**.
2. **Área da equipe (autenticada):** painéis, mapa, séries históricas, cenários de alagamento, avaliações territoriais e o fluxo de comunicados com revisão.

Os dados chegam por um **pipeline ETL** em camadas (bronze → silver). A camada bronze e a base territorial ficam no **MongoDB Atlas**.

### 1.1 Princípios que orientam todos os requisitos

1. **Ausência de dado nunca é ausência de risco.** Falta de informação aparece como “dados insuficientes”.
2. **Toda prioridade vem com o motivo.** Nenhum número aparece sem fonte, horário e limitação.
3. **Nada chega à população sem revisão humana.**
4. **Feito para quem não é técnico.** Linguagem simples, letras grandes, poucos elementos por tela.
5. **Aproveitar o que já funciona.** O ETL e a visualização territorial existentes são preservados.

---

## 2. Ponto de partida: o que já existe e o que será aproveitado

Levantamento feito na leitura das pastas originais. Essas pastas **não serão alteradas**: o código é copiado e adaptado para `ClimaSense/`.

### 2.1 Inventário

| Origem | Conteúdo | Situação verificada | Destino no ClimaSense |
|---|---|---|---|
| `Desktop/Projeto-ETL_AVD/` | ETL em classes `Extract`, `Transform` e `Load`. Lê a API CKAN da Prefeitura (vacinação COVID-19) paginada em 500 registros, até 5.000. Grava a **bronze no Atlas** (`vacinacao.bronze_vacinados`), limpa e grava a **silver no NeonDB/Postgres** (`silver_vacinados`). | Código funcional. A etapa API→bronze está comentada em `run_etl.py`. A bronze é substituída a cada carga (`delete_many`). O arquivo `src/_init_.py` está com nome incorreto. | **Preservar e generalizar** como módulo de ingestão de várias fontes (RF-12). O dado de vacinação vira o primeiro indicador de saúde agregado por distrito (RF-15). |
| `Desktop/AVD/` (Aula 07) | Visão territorial completa. `load_mongo.py` baixa os dados oficiais, corrige os vínculos de bairros dos DS VII e VIII, calcula a área geodésica e faz upsert em `Recife.DistritosSanitarios`. `gerar_mapa.py` lê o Atlas e gera um HTML portátil com Leaflet. Interface em `mapa_assets/` e testes Python, Node e Playwright. | Versão mais completa e testada. **Referência canônica** da visualização territorial. | **Preservar todas as funcionalidades** no novo módulo Território (RF-07, RF-13). |
| `Projetos/AVD/Atividade5-Atlas/` | Primeira versão da carga e do mapa: Folium, `delete_many` e variáveis `MONGODB_URI`, `MONGODB_USERNAME` e `MONGODB_PASSWORD`. | Superada pela versão do `Desktop/AVD`. O host do cluster está fixo no código. | Usada só como referência histórica. As variáveis passam a ser unificadas em `MONGO_URI`. |
| `Projetos/AVD/Atividade1–4/`, `Desktop/AVD/main.py`, `notebook.ipynb`, `aula05.html`, `v2/` | Exercícios com a API do IBGE (PNAD, desocupação): média, mediana, moda, variância, desvio padrão, amplitude, assimetria, curtose e um painel em Chart.js. | Exercícios acadêmicos, sem relação direta com o clima. | **Reaproveitar os métodos estatísticos** como serviço de estatística descritiva das séries (RF-08). Os dados da PNAD não entram no produto. |
| `Projetos/AVD/README.md` + `Planejamento-CRISP-DM.pdf` | Planejamento CRISP-DM com a base do **SAMU-192** (bairro × horário). | Só planejamento, sem código. | Fonte candidata de saúde agregada (RF-15, evolução). O método CRISP-DM orienta a documentação dos dados. |
| Template de Arquitetura de Software | Requisitos arquiteturais, estilo combinado (camadas, MVC e microsserviços), componentes, módulos e serviços. | Preenchido pela equipe. | Será respeitado e refinado no `design.md` (seção 11 deste documento). |
| `ClimaSense-contexto-completo.md` | Problema, personas, jornada, módulos, RF01–RF11, governança, riscos e validação. | Documento-mãe do produto. | Base desta especificação. |

### 2.2 Pontos de atenção encontrados no código existente

| # | Achado | Tratamento exigido |
|---|---|---|
| A1 | A bronze da vacinação é **apagada e regravada** a cada execução (`delete_many`). Perde-se o histórico do que estava disponível em cada momento. | RN-09: a bronze passa a ser acumulativa e versionada por execução. |
| A2 | O ETL limita a extração a **5.000 de cerca de 1,4 milhão** de registros. | RN-10: um indicador calculado sobre uma extração parcial DEVE ser rotulado como **amostra**. |
| A3 | Existem três nomes de variável para a conexão com o Atlas, e o host do cluster aparece fixo em `Atividade5-Atlas/main.py`. | RNF-SEG-01: uma única variável `MONGO_URI`, apenas no `.env`. |
| A4 | O CSV oficial de bairros diverge da Secretaria de Saúde nos DS VII e VIII. Há 15 correções documentadas em `correcoes-bairros.json`. | RN-12: manter as correções e a auditoria, e exibir a nota na interface. |
| A5 | O mapa atual é uma **fotografia estática** gerada em HTML. Não há conexão contínua com o banco. | RF-07 passa a ler os dados pela API. A exportação portátil continua disponível (RF-07.12). |
| A6 | As telas citadas no contexto (`01-visao-territorial.png` … `04-comunicacao.png`) e a logo (`Design sem nome (6).png`) **não estão nas pastas compartilhadas**. | Pendência P1 (seção 12). |

---

## 3. Atores e papéis

| Ator | Descrição | Acesso |
|---|---|---|
| **Cidadão / população** | Morador do Recife que consulta avisos. Pode ser idoso, ter baixa familiaridade digital ou usar o celular com conexão ruim. | Landing page pública, sem login. |
| **Analista** (persona Carlos, em parte) | Técnico da Vigilância em Saúde. Consulta dados, registra avaliações e escreve rascunhos. | Área autenticada: leitura de tudo e escrita de avaliações e rascunhos. |
| **Revisor responsável** | Aprova, ajusta ou devolve comunicados e avaliações, sempre com justificativa. | Analista + revisão e aprovação. |
| **Coordenação** (persona Carlos, gestor) | Define destinatários e critérios e publica comunicados aprovados. | Revisor + publicação e despublicação. |
| **Administrador técnico** | Gerencia usuários, fontes e execuções do ETL. | Tudo, incluindo usuários e fontes. Não aprova comunicados próprios. |
| **Profissional de campo** (persona Ana, ACS) | Recebe informação local aprovada. | No MVP, consulta a landing pública. Uma visão simplificada autenticada fica para a evolução (RF-04.6). |

Uma pessoa pode acumular papéis (RN-15), mas **nunca aprova o próprio conteúdo** (RN-05).

---

## 4. Jornadas do usuário

### J1 — Cidadão consulta avisos (pública)

1. Abre o ClimaSense no celular ou computador.
2. Vê no topo, sem rolar, o **estado atual**: há avisos ativos ou não, e o horário da última atualização.
3. Se houver aviso, lê o território afetado, o que fazer, até quando vale e quem emitiu.
4. Encontra os telefones de emergência (Defesa Civil 199, Bombeiros 193, SAMU 192) sempre visíveis.
5. Pode rolar para entender o que é o ClimaSense, de onde vêm os dados e quem é a equipe.

### J2 — Membro da equipe entra no sistema

1. Na landing, clica em **“Acesso da equipe”** (sempre visível no topo).
2. Informa e-mail e senha numa tela simples, com letras grandes e mensagens claras.
3. Entra no **Painel inicial**, com o menu lateral à esquerda.
4. Se errar a senha várias vezes, recebe uma orientação clara e o acesso é bloqueado temporariamente.

### J3 — Analista avalia o território (jornada principal do contexto, passos 1–4)

1. Escolhe **território** (Recife inteiro, um distrito sanitário ou um bairro) e **período**. Os filtros valem para todas as telas.
2. Vê o **estado das fontes**: atualização, cobertura e lacunas.
3. Abre o **mapa**, com distritos, bairros, faixas hídricas e indicadores.
4. Clica num distrito e vê os detalhes, os fatores e a qualidade dos dados.

### J4 — Analista estuda o histórico (passo 5)

1. Abre **Séries e sazonalidade** e escolhe a variável (ex.: chuva), a frequência e o período.
2. Vê a evolução no tempo, a comparação com a referência histórica e o calendário sazonal.
3. Consulta as estatísticas descritivas e a cobertura da série.

### J5 — Analista examina um cenário de alagamento (passo 6, experimental)

1. Abre **Cenários de alagamento**, escolhe o território e o horizonte (24, 48 ou 72 horas).
2. Vê chuva prevista, maré, fatores, faixa de incerteza e qualidade. Tudo marcado como **experimental**.
3. Se os insumos forem insuficientes, vê “dados insuficientes”, nunca “risco baixo”.

### J6 — Analista registra a avaliação e prepara um comunicado (passos 7–8)

1. Registra uma **avaliação territorial**: território, período, prioridade sugerida, justificativa e evidências.
2. A partir dela, cria um **rascunho de comunicado** com território, público, texto, validade e evidências.
3. Vê a **prévia** exatamente como a população verá.
4. Envia para revisão.

### J7 — Revisor decide e Coordenação publica (passos 8–10)

1. O revisor vê os itens **“Aguardando sua revisão”** no painel.
2. Aprova, ajusta ou devolve, com justificativa obrigatória para ajuste ou devolução.
3. A coordenação publica o comunicado aprovado. Ele aparece na landing (J1).
4. Ao expirar a validade, ou se a coordenação encerrar, o aviso sai da landing e fica no histórico.

### J8 — Administrador mantém dados e acessos

1. Cadastra usuários e papéis.
2. Vê a lista de fontes com a última execução, o status e o número de registros.
3. Dispara ou agenda uma execução do ETL e vê o registro (log) da execução.

---

## 5. Requisitos funcionais

### RF-01 — Landing page pública · **DEVE**

**História:** Como cidadão, quero ver rapidamente se há algum aviso para minha região e o que devo fazer, para me proteger.

| ID | Critério de aceite |
|---|---|
| RF-01.1 | QUANDO a página carregar, ENTÃO o sistema DEVE mostrar acima da dobra (sem rolar) o estado dos avisos: “X avisos ativos” ou “Nenhum aviso ativo no momento”, e a data e hora da última atualização. |
| RF-01.2 | SE não houver aviso ativo, ENTÃO o sistema NÃO DEVE usar frases como “tudo seguro” ou “sem risco”. DEVE dizer “Nenhum aviso ativo publicado pela equipe” (RN-01). |
| RF-01.3 | Cada aviso DEVE mostrar: título em linguagem simples, territórios afetados, nível em **texto e cor**, o que fazer, início e fim da validade, quem emitiu e quando. |
| RF-01.4 | SE houver mais de um aviso, ENTÃO o sistema DEVE ordená-los por nível (mais alto primeiro) e depois pelo mais recente. |
| RF-01.5 | O cidadão DEVERIA poder filtrar os avisos digitando o nome do bairro, sem diferenciar acentos (mesma regra da busca do mapa existente). |
| RF-01.6 | Os telefones de emergência (199, 193, 192) DEVEM estar visíveis na primeira tela e ser clicáveis no celular (`tel:`). |
| RF-01.7 | A página DEVE ter uma seção **Sobre o ClimaSense** (o que é, o que não é, de onde vêm os dados, equipe). |
| RF-01.8 | O botão **“Acesso da equipe”** DEVE estar sempre visível no topo, sem competir visualmente com os avisos. |
| RF-01.9 | A página DEVE dizer que o ClimaSense **não substitui** os alertas oficiais da Defesa Civil, com link para os canais oficiais. |
| RF-01.10 | Efeitos visuais e animações DEVEM ser sutis e respeitar `prefers-reduced-motion`. Nenhum efeito pode atrasar a exibição do estado dos avisos. |
| RF-01.11 | A landing DEVE funcionar sem login e sem chamar endpoints autenticados. Ela consome só um endpoint público de avisos publicados. |

### RF-02 — Autenticação · **DEVE**

**História:** Como membro da equipe, quero entrar com segurança e sem complicação.

| ID | Critério de aceite |
|---|---|
| RF-02.1 | O sistema DEVE autenticar por e-mail e senha. Não há cadastro aberto: contas são criadas pelo administrador. |
| RF-02.2 | QUANDO as credenciais forem inválidas, ENTÃO o sistema DEVE mostrar “E-mail ou senha incorretos”, sem revelar qual dos dois está errado. |
| RF-02.3 | SE houver 5 tentativas falhas em 15 minutos para a mesma conta, ENTÃO o sistema DEVE bloquear novas tentativas por 15 minutos e explicar isso em linguagem simples. |
| RF-02.4 | A tela de login DEVE ter campo de senha com botão “mostrar senha” rotulado em texto, rótulos visíveis (não só placeholder) e foco inicial no e-mail. |
| RF-02.5 | ENQUANTO o usuário estiver inativo por mais de 60 minutos, a sessão DEVE expirar. O sistema DEVE avisar 2 minutos antes, com um botão grande “Continuar conectado”. |
| RF-02.6 | O usuário DEVE poder sair (logout) pelo menu a qualquer momento. |
| RF-02.7 | O administrador DEVE poder redefinir a senha de um usuário. No primeiro acesso após a redefinição, a troca de senha é obrigatória. |
| RF-02.8 | Recuperação de senha por e-mail PODE ser adicionada na evolução, quando houver um serviço de e-mail. |

### RF-03 — Autorização por papéis · **DEVE**

| ID | Critério de aceite |
|---|---|
| RF-03.1 | O sistema DEVE aplicar os papéis da seção 3 **no backend**. Esconder botões na interface não basta. |
| RF-03.2 | SE um usuário chamar uma ação sem permissão, ENTÃO a API DEVE responder 403 e a interface DEVE explicar “Você não tem permissão para esta ação. Fale com a coordenação.” |
| RF-03.3 | O menu lateral DEVE mostrar só os itens que o papel do usuário pode usar. |

### RF-04 — Navegação autenticada (menu lateral) · **DEVE**

| ID | Critério de aceite |
|---|---|
| RF-04.1 | Após o login, o sistema DEVE mostrar um menu lateral fixo com, no máximo, **8 itens de primeiro nível**, cada um com **ícone e texto** (nunca só ícone). |
| RF-04.2 | Itens previstos: Painel inicial · Mapa do território · Séries e sazonalidade · Cenários de alagamento · Avaliações · Comunicados · Fontes de dados · Administração (só para administrador). |
| RF-04.3 | O item da tela atual DEVE ficar destacado por cor, peso da fonte e marcador. A cor sozinha não basta. |
| RF-04.4 | Em telas menores que 1024 px, o menu DEVE virar uma gaveta aberta por um botão rotulado “Menu”. |
| RF-04.5 | O **Painel inicial** DEVE responder em poucos blocos: avisos ativos, itens aguardando revisão, territórios em atenção e saúde das fontes. Sem gráficos supérfluos. |
| RF-04.6 | Uma visão simplificada para o profissional de campo PODE ser criada na evolução. |

### RF-05 — Filtros globais de território e período · **DEVE** (contexto RF01)

| ID | Critério de aceite |
|---|---|
| RF-05.1 | O sistema DEVE oferecer um seletor de **território** (Recife, distrito sanitário ou bairro) e de **período** que vale para todas as telas analíticas. |
| RF-05.2 | QUANDO o usuário mudar o filtro, ENTÃO todos os gráficos, listas e o mapa da tela DEVEM refletir o mesmo recorte (CA-01). |
| RF-05.3 | O filtro ativo DEVE ficar sempre visível em texto, ex.: “Mostrando: DS IV · 01/01/2026 a 30/09/2026”. |
| RF-05.4 | O recorte DEVE ser mantido ao navegar entre telas e ao recarregar a página (na URL). |
| RF-05.5 | SE o dado não existir na granularidade escolhida (ex.: indicador só por distrito e filtro por bairro), ENTÃO o sistema DEVE avisar e mostrar o nível disponível, sem inventar valores por bairro (RN-07). |

### RF-06 — Fontes e qualidade dos dados · **DEVE** (contexto RF02)

| ID | Critério de aceite |
|---|---|
| RF-06.1 | O sistema DEVE listar cada fonte com nome, órgão, link, tipo (observada, prevista ou derivada), última coleta bem-sucedida, cobertura temporal e espacial, licença e status. |
| RF-06.2 | O status DEVE ser um de: **Atualizada**, **Desatualizada**, **Com falha** ou **Planejada** (ainda não integrada), sempre com texto, ícone e cor. |
| RF-06.3 | SE a última coleta for mais antiga que o limite configurado para a fonte, ENTÃO a fonte DEVE aparecer como “Desatualizada” em todas as telas que usam seus dados. |
| RF-06.4 | Todo gráfico, card e camada do mapa DEVE ter uma legenda “Fonte: … · Atualizado em …”. |
| RF-06.5 | Lacunas DEVEM aparecer de forma visível (falha na linha do gráfico, hachura no mapa ou célula “sem dado”), nunca como zero (RN-02). |

### RF-07 — Mapa do território · **DEVE** (contexto RF04, RF05). Preserva a visualização existente.

Todas as funcionalidades do mapa atual (`Desktop/AVD`, Aula 07) DEVEM continuar existindo:

| ID | Critério de aceite |
|---|---|
| RF-07.1 | Exibir os **8 distritos sanitários** com seus **94 bairros**, vinculados pelo código oficial (`cdistscodi` ↔ `distrito_sanitario`). |
| RF-07.2 | Colorir os distritos por indicador. São mantidas “Quantidade de bairros” e “Área (km²)”, e entram os novos indicadores do ClimaSense (ex.: vacinação agregada, ocorrências e prioridade). |
| RF-07.3 | Usar **5 classes de intervalos iguais** calculadas sobre todos os distritos. Busca e filtro **não alteram** a escala. Valores constantes viram uma classe só, sem divisão por zero. |
| RF-07.4 | Busca de distrito ou bairro **sem diferenciar acentos nem maiúsculas**, que filtra a lista e o mapa. Com Enter e um único resultado, seleciona esse resultado. |
| RF-07.5 | Ao selecionar um distrito, enquadrar o mapa nele e mostrar o painel de detalhes (código, quantidade de bairros, área e lista de bairros). |
| RF-07.6 | Ranking comparativo dos distritos visíveis, com barras proporcionais, clicáveis para selecionar. |
| RF-07.7 | Liga e desliga as camadas **Distritos** e **Faixas marginais dos recursos hídricos** (81 feições, com nome e bacia no tooltip). |
| RF-07.8 | Controle de **intensidade do preenchimento** (20–95%). |
| RF-07.9 | Legenda com os limites exatos das classes e um texto **“Como interpretar”** dizendo o que as cores **não** representam. |
| RF-07.10 | **Exportar CSV** do resultado filtrado: BOM UTF-8, separador `;`, decimal com vírgula e proteção contra fórmulas de planilha (`=`, `+`, `-`, `@`). |
| RF-07.11 | Se o mapa de fundo (tiles) falhar, avisar e manter distritos e camadas navegáveis. |
| RF-07.12 | Manter a geração do **HTML portátil offline** (equivalente ao `gerar_mapa.py`, com os modos Atlas e `--local` explícitos) como exportação para apresentação. |
| RF-07.13 | Mostrar a **nota da correção DS VII/VIII** e a procedência (“Sobre os dados”). |
| RF-07.14 | Navegação por teclado (setas, `+`/`-`), rótulos ARIA e respeito a `prefers-reduced-motion`. |
| RF-07.15 | DEVERIA mostrar camadas de **ocorrências de alagamento** e de **prioridade territorial**, quando houver dados, com o estado “dados insuficientes” próprio. |
| RF-07.16 | A representação espacial NÃO DEVE sugerir precisão maior que a da fonte (RN-07). |

### RF-08 — Séries temporais e sazonalidade · **DEVE**, conforme o histórico disponível (contexto RF03, RF07)

| ID | Critério de aceite |
|---|---|
| RF-08.1 | Filtros de **variável** (chuva no MVP; temperatura, maré e outras conforme as fontes), **frequência** (diária, semanal, mensal) e **período**. |
| RF-08.2 | Gráfico de evolução temporal com **unidade**, **frequência** e **lacunas** visíveis. |
| RF-08.3 | Acumulados por janela (ex.: 24 h, 72 h, mês), sem somar janelas sobrepostas como independentes. |
| RF-08.4 | Comparação com uma **referência histórica** explícita: anos usados, método (média ou mediana) e cobertura. |
| RF-08.5 | **Calendário sazonal** (mês × ano em mapa de calor) mostrando os padrões recorrentes. |
| RF-08.6 | Painel de **estatística descritiva** reaproveitando os métodos das Atividades 3 e 4: média, mediana, moda, variância, desvio padrão, amplitude (mín. e máx.), assimetria e curtose, com classificação em linguagem simples. |
| RF-08.7 | SE a série tiver menos observações que o mínimo configurado, ENTÃO o sistema DEVE avisar “Série curta: não use para caracterizar o clima” (RN-08). |
| RF-08.8 | Exportar os dados do gráfico em CSV, com as mesmas regras do RF-07.10. |
| RF-08.9 | Comparação entre municípios da RMR (Olinda, Jaboatão) PODE vir na evolução (contexto RF09), com critérios equivalentes. |

### RF-09 — Cenários de alagamento · **DEVE** a tela, com dados reais de chuva prevista e maré · o modelo de ML fica para a evolução (contexto RF08)

| ID | Critério de aceite |
|---|---|
| RF-09.1 | Selecionar território e horizonte (24, 48 ou 72 h, conforme os insumos disponíveis). |
| RF-09.2 | Mostrar separadamente: **observação**, **previsão meteorológica**, **estimativa de alagamento** e **prioridade operacional** (contexto §14.1). |
| RF-09.3 | Toda estimativa DEVE trazer origem, horário de emissão, horizonte, **versão do método**, faixa de incerteza e limitações. |
| RF-09.4 | A tela inteira DEVE ter o selo visível **“Experimental: não validado para uso operacional”** até a validação preditiva ser aprovada (RN-11). |
| RF-09.5 | SE os insumos forem insuficientes, ENTÃO o sistema DEVE mostrar “Dados insuficientes para estimar” (RN-01). |
| RF-09.6 | A prioridade operacional NÃO DEVE ser exibida como probabilidade física de alagamento (RN-06). |
| RF-09.7 | O botão “Encaminhar para avaliação” DEVE criar uma avaliação pré-preenchida (RF-10) com as evidências do cenário. |
| RF-09.8 | Cada previsão emitida DEVE ser guardada como foi emitida, para avaliação posterior (contexto §17.2). |

### RF-10 — Avaliações territoriais · **DEVE** (contexto RF05, RF06)

| ID | Critério de aceite |
|---|---|
| RF-10.1 | O analista DEVE poder registrar uma avaliação com: território, período, prioridade sugerida (Atenção, Alerta, Crítico ou Sem indicação), justificativa em texto, evidências vinculadas (fontes, gráficos e valores com horário) e limitações. |
| RF-10.2 | A avaliação DEVE seguir o fluxo **Rascunho → Em revisão → Aprovada ou Devolvida → Encerrada**. |
| RF-10.3 | Toda mudança de estado DEVE registrar autor, data e hora e, quando for ajuste ou devolução, a justificativa. |
| RF-10.4 | A lista de avaliações DEVE poder ser filtrada por estado, território e período. |

### RF-11 — Comunicados com revisão e publicação · **DEVE** (contexto RF06, RF10; §19)

| ID | Critério de aceite |
|---|---|
| RF-11.1 | Um comunicado DEVE ter: território, público-alvo, nível, título, texto, orientações (“o que fazer”), início e fim da validade, evidências, responsável e versão. |
| RF-11.2 | Fluxo de estados: **Rascunho → Em revisão → Aprovado ou Devolvido → Publicado → Encerrado**. A cada edição, o texto pode voltar para revisão. |
| RF-11.3 | A **prévia** DEVE mostrar exatamente a versão em revisão, como ela aparecerá na landing (RN-04). |
| RF-11.4 | SE um comunicado aprovado for editado, ENTÃO o sistema DEVE criar uma **nova versão** que volta para “Em revisão”, preservando a anterior (RN-03). |
| RF-11.5 | Só comunicados **Aprovados** podem ser **Publicados**, e só pela Coordenação (RN-04, RN-05). |
| RF-11.6 | QUANDO o fim da validade passar, ENTÃO o comunicado DEVE sair da landing automaticamente e ir para “Encerrado”. |
| RF-11.7 | O histórico de versões e decisões DEVE ser consultável e comparável (o que mudou entre versões). |
| RF-11.8 | O editor DEVE mostrar um contador de caracteres e um aviso de leitura difícil para frases muito longas (texto voltado à população idosa). |
| RF-11.9 | O envio por canais externos (SMS, WhatsApp, e-mail) PODE vir na evolução (contexto RF10). O estado “Encaminhado” só muda após a confirmação do canal. |

### RF-12 — Pipeline ETL · **DEVE**. Preserva o ETL existente.

| ID | Critério de aceite |
|---|---|
| RF-12.1 | Manter a estrutura **Extract / Transform / Load** e as camadas **bronze → silver** do projeto `Projeto-ETL_AVD`. |
| RF-12.2 | Manter a extração **paginada** da API CKAN da Prefeitura (`datastore_search`, 500 registros por página, limite configurável). |
| RF-12.3 | Manter todas as transformações atuais da vacinação: texto sem espaços e em maiúsculas, vazio vira nulo, conversão de idade, dose e data, derivação de `vacina`, `distrito_sanitario` e `unidade_saude`, e remoção de inválidos e duplicados. |
| RF-12.4 | Generalizar para **várias fontes**, todas **reais**. Cada fonte é uma classe conector (POO) com configuração própria. No MVP: vacinação, distritos e bairros, faixas hídricas (existentes) + `open-meteo-historico` (chuva horária e diária por distrito, reanálise ERA5), `open-meteo-previsao` (chuva prevista até 72 h), `open-meteo-mare` (nível do mar previsto, que inclui a maré) e `recife-alagamento` (Dados Abertos do Recife, ocorrências **não confirmadas** por padrão). Ficam especificados para a sequência: **ANA** (HidroWebService, exige cadastro), APAC, INMET, Cemaden e a tábua de maré da Marinha. Esses conectores alimentam o futuro modelo de ML. |
| RF-12.10 | **Somente dados reais.** O produto não contém dados simulados, sintéticos ou inventados. Quando uma fonte ainda não está integrada ou não respondeu, a tela mostra **“Dados insuficientes”** e diz qual fonte falta (RN-01, RN-19). |
| RF-12.5 | Cada execução DEVE registrar: fonte, início, fim, status, registros lidos, gravados e descartados, motivo dos descartes e mensagem de erro (sem segredos). |
| RF-12.6 | Executar por linha de comando (ex.: `python -m climasense.etl run vacinacao`) e, para o administrador, pela interface (RF-16). |
| RF-12.7 | A bronze DEVE guardar o dado **original**, com metadados técnicos (`_data_carga`, `_execucao_id`, `_fonte`). |
| RF-12.8 | SE a fonte externa falhar, ENTÃO a execução DEVE terminar com status “Com falha”, manter os dados anteriores intactos e refletir o status em RF-06. |
| RF-12.9 | A camada **gold** (agregados prontos para os painéis, ex.: vacinação por distrito e mês) DEVE ser gerada a partir da silver, de forma reprodutível (CA-04). |

### RF-13 — Base territorial no Atlas · **DEVE**. Preserva o `load_mongo.py`.

| ID | Critério de aceite |
|---|---|
| RF-13.1 | Baixar os arquivos oficiais (GeoJSON dos distritos, CSV de bairros e GeoJSON das faixas hídricas) e validar que os GeoJSON são `FeatureCollection`. |
| RF-13.2 | Aplicar as correções de `correcoes-bairros.json`, preservando o CSV bruto e os `codigos_originais_csv` e `fonte_vinculo_bairros` para auditoria. |
| RF-13.3 | Calcular a **área geodésica** (WGS84, `pyproj.Geod`), descontando os buracos e somando os multipolígonos, com 3 casas decimais em km². |
| RF-13.4 | Gravar por **upsert** na coleção `Recife.DistritosSanitarios`, sem apagar a coleção. |
| RF-13.5 | Validar a leitura: exatamente 8 distritos, sem duplicação. Caso contrário, falhar com mensagem clara. |
| RF-13.6 | Os testes existentes (`test_distritos.py`, `model.test.cjs`) DEVEM ser migrados e continuar passando. |

### RF-14 — Auditoria · **DEVE**

| ID | Critério de aceite |
|---|---|
| RF-14.1 | Registrar login (sucesso e falha), mudança de estado de avaliações e comunicados, publicação e despublicação, execução do ETL e alteração de usuários e papéis. |
| RF-14.2 | O registro de auditoria só aceita inclusões: não pode ser editado nem apagado pela interface. |
| RF-14.3 | O administrador DEVE poder consultar a auditoria com filtros por usuário, ação e período. |

### RF-15 — Indicadores de saúde agregados · **DEVE** para vacinação (dado já disponível) · **PODE** para os demais

| ID | Critério de aceite |
|---|---|
| RF-15.1 | Disponibilizar o indicador **vacinação agregada por distrito sanitário e período**, derivado do ETL existente, como camada do mapa e como série. |
| RF-15.2 | Só usar **dados agregados**, sem registros individuais na interface ou na API (RN-13). |
| RF-15.3 | SE o agregado for calculado sobre uma extração parcial, ENTÃO DEVE ser rotulado “Amostra de N registros, não representa o total” (RN-10). |
| RF-15.4 | Incorporar o SAMU-192 (bairro × horário, do planejamento CRISP-DM) PODE vir na evolução. |

### RF-16 — Administração · **DEVE**

| ID | Critério de aceite |
|---|---|
| RF-16.1 | Criar, editar, desativar e reativar usuários e atribuir papéis. Usuários não são apagados, só desativados, para preservar a auditoria. |
| RF-16.2 | Ver a lista de execuções do ETL e disparar uma execução manual por fonte. |
| RF-16.3 | Configurar, por fonte, o limite de desatualização (RF-06.3) e o mínimo de observações (RF-08.7). |

---

## 6. Regras de negócio

| ID | Regra |
|---|---|
| **RN-01** | **Ausência de dado ≠ ausência de risco.** Sem informação suficiente, o sistema exibe “dados insuficientes”. Nunca converte a falta em “baixo”, “normal” ou “seguro”. |
| **RN-02** | **Zero ≠ ausente.** Um valor medido igual a zero e um valor não medido são guardados e exibidos de forma diferente. (O tratamento `'...' → 0` dos exercícios do IBGE **não** é reproduzido: o ausente vira nulo.) |
| **RN-03** | **Versões imutáveis.** Uma versão de comunicado ou avaliação que já foi revisada não é sobrescrita. A edição gera uma nova versão. |
| **RN-04** | **Só o aprovado é publicado.** A landing exibe apenas comunicados no estado Publicado, que exige aprovação prévia da mesma versão. |
| **RN-05** | **Ninguém aprova o próprio conteúdo.** O autor de uma versão não pode ser o revisor dela. |
| **RN-06** | **Prioridade não é probabilidade.** A prioridade operacional é uma indicação para avaliação e nunca aparece como “% de chance de alagar”. |
| **RN-07** | **Precisão espacial honesta.** Um dado é mostrado na granularidade da fonte. Um indicador por distrito não é distribuído entre os bairros. |
| **RN-08** | **Série curta não caracteriza o clima.** Séries abaixo do mínimo configurado recebem um aviso explícito. |
| **RN-09** | **Histórico de cargas.** A bronze é acumulativa e identificada por execução. Os dados corrigidos depois se distinguem da versão disponível naquele momento. |
| **RN-10** | **Amostra rotulada.** Um indicador calculado sobre uma extração parcial é sempre rotulado como amostra, com o N usado. |
| **RN-11** | **Experimental até validar.** Estimativas de alagamento levam o selo experimental até haver uma validação temporal documentada (contexto §21.3). |
| **RN-12** | **Correções documentadas.** Toda correção de dado oficial fica num arquivo versionado, com fonte, data e motivo, e o bruto é preservado. |
| **RN-13** | **Privacidade (LGPD).** Nenhum dado pessoal de pacientes ou vacinados é exibido. Agregados com contagem muito pequena (limite configurável, proposta: menos de 5) são suprimidos. |
| **RN-14** | **Validade obrigatória.** Todo comunicado publicado tem fim de validade e sai sozinho da landing quando ela vence. |
| **RN-15** | **Acúmulo de papéis permitido**, respeitando a RN-05. |
| **RN-16** | **Fuso e formatos.** Horários exibidos em `America/Recife`, datas no formato dd/mm/aaaa, números no padrão pt-BR (vírgula decimal). O armazenamento é em UTC. |
| **RN-17** | **Cor nunca sozinha.** Todo nível ou estado aparece em texto e cor (e ícone quando couber). |
| **RN-18** | **Não é alerta oficial.** O ClimaSense apoia a decisão e a comunicação da equipe. Não substitui a Defesa Civil e não emite alerta oficial. |
| **RN-19** | **Somente dados reais e identificados.** Todo valor exibido vem de uma fonte real, com nome, tipo (observada, prevista ou derivada) e data. Nenhum dado é simulado ou inventado: na falta, vale a RN-01. Dados de modelos (reanálise, previsão) são reais, mas aparecem como **“derivada”** ou **“prevista”**, nunca como “observada”. |

### 6.1 Níveis de aviso (proposta para validação)

| Nível | Texto exibido | Uso |
|---|---|---|
| Informativo | “Fique atento” | Orientação preventiva. |
| Atenção | “Atenção” | Condição que pede cuidado na região. |
| Alerta | “Alerta” | Condição que pede ação preventiva. |
| Crítico | “Situação crítica” | Siga imediatamente as orientações da Defesa Civil. |

Os nomes e os critérios dos níveis DEVEM ser validados com a equipe da Vigilância e alinhados à nomenclatura da Defesa Civil antes do piloto (pendência P5).

---

## 7. Requisitos não funcionais

### 7.1 Acessibilidade e usabilidade (público não técnico e idoso) · **DEVE**

| ID | Requisito | Medida verificável |
|---|---|---|
| RNF-ACE-01 | Conformidade **WCAG 2.2 nível AA**. | Auditoria automática (axe) sem violações críticas, mais um checklist manual. |
| RNF-ACE-02 | Texto base de **18 px** (mínimo 16 px em textos secundários). Títulos com hierarquia clara. | Inspeção do design system. |
| RNF-ACE-03 | Contraste mínimo de **4,5:1** para o texto e **3:1** para os componentes. Meta de **7:1** para o texto dos avisos públicos. | Verificador de contraste nos tokens. |
| RNF-ACE-04 | Alvos de clique de pelo menos **44 × 44 px**. | Inspeção. |
| RNF-ACE-05 | Ícones sempre acompanhados de texto nos menus e botões principais. | Revisão de telas. |
| RNF-ACE-06 | Linguagem simples: sem siglas não explicadas (ex.: “DS IV” vem com “Distrito Sanitário IV”) e mensagens de erro que dizem o que fazer. | Revisão de conteúdo. |
| RNF-ACE-07 | Uso completo por teclado, com foco sempre visível. | Teste manual. |
| RNF-ACE-08 | Zoom de 200% sem perder conteúdo e sem rolagem horizontal. | Teste em 320 px de largura. |
| RNF-ACE-09 | Gráficos com alternativa em tabela (“Ver como tabela”) e um resumo textual do que o gráfico mostra. | Revisão de telas. |
| RNF-ACE-10 | No máximo **um** gráfico protagonista por bloco. Telas com no máximo 4–6 blocos visíveis, sem poluição. | Revisão de design. |
| RNF-ACE-11 | Ações irreversíveis (publicar, encerrar, desativar usuário) pedem confirmação, com o texto da consequência. | Teste. |

### 7.2 Identidade visual · **DEVE**

| ID | Requisito |
|---|---|
| RNF-VIS-01 | Identidade **própria do ClimaSense**, derivada da logo (nuvem, sol, água e gráfico) e da paleta do contexto (azul, verde-azulado e superfícies claras; âmbar e coral só para atenção). Nada de visual genérico de template. |
| RNF-VIS-02 | Um único design system (tokens de cor, tipografia, espaçamento e componentes) compartilhado entre a landing e a área da equipe. |
| RNF-VIS-03 | A landing pode ter efeitos modernos (movimento sutil, profundidade, transições), desde que **o estado dos avisos seja o primeiro elemento percebido**. |
| RNF-VIS-04 | Modo claro como padrão. O modo escuro DEVERIA existir na área da equipe. |
| RNF-VIS-05 | A paleta de níveis de aviso DEVE ser distinguível por pessoas com daltonismo (validação por simulação). |

### 7.3 Segurança e privacidade · **DEVE**

| ID | Requisito |
|---|---|
| RNF-SEG-01 | Segredos (`MONGO_URI`, `NEON_URL`/`DATABASE_URL`, chave de sessão) **apenas** em `.env`, que fica fora do controle de versão. O repositório traz um `.env.example` sem valores reais. |
| RNF-SEG-02 | Senhas guardadas com hash forte (Argon2 ou bcrypt). Nunca em texto puro e nunca em log. |
| RNF-SEG-03 | Sessão em cookie `HttpOnly`, `Secure` e `SameSite`, ou token de curta duração com renovação. A decisão fica no `design.md`. |
| RNF-SEG-04 | Proteção contra força bruta (RF-02.3), CSRF (se for cookie), XSS (texto de comunicado sempre escapado) e injeção de fórmula no CSV. |
| RNF-SEG-05 | Mensagens de erro e logs não expõem a string de conexão, a pilha de exceção ao usuário ou dados pessoais (o padrão já usado em `load_mongo.py` e `mongo_teste.py`). |
| RNF-SEG-06 | CORS restrito às origens configuradas. |
| RNF-SEG-07 | Dependências com versões fixadas e verificação de vulnerabilidades conhecidas. |

### 7.4 Confiabilidade e qualidade de dados · **DEVE**

| ID | Requisito |
|---|---|
| RNF-CON-01 | Uma falha de fonte externa não derruba a aplicação: a tela mostra o último dado válido com o rótulo “desatualizado”. |
| RNF-CON-02 | A falha do Atlas na leitura é mostrada como erro explícito, nunca mascarada por dados locais (padrão do `--local` explícito). |
| RNF-CON-03 | Toda agregação exibida é reproduzível a partir da silver por um script versionado (CA-04). |
| RNF-CON-04 | Metadados mínimos por dado (contexto §16.2): fonte, tipo, horários de observação, emissão e coleta, fuso, unidade, referência espacial, cobertura e versão. |

### 7.5 Desempenho

| ID | Requisito |
|---|---|
| RNF-DES-01 | A landing exibe o estado dos avisos em até **2,5 s** (LCP) em 4G móvel simulado. Proposta a confirmar no piloto. |
| RNF-DES-02 | Telas da área da equipe interativas em até 3 s, com dados agregados pré-calculados na camada gold. |
| RNF-DES-03 | O mapa com 8 distritos e 81 faixas hídricas responde à busca e à seleção sem atraso perceptível (menos de 200 ms). |

Metas numéricas definitivas ainda deverão ser pactuadas com a equipe (contexto §18.2).

### 7.6 Manutenibilidade, testes e portabilidade

| ID | Requisito |
|---|---|
| RNF-MAN-01 | **Backend em Python.** O código é organizado em camadas (apresentação/API, aplicação/serviços, domínio, infraestrutura), conforme o documento de arquitetura. |
| RNF-MAN-02 | Testes automatizados: unidade (domínio e ETL), integração (API) e ponta a ponta (fluxos J1, J2, J6 e J7). Os testes existentes são preservados. |
| RNF-MAN-03 | Lint e formatação padronizados (Python e frontend). |
| RNF-MAN-04 | O projeto roda em **Windows** (ambiente atual da equipe) e em Linux. Instruções com PowerShell e com bash. |
| RNF-MAN-05 | Um único comando para subir o ambiente local (ex.: Docker Compose ou um script), documentado no README. |
| RNF-MAN-06 | Documentação viva: `specs/` (requirements, design, tasks), README, `.env.example` e dicionário de dados por fonte (no estilo CRISP-DM). |
| RNF-MAN-07 | Interface em pt-BR. Os textos ficam centralizados para facilitar a revisão de linguagem. |

---

## 8. Restrições

| ID | Restrição |
|---|---|
| R-01 | **Não alterar nem apagar** nada em `Projetos/AVD`, `Desktop/AVD` e `Desktop/Projeto-ETL_AVD`. Apenas ler, copiar e adaptar para `ClimaSense/`. |
| R-02 | **Backend em Python.** |
| R-03 | **MongoDB Atlas** continua sendo o destino após o ETL (bronze e base territorial). |
| R-04 | Credenciais só via `.env`. Gerar um `.env.example` e nunca versionar segredos. |
| R-05 | Preservar o ETL e a visualização territorial sem perder funcionalidade (seção 2 e RF-07, RF-12, RF-13). |
| R-06 | O frontend é livre, mas precisa suportar muitos dashboards e gráficos (decisão no `design.md`). |
| R-07 | Seguir o Spec-Driven Development: requirements → design → tasks → execução, com aprovação ao fim de cada fase. |
| R-08 | Aderência ao Template de Arquitetura da equipe (seção 11). |

---

## 9. Fora de escopo do MVP

- Emissão de alerta oficial, ordem de evacuação ou diagnóstico de doenças (RN-18).
- Envio real por SMS, WhatsApp ou e-mail (RF-11.9, evolução).
- Modelo preditivo validado (RF-09 entra como experimental).
- Comparação metropolitana completa (RF-08.9).
- Dados individuais de saúde (RN-13).
- Aplicativo móvel nativo (a landing e a área da equipe são web responsivas).
- Cadastro aberto de usuários.

---

## 10. Critérios de aceite do MVP (globais)

Herdados do contexto §20.2 e tornados verificáveis:

| ID | Critério | Como verificar |
|---|---|---|
| CA-01 | O território e o período selecionados correspondem ao que aparece em gráficos, listas e mapa. | Teste E2E: muda o filtro e confere os títulos, os dados e a URL. |
| CA-02 | Todo valor exibido se relaciona a uma fonte e a um horário. | Teste de componente: nenhum card ou gráfico renderiza sem a legenda de fonte. |
| CA-03 | Lacunas e desatualizações aparecem de forma explícita. | Teste com dados sintéticos com lacuna e com fonte vencida. |
| CA-04 | Os agregados podem ser reproduzidos a partir da silver. | Script de reprodução que compara com a gold. |
| CA-05 | O mapa não excede a precisão dos dados. | Revisão: indicador por distrito não aparece por bairro. |
| CA-06 | Rascunhos guardam versão e responsável. | Teste de API. |
| CA-07 | Conteúdo não aprovado não pode ser publicado. | Teste de API: publicar um rascunho retorna erro. Teste E2E: o botão não aparece. |
| CA-08 | Autor não aprova a própria versão. | Teste de API (RN-05). |
| CA-09 | A landing mostra só avisos publicados e vigentes, com o estado acima da dobra. | Teste E2E em desktop e em 375 px. |
| CA-10 | Todas as funcionalidades do mapa existente continuam presentes. | Checklist RF-07.1 a RF-07.14 e testes migrados verdes. |
| CA-11 | O ETL da vacinação produz bronze (Atlas) → silver → gold com registro de execução. | Execução de ponta a ponta com um limite pequeno, mais testes. |
| CA-12 | Nenhum segredo no repositório. | Varredura de segredos no CI. Só existe `.env.example`. |
| CA-13 | Acessibilidade AA nas telas do MVP. | axe sem violações sérias, mais checklist manual. |
| CA-14 | Usuários do piloto concluem as tarefas guiadas (contexto §21.1). | Teste de usabilidade. Registro de tempo, erros e dúvidas. |

---

## 11. Aderência ao documento de arquitetura da equipe

O template preenchido define os componentes **Interface Web**, **Controladores REST**, **Autenticação e Autorização**, **Núcleo de Domínio**, **Fontes Externas** e **Persistência**, e os serviços de Autenticação, Consulta de Fontes, Validação e Qualidade e Consulta de Mapas e Indicadores.

| Componente do template | Requisitos atendidos |
|---|---|
| Interface Web | RF-01, RF-04, RF-05, RF-07, RF-08, RF-09, RNF-ACE, RNF-VIS |
| Controladores REST | Todos os RFs expostos via API (contrato no `design.md`) |
| Autenticação e Autorização | RF-02, RF-03, RF-14 |
| Núcleo de Domínio | RF-10, RF-11, RN-01 a RN-18 |
| Fontes Externas | RF-12, RF-13 |
| Persistência | RF-12.7, RF-13.4, RNF-CON |
| Serviço de Validação e Qualidade | RF-06, RF-12.5, RNF-CON-04 |

O template marca a combinação de **camadas + MVC + microsserviços**. O `design.md` vai justificar a forma de implementar essa combinação no escopo de um MVP acadêmico (proposta inicial: monólito modular em camadas, com módulos isolados que podem ser separados depois).

**Observação:** o template lista o “Grupo 1” com integrantes diferentes do “Grupo 3” do contexto. Confirmar qual composição vale para o ClimaSense (pendência P6).

---

## 12. Pendências e decisões para aprovação

| # | Pendência | Impacto | Proposta |
|---|---|---|---|
| **P1** ✅ | Logo e telas de protótipo. | Identidade visual. | **Resolvido (15/10):** logo anexada e acesso liberado a `Documents/Codex/2026-09-10/ger/outputs/`. |
| **P2** ✅ | Onde fica a silver. | Arquitetura de dados. | **Decidido (15/10):** Atlas para a bronze e o território. **Postgres/Neon** para a silver, a gold e os dados da aplicação (usuários, comunicados, auditoria). O ETL é preservado como está. |
| **P3** ✅ | Fontes climáticas do MVP. | RF-08, RF-09. | **Decidido (15/10) e revisado (15/10, 19h50):** o objetivo é ter **todas as telas prontas e o backend existente unido e completo**, usando **somente dados reais** (sem dados simulados). Fontes climáticas reais do MVP: `open-meteo-historico` (chuva horária e diária por distrito, reanálise ERA5), `open-meteo-previsao` (chuva prevista até 72 h), `open-meteo-mare` (nível do mar previsto, que inclui a maré) e `recife-alagamento` (Dados Abertos do Recife, ocorrências **não confirmadas** por padrão). ANA (com credenciais), APAC, INMET, Cemaden e a tábua da Marinha vêm em seguida. O ETL segue POO (classes `Extract`, `Transform`, `Load` e `Conector`), como ensinado na disciplina. O modelo de ML fica para uma etapa posterior. Os termos de uso e a disponibilidade de cada API serão verificados na tarefa do conector. |
| **P4** | Limite de 5.000 registros da vacinação. | RF-15, RN-10. | Manter configurável e rotular como amostra. Avaliar uma carga completa com agregação na fonte. |
| **P5** | Nomes e critérios dos níveis de aviso. | RF-01, RF-11. | Validar a seção 6.1 com a Vigilância e a Defesa Civil. |
| **P6** | Composição da equipe (Grupo 1 × Grupo 3). | Landing (“Sobre”), documentação. | Confirmar a lista. |
| **P7** | Dados de teste dos exercícios do IBGE (PNAD). | Escopo. | Não entram no produto. Só os métodos estatísticos são reaproveitados. |

---

## 13. Rastreabilidade com o documento de contexto

| Contexto | Este documento |
|---|---|
| RF01 Selecionar território e período | RF-05 |
| RF02 Fonte, atualização, cobertura, lacunas | RF-06 |
| RF03 Histórico e agregações | RF-08, RF-12.9 |
| RF04 Mapa e lista | RF-07 |
| RF05 Justificativas | RF-07.5, RF-09.3, RF-10 |
| RF06 Rascunho e revisão | RF-10, RF-11 |
| RF07 Sazonalidade | RF-08.4, RF-08.5 |
| RF08 Estimativa de alagamento | RF-09 |
| RF09 Comparação metropolitana | RF-08.9 |
| RF10 Canais de envio | RF-11.9 |
| RF11 Saúde agregada | RF-15 |
| §11 Jornada principal | J3 a J7 |
| §19 Governança | RF-11, RN-03, RN-04, RN-05 |
| §20.2 Critérios de aceite | Seção 10 |
| Novo nesta especificação | RF-01 (landing pública), RF-02/03 (login e papéis), RF-04 (menu lateral), RF-12/13 (preservação do ETL e do Atlas), RF-14 (auditoria), RF-16 (administração) |
