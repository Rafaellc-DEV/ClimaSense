# IBGE — Censo Demográfico 2022: moradores por bairro e faixa de idade

- **Identificador:** `ibge-censo-2022-bairro`
- **Situação:** Implementada (06/11/2026). RF-02, RF-03.
- **Órgão:** IBGE. **Licença:** dados públicos do IBGE (Censo Demográfico 2022).
- **Acesso:** `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/Agregados_por_bairros_demografia_BR.zip`
  (1,3 MB, um CSV `;`, 17.576 bairros do Brasil; o conector filtra `CD_BAIRRO` que começa em `2611606`).
  Dicionário: `dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx` na pasta pai.
- **Granularidade:** bairro × faixa de idade, ano 2022. Só contagens: nada identifica pessoa (RN-13).
- **Atualização:** retrato fixo (data de referência do Censo, 2022); o próximo é em 2030. Sem limite de frescor.
- **Cadência no ETL:** `python -m climasense.etl run ibge-censo-2022-bairro` (uma vez; refazer só se o IBGE republicar).
  O arquivo é pequeno (1,3 MB).

## Variáveis usadas

| Variável | Significado (dicionário do IBGE) |
|---|---|
| V01006 | Quantidade de moradores |
| V01031 / V01032 / V01033 | 0 a 4 / 5 a 9 / 10 a 14 anos |
| V01034 a V01039 | 15 a 19, 20 a 24, 25 a 29, 30 a 39, 40 a 49, 50 a 59 anos |
| V01040 | 60 a 69 anos |
| V01041 | 70 anos ou mais |

Faixas gravadas em `silver.populacao_bairro.faixa`:

| Faixa | Cálculo |
|---|---|
| `0-4` | V01031 |
| `0-14` | V01031 + V01032 + V01033 |
| `60+` | V01040 + V01041 |
| `70+` | V01041 (acrescentada: é o corte mais alto que o IBGE publica por bairro) |
| `total` | V01006 |

- **`80+` não existe por bairro**: os agregados por bairro agrupam "70 anos ou mais". Não é estimado nem redistribuído
  (pergunta P-24 em `docs/perguntas-abertas.md`).
- A soma das 11 faixas de idade pode diferir do total V01006 em poucas pessoas (34 dos 94 bairros diferem em poucas
  pessoas; causa não investigada). O `total` gravado é V01006.
- **Supressão:** célula "X", em branco ou não numérica em qualquer parcela de uma faixa → `pessoas` nulo e
  `suprimido` verdadeiro, **nunca 0** (RN-02). Na carga de 06/11/2026 nenhuma célula do Recife veio suprimida.

## Casamento do bairro do IBGE com os 94 oficiais

Nome normalizado (sem acento, sem caixa; mesmo critério de `recife-alagamento`). Resultado: **94 de 94 bairros**
casados. Único caso fora do critério simples: "Sítio dos Pintos - São Brás" (IBGE) = Sítio dos Pintos (oficial),
tratado por um apelido no conector. O que não casar é contado (`bairro_do_ibge_sem_par_oficial`), listado na saída da
carga e nunca atribuído a outro bairro; o plano B (setores censitários + malha de setores, ponto no bairro) não foi
necessário.

Total da cidade pelos bairros: **1.482.654 moradores**; 60+: 263.676; 0-4: 80.920. Pode ficar abaixo do total
municipal do Censo (não conferido aqui); a diferença não é corrigida nem redistribuída.

## Deficiência: não existe por bairro

Os agregados do Censo 2022 por bairro (e por setor) **não trazem pessoas com deficiência**. A pesquisa da amostra
publica deficiência só por município e área de ponderação (que agrupa vários bairros). **Nenhum dado é criado nem
estimado**: a camada de pessoas com deficiência mostra "Dados insuficientes" e cita a fonte que falta (Assistência
Social, CadÚnico/BPC agregado por bairro). Pergunta P-23.

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.ibge_censo_2022_bairro` | um documento `registro = arquivo` (url, sha256, linhas do Brasil e do Recife) e 94 `registro = bairro` com V01006 e V01031 a V01041 usados, como vieram |
| Silver | `silver.populacao_bairro` | `bairro_id`, `ano` (2022), `faixa`, `pessoas` (nulo se suprimido), `suprimido`, `fonte_id`, `execucao_id`; 94 bairros × 5 faixas = 470 linhas; carga completa (apaga e regrava a fonte) |

## Limitações

- Moradores em domicílios, retrato de 2022; não é a população presente no momento do evento.
- Bairros do IBGE têm limites próprios; o casamento é por nome, não por geometria.
- Bairro com pouca gente tem mais risco de supressão em recortes futuros.

## Frescor

- Limite: sem limite (valor 0 em `backend/climasense/etl/frescor.toml`, chave `ibge-censo-2022-bairro`; retrato fixo).
- A tela mostra a data de referência (2022) e a hora da carga (RF-19).
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
