# Dados Abertos do Recife — atendimentos da Defesa Civil com grau de risco (R1 a R4)

- **Identificador:** `recife-atendimentos-grau-risco`
- **Situação:** Implementada (06/11/2026). RF-02, RF-04, RF-19. Migração 0022.
- **Acesso:** o mesmo CKAN do `recife-alagamento` (`registro-de-atendimentos-da-defesa-civil`), um CSV por ano (`;`).
  O conector reaproveita `recursos_por_ano` (o recurso mais recente de cada ano).
- **Licença:** ODbL.
- **Cadência:** conjunto histórico; carga manual (`python -m climasense.etl run recife-atendimentos-grau-risco`, baixa ~150 MB).
  Não está em `etl atualizar`.

## O indicador e o que ele não é

Indicador **factual**: "atendimentos com grau R3/R4 de 2014 a 2024" (rótulo gravado com o período real), contagem agregada
por bairro. **Não** é mapeamento de risco: o grau vem do atendimento, pode refletir o ponto vistoriado e não o bairro, e a
fonte não diz o que o grau avalia (P-60). Nunca "bairro de risco" nem "risco do bairro". Uma contagem alta também reflete onde a
Defesa Civil atende mais, não só onde há mais risco.

**O histórico parou em 2024**: o arquivo de 2025 do portal tem 1 linha (sem grau) e não há 2026 (P-42). Sem dado depois de
2024 não se conclui que 2025 e 2026 foram calmos (RN-01). A `observacao` da cobertura diz isso.

Cuidado ao comparar anos: a prática de preencher o grau mudou. Em 2016, todas as 92 mil linhas têm grau; em 2020 a 2024, perto
de metade. Use a soma do período, não a tendência por ano.

## Privacidade (RN-13, RNF-03)

A coluna `Endereco` (já ofuscada pela fonte, "Rua Taipu, #_|/") **nunca é lida**: o leitor `contar_graus` pega só o bairro e o grau,
pelas âncoras de posição (os 9 últimos campos são fixos: Bairro é o 9º e Grau_de_Risco o 7º a partir do fim; a presença de uma
data AAAA-MM-DD entre os 5 primeiros campos prova o layout, também com as colunas deslocadas de 2020 e 2022). Não se geocodifica nada.
O ano é o do **arquivo**, não da data da linha (há datas erradas, como 1900).

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.recife_atendimentos_grau_risco` | `registro = arquivo` (ano, url, `sha256`, `linhas`, `sem_ancora`, `sem_grau`, `grau_invalido`, `amostra`) e `registro = contagem` (`ano`, `bairro` como escrito, `grau`, `atendimentos`). **A bronze é agregada**: o arquivo inteiro (~890 mil linhas) não cabe no Atlas gratuito; o `sha256` identifica o arquivo lido |
| Silver | `silver.atendimentos_grau_risco` | `(bairro_id, ano, grau)` pk; `grau` in R1..R4; `atendimentos` > 0; carga completa (apaga e regrava a fonte) |
| Gold | `gold.indicador_territorial` | `atendimentos_grau_r3_r4` (soma de R3 e R4; **0 = o bairro tem atendimentos com grau, nenhum R3/R4**) e `atendimentos_grau_total` (R1 a R4). Unidade `atendimentos`; `periodo` e rótulo com os anos reais da silver |
| Gold | `gold.cobertura_indicador` | `bairros_com_dado`, `bairros_com_valor_positivo`, `bairros_total`, `observacao` |

Bairro: nome do campo `Bairro` resolvido pelo mesmo mapa do `recife-alagamento` (`resolver_bairro`, com os apelidos já
validados). Texto que não é bairro oficial (localidades escritas no campo, como "Alto da Esperança" ou "Boqueirão") **não é
atribuído a outro bairro**: é contado em `descartes.bairro_fora_da_base_oficial`. Extração parcial (`--limite` = nº de anos)
vira amostra e só grava a bronze (RN-10).

## Cobertura medida (carga real de 06/11/2026, 2014 a 2025, sem banco)

- 553.520 atendimentos com grau: R1 194.824, R2 154.434, **R3 194.590, R4 9.672**. Anos 2014 a 2024 (2025: sem grau).
- **91 de 94 bairros** têm atendimento com grau; sem nenhum: Jaqueira, Pau Ferro e Zumbi.
- **89 de 94** têm pelo menos um R3 ou R4 (os cinco sem: Jaqueira, Paissandu, Pau Ferro, Porto da Madeira e Zumbi).
  Valor 0 aparece em Paissandu e Porto da Madeira (têm grau, nenhum R3/R4).
- Maiores somas R3/R4 do período: Nova Descoberta 34.380, Cohab 31.376, Dois Unidos 15.784, Vasco da Gama 12.126, Guabiraba 11.352.
- 8.062 atendimentos com grau ficaram de fora por trazer no campo `Bairro` um nome que não é bairro oficial (1,5%).
- Os números diferem um pouco da estimativa da pesquisa (88 e 86 bairros), que casava nomes à mão; esta é a medição do conector.

## Frescor

- Limite: 13140 h (18 meses) (`frescor.toml`, chave `recife-atendimentos-grau-risco`), como as arboviroses (um arquivo por ano,
  publicado depois). Carga em dia **não** significa dado de 2025: o aviso do histórico fica na cobertura.
