# InfoDengue — dengue e chikungunya no Recife por semana

- **Identificador:** `infodengue`
- **Situação:** Implementada (05/11/2026)
- **Acesso:** `GET https://info.dengue.mat.br/api/alertcity?geocode=2611606&disease={dengue|chikungunya}&format=json&ew_start=1&ew_end=53&ey_start=2015&ey_end=<ano atual>`,
  sem chave. Uma linha por semana epidemiológica (SE), a mais recente primeiro. Dicionário oficial:
  https://info.dengue.mat.br/services/api
- **Órgão:** InfoDengue (Fiocruz e FGV). Casos vêm do SINAN; clima, da REDEMET.
- **Licença:** o código do AlertaDengue é GPL-3.0; **para os dados não há licença explícita nem limite de uso
  publicado**. Citar "InfoDengue (Fiocruz/FGV)" e o artigo de método (Codeço et al.). Confirmar o uso com a equipe
  do InfoDengue se o produto sair do piloto.
- **Granularidade:** município (Recife inteiro), semana epidemiológica (domingo a sábado). `Localidade_id` (recorte
  intramunicipal) só existe no Rio de Janeiro; no Recife é 0.
- **Atraso:** ~1 semana (em 05/11/2026 a última SE era a 43, iniciada em 25/10). A série muda uma vez por semana.
- **Cadência:** `etl atualizar` (diário) e `etl semanal`. Uma chamada por agravo.
- **Zika:** fora. A série do Recife termina em 2024-SE07; carregá-la seria mostrar semanas vazias como zero.

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.infodengue` | cada linha da API como veio, mais `agravo` (sem dado pessoal: a fonte já é agregada por município) |
| Silver | `silver.infodengue_semanal` | upsert por (`agravo`, `ano`, `semana`): o InfoDengue revisa semanas passadas a cada versão do modelo |
| Gold | `gold.saude_semanal` | série única com a leptospirose (`fonte_id = infodengue`) |

| Campo da silver | Origem | Observação |
|---|---|---|
| `ano`, `semana`, `inicio` | `SE`, `data_iniSE` | o domingo é recalculado pela regra do Ministério e conferido com `data_iniSE` (divergência descarta) |
| `casos` | `casos` | notificados na semana; **revisado** nas semanas seguintes |
| `casos_est`, `casos_est_min`, `casos_est_max` | nowcasting | estimativa corrigindo o atraso, IC 95% |
| `rt`, `p_rt1` | `Rt`, `p_rt1` | número reprodutivo e probabilidade de Rt > 1 |
| `p_inc100k` | `p_inc100k` | incidência estimada por 100 mil |
| `nivel` | `nivel` | 1 verde, 2 amarelo, 3 laranja, 4 vermelho (o nível é do InfoDengue, não do ClimaSense) |
| `nivel_inc`, `receptivo`, `transmissao` | idem | limiares de incidência, receptividade climática, transmissão sustentada |
| `versao_modelo` | `versao_modelo` | data da versão do modelo |
| `incompleta` | calculado | uma das 4 semanas mais recentes **ou** estimativa > 1,1 × notificado |

## Limitações

- O número notificado das últimas semanas é sempre baixo e **não é queda**: é atraso de notificação. A tela usa a
  estimativa e marca a semana como incompleta.
- A estimativa é modelo, não contagem. O nível de alerta já incorpora clima, Rt e incidência; o ClimaSense não cria
  índice próprio.
- Sem recorte por bairro. Não há chuva nos campos do InfoDengue: a chuva do gráfico vem do próprio ClimaSense.

## Frescor

- Limite: 192 h (8 dias) (configurado em `backend/climasense/etl/frescor.toml`, chave `infodengue`; lido por `climasense.etl.frescor`).
- Motivo: publicacao por semana epidemiologica, mais um dia de folga.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
