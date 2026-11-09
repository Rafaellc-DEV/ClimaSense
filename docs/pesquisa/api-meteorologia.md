# Pesquisa de fontes reais: meteorologia e alertas

Data da pesquisa: 06/11/2026 (testes com `curl` e Python, só GET públicos, sem criar conta). Tudo marcado como "testado" foi chamado nesse dia. O que não foi testado está dito como tal.

Escopo: o que falta ao ClimaSense (RF-12.10, RN-01, RN-02): chuva medida por hora e por distrito, acumulado observado de 72 h, umidade do solo, temperatura e alertas oficiais. Hoje a chuva das últimas 24 h vem do modelo Open-Meteo, e a APAC/Cemaden já entra por `apac-chuva` (19 pluviômetros, janelas de 1 h a 120 h).

## 1. Resumo em uma página

| Necessidade | Existe dado real acessível sem conta? | Melhor caminho |
|---|---|---|
| Chuva observada horária por distrito | Sim, mas só tempo real e por acúmulo. O histórico horário da APAC vem vazio para o Recife | Guardar o que a APAC já devolve a cada 10–15 min (`ultima_medicao`, `1_hora`) e somar por hora e distrito |
| Acumulado observado de 72 h | Sim, já chega no JSON atual (`72_horas`) | Usar `72_horas` por estação e conferir com a soma dos dias da silver |
| Umidade do solo | Não existe medida pública para o Recife | Open-Meteo (modelo ERA5-Land/ECMWF), rotulado como modelado |
| Temperatura | Medida: só o INMET A301, que exige token. Sem token: previsão e modelo | Open-Meteo e previsão oficial do INMET (`apiprevmet3`), rotulados como previsão ou modelo |
| Alertas oficiais | Sim, as quatro origens já estão integradas | Manter; acrescentar a tendência de chuva da APAC e o radar como contexto |

## 2. Fontes testadas

### 2.1 APAC: `https://api.apac.pe.gov.br/api.php`

- Autenticação: nenhuma para os endpoints abaixo (há `/login`, não usado). Formato JSON. Swagger em `/swagger.json` (31 rotas). Erros vêm como HTTP 200 com `{"erro": ...}`.
- Licença e limite: nenhum declarado. Pedir confirmação por escrito à APAC antes de uso em produção (pergunta aberta).
- Codificação: alguns nomes de estação chegam com acentos quebrados em certas rotas (`Torre�o`); decodificar como UTF-8 e normalizar.

| Endpoint | Resultado do teste | Serve para |
|---|---|---|
| `GET /precipitacao_acumulada?municipio=Recife` | OK. 18 estações no teste (dicionário diz 19). Campos `ultima_medicao`, `1_hora` … `120_horas`, `data_hora_ultima_leitura` | Chuva em tempo real e acumulado de 72 h |
| `GET /historico_pluviometrico_mensal?tipo=diario` | OK (já integrado) | Série diária |
| `GET /estacoes?municipio=Recife` | OK. 40 cadastros com `status_dados` (`atualizada`, `desatualizada`, `em manutenção`, `observação`) e `tempo_min` | Saúde de cada pluviômetro |
| `GET /variaveis_atmosfericas_horarias?codigo_estacao=&data_inicio=&data_fim=` | Responde, mas para as estações do Recife (261160623A, 261160603G, 261160604G, 261160616G, 261160605A) todas as linhas vêm com `precipitacao_horaria` e `temperatura_horaria` nulos. Estações de outros municípios (ex.: 260510301M) trazem temperatura, umidade, vento, pressão e chuva | Não serve para o Recife hoje |
| `GET /variaveis_meteorologicas?municipio=Recife` | Ignora o filtro e devolve 17 estações do estado, nenhuma do Recife. Valores suspeitos (máxima de 46,5 °C em Amaraji) | Não usar |
| `GET /previsao_municipio?municipio=Recife` | OK. Previsão horária de 5 dias (temperatura, umidade, vento, nuvens, `precipitacao`). Atenção: devolve `codigo_municipio` 2612000, que não é o IBGE do Recife (2611606); com `codigo=2611606` devolveu "Pombos". Coordenadas (-8,05; -34,95) são do Recife | Previsão oficial horária; validar o mapeamento de município antes de usar |
| `GET /tendencia_precipitacao` | OK. Categoria diária por mesorregião ("Sem chuva", "<2 mm" …), com `data_atualizacao` | Contexto de aviso, não é chuva medida |
| `GET /radar_meteorologico` | OK. Lista de imagens PNG a cada 10 min (`acumulado_1h`, `acumulado_24h`, `cappi_1km`), radar em -8,195/-35,464 | Camada visual no mapa |
| `GET /alertas` | OK (já integrado). Aviso vigente em 06/11: umidade baixa, nível vermelho, nº 91/2026, validade 09/11 | Alertas |

Exemplo real (resumido) de `/precipitacao_acumulada`: `{"estacao":"[CEMADEN] Barreira [G]","codigo_estacao":"261160604G","data_hora_ultima_leitura":"2026-11-06 22:10:00","ultima_medicao":0,"1_hora":0,"24_horas":0,"72_horas":0,...}`.

Cobertura e qualidade em 06/11 às ~22h30:
- 15 das 18 estações com leitura nas últimas horas. Três estavam velhas: Campina do Barreto (08:20), Imbiribeira (13:10) e Torreão (16:00), com `1_hora` igual a `"-"`. Esse `"-"` é ausente, nunca zero (RN-02).
- Dos 40 cadastros do Recife, só cerca de 15 estão `atualizada`; o resto está desatualizado, em manutenção ou é pluviômetro convencional com leitura manual.
- Confiabilidade: alta como fonte oficial, mas o equipamento falha (a carga histórica já encontrou meses de falha e picos suspeitos). Disponibilidade da API não tem garantia nenhuma.
- Esforço: baixo (conector já existe).

### 2.2 INMET

| Item | Resultado |
|---|---|
| `https://apitempo.inmet.gov.br/estacoes/T` | OK sem token. A301 RECIFE `Operante` (668 estações no país) |
| `https://apitempo.inmet.gov.br/estacao/{ini}/{fim}/A301` | **204 sem conteúdo** também em 06/11. Sem token não há dado observado. Fluxo do token institucional: não confirmado |
| `https://apiprevmet3.inmet.gov.br/avisos/ativos` | OK, sem token (já integrado) |
| `https://apiprevmet3.inmet.gov.br/previsao/2611606` | OK, sem token. Previsão por dia e período (manhã/tarde/noite): `temp_max`, `temp_min`, vento, resumo, ícone em base64. Não é horária |
| `https://portal.inmet.gov.br/uploads/dadoshistoricos/2025.zip` | Baixa (HTTP 200, `application/zip`). Dados horários históricos das estações automáticas, um CSV por estação, defasado (o ano corrente costuma ficar incompleto). Conteúdo do A301 não foi aberto neste teste |
| `https://sisam.inmet.gov.br`, `https://alertas2.inmet.gov.br/` | Não responderam |

Licença: dados públicos, citar INMET. Limite: não declarado. Confiabilidade alta; esforço: baixo para previsão, médio para histórico em ZIP, desconhecido para o token. Risco: a estação A301 é a única do INMET no Recife, então não dá temperatura por distrito.

### 2.3 Cemaden

| Item | Resultado |
|---|---|
| `https://painelalertas.cemaden.gov.br/wsAlertas2` | OK, JSON público, nacional (já integrado) |
| `https://resources.cemaden.gov.br/graficos/interativo/getJson2.php?uf=PE` | OK, JSON público com 440 estações de PE, 24 do Recife (`codibge` 2611606). Traz só `ultimovalor` e a data; todos os `acc1hr … acc96hr` vêm `"-"`, e várias estações com data antiga (ex.: Brega e Chique em 28/06/26; Ibura em 30/10/26). Endpoint **não documentado**, de uso interno do mapa |
| `https://sws.cemaden.gov.br/PED/rest/pcds-cadastro/docs` e `mapservices…/MapaInterativo/rest/pcds/pluviometros` | 404 |
| `alertadoscemaden.cemaden.gov.br` | Não respondeu |

Conclusão honesta: não encontrei API oficial pública e documentada do Cemaden para pluviômetros. A busca na web também não achou documentação. A rota viável é a que já usamos: o Cemaden republicado pela APAC. A API oficial parece exigir cadastro e solicitação ao órgão (pergunta aberta; não verificado). O `getJson2.php` não traz acumulados e não é contrato estável: não usar como fonte principal.

### 2.4 Defesa Civil Nacional (IDAP)

Feed CAP `https://idapfile.mdr.gov.br/idap/api/rss/cap` já integrado: público, sem token, Atom/CAP 1.2, ~15 MB, guarda ~12 h. Confiável como canal oficial, pesado, e o tempo de retenção curto exige coleta frequente. Esforço: já feito. Não encontrei API do COP Recife nem da Defesa Civil do Recife; não testei (pergunta aberta).

### 2.5 Open-Meteo

Todos testados sem chave em 06/11. Licença CC-BY 4.0; o plano gratuito é para uso não comercial (limites públicos de uso, na casa de 10 mil chamadas por dia; conferir a página de preços). Um painel de órgão público de saúde provavelmente se enquadra, mas vale registrar a decisão num ADR.

| Endpoint | Resultado |
|---|---|
| `api.open-meteo.com/v1/forecast` com `soil_moisture_0_to_1cm`, `1_to_3cm`, `3_to_9cm`, `9_to_27cm`, `temperature_2m`, `current=` | OK. Horário. Em 06/11 06h, solo 0,149 m³/m³ nas camadas rasas e 0,309 a 9–27 cm; 27,0 °C |
| `archive-api.open-meteo.com/v1/archive` com `soil_moisture_0_to_7cm`, `7_to_28cm`, `temperature_2m` | OK (ERA5-Land; em 20/10: 0,155 e 0,324; 29,9 °C). Atraso de ~5–7 dias |
| `historical-forecast-api.open-meteo.com/v1/forecast` | OK. Guarda as previsões antigas dos modelos, útil para validar previsão contra chuva medida |
| `ensemble-api.open-meteo.com/v1/ensemble` | OK (`ecmwf_ifs025`, membros 01..N). Serve para faixa de incerteza, nunca para percentual de risco (RN-06) |
| `satellite-api.open-meteo.com/v1/archive` | OK, mas só radiação solar; não traz chuva |

Natureza do dado: tudo é modelo ou reanálise, não medida. Chuva do modelo pode errar a posição e a intensidade de células convectivas. Confiabilidade: boa como tendência, ruim como "chuva que caiu em um bairro". Esforço: baixo (já há dois conectores).

### 2.6 CPTEC/INPE, REDEMET, ANA e satélite

| Fonte | Resultado do teste | Observação |
|---|---|---|
| CPTEC `servicos.cptec.inpe.br/XML/estacao/SBRF/condicoesAtuais.xml` | Responde, mas todos os campos vêm `undefined` e atualização `00/00/0000` | Sem dado útil para o Recife |
| BrasilAPI (espelho CPTEC) `/api/cptec/v1/clima/previsao/244/1` | Responde (retornou São Paulo para o id 244; id do Recife não testado) | Terceiro, sem garantia; previsão diária apenas |
| REDEMET `api-redemet.decea.mil.br` | 403 sem chave; `api.redemet.aer.mil.br` não respondeu | Exige chave gratuita via cadastro (não criada). Teria METAR do aeroporto SBRF (temperatura e umidade horárias observadas). Não verificado |
| ANA telemetria/Hidroweb | `dadosabertos.ana.gov.br` responde; `hidro.ana.gov.br` não respondeu | Já há ficha `ana-telemetria`; nível de rio, não meteorologia |
| NASA IMERG/GPM | Não testado | Exige login Earthdata (conta); fora do escopo sem conta |
| CHIRPS, INPE MERGE | Não testados | Públicos e gratuitos pelo que se sabe, mas diários, em grade de ~5–10 km e com atraso de dias. Não resolvem hora nem bairro; só serviriam para conferir o acumulado |

## 3. Recomendação priorizada

### 3.1 Chuva observada horária por distrito

1. Fonte: `/precipitacao_acumulada` da APAC, já coletada a cada 10–15 min. Não existe série horária histórica medida para o Recife em fonte aberta (a rota horária da APAC vem vazia para a cidade).
2. Como: gravar na silver cada leitura única (`lida_em`, `ultima_medicao`) e somar por hora local por estação; para o distrito, usar a mediana ou a média das estações com leitura válida naquela hora e mostrar quantas estações entraram. A série só existe a partir do momento em que a coleta começou; é preciso dizer isso na tela e jamais preencher o passado com o modelo. Hora com leitura faltando é "ausente", não zero. Se a estação ficou sem leitura por mais de 120 min, ela sai da conta (regra de frescor já adotada).
3. Cuidados: `1_hora` vem `"-"` em estações desatualizadas; `ultima_medicao` representa o último intervalo da estação (confirmar o passo, 10 min, com a APAC); bairros sem estação herdam o distrito, e distrito sem estação válida mostra "Dados insuficientes" com a fonte que falta (RN-01).
4. Esforço: baixo a médio (nova agregação gold; sem conector novo). Risco: lacunas por indisponibilidade da API e por estações em manutenção.

### 3.2 Acumulado observado de 72 h

1. Usar `72_horas` de cada estação (já está em `janela_h=72` na silver), com a regra de frescor existente.
2. Para cada distrito mostrar o acumulado observado, o número de estações válidas e a hora da última leitura. Como controle de qualidade, comparar com a soma dos três últimos dias de `apac_chuva_diaria` e sinalizar divergência grande.
3. Esforço: baixo (dado já coletado; falta a gold por distrito e a tela). Risco: estação com `72_horas` zero por falha de equipamento; as regras de falha e suspeito do histórico devem ser reaproveitadas.

### 3.3 Umidade do solo e saturação

Não achei medida pública no Recife. Recomendação: Open-Meteo, camadas `soil_moisture_0_to_1cm` até `9_to_27cm` (previsão e histórico), mostradas como "estimativa de modelo" com selo experimental (RN-11). Para virar classe (seco, úmido, saturado), comparar com o histórico do próprio ponto (percentis desde 2021 pelo arquivo ERA5-Land) em vez de usar valor absoluto. Um proxy complementar que já é medido: o acumulado de 72 h e 120 h da APAC. Esforço: baixo a médio. Risco: o modelo tem resolução de dezenas de km e não conhece solo urbano impermeabilizado; não dá para validar sem medida local.

### 3.4 Temperatura

1. Observada: só o INMET A301, e só com token (204 sem ele). Pedir o token institucional (pergunta aberta). Alternativa a investigar: chave gratuita da REDEMET para o METAR de SBRF (não verificado).
2. Hoje, sem token: previsão oficial do INMET (`apiprevmet3/previsao/2611606`, máxima e mínima por período) e previsão horária da APAC (`/previsao_municipio`, após corrigir o código do município), mais Open-Meteo como modelo. Rotular sempre como "previsão" ou "modelo", nunca como temperatura medida.
3. Esforço: baixo (previsão), médio (token, em prazo incerto).

### 3.5 Alertas oficiais

1. Manter as quatro origens já integradas (APAC, INMET, Cemaden, IDAP), cada uma com origem, hora de emissão, validade e território, como já está no dicionário. O sistema repete o que o órgão publicou, com link, e não cria nem reclassifica aviso (RN-05). A equipe é quem declara o estágio.
2. Acrescentar como contexto, e não como alerta: a tendência de chuva da APAC (`/tendencia_precipitacao`, mesorregião Metropolitana, com `data_atualizacao`) e as imagens do radar (`/radar_meteorologico`), sempre com a fonte e a hora da imagem.
3. Observações: o filtro do Recife da APAC é por mesorregião, então um aviso para "Metropolitana" vale para vários municípios e deve ser exibido assim; o aviso de umidade baixa em vigor hoje não é alerta de chuva. O feed do IDAP guarda ~12 h e pesa ~15 MB.
4. Esforço: baixo. Risco: origem fora do ar aparece como `origem_indisponivel`, nunca como "sem alerta".

## 4. Perguntas abertas sugeridas (para `docs/perguntas-abertas.md`)

- A APAC autoriza uso da API em produção, com limite de chamadas e cadência de 10–15 min? Qual é o passo de `ultima_medicao`?
- Como obter o token do INMET (apitempo) e a API oficial de pluviômetros do Cemaden para o Vigidesastres?
- Por que `/previsao_municipio` da APAC devolve código 2612000 para o Recife e "Pombos" para 2611606?
- O Open-Meteo gratuito é aceitável para o painel (uso não comercial), ou será preciso plano pago ou fonte alternativa?
- Existe canal de dados do COP Recife ou da Defesa Civil municipal (CAP ou API) além do IDAP nacional?

## 5. O que não foi possível confirmar

API oficial do Cemaden; fluxo do token INMET; conteúdo das planilhas históricas do INMET para A301; REDEMET (exige chave); NASA IMERG (exige conta); CHIRPS e MERGE (não testados); qualquer fonte do COP Recife; limites e termos formais da APAC. Nenhum desses itens foi dado como disponível.
