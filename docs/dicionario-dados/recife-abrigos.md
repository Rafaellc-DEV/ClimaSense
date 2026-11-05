# Abrigos e pontos de apoio do Recife (Dados Abertos, lista curada e COP)

- **Identificador:** `recife-abrigos`
- **Situação:** Implementada
- **Destino:** `app.abrigos` com `origem = 'dados-abertos'` e `codigo_fonte` (único por origem), servido em
  `/abrigos` (equipe) e `/publico/abrigos` (landing, sem login).

## Modo `cadastro` (padrão): locais que podem ser ativados

| Origem | Acesso | Conteúdo |
|---|---|---|
| CKAN `abrigos-temporarios-disponiveis` (ODbL) | `datastore_search?resource_id=35566d21-a428-4595-89dc-eb405380b33e` + `resource_show` (data) | 17 locais da Ação Inverno 2022: `equipamento_publico_disponivel`, `tipo`, `municipal_estadual`, `endereco`, `bairro`, `latitude`, `longitude`. Lista estática, sem status |
| `data/abrigos/abrigos-curados.csv` | arquivo do repositório (ver `data/abrigos/README.md`) | 193 locais (camada ABRIGOS_2023, Censo SUAS 2024, Plano de Contingência 2026); colunas `nome;endereco;bairro;latitude;longitude;tipo;responsavel;fonte_url;fonte_data;observacao` |

- **Bronze:** `bronze.recife_abrigos`: os registros do CKAN (`registro = ckan`, `ckan_id`, `fonte_data`) e do CSV
  (`registro = curado`, `n_linha`), mais um documento com o `sha256` e o número de linhas do arquivo curado.
- **Mesmo local:** nome igual (sem acento e sem "(ABRIGO)") ou, entre fontes diferentes, coordenadas a até 120 m com
  nomes que compartilham a parte distintiva ("Adauto Pontes" × "Professor Adauto Pontes"). O curado completa o do
  CKAN (capacidade, tipo); escolas vizinhas com nomes diferentes continuam separadas. Carga de 04/11/2026: 11
  locais juntados (os 11 marcados "também no CKAN 2022"), 199 abrigos.
- **Bairro:** ponto-em-polígono na malha oficial de bairros (o texto da fonte tem "COHAB/IBURA", "DETRAN"); sem
  coordenada, o nome do bairro pelos apelidos oficiais.
- `codigo_fonte`: `ckan:<slug do nome>` ou `curado:<slug do nome>`. `capacidade_fonte` vem do texto "capacidade
  estimada (pessoas): 100 em salas + 150 em quadra" (soma).
- **Upsert sem sobrescrever a equipe:** `aberto`, `capacidade`, `pessoas_abrigadas`, `desabrigados` e `observacao`
  nunca são alterados pela carga; nome, endereço, bairro e coordenada só enquanto a equipe nunca editou o abrigo.
  Local que sai do cadastro só é removido se ninguém nunca mexeu nele (sem histórico).

## Modo `ativos` (a cada 10–15 min): abertos agora

- **Fonte:** feed público "Abrigos Ativos" do COP Recife (ArcGIS)
  `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/COP/Abrigos_Ativos/FeatureServer/0/query`. Em
  04/11/2026 devolvia 0 locais (período seco).
- **Bronze:** `bronze.recife_abrigos_ativos` (resumo da consulta + cada local). Campos pedidos:
  `no_entidade, tipo, endereco, latitude, longitude, status, estagio_operacional, capacidades, last_edited_date`.
- **LGPD:** `coordenador_*`, `contato_*` e `*_user` (nomes e telefones) nem são pedidos à fonte e são removidos
  antes da bronze; não vão para silver, app nem landing.
- Estar no feed = aberto (salvo `status` com inativo/fechado). Casa com o cadastrado por nome ou coordenada (ou cria
  `cop:<globalid>`), grava `aberto = true`, `status_origem = 'cop'`, `status_lido_em` (edição do COP) e
  `capacidade_fonte` (salas × pessoas + vagas na quadra). Cada mudança vira uma linha em `app.abrigo_atualizacoes`
  sem autor.
- Local que some do feed volta a `aberto = false` **só** se o último status veio do COP. Um registro da equipe
  mais recente que a leitura do COP sempre prevalece.

## `/publico/abrigos`

`{itens: [{id, nome, endereco, bairro_nome, distrito_nome, latitude, longitude, aberto, aberto_fonte, aberto_lido_em,
atualizado_em, origem, fonte_url, tipo, capacidade}], atualizado_em, aviso}`. `aberto` é `null` quando nem o COP nem a
equipe informaram (nunca informado ≠ fechado); `aberto_fonte` é `cop`, `equipe` ou `null`. Sem nomes de servidores,
autores, pessoas abrigadas ou desabrigados. O `aviso` orienta ligar para a Defesa Civil do Recife (0800 081 3400,
gratuito, 24 h) ou de Pernambuco (199).
