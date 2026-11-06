# Dados Abertos do Recife — atendimentos de alagamento e deslizamento (Defesa Civil)

- **Identificador:** `recife-alagamento`
- **Situação:** Implementada (rótulo fraco, ver limitações)
- **Acesso:** CKAN `https://dados.recife.pe.gov.br/api/3/action/package_show?id=registro-de-atendimentos-da-defesa-civil`,
  um CSV por ano (`;`), 2014–2025. O portal republica recursos: fica o mais recente de cada ano (`last_modified`).
- **Licença:** ODbL.
- **Cadência:** conjunto histórico; `atualizar` repete a cada 7 dias (`--forcar` ignora).
- **Bronze:** `bronze.recife_alagamento`: um resumo por arquivo (`ano`, `url`, `sha256`, `linhas`, `cabecalho`) e as
  linhas brutas que citam "alag", "desliz" ou "conten" em qualquer campo (superconjunto do critério). O arquivo inteiro (~890 mil linhas,
  150 MB) não cabe no Atlas gratuito a cada carga.
- **Silver:** `silver.ocorrencias` (`fonte_id = recife-alagamento`, `tipo = alagamento | deslizamento`; a 0011
  restringe `tipo` a esses dois valores), carga completa da fonte numa transação.
- **Gold:** `gold.alagamento_bairro_dia` (só alagamento: `territorio_id`, `distrito_id`, `dia`, `registros`) e
  `gold.ocorrencias_bairro` (por `tipo` e bairro: `registros`, `dias_com_registro`, `primeiro_dia`, `ultimo_dia`),
  que alimenta `GET /ocorrencias/historico`.

## Leitura e critério

A leitura é a mesma do estudo de ML (`climasense/ml/alagamento/ocorrencias.py`, importada pelo conector):

- âncoras pela data AAAA-MM-DD (as colunas vêm deslocadas em 2020 e 2022: a data aparece em `Mês`, o tipo em
  `Data`); os 9 últimos campos são fixos, então o bairro é o 9º a partir do fim mesmo com aspas quebradas no
  endereço; codificação UTF-8 com recuo para Latin-1;
- critério `evento`: `Ocorrencia` com "alag" (`Alagamentos`, `Imóveis Alagados`) **ou** `Solicitacao` de vistoria
  de alagado/monitoramento de setor alagado. **O endereço nunca é lido para classificar** (há ruas "Alagoinha");
- critério de **deslizamento** (a partir de 05/11/2026), também só pela categoria `Ocorrencia`: "Deslizamentos de
  Barreiras" (3.157 atendimentos em 2014–2024) e "Desabamento Parcial/Total de Obras de Contenção / Drenagem"
  (contenção de encosta ou muro de arrimo que cedeu, ~130). "Colocação/Reposição de Lonas Plásticas" (~120 mil) é
  medida **preventiva** nas encostas, acontece em dias secos e **não** conta como ocorrência. Categorias encontradas
  e descartadas: "Imóveis com Danos / Risco", "Árvores em Risco", "Muro com Danos", "Desabamento Parcial/Total
  Imóveis" (sem indicar a causa);
- bairro pelo nome oficial (com apelidos verificados: Ibura de Baixo/Cima → Ibura, Jordão Alto/Baixo → Jordão…).

| Campo da silver | Valor |
|---|---|
| `codigo_fonte` | `<ano>:<linha do CSV>` |
| `territorio_id` | `bairro-<slug>` |
| `registrado_em` | dia da solicitação/vistoria, 00:00 do Recife |
| `ocorrido_em`, `confirmada` | nulos (a fonte não diz quando alagou nem confirma) |
| `precisao_espacial` | `bairro` |

Carga de 04/11/2026: 4.496 linhas na bronze; 1.722 atendimentos de alagamento em 71 bairros, de 16/01/2014 a
25/06/2024 (461 bairro-dias). Descartes: 2.402 não são atendimento de alagamento (endereço ou rotina planejada),
358 linhas malformadas, 2 bairros fora da base oficial.

Carga de 05/11/2026 (com deslizamento): 1.722 atendimentos de alagamento em 71 bairros e 3.266 de deslizamento em
29 bairros (todos de morro: Dois Unidos, Água Fria, Passarinho, Nova Descoberta, Ibura, Cohab…).

## Limitações (rótulo fraco)

- É "houve atendimento de alagamento no bairro no dia", indicador indireto e incompleto: ausência de registro não
  prova que não alagou.
- A data é a da solicitação/vistoria e pode vir dias depois do alagamento (o ML usa janela de tolerância).
- 2025 está publicado sem linhas de alagamento; o histórico termina em junho de 2024.
- Deslizamento: o registro é da vistoria, não do momento do deslizamento; o grau de risco (`Grau_de_Risco`, R1–R4)
  não é usado nesta versão.
- O conjunto que alimenta os estágios e o ML continua sendo só o de alagamento (`tipo = alagamento`).

## Frescor

- Limite: 1440 h (60 dias) (configurado em `backend/climasense/etl/frescor.toml`, chave `recife-alagamento`; lido por `climasense.etl.frescor`).
- Motivo: publicacao com defasagem, diaria ou mensal.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
