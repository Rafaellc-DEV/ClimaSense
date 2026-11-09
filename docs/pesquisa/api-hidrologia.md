# Pesquisa de fontes reais: hidrologia (nível de rios e canais, possibilidade de inundação)

Data da pesquisa: 06/11/2026 (testes feitos às 22h44, hora do Recife, só com GET públicos, sem cadastro).
Escopo: Recife e bacias do Capibaribe, Beberibe, Tejipió, Jordão e Pina. Ligado a RF-12.10, RN-01, RN-02, RN-06, RN-11, RF-19.

## 1. Resumo

- **Achado principal:** a API pública da APAC que o ClimaSense já usa para chuva (`https://api.apac.pe.gov.br/api.php`) também expõe **nível de rios e reservatórios**: `/estacoes_rios`, `/historico_rios` e `/reservatorio`. Sem cadastro, JSON, CORS aberto. É a menor integração possível (mesmo host, mesmo padrão de erro do conector `apac-chuva`).
- **Segundo achado:** o web service antigo da ANA (`telemetriaws1.ana.gov.br/ServiceANA.asmx`) **responde sem autenticação** com a lista de estações telemétricas e as leituras de nível/vazão/chuva. Serve de redundância e de fonte mais fresca. O HidroWebService novo (REST) exige token; a doc interna (`ana-telemetria.md`) que diz "exige cadastro" vale só para o novo.
- **Cobertura no Recife é pequena e rio acima.** Existe **uma** estação de nível no Capibaribe cujo município inclui Recife: `39187800` São Lourenço da Mata (ANA/SGB), a montante da cidade. Não achei estação pública de nível dentro do Recife, nem em Beberibe, Tejipió, Jordão ou Pina. Há duas estações do Cemaden em Jaboatão (rios Jaboatão e Duas Unas, bacia GL2, vizinha ao Jordão/Tejipió).
- **Não existe** (verificado) boletim público do SGB para o Capibaribe: o SACE do SGB monitora 19 bacias e em Pernambuco só o Mundaú. Os dados abertos do Recife não têm conjunto de sensores de nível de canais.
- Tudo é nível em ponto de rio, **não** mancha de inundação por bairro. "Possibilidade de inundação" por território só dá para mostrar como **situação do rio de referência** (níveis de atenção/alerta/inundação da própria estação) mais chuva, e deve levar o selo "Experimental" (RN-11).

## 2. O que já está integrado e o que falta

Lido em `docs/dicionario-dados/ana-telemetria.md`, `cemaden.md`, `apac-chuva.md` e `docs/apis-e-etl.md`.

| Fonte | Estado hoje | Hidrologia |
|---|---|---|
| `apac-chuva` | real, 19 pluviômetros do Recife (APAC + Cemaden) | só chuva. **Nenhum endpoint de rio ou reservatório usado.** |
| `alertas-oficiais` | real (APAC `/alertas`, INMET, Cemaden `wsAlertas2`, IDAP CAP) | já traz avisos, inclusive "Risco Hidrológico" do Cemaden, filtrados por Recife. Não traz nível. |
| `ana-telemetria` | planejado, "exige cadastro", conector falha com "Conector planejado" | nada |
| `cemaden` | planejado, "API restrita" | nada além da chuva que chega via APAC |
| `recife-alagamento` | real, histórico 2014 a 2024 da Defesa Civil | rótulo fraco de alagamento, não é nível |
| `open-meteo-mare` | real, maré prevista | influencia drenagem em Recife (remanso de maré) |

Falta: nível dos rios, cota de referência (atenção, alerta, inundação), situação dos reservatórios que controlam o Capibaribe (Tapacurá, Goitá, Carpina) e a ligação rio-território.

## 3. Fontes testadas

### 3.1 APAC, rios: `/estacoes_rios` e `/historico_rios` (RECOMENDADA)

- **URL base:** `https://api.apac.pe.gov.br/api.php` (Swagger: `https://api.apac.pe.gov.br/swagger.json`, tag "Monitoramento Hidrológico", API de Dados da Apac v2.0).
- **Endpoints:**
  - `GET /estacoes_rios` (filtros `cod_estacao`, `nome_estacao`): 36 estações de rios em PE (Una 10, Goiana 6, Sirinhaém 5, Capibaribe 5, Ipojuca 4, Mundaú 3, GL2 3).
  - `GET /historico_rios?cod_estacao=<cod>&periodo=24h|72h|7d|1m|3m|6m|1y|integral` (ou `data_inicio`/`data_fim`). Retorna nível, limiares e `alerta_pcd`. A descrição da doc diz "nível, vazão e chuva"; nas respostas que vi só vieram nível e limiares.
- **Autenticação:** nenhuma para esses GET (existe `/login` POST, não precisei). **CORS:** `access-control-allow-origin: *`.
- **Formato:** JSON. Erro como `{"erro": "..."}` com HTTP 200 (igual ao `apac-chuva`). Texto com acentos às vezes em Latin-1 mal convertido no `reservatorio` (ver 3.3); em `estacoes_rios` veio UTF-8 correto.
- **Frequência:** pontos a cada 15 min na estação ANA; a cada 30 a 60 min nas do Cemaden. A **defasagem varia**: na consulta de 22h44 (local) a última leitura de `39187800` na APAC era de 05/11 16:15, ou seja, cerca de 30 h de atraso, enquanto a mesma estação na ANA (3.2) tinha 06/11 15:15. Tratar `recente`, `data_hora` e idade da leitura como obrigatórios (RN-01).
- **Cobertura no Recife e vizinhança:**

| Código | Estação | Rio | Município(s) | Lat, lon |
|---|---|---|---|---|
| `39187800` | São Lourenço da Mata (ANA/SGB) | Rio Capibaribe | Camaragibe, Recife, São Lourenço da Mata (IBGE 2611606 incluso) | -7.998611, -35.0392 |
| `39150010` | Paudalho | Rio Capibaribe | Paudalho, São Lourenço da Mata | -7.894167, -35.173333 |
| `39145010` | Limoeiro | Rio Capibaribe | Limoeiro | -7.878889, -35.451944 |
| `39130010` | Toritama | Rio Capibaribe | Toritama | -8.012778, -36.057778 |
| `39170000` | Vitória de Santo Antão | Rio Tapacurá (afluente do Capibaribe) | Vitória de Santo Antão | -8.113611, -35.283889 |
| `260790115` | Jaboatão (Vila Natal), Cemaden | Rio Jaboatão | Jaboatão dos Guararapes | -8.108782, -34.999402 |
| `260790119` | Jaboatão (Centro), Cemaden | Rio Duas Unas | Jaboatão dos Guararapes | -8.111846, -35.013613 |
| `39189560` | Moreno | Rio Jaboatão | Jaboatão, Moreno | -8.119583, -35.106083 |

  `39189560` e `39170000` voltaram **lista vazia** em `historico_rios?periodo=24h`: estação cadastrada sem dado recente. Beberibe, Tejipió, Jordão e Pina **não aparecem** em nenhuma estação.
- **Exemplo REAL (estação 39187800, `periodo=24h`, 48 pontos, último ponto retornado):**

```json
{"cod_estacao":"39187800","nome_estacao":"SÃO LOURENÇO DA MATA (ANA/SGB)","nome_rio":"RIO CAPIBARIBE",
 "data_hora":"2026-11-05 16:15:00","data_coleta":"2026-11-05","hora_coleta":"16:15:00",
 "nivel_atual":"179.00","nivel_pre_alerta":"250","nivel_alerta":"300","nivel_alerta_enchente":"400",
 "alerta_pcd":"N","recente":0}
```

  Unidade: centímetros (179 cm contra pré-alerta 250, alerta 300, enchente 400). Faixa observada nas 24 h: 177 a 179 cm, bem abaixo do pré-alerta. Outros exemplos reais: Paudalho 189 cm (limiares 300/350/450); Jaboatão Vila Natal 183,4 cm (320/340/440); Duas Unas 138,8 cm (200/230/330).
- **Licença/termos:** nenhuma declarada na API (mesma situação do `apac-chuva`); citar "APAC". Limite de uso: não documentado; usar a cadência do ETL (15 min) e cache.
- **Confiabilidade:** média. Fonte oficial estadual, com limiares oficiais por estação (valioso), mas atraso variável e estações sem dado. Esforço de integração: **baixo** (reaproveita `ConectorApacChuva`, `silver.estacoes`).
- **Riscos:** atraso de leitura, limiares estáticos que podem mudar sem aviso, `erro` com HTTP 200, texto com codificação irregular, API sem SLA e sem termos escritos (pedir confirmação por escrito à APAC, registrar em `perguntas-abertas.md`).

### 3.2 ANA, telemetria: web service antigo `ServiceANA.asmx` (RECOMENDADA como redundância)

- **URLs (GET, sem token):**
  - Inventário: `https://telemetriaws1.ana.gov.br/ServiceANA.asmx/ListaEstacoesTelemetricas?statusEstacoes=0&origem=0`
  - Dados: `https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos?codEstacao=39187800&dataInicio=06/11/2026&dataFim=06/11/2026`
- **Autenticação:** nenhuma (HTTP 200). **Formato:** XML (DataSet .NET; 5.400 linhas, ~4 MB o inventário nacional; filtrar por `CodEstacao`). Colunas de dados: `CodEstacao, DataHora, Vazao, Nivel, Chuva`.
- **Frequência:** 15 min (último ponto às 15:15 do mesmo dia na consulta das 22h44; atraso de cerca de 7 h, aceitável, a checar em produção).
- **Cobertura:** inventário traz as mesmas estações do Capibaribe da APAC (`39100000` Santa Cruz, `39130010`, `39145010`, `39150010`, `39187800`, `39167000`, `39170000`) e os açudes Cursaí, Goitá, Tapacurá, Carpina, Matriz da Luz, Duas Unas (Jaboatão), Pirapama/Gurjaú. **Sem estação no município do Recife** e sem limiares de alerta (a ANA entrega só a série; os limiares vêm da APAC).
- **Exemplo REAL:**

```xml
<DadosHidrometereologicos><CodEstacao>39187800</CodEstacao><DataHora>2026-11-06 15:15:00 </DataHora>
<Vazao>1.19</Vazao><Nivel>177.00</Nivel><Chuva>0.00</Chuva></DadosHidrometereologicos>
```

  Mesma cota (177 cm) que a APAC mostra, o que confirma que a APAC republica a telemetria ANA/SGB.
- **Licença:** dados abertos da ANA (política de dados abertos; confirmar a licença exata do serviço). Limite: não documentado.
- **Confiabilidade:** alta na origem (RHN/SGB). **Mas** é um serviço legado (ASP.NET, host `telemetriaws1`) que a ANA vem migrando para o HidroWebService novo; pode ser desligado sem aviso. Esforço: **baixo a médio** (parse de XML; sem token).
- **Novo HidroWebService (REST):** `https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas/HidroInventarioEstacoes/v1` e `https://www.snirh.gov.br/hidroweb/rest/api/...` responderam **HTTP 401** ("Token de Autenticação da API Inexistente ou mal Formatado"). Exige cadastro e token (identificador + senha, token de vida curta). Não criei conta. Esforço: médio; só vale se o serviço antigo cair.
- **Riscos:** legado sem garantia, XML grande, sem CORS conhecido (chamar sempre do backend), horário em hora local sem fuso explícito.

### 3.3 APAC, reservatórios: `/reservatorio` e `/historico_reservatorios` (COMPLEMENTAR)

- **URL:** `GET https://api.apac.pe.gov.br/api.php/reservatorio?bacia_hidrografica=Capibaribe` (também `codigo=2611606`, `lat`/`lon`, `codigo_estacao`, `nome_estacao`). Sem autenticação, JSON, CORS aberto.
- **Conteúdo:** capacidade, cota atual, volume, `volume_percentual`, `status` (COLAPSO / ENTRE 10% e 30% / ENTRE 30% e 80% / ENTRE 80% e 100% / VERTENDO), cor, data da leitura, qualidade da água. O `historico_reservatorios` traz também `cota_vertedouro` e `per_volume_vertedouro`.
- **Cobertura relevante ao Recife (bacia Capibaribe, 15 reservatórios na consulta):** Tapacurá (`39175000`, 104,9 hm³), Goitá (`39151000`, 52,9 hm³), Carpina/Lagoa do Carro (`39145550`, 255,4 hm³), Cursaí (`39146000`), Matriz da Luz (`39187900`). Sem reservatório em Beberibe (consulta voltou `[]`).
- **Exemplo REAL (Tapacurá):**

```json
{"reservatorio":"TAPACURA","municipio":"São Lourenço da Mata","codigo_estacao":39175000,"capacidade":104870609,
 "volume_percentual":95.36,"status":"ENTRE 80% e 100%","data_leitura_cota_atual":"2026-11-06"}
```

  Em 06/11/2026: Tapacurá 95,36% (cota 102,48 m, vertedouro 103 m), Goitá 38,2%, Carpina 24,12%, Matriz da Luz 100,2% (VERTENDO).
- **Por que importa:** o Capibaribe a montante do Recife é controlado por Carpina e Goitá (barragens de contenção de cheias) e Tapacurá é afluente. Reservatório cheio e vertendo antes da chuva eleva a possibilidade de inundação. Isto é uma **variável de contexto**, não previsão.
- **Atenção:** campo `municipio` e `reservatorio` vieram com bytes quebrados (`S�o Louren�o`, `PO�O FUNDO`): tratar a decodificação (provavelmente Latin-1 gravado como UTF-8 inválido) e casar por `codigo_estacao`. Alguns têm `codigo_estacao: 0` (Várzea do Una); `cota: 154.33` com data futura apareceu em `historico_reservatorios` (Nilo Coelho, `data: 2026-11-12`): **validar datas futuras e descartar**.
- Confiabilidade média; esforço **baixo**; licença e limite como em 3.1.

### 3.4 Cemaden: PCDs hidrológicas, mapa interativo, alertas

- **`https://painelalertas.cemaden.gov.br/wsAlertas2`** (já integrado em `alertas-oficiais`): GET sem autenticação, JSON, 11 alertas nacionais no momento do teste, nenhum de PE. Campos: `cod_alerta`, `datahoracriacao`, `ult_atualizacao`, `codibge`, `evento` (ex.: "Risco Hidrológico - Moderado"), `nivel`, `status`, `uf`, `municipio`, `latitude`, `longitude`. Útil como sinal oficial ("Risco Hidrológico") por município (IBGE 2611606), nunca nível numérico.
- **Dados das PCDs (nível/chuva) do Cemaden:** o mapa interativo (`https://mapainterativo.cemaden.gov.br/`, responde 200, HTML) não tem API documentada publicamente. O endereço `sws.cemaden.gov.br/PED/rest/pcds-dados/...` que tentei retornou **404** e não achei documentação que o confirme. `mapservices.cemaden.gov.br` só aponta de volta para o mapa. **Conclusão honesta: não consegui acesso programático público às PCDs hidrológicas do Cemaden.** As duas estações do Cemaden de rio em Jaboatão chegam hoje pela APAC (3.1).
- Esforço: **alto** e incerto (exigiria pedir acesso/convênio ao Cemaden). Raspar o mapa interativo: **não recomendado** (termos não verificados, risco de bloqueio).

### 3.5 SGB/CPRM: SACE, SAH, boletins

- `https://www.sgb.gov.br/sace/` redireciona (301) para `https://sace.sgb.gov.br/`. "Bacias monitoradas" lista 19 bacias: Amazonas, Paraguai, Doce, Caí, Muriaé, Acre, Madeira, Parnaíba, Taquari, Branco, Xingu, **Mundaú**, Uruguai, das Velhas, Itapecuru, Pomba, São Francisco, Guaíba e Araguaia.
- **Capibaribe, Beberibe, Tejipió, Jordão e Pina não têm sistema de alerta do SGB.** Em Pernambuco só o Mundaú (fora da RMR, próxima a Garanhuns e Alagoas). As URLs `/sace/capibaribe` e `/sace/boletins/Capibaribe/` dão 404. Nenhuma API, links de boletim eram placeholders, sem licença escrita.
- O SGB opera a estação `39187800` pela RHN (dado já chega por ANA/APAC). Confiabilidade da fonte: alta; utilidade para o Recife: baixa. Esforço: não aplicável.

### 3.6 Prefeitura do Recife (dados abertos e sensores municipais)

- Busca no CKAN (`https://dados.recife.pe.gov.br/api/3/action/package_search`) por "nivel", "sensor", "hidrol", "canal", "pluviometro" e "alagamento": **nenhum** conjunto de sensores de nível de canal ou pluviômetro. O único achado relevante é `registro-de-atendimentos-da-defesa-civil` (já integrado). "Equipamentos de monitoramento e fiscalização de trânsito" não é hidrologia.
- Há notícia pública de que a Prefeitura instalou pluviômetros e sensores de alagamento e planejou 8 sensores de vazão e nível na bacia do Tejipió, com dados internos ao COP. Não achei publicação aberta nem API. **Hoje não existe fonte aberta municipal de nível de canal.** O caminho é pedir ao COP/Defesa Civil (registrar em `docs/perguntas-abertas.md`).
- Estudo acadêmico da UFPE (4 estações de nível na macrodrenagem em 2021-2022) é histórico, não é fonte operacional.

### 3.7 INMET

- Para chuva, não nível; a doc interna já registra que a API exige token e devolve 204 sem ele. Meu teste direto de `apitempo.inmet.gov.br` não obteve resposta (timeout, HTTP 000) nesta rede. Sem valor hidrológico novo. Fora do escopo.

## 4. Quadro comparativo

| Fonte | Acesso | Formato | Nível no Recife | Esforço | Confiabilidade |
|---|---|---|---|---|---|
| APAC `/historico_rios` + `/estacoes_rios` | público, CORS aberto | JSON | 1 estação com Recife no município (Capibaribe, rio acima); limiares oficiais | baixo | média |
| ANA `ServiceANA.asmx` | público, sem token | XML | mesma estação, sem limiares | baixo a médio | alta na origem, serviço legado |
| APAC `/reservatorio` | público | JSON | Tapacurá, Goitá, Carpina (contexto da bacia) | baixo | média |
| ANA HidroWebService novo | token | JSON | igual ao legado | médio | alta |
| Cemaden `wsAlertas2` | público | JSON | alerta qualitativo por município | já feito | média |
| Cemaden PCDs/mapa interativo | sem API pública | HTML/mapa | desconhecido | alto | n/d |
| SGB SACE | não cobre | PDF/HTML | nenhuma | n/a | n/a |
| Prefeitura do Recife | sem dado aberto | n/a | nenhuma | n/a | n/a |

## 5. Recomendação priorizada

1. **Conector `apac-rios` (baixo esforço, fazer primeiro).** Mesmo host e padrão do `apac-chuva`. Fluxo: `GET /estacoes_rios` (cadastro: código, rio, bacia, municípios, lat/lon) para `silver.estacoes`; `GET /historico_rios?periodo=24h` por estação de interesse a cada 15 min para uma tabela silver de leituras (`estacao_id`, `lida_em`, `nivel_cm`, e os limiares `pre_alerta`, `alerta`, `enchente` guardados com a leitura); bronze com a resposta bruta. Estações iniciais: `39187800`, `39150010`, `39145010`, `39130010`, `39170000`, `260790115`, `260790119`, `39189560`. Gold: classe por estação (abaixo do pré-alerta, pré-alerta, alerta, enchente) a partir dos limiares oficiais, com `lida_em` e idade da leitura. Ausência ou lista vazia = ausente, nunca zero (RN-02).
2. **Reservatórios (`/reservatorio?bacia_hidrografica=Capibaribe`)**: no mesmo conector ou em `apac-reservatorios`. Mostrar `volume_percentual` e `status` de Tapacurá, Goitá e Carpina como contexto da bacia. Descartar data futura e corrigir a codificação.
3. **ANA legado como segunda fonte da estação `39187800`** (e validação cruzada da APAC). Quando a APAC estiver atrasada e a ANA mais fresca, usar a mais recente e citar as duas. Marcar o conector como "legado, sujeito a descontinuação".
4. **Alertas de Risco Hidrológico do Cemaden** já entram por `alertas-oficiais`; exibir ao lado do nível para o município.
5. **Pedidos formais (perguntas abertas, sem construir):** (a) à APAC, termos de uso e limite da API e se há estações de nível dentro do Recife; (b) ao COP/Defesa Civil do Recife, os sensores de nível do Tejipió; (c) ao Cemaden, acesso às PCDs hidrológicas.

### Como ligar o rio ao território (e o que a tela pode afirmar)

A estação `39187800` tem o município de Recife no cadastro, mas fica em São Lourenço da Mata. Portanto:

- Não é nível "do bairro". Mostrar como **"Rio Capibaribe, estação São Lourenço da Mata (a montante do Recife), leitura de [data e hora]"**, aplicada somente aos territórios que o PRD/equipe definirem como ribeirinhos do Capibaribe. O mapeamento bairro para rio de referência deve vir de fonte documentada (por exemplo as faixas hídricas já carregadas em `territorio-oficial`), com decisão registrada em ADR (próximo número 0015, conforme o CLAUDE.md).
- A classe vem **dos limiares oficiais da estação** (pré-alerta, alerta, enchente), nunca de percentual (RN-06).
- "Possibilidade de inundação" combinando nível, reservatórios e chuva é inferência nossa: leva o selo **Experimental** (RN-11) até haver validação temporal documentada.
- Beberibe, Tejipió, Jordão e Pina: sem nenhum dado.

### Textos para a tela (RN-01, RF-19)

- Com leitura válida: "Rio Capibaribe, São Lourenço da Mata: 179 cm, abaixo do nível de pré-alerta (250 cm). Fonte: APAC/ANA/SGB. Atualizado em 05/11/2026 16:15." Se a leitura tiver mais de um limite de frescor (sugestão: 2 h, a definir em `frescor.toml`), adicionar "Leitura desatualizada".
- Sem leitura (lista vazia, estação parada ou fonte fora do ar): "Dados insuficientes. Falta: leitura de nível da estação [nome] (fonte: APAC/ANA)." Nunca mostrar "nível baixo" nem "sem risco".
- Bacia sem estação (Beberibe, Tejipió, Jordão, Pina): "Dados insuficientes. Falta: estação de nível no rio [nome]. Fonte necessária: sensores de nível do COP/Prefeitura do Recife ou da APAC."
- Possibilidade de inundação no território: "Experimental. Indicador sem validação. Combina a situação do rio de referência e a chuva observada." Sem rio de referência: "Dados insuficientes. Falta: estação de nível no rio que atinge este território."

## 6. Riscos gerais e pendências

- Nenhuma fonte testada é dado de nível **dentro** do Recife nem entrega mancha de inundação.
- APAC: atraso de leitura variável (30 h vista numa estação enquanto a ANA estava com 7 h), sem SLA e sem termos escritos; ANA legado pode sumir; sem captcha ou bloqueio observado; só 1 a 2 requisições por teste, mas confirmar limites antes de rodar a cada 15 min por 8 estações mais reservatórios (cerca de 9 chamadas por ciclo).
- Chamar sempre do backend (ETL); os endpoints da ANA não têm CORS confirmado e a APAC tem CORS aberto, mas centralizar mantém o padrão bronze/silver/gold.
- Não fiz scraping de nenhum portal e não criei contas. Nenhum dado desta pesquisa foi gravado em código ou banco.

## Fontes consultadas

- `https://api.apac.pe.gov.br/swagger.json`, `.../api.php/estacoes_rios`, `/historico_rios`, `/reservatorio`, `/historico_reservatorios`, `/alertas`
- `https://telemetriaws1.ana.gov.br/ServiceANA.asmx` (`ListaEstacoesTelemetricas`, `DadosHidrometeorologicos`)
- `https://www.snirh.gov.br/hidroweb/rest/api/...` e `https://www.ana.gov.br/hidrowebservice/...` (401, exigem token)
- `https://painelalertas.cemaden.gov.br/wsAlertas2`, `https://mapainterativo.cemaden.gov.br/`
- `https://sace.sgb.gov.br/` e `https://sace.sgb.gov.br/index_bacias_monitoradas.php`
- `https://dados.recife.pe.gov.br/api/3/action/package_search`
- Notícias e estudos achados em busca: portaldeprefeitura.com.br (Capibaribe em alerta, jun a jul/2026) e repositórios da UFPE, apenas como contexto.
