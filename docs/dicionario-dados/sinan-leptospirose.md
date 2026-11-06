# SINAN (DATASUS) — leptospirose no Recife por semana de sintomas

- **Identificador:** `sinan-leptospirose`
- **Situação:** Implementada (05/11/2026)
- **Acesso:** FTP anônimo do DATASUS, `ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/FINAIS/LEPTBRAA.dbc`
  (anos encerrados) e `…/PRELIM/LEPTBRAA.dbc` (anos em curso). Um arquivo por **ano de notificação**, Brasil
  inteiro. Carregados de 2015 em diante; quando um ano existe nas duas pastas, vale o FINAL.
- **Formato:** `.dbc` = DBF comprimido com PKWare implode. Lido por `climasense/etl/conectores/dbc.py`, porta em
  Python puro do `blast.c` do zlib (o mesmo algoritmo do `pyreaddbc` do PySUS), sem dependência nativa.
- **Órgão:** Ministério da Saúde, DATASUS / SINAN. **Licença:** dado público do Ministério; não há licença aberta
  explícita no FTP. Citar "SINAN/DATASUS".
- **Granularidade:** município de **residência** (`ID_MN_RESI = 261160`), semana epidemiológica de início dos
  sintomas (`SEM_PRI`). **Não há bairro nem distrito** no arquivo público; a unidade notificadora não é proxy de
  residência nem de exposição.
- **Atraso (medido em 2026):** arquivo publicado ~2 semanas depois da última digitação; sintomas → notificação,
  mediana 5 dias; notificação → encerramento, mediana 18 dias. As últimas 4–6 semanas ainda têm casos sem
  encerramento.
- **Cadência:** `etl semanal` e, no `atualizar`, no máximo a cada 6 dias (são ~18 MB de download).

## Minimização (LGPD)

O `.dbc` é lido só nas colunas `ID_MN_RESI`, `SEM_PRI`, `CLASSI_FIN`, `EVOLUCAO`, `ANT_CB_LAM` e `DT_NOTIFIC`
(nenhuma identifica a pessoa). Nada de nome, endereço, nascimento, sexo, raça ou unidade sai do leitor. A bronze
guarda só:

- um resumo por arquivo: `pasta`, `arquivo`, `ano`, `atualizado_em` (MDTM do FTP), `tamanho`, `sha256`,
  `registros_brasil`, `registros_recife`, `ultima_notificacao` (data mais recente de notificação no Brasil);
- contagens do Recife por `sem_pri` × `classi_fin` × `evolucao` × `ant_cb_lam` (`n`).

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.sinan_leptospirose` | resumos e contagens (acima) |
| Silver | `silver.leptospirose_semanal` | uma linha por SE, de 2015-SE01 até a SE da última notificação; carga completa |
| Gold | `gold.saude_semanal` | `agravo = leptospirose`, `casos` = notificados, `confirmados` |

| Campo da silver | Regra |
|---|---|
| `notificados` | todas as notificações de residentes com sintomas na semana |
| `confirmados` | `CLASSI_FIN = 1` |
| `descartados` | `CLASSI_FIN = 2` |
| `em_investigacao` | classificação em branco (ou outra) |
| `obitos` | confirmados com `EVOLUCAO = 2` (óbito pelo agravo) |
| `expostos_enchente` | confirmados com `ANT_CB_LAM = 1` (contato com água ou lama de enchente nos 30 dias anteriores) |
| `incompleta` | semana começou há menos de 6 semanas antes da última notificação do arquivo mais recente |
| `preliminar` | semana de um ano que só existe na pasta PRELIM |
| `ultima_notificacao`, `versao_fonte` | data de corte e arquivos usados |

Semana coberta pelo arquivo e sem notificação de residente aparece com 0 (o arquivo é o censo das notificações);
semanas depois da última notificação não existem na série (sem dado não é zero, RN-01).

Descartes registrados: sintomas antes de 2015 (casos de 2014 notificados em 2015) e `SEM_PRI` inválida.

## Limitações

- Só município. Decisão por bairro após alagamento precisa do extrato do SINAN local da Vigilância (pedido
  registrado em `docs/pesquisa/saude-e-chuva.md`).
- Semana recente baixa é atraso, não queda. A tela hachura as semanas incompletas.
- Chuva e casos lado a lado são coincidência temporal descritiva, não causa.
- `NDUPLIC_N` (marca de duplicidade do SINAN) não é usado como filtro: o significado dos códigos não foi
  confirmado; 5 de 331 notificações do Recife em 2026 têm `NDUPLIC_N = 1`.

## Frescor

- Limite: 360 h (15 dias) (configurado em `backend/climasense/etl/frescor.toml`, chave `sinan-leptospirose`; lido por `climasense.etl.frescor`).
- Motivo: o DATASUS republica o preliminar a cada 1 a 3 semanas.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
