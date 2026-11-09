# Ministério da Saúde — SISAGUA, qualidade da água por bairro e semana

- **Identificador:** `sisagua`
- **Situação:** Implementada (06/11/2026). Migração 0023.
- **Acesso:** API de Dados Abertos do MS, sem autenticação:
  `GET https://apidadosabertos.saude.gov.br/sisagua/vigilancia-parametros-basicos?codigo_ibge=261160&ano=<ano>&limit=1000&offset=<n>`
  (Swagger em `https://apidadosabertos.saude.gov.br/v1/`). Resposta JSON, lista na chave `parametros`; o conector
  pagina até vir uma página com menos de 1000 linhas. Lê o ano corrente e o anterior.
- **Órgão:** Ministério da Saúde, SISAGUA (vigilância da qualidade da água para consumo humano).
- **Licença:** dado aberto do MS; **termo de uso não localizado na API** (não verificado). Citar "Ministério da Saúde,
  SISAGUA".
- **Granularidade:** uma linha por parâmetro de uma amostra, com bairro (`area`), data da coleta, do laudo e do
  registro. A série do Recife **começa em 11/2025** (2022 a 2024 vêm vazios; 2025 tem 2.967 linhas e 2026 tem 5.680
  até 28/10).
- **Atraso:** medido em 06/11/2026 (8.647 linhas): mediana de **14 dias** entre coleta e registro, 90% até 35 dias,
  95% até 49. Último registro 03/11, última coleta 28/10.
- **Cadência:** semanal (`frescor.toml`: 192 h). `etl run sisagua`.

## Rótulo obrigatório

**"Qualidade da água, coleta de rotina, não dirigida pelo evento."** A amostragem é programada pela Vigilância
Ambiental e não segue a chuva. Não é caso de doença. **Semana sem amostra no bairro é "sem coleta", nunca "água boa"**
(RN-01).

## O que se conta (sem percentual e sem classe de risco, RN-06)

| Grandeza | Análises (`analises_*`) | Positivos |
|---|---|---|
| E. coli (`parametro = Escherichia coli`) | resultados `PRESENTE` ou `AUSENTE` | `ecoli_presente` |
| Cloro residual livre (`Cloro residual livre (mg/L)`) | resultados numéricos (vírgula decimal) | `cloro_fora_padrao`: abaixo de 0,2 mg/L ou acima de 5,0 mg/L |

A faixa do cloro segue a Portaria GM/MS nº 888/2021 (mínimo de 0,2 mg/L na distribuição e valor máximo permitido de
5 mg/L); está em `CLORO_MIN_MG_L` e `CLORO_MAX_MG_L` em `climasense/etl/conectores/sisagua.py`. **Confirmar com a
Vigilância Ambiental** se a faixa vale igual para solução alternativa coletiva (SAC) e individual (SAI). Resultado
que não dá para contar (texto, negativo, vazio) fica fora e entra em `motivos` como `resultado_nao_contavel`.

Coliformes totais, turbidez, pH, cor aparente e dióxido de cloro **não são usados**; aparecem só na lista
`parametros` do resumo da bronze.

**Rotina e dirigida:** `motivo_grupo = rotina` quando `motivo_da_coleta = Rotina`; qualquer outro (Surto, Denúncia,
Desastre) é `dirigida`. Os dois ficam em linhas separadas: somar as dirigidas à rotina inflaria os positivos
justamente depois de um evento. Para o rótulo acima, a API usa `rotina`.

## Minimização

A API devolve também `numero_da_amostra`, `descricao_do_local` (logradouro do ponto de coleta), `local`,
`latitude`/`longitude`, `nome_da_forma_de_abastecimento` e outros. O conector agrega na leitura; a bronze recebe só:

- resumo por ano: `ano`, `url`, `linhas`, `ultima_coleta`, `ultimo_registro`, `parametros` (nome e contagem),
  `motivos`;
- contagens `inicio` (domingo da SE) × `bairro_fonte` × `motivo_grupo` × `grandeza` × `classe` → `n`.

Ponto de coleta não é dado pessoal, mas não precisa ir para o produto. Teste:
`test_sisagua_agrega_na_leitura_e_nenhum_campo_de_local_chega_a_bronze`.

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.sisagua` | resumos e contagens (acumulativa, RN-09) |
| Silver | `silver.agua_vigilancia_semana` | `inicio`, `bairro_fonte`, `territorio_id` (nulo se não casar), `motivo_grupo`, `analises_ecoli`, `ecoli_presente`, `analises_cloro`, `cloro_fora_padrao`, `incompleta`, `ultima_coleta`, `ultimo_registro`, `coletado_em`, `execucao_id`; carga completa |
| Gold | `gold.agua_vigilancia_semana` | os mesmos contadores por `territorio_id` e `nivel` (`bairro`, `distrito`, `municipio`), `inicio`, `motivo_grupo`, `incompleta`, `ultima_coleta`, `ultimo_registro`, `coletado_em` |

Bairro: `area` casada com os 94 oficiais (mesmo critério da Defesa Civil). 88 `area` distintas em 2025–2026. Sem
correspondência ou em branco: fica na silver com `territorio_id` nulo e **entra só no total do município**.

### Semana incompleta

Pelo atraso medido, as **6 semanas mais recentes** contadas a partir do último registro (`SEMANAS_INCOMPLETAS`)
saem com `incompleta = true`: o número baixo ali pode ser atraso de registro, não menos coleta. Sem variação
percentual sobre semana incompleta.

## Contrato para a API

- Servir contagens: `analises_ecoli`, `ecoli_presente`, `analises_cloro`, `cloro_fora_padrao`. **Sem percentual, sem
  classe de risco.** A tela pode escrever "3 de 12 análises com E. coli presente".
- Água não é dado pessoal; **não há supressão de células pequenas** aqui.
- Linha ausente = "sem coleta" (não 0). Zero só quando a linha existe com `ecoli_presente = 0` e `analises_ecoli > 0`.
- Cada valor leva fonte `sisagua`, `ultimo_registro` ("dados até"), `coletado_em` (RF-19) e o rótulo da seção
  "Rótulo obrigatório".

## Limitações

- Amostragem de rotina, não dirigida pelo evento; bairros com poucas coletas por semana.
- Atraso mediano de 14 dias entre coleta e registro.
- O conjunto começa em 11/2025: não há linha de base de anos anteriores.
- Há coleta em SAA (sistema), SAC e SAI; o conector não separa a forma de abastecimento.

## Frescor

- Limite: 192 h (8 dias) (`backend/climasense/etl/frescor.toml`, chave `sisagua`).
- Motivo: carga semanal mais um dia de folga; o atraso de registro está em `ultimo_registro` e `incompleta`.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
