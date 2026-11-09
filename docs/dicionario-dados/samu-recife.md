# Dados Abertos do Recife — demanda de urgência do SAMU por semana e bairro

- **Identificador:** `samu-recife`
- **Situação:** Implementada (06/11/2026). Migração 0023.
- **Acesso:** CKAN `https://dados.recife.pe.gov.br/api/3/action/package_show?id=servico-de-atendimento-movel-de-urgencia-samu-<ano>`
  (um conjunto por ano, 2011 a 2026). O CSV "Solicitações de Atendimento `<ano>`" fica em `resources[].url`; o download
  redireciona para o armazenamento do portal. Sem autenticação. O conector lê os 5 anos mais recentes (ano corrente e
  os 4 anteriores, para linha de base sazonal) e nunca antes de 2016: os arquivos de 2011 a 2015 têm outro layout, sem
  `tipo` e `subtipo`.
- **Órgão:** Secretaria de Saúde do Recife, publicação Emprel. **Licença:** ODbL (`odc-odbl`); atribuição obrigatória.
- **Formato:** CSV `;`, UTF-8 (2026: 26 MB, 162.524 linhas; 62.926 do Recife até 31/10). Colunas: `data`,
  `hora_minuto`, `municipio`, `bairro`, `endereco`, `origem_chamado`, `tipo`, `subtipo`, `sexo`, `idade`,
  `motivo_finalizacao`, `motivo_desfecho`. O cabeçalho vem ora entre aspas, ora não; o conector lê por nome.
- **Cobertura:** a central regula o Recife e 17 municípios da região; o conector fica só com `municipio = RECIFE`
  (os outros entram na contagem de descartes como `outro_municipio_da_regulacao`).
- **Atraso:** publicação mensal. Em 06/11/2026 o arquivo ia até 31/10. **Um evento do dia 10 só aparece no início do
  mês seguinte**: serve para retrospectiva em semanas, não para o "durante". O ritmo mensal vem da metadata do CKAN e
  foi visto num único ponto de observação.
- **Cadência:** mensal (`frescor.toml`: 1440 h). O recomendado é rodar `etl run samu-recife` uma vez por mês.

## O que é e o que não é

**É** a demanda de urgência atendida pelo SAMU: chamados com o bairro do chamado (não o da residência). **Não é**
caso de doença nem diagnóstico. Rótulo fixo em qualquer tela ou API: **"demanda de urgência (SAMU)"**. Nunca "casos
de diarreia", "casos de febre" etc. O subtipo é a classificação do regulador no atendimento.

## Minimização (LGPD, RN-13, RNF-03)

Cada linha é um atendimento a uma pessoa, com **endereço, sexo e idade**. O conector lê o CSV em memória, por
**posição de coluna**, e só consulta `data`, `municipio`, `bairro`, `tipo` e `subtipo`. `hora_minuto`, `endereco`,
`origem_chamado`, `sexo`, `idade`, `motivo_finalizacao` e `motivo_desfecho` não são lidos para variável alguma e não
chegam à bronze, à silver nem à gold. A bronze recebe só:

- um resumo por arquivo: `ano`, `url`, `atualizado_em`, `sha256`, `linhas`, `chamados_recife`, `primeiro_dia`,
  `ultimo_dia`, `colunas`, `colunas_individuais_descartadas` (**só os nomes**), `motivos` de descarte;
- contagens `inicio` (domingo da semana epidemiológica) × `bairro_fonte` × `grupo` → `n`.

Teste automatizado: `backend/tests/unit/etl/test_conectores_saude_historico.py::test_samu_nenhum_campo_individual_chega_a_bronze`
põe valores-sentinela em todas as colunas individuais e prova que nenhum sobrevive.

## Grupos

Pelo `subtipo`, sem acento nem diferença de caixa:

| `grupo` | `subtipo` na fonte | Chamados em 2026 (Recife, até 31/10) |
|---|---|---|
| `diarreia` | DIARREIA (tipo GASTROINTESTINAL) | 229 |
| `infeccao_gastrointestinal` | INFECCAO GASTROINTESTINAL | 93 |
| `vomitos` | VOMITOS | 531 |
| `desidratacao` | DESIDRATACAO (tipo GERAIS/OUTROS) | 282 |
| `febre` | FEBRE | 416 |
| `mialgia` | MIALGIA | 323 |
| `sindrome_viral` | SINDROME VIRAL | 247 |
| `total` | todos os chamados do Recife | 62.926 |

Um chamado conta no `total` e, se for de um grupo, nele. **A soma dos grupos não é o total.** `OUTROS` é cerca de 40%
dos chamados e não entra em grupo algum. Causas externas (choque elétrico, acidente com animais, afogamento) existem
na fonte, mas ficaram de fora do recorte pedido; acrescentar é um item novo em `GRUPOS`.

## Semana epidemiológica

Domingo a sábado, regra do SINAN (`climasense/dominio/semana_epi.py`). Uma semana pode cruzar dois arquivos anuais
(a SE 53/2025 vai de 28/12 a 03/01): o conector agrega pelo domingo inicial e soma os arquivos na transformação.

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.samu_recife` | resumos e contagens (acumulativa, uma execução por carga, RN-09) |
| Silver | `silver.samu_demanda_semana` | `inicio`, `bairro_fonte`, `territorio_id` (nulo se o bairro não casa), `grupo`, `chamados` (> 0), `incompleta`, `primeiro_dia_dado`, `ultimo_dia_dado`, `fonte_atualizada_em`, `coletado_em`, `execucao_id`; carga completa (os arquivos são republicados inteiros) |
| Gold | `gold.samu_demanda_semana` | `territorio_id`, `nivel` (`bairro`, `distrito`, `municipio`), `inicio`, `grupo`, `chamados`, `incompleta`, `dados_ate`, `coletado_em` |

Bairro: o nome escrito é casado com os 94 bairros oficiais pelo critério de `climasense/ml/alagamento/ocorrencias.py`.
Sem bairro ou grafia sem correspondência: fica com `territorio_id` nulo e entra **só no total do município**
(`territorio_id = 'recife'`), nunca no mapa. Distrito = soma dos bairros oficiais dele.

### Zero, ausente e incompleta (RN-01, RN-02)

- **Linha ausente em semana coberta pelo arquivo = 0 chamados** (zero medido). A silver só tem linhas com
  `chamados > 0`; quem monta a série preenche 0 para as semanas entre `primeiro_dia_dado` e `dados_ate`.
- **Semana depois de `dados_ate` = sem dado** ("Dados insuficientes", fonte `samu-recife`), nunca 0.
- `incompleta = true` quando a semana não cabe inteira no que o portal publicou (primeira semana da série ou semana
  que passa do último dia do arquivo). Não calcular variação percentual sobre semana incompleta.

## Contrato para a API (supressão no servir)

- A gold guarda a **contagem inteira**. Quem serve aplica `climasense.dominio.supressao.suprimir(valor,
  settings.supressao_minima)` (padrão 5): contagem de 1 a 4 sai como `null` com `suprimido: true`; 0 continua 0.
  Vale para qualquer nível (bairro, distrito, município) e para qualquer grupo, inclusive `total`.
- **Supressão complementar:** se um valor suprimido puder ser deduzido por diferença (por exemplo, o distrito mostra
  7, um bairro mostra 4 e outro 3), a API não deve devolver os dois. Padrão do repositório em
  `servicos/saude_agravos.py::_suprimir_bairros`: ao suprimir, esconder também o total que revelaria a célula.
- Todo valor leva `fonte` (`samu-recife`, "Prefeitura do Recife — Dados Abertos"), `dados_ate`, `coletado_em` (RF-19) e o
  rótulo "demanda de urgência (SAMU)".
- Evidência da pesquisa: nos subtipos de interesse há 10 a 30 chamados por semana na cidade inteira; por bairro, 0 a 2.
  Usar município ou distrito; bairro só para o total.

## Limitações

- É solicitação de atendimento, não diagnóstico; o bairro é o do chamado.
- Na semana de 167 mm de maio de 2026 não há sinal visível nos subtipos de interesse (pesquisa de 06/11/2026).
  Coincidência temporal descritiva, não prova de causa; selo "Experimental" (RN-11) em qualquer comparativo.
- O dicionário do recurso no CKAN descreve 2025 num campo de 2026 (erro de texto na fonte).
- 103 grafias de bairro em 2026 contra 94 oficiais; as que não casam ficam fora do mapa.

## Frescor

- Limite: 1440 h (60 dias) (`backend/climasense/etl/frescor.toml`, chave `samu-recife`).
- Motivo: publicação mensal; 60 dias toleram uma publicação perdida. O limite mede a coleta; o último dia coberto
  vai em `dados_ate`.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
