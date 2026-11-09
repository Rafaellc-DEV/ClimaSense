# APAC — nível dos rios e reservatórios do Capibaribe (ANA como segunda fonte)

Duas fontes no mesmo verbete, porque usam a mesma API e a mesma lógica de frescor:

| Identificador | Conteúdo |
|---|---|
| `apac-rios` | nível em cm de 8 estações de rio (Capibaribe, Tapacurá, Jaboatão, Duas Unas), com os limiares oficiais de cada estação. Segunda fonte da estação 39187800: ANA (telemetria legado) |
| `apac-reservatorios` | cota, volume e status oficial de 4 reservatórios (Tapacurá, Goitá, Carpina e Matriz da Luz) |

- **Situação:** Implementadas (verificadas em 06/11/2026, 22h58, hora do Recife; ligadas a RF-12.10, RN-01, RN-02, RN-06, RN-11, RF-19)
- **Acesso:** API pública da APAC, sem cadastro: `https://api.apac.pe.gov.br/api.php`. Erro vem como `{"erro": ...}` com HTTP 200
  e vira falha explicada na execução. ANA: `https://telemetriaws1.ana.gov.br/ServiceANA.asmx` (GET, XML, sem token).
- **Licença:** nenhuma declarada na API da APAC (pergunta P-33); citar "APAC". Dados abertos da ANA; licença exata do serviço a confirmar.
- **Cadência real:** o ETL roda a cada 10–15 min (`etl tempo-real`, `apac-rios`) e uma vez por `atualizar` (`apac-reservatorios`,
  leitura diária). As estações publicam a cada 15 min (ANA/SGB) a 1 h (Cemaden), **mas a defasagem varia**: às 22h58 de 06/11 a
  APAC estava 30 h atrasada em São Lourenço da Mata (última leitura 05/11 16:15) e 24 h em Paudalho, enquanto a ANA tinha a
  leitura de 06/11 15:15 (cerca de 7,7 h). Por isso a idade de cada leitura vai para a gold; coleta em dia não é leitura em dia.
- **Modos (`etl run apac-rios --modo`):** `24h` (padrão) e `72h` (janela de `/historico_rios`). `--limite N` lê só as N primeiras estações
  e a execução é uma **amostra** (RN-10): cada documento da bronze leva `amostra: true` e `n_estacoes`. Estação que não responde
  também rotula a execução como amostra.
- **Bronze (Mongo Atlas):** `bronze.apac_rios` (documentos com `_origem`: `apac_estacao` = cadastro; `apac_historico` = uma resposta de
  `/historico_rios` por estação e execução, com a lista `leituras`; `ana_telemetria` = linhas do XML da ANA já em dicionário, ou o
  `erro` se a ANA falhou) e `bronze.apac_reservatorios` (um documento por reservatório da bacia do Capibaribe, 14 na gravação).
  Acumulativas, com `_execucao_id` (RN-09).
- **Silver (Postgres):** `silver.rios_estacoes`, `silver.rios_leituras`, `silver.reservatorios`, `silver.reservatorios_leituras`,
  `silver.rio_referencia_territorio` (vazia).
- **Gold:** `gold.rio_situacao` (uma linha por estação cadastrada) e `gold.reservatorio_situacao` (uma linha por reservatório).
- **Migração:** `0020_hidrologia.py`. O papel `climasense_app` só tem SELECT nas sete tabelas.

## Estações de rio

Confirmadas em 06/11/2026 (`GET /estacoes_rios` e `GET /historico_rios?periodo=24h`):

| Código | Estação | Rio | Bacia | Município(s) | Resposta em 24 h |
|---|---|---|---|---|---|
| `39187800` | São Lourenço da Mata (ANA/SGB) | Rio Capibaribe | Capibaribe | Camaragibe, **Recife**, São Lourenço da Mata | 48 pontos (também na ANA) |
| `39150010` | Paudalho | Rio Capibaribe | Capibaribe | Paudalho, São Lourenço da Mata | 93 pontos |
| `39145010` | Limoeiro | Rio Capibaribe | Capibaribe | Limoeiro | 72 pontos |
| `39130010` | Toritama | Rio Capibaribe | Capibaribe | Toritama | 12 pontos |
| `39170000` | Vitória de Santo Antão | Rio Tapacurá | Capibaribe | Vitória de Santo Antão | **lista vazia** (sem dado recente) |
| `260790115` | Jaboatão dos Guararapes (Vila Natal) (Cemaden) | Rio Jaboatão | GL2 | Jaboatão dos Guararapes | 24 pontos |
| `260790119` | Jaboatão dos Guararapes (Centro) (Cemaden) | Rio Duas Unas | GL2 | Jaboatão dos Guararapes | 19 pontos |
| `39189560` | Moreno | Rio Jaboatão | GL2 | Jaboatão dos Guararapes, Moreno | **lista vazia** |

Só a 39187800 tem o Recife (código IBGE 2611606) no cadastro, e ela fica **em São Lourenço da Mata, a montante da cidade**: não é nível
de bairro. Não há estação de nível dentro do Recife nem em Beberibe, Tejipió, Jordão ou Pina (P-33, P-35, P-37). A lista de estações está
em `ESTACOES_INICIAIS` (`etl/conectores/apac_rios.py`); incluir outra é um item novo do cliente.

### Campos: cadastro (`/estacoes_rios`) → `silver.rios_estacoes`

| Campo da fonte | Coluna | Observação |
|---|---|---|
| `cod_estacao` | `codigo` | chave; casa com `ESTACOES_INICIAIS` |
| `nome_estacao`, `nome_rio`, `bacia_hidrografica`, `municipios` | `nome`, `rio`, `bacia`, `municipios` | texto com UTF-8 lido como Latin-1 é consertado; com bytes perdidos (U+FFFD) vale o nome canônico do conector. A APAC publica em maiúsculas (`RIO CAPIBARIBE`) |
| `cod_municipio` (`2603454;2611606;2613701`) | `codigos_municipio`, `inclui_recife` | `inclui_recife` = contém 2611606 |
| `latitude`, `longitude` | `lat`, `lon` | |

### Campos: leitura (`/historico_rios`) → `silver.rios_leituras`

| Campo da fonte | Coluna | Observação |
|---|---|---|
| `data_hora` | `lida_em` | hora local do Recife (UTC−3), gravada em UTC. **Data futura é descartada** (tolerância de 15 min de relógio adiantado) |
| `nivel_atual` | `nivel_cm` | centímetros. `-`, vazio, texto e negativo = ausente, a leitura é descartada (RN-02). Zero medido é zero |
| `nivel_pre_alerta`, `nivel_alerta`, `nivel_alerta_enchente` | `pre_alerta_cm`, `alerta_cm`, `enchente_cm` | **limiares oficiais da estação**, guardados com cada leitura. Só valem completos, positivos e em ordem crescente; senão ficam nulos na leitura (o nível fica) e a execução registra `limiares_invalidos` em `avisos` |
| `alerta_pcd` | `alerta_pcd` | `S` ou `N`, informado pela estação; **não é usado** na classe (a classe vem dos limiares) |
| `recente` | `recente` | 0 ou 1 da APAC, sem uso |
| ANA: `DataHora`, `Nivel`, `Vazao` | `lida_em`, `nivel_cm`, `vazao_m3s` | `fonte = 'ana'`; sem limiares. `Chuva` não é lida |
| (coleta) | `coletado_em`, `visto_em`, `execucao_id` | `visto_em` é a última coleta que viu a leitura |

Uma leitura não se repete: chave (`estacao_codigo`, `fonte`, `lida_em`). Os limiares atuais podem mudar sem aviso na API; a silver guarda os de cada leitura.

### ANA como segunda fonte

Só para a 39187800 (`ANA_ESTACOES`). A ANA entrega a mesma série (177 cm nas duas em 06/11), mais fresca, e **não tem limiares**:
a classe usa o nível mais recente entre as duas fontes e os limiares da APAC. Se a ANA falhar (rede, XML inválido, XML com DTD,
que é recusado), a execução segue só com a APAC e `avisos.ana_falhou` conta a falha. **Serviço legado** (ASP.NET, host `telemetriaws1`): a ANA
migra para o HidroWebService novo (token, ver `ana-telemetria.md`) e pode desligar este sem aviso.

## Classe do rio (`gold.rio_situacao`)

Uma linha por estação cadastrada em `silver.rios_estacoes`. Regra (RN-06: classe, nunca percentual):

| `classe` | Quando |
|---|---|
| `abaixo_pre_alerta` | nível < pré-alerta |
| `pre_alerta` | pré-alerta ≤ nível < alerta |
| `alerta` | alerta ≤ nível < enchente |
| `enchente` | nível ≥ enchente |
| `dados_insuficientes` | sem leitura, leitura com mais de 12 h, ou sem limiares válidos. `motivo` diz qual: `sem_leitura`, `leitura_antiga`, `sem_limiares` |

Colunas: `estacao_codigo`, `nome`, `rio`, `bacia`, `municipios`, `inclui_recife`, `lat`, `lon`, `classe`, `motivo`, `nivel_cm`,
`pre_alerta_cm`, `alerta_cm`, `enchente_cm`, `lida_em` (hora da leitura), `fonte_leitura` (`apac` ou `ana`, a leitura mais recente; em empate, a APAC),
`fontes` (as duas, quando há leituras das duas), `referencia_em`, `idade_min`, `desatualizada`.

- **Idade** = `referencia_em` (última coleta, `max(visto_em)`) menos `lida_em`, em minutos. Não usa `now()`, para a gold ser reproduzível
  (`etl verificar-gold`). A API soma o tempo desde `referencia_em` se quiser a idade na hora da consulta.
- **Limites de idade (em `gold.RIOS_SITUACAO`):** mais de 2 h = `desatualizada` (a tela escreve "Leitura desatualizada" com a hora);
  mais de 12 h = `dados_insuficientes`, `motivo = leitura_antiga`. Em 06/11, às 22h58, São Lourenço da Mata (via ANA, 7,7 h) tinha classe;
  Paudalho (APAC, 24 h) não.
- Estação sem classe mantém `nivel_cm` e `lida_em` da última leitura só para a tela dizer "última leitura há N h"; **não é nível atual** e
  nunca deve ser mostrado como "nível baixo" ou "sem risco" (RN-01).
- Texto da tela: "Rio Capibaribe, São Lourenço da Mata: 177 cm, abaixo do nível de pré-alerta (250 cm). Fonte: ANA/APAC. Atualizado em 06/11/2026 15:15."
  Sem classe: "Dados insuficientes. Falta: leitura de nível da estação [nome] (fonte: APAC/ANA)."

## Ligação rio ↔ território: não existe

`silver.rio_referencia_territorio` (`territorio_id`, `estacao_codigo`, `base_documental`, `decidido_em`) **nasce vazia** e nada a preenche.
Dizer que um bairro "está no Capibaribe" ou inferir inundação por território exige base documentada (por exemplo as faixas hídricas de
`territorio-oficial`) e uma decisão em ADR, com o selo **Experimental** (RN-11) até haver validação temporal. Pergunta P-49. Beberibe, Tejipió,
Jordão e Pina não têm estação: "Dados insuficientes. Falta: estação de nível no rio [nome]".

## Reservatórios — `GET /reservatorio?bacia_hidrografica=Capibaribe`

A resposta traz a bacia inteira (14 reservatórios em 06/11/2026); o conector guarda na silver só os quatro abaixo, casados por
`codigo_estacao` (nunca pelo nome). O restante fica na bronze. Varzea do Una tem `codigo_estacao: 0` e não entra.

| `codigo_estacao` | Reservatório | Município (APAC) | Leitura de 06/11/2026 |
|---|---|---|---|
| `39175000` | Tapacurá | São Lourenço da Mata | 95,36 % (ENTRE 80% e 100%), cota 102,48 m, 104,87 hm³ |
| `39151000` | Goitá | Paudalho | 38,2 % (ENTRE 30% e 80%) |
| `39145550` | Carpina (Lagoa do Carro) | Lagoa do Carro | 24,12 % (ENTRE 10% e 30%) |
| `39187900` | Matriz da Luz | São Lourenço da Mata | 100,2 % (VERTENDO) |

| Campo da fonte | Coluna (`silver.reservatorios_leituras`) | Observação |
|---|---|---|
| `data_leitura_cota_atual` | `data_leitura` | só a data. **Data futura é descartada** (a APAC já devolveu `2026-11-12` no histórico); sem data, descartada |
| `cota_atual`, `volume_atual`, `volume_percentual` | `cota_m`, `volume_m3`, `volume_pct` | negativo = ausente |
| `status`, `cor_status_reservatorio` | `status`, `cor` | status oficial; texto quebrado vira nulo |
| `capacidade`, `latitude`, `longitude`, `uso_principal` | `silver.reservatorios` | cadastro |

Chave (`codigo_estacao`, `data_leitura`). Acentos: o `/reservatorio` já devolveu `S�o Louren�o` (bytes perdidos); nome e município vêm da tabela
canônica `RESERVATORIOS` quando isso acontece, e UTF-8 lido como Latin-1 é consertado.

### Situação (`gold.reservatorio_situacao`)

`situacao`: `vertendo`, `entre_80_e_100`, `entre_30_e_80`, `entre_10_e_30`, `colapso` (o status oficial) ou `dados_insuficientes` (`motivo`:
`sem_leitura`, `leitura_antiga` se a leitura tem mais de 3 dias, `status_desconhecido`). Colunas: `codigo_estacao`, `nome`, `municipio`, `bacia`,
`capacidade_m3`, `data_leitura`, `cota_m`, `volume_pct`, `status`, `situacao`, `motivo`, `referencia_em`, `idade_dias`. "Colapso" é o termo da APAC
para volume abaixo de 10 %, não é risco de ruptura. É **contexto da bacia, não previsão** de inundação.

## Frescor

- `apac-rios`: 3 h (`etl/frescor.toml`). Mede a última **coleta** bem-sucedida (o ETL roda a cada 15 min; 3 h = deixou de coletar). Não mede a idade
  da leitura: leitura de rio com mais de 12 h já sai como "Dados insuficientes" na gold e com mais de 2 h aparece como "desatualizada".
- `apac-reservatorios`: 30 h. A leitura é diária e vem só com a data; mais de 3 dias de idade vira "Dados insuficientes" na gold.
- Sem coleta registrada, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).

## Limitações

- Nenhuma fonte é nível dentro do Recife nem mancha de inundação por bairro.
- A APAC pode estar muito mais atrasada que a ANA na mesma estação; sem a ANA (só a 39187800 tem), uma estação atrasada fica sem classe.
- Estações 39170000 e 39189560 estão cadastradas, mas voltam lista vazia: aparecem como "Dados insuficientes: sem leitura".
- API sem termos, limite de chamadas ou SLA (P-33); ANA legado sem garantia de continuidade.
- Chamadas por ciclo de `apac-rios`: 1 (cadastro) + 8 (histórico) + 1 (ANA); `apac-reservatorios`: 1.
