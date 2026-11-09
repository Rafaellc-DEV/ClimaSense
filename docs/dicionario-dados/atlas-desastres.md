# Sedec/MIDR e Ceped/UFSC — Atlas Digital de Desastres no Brasil (histórico do Recife)

- **Identificador:** `atlas-desastres`
- **Situação:** Implementada (06/11/2026). Migração 0023.
- **Acesso: não há API.** A página `https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml` publica o consolidado
  nacional em CSV (`;`, **latin-1**, ~74 MB, 70 colunas, 70.163 registros de 1991 a 2025), por exemplo
  `/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv`. O nome do arquivo muda a cada consolidação:
  o conector **descobre o link na página** (o `Consolidado.csv` de data mais nova) e, se a página não listar mais nenhum,
  falha com a mensagem "o endereço mudou" em vez de adivinhar. Baixa em **fluxo** (blocos de 1 MB, nunca o arquivo inteiro
  na memória), filtra `Cod_IBGE_Mun = 2611606` (Recife) e descarta o resto na hora.
- **Órgão:** Secretaria Nacional de Proteção e Defesa Civil (Sedec/MIDR) e Centro de Estudos e Pesquisas em
  Engenharia e Defesa Civil (Ceped/UFSC). Os registros vêm do S2iD, informados pelo município.
- **Licença: não declarada** na página (dado oficial federal). Atribuição obrigatória: "Sedec/MIDR, Atlas Digital de
  Desastres no Brasil". Risco baixo para uso interno; **perguntar ao MIDR** antes de redistribuir fora do painel
  (pergunta 8 de `docs/pesquisa/api-operacional.md`).
- **Cadência:** uma consolidação por ano (a de 2026 é de 06/08 e cobre até 2025). `etl run atlas-desastres` uma vez
  por ano ou quando o MIDR publicar (`frescor.toml`: 13140 h).
- **Granularidade:** evento (protocolo S2iD), dia e município. **Sem bairro e sem horário.**

## Cobertura e limites

Só entram eventos que viraram **registro ou decreto**; subnotificação é possível. Recife: **16 registros, 1991 a
2022**. Os de chuva: enxurradas (1991, 1994, 1996, 1997, 2000, 2010), movimento de massa (1997, 1997, 2005, 2007),
inundação (2008), alagamento (2012) e chuvas intensas (2022). Não são de chuva: estiagem (1999) e doenças
infecciosas (2 registros, 2015). **O evento de abril a maio de 2026 não está aqui** (a consolidação vai até 2025);
para ele só existe o que a equipe registrar com fonte.

## Zero não é "zero medido"

O município pode não ter preenchido um campo e o CSV grava `0`. O conector guarda **campo vazio como ausente
(nulo)** e **`0` como 0**; a fonte não distingue "não informado" de "nenhum". Qualquer tela precisa dizer isso ao
mostrar mortos, desabrigados ou R$ 0,00. Exemplo real: o evento de 03/08/2000 tem 8 mortos e R$ 72,8 milhões; o de
20/04/2010 tem 6 mortos e R$ 0,00 de danos materiais.

## Colunas guardadas

Só administrativas; nenhuma identifica pessoa. Os campos de texto livre (`DH_Descricao`, `DM_Descricao`,
`DA_Descricao`, `PEPL_Descricao`, `PEPR_Descricao`), que trazem a narrativa do município, **não são lidos para a bronze**.

| Coluna do CSV | Campo | Observação |
|---|---|---|
| `Protocolo_S2iD` | `protocolo` (chave) | ex.: `PE-F-2611606-13214-20220529` |
| `Data_Evento` | `data_evento` | `DD/MM/AAAA`; sem data válida o registro é descartado (`sem_data_do_evento`) |
| `Data_Registro` | `data_registro` | |
| `Cod_Cobrade` | `cobrade` | tipologia Cobrade (12200 enxurradas, 13214 chuvas intensas...) |
| `descricao_tipologia` | `tipologia` | texto da fonte |
| `Status` | `status` | `Registro` ou `Reconhecido` (reconhecimento federal) |
| `DH_MORTOS`, `DH_FERIDOS`, `DH_DESABRIGADOS`, `DH_DESALOJADOS`, `DH_OUTROS AFETADOS` | `mortos`, `feridos`, `desabrigados`, `desalojados`, `outros_afetados` | inteiros, agregados do município |
| `DH_total_danos_humanos_diretos` | `danos_humanos_total` | soma de danos humanos diretos da fonte |
| `DM_total_danos_materiais` | `danos_materiais_rs` | R$ |
| `PEPL_total_publico`, `PEPR_total_privado` | `prejuizo_publico_rs`, `prejuizo_privado_rs` | R$ (prejuízos econômicos público e privado) |

`chuva_relacionada` (booleano) **é classificação do ClimaSense, não do Atlas**, pela tipologia Cobrade: hidrológicos
(`12xxx`), movimento de massa (`113xx`) e chuvas intensas (`13214`). Não afirma causa.

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.atlas_desastres` | um resumo do arquivo (`url`, `versao`, `consolidado_em`, `sha256`, `bytes`, `linhas_brasil`, `registros_recife`) e os registros do Recife já reduzidos às colunas acima |
| Silver | `silver.desastres_atlas` | um evento por protocolo, mais `versao_fonte`, `consolidado_em`, `coletado_em`, `execucao_id`; carga completa a cada consolidação |
| Gold | `gold.desastres_historico` | os mesmos campos (menos `execucao_id`), gerado por SQL a partir da silver |

## Contrato para a API

- Cada evento sai com `fonte` ("Atlas Digital de Desastres no Brasil, Sedec/MIDR"), `versao_fonte`,
  `consolidado_em` e `coletado_em` (RF-19), `protocolo` como identificador.
- Campo nulo = "não informado" (RN-01). Campo 0 = "0 no Atlas (a fonte não distingue não informado de nenhum)".
- Totais agregados do município; não há dado individual nem supressão a aplicar.
- Evento retrospectivo: sem estágio, sem comunicados e sem linha do tempo horária ("não disponível nesta fonte"). Quem
  usar como `origem_dado = oficial_historico` no histórico de eventos referencia o `protocolo`.
- Atribuição obrigatória visível onde o dado aparecer.

## Limitações

- Sem API e sem licença declarada; o link do arquivo muda a cada consolidação.
- Subnotificação e preenchimento heterogêneo entre municípios e anos.
- Sem bairro e sem horário; granularidade de dia e município.
- Os números do evento de 2022 incluem "outros afetados" de 1.532.177, que é o que o município informou; não somar
  com desabrigados e desalojados sem ler a definição no manual (`/arquivos/Atlas_Digital_Desastres_Manual_Aplicacao.pdf`).

## Frescor

- Limite: 13140 h (18 meses) (`backend/climasense/etl/frescor.toml`, chave `atlas-desastres`).
- Motivo: consolidação anual (agosto); 18 meses evitam o selo de desatualizado entre uma publicação e a seguinte.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
