# Perguntas abertas

Atualizado em 06/11/2026 (Onda 0, agente `arquiteto`). P-01 a P-10 vêm da seção 13 do `docs/PRD.md`; P-11 em diante
surgiram na matriz (`docs/matriz-prd-codigo.md`). As decisões do dono do produto para o Gate 0 estão na seção 2.

## 1. Perguntas para o cliente

| Nº | Pergunta | Quem responde | O que bloqueia |
|---|---|---|---|
| P-01 | Por onde os dados de saúde chegam hoje (sistema, planilha, e-mail) e com que atraso? A vigilância tem algo mais atual que o SINAN semanal? | Centro de vigilância epidemiológica | RF-11, RF-12 por território; RNF-04 |
| P-02 | Os abrigos abertos já vêm do feed do COP. O COP consegue disponibilizar também ocupação e desabrigados? | COP e Assistência Social | RF-08, RF-09 sem digitação; RNF-04 |
| P-03 | Existe fonte estruturada para animais peçonhentos e para consultas, vacinas e medicamentos dos abrigos, ou o registro é manual? | Vigilância epidemiológica e Assistência Social | RF-12 (peçonhentos por território), RF-13 |
| P-04 | Existem ocorrências de deslizamento com bairro e data? | Defesa Civil do Recife (Sedec) | RF-23 para deslizamento; estudo de ML de deslizamento (PRD §8.4) |
| P-05 | Existe mapeamento oficial de áreas de risco por bairro ou setor? O CKAN do Recife só publica a Regional Sul. | Defesa Civil do Recife (Sedec) | RF-02 (camada de áreas de risco), RF-06, RF-23 |
| P-06 | Quem pode oficializar o estágio por bairro (hoje a decisão é do COP)? Quais gatilhos e limiares o cliente aceita para cada estágio? | Cliente e COP | RF-01, RF-29 (limiares hoje são proposta) |
| P-07 | Onde a plataforma pode ser hospedada, dada a falha em PHP que deixou todos sem acesso? | Cliente e TI da Prefeitura (Emprel) | RNF-02, RNF-07, RNF-12; qualquer dado não público (ADR 0013) |
| P-08 | O relatório executivo tem modelo obrigatório? O Boletim atual atende? | Secretaria de Saúde, via Vigidesastres | RF-17 |
| P-09 | A mensagem pronta de WhatsApp atende à dor da comunicação, ou o cliente espera algo a mais? | Mariana Siqueira e Mariana Lima | RF-31 (escopo da comunicação) |
| P-10 | Resposta 9 do primeiro grupo: quais outros indicadores e painéis o cliente quer ter? | Cliente | RF-20 (o que entra em cada tela) |
| P-11 | Como o estágio oficial do COP chega hoje (boletim, WhatsApp, sistema)? Quais são os nomes oficiais dos níveis? O campo `estagio_operacional` do feed de abrigos do COP é o estágio da cidade? | COP | RF-01 (estágio oficial ao lado do sugerido) |
| P-12 | Para pessoas com deficiência por bairro não há dado público (o Censo 2022 só tem por área de ponderação). A Assistência Social pode fornecer contagem agregada por bairro (CadÚnico, BPC)? Que faixas de idade valem para "criança" e "idoso"? | Assistência Social e Vigidesastres | RF-03, RF-04, RF-25 |
| P-13 | Qual o limite mínimo para mostrar uma contagem por bairro (hoje `supressao_minima = 5`)? | Vigilância epidemiológica e encarregado de dados | RNF-03, RF-03, RF-12 |
| P-14 | Qual a meta de disponibilidade durante eventos de chuva? (Proposta: 99,5% no mês.) | Cliente | RNF-07 |
| P-15 | Qual o limite de frescor aceito para cada tipo de dado (abrigos, alertas, chuva, saúde, cadastros)? | Mariana Siqueira e Mariana Lima | RF-19, RNF-05 |
| P-16 | As premissas do simulador (PRD §8.1) são as certas? Quem fornece o boletim climático do COP? | Cliente e COP | RF-23 a RF-28 |
| P-17 | Quem informa que uma unidade de saúde fechou ou foi danificada? O CNES serve como cadastro das unidades? | Vigilância e gerências dos distritos | RF-14, RF-04 |
| P-18 | Que dados exigem registro de quem **leu** (além de quem alterou)? Só a camada de vulneráveis? | Cliente e encarregado de dados | RNF-01, RNF-03 |
| P-19 | Trocar a senha do neondb_owner antes do Gate 1 ou antes de qualquer dado não público; credencial exposta no histórico de uma sessão em 06/11/2026. | Dono do produto | RNF-01, RNF-12 |
| P-20 | `POST /etl/execucoes` (a API dispara o ETL) usa a URL do dono do banco (`DATABASE_URL_MIGRACOES`), que fica ao alcance da API. Em produção, mover o disparo do ETL para fora da API (agendador ou GitHub Actions) e não dar essa variável à API? | Dono do produto | RNF-01, RNF-12, ADR 0014 |
| P-21 | O COP pode publicar o estágio oficial da cidade num formato legível por máquina (camada ArcGIS, JSON ou RSS)? Hoje ele não existe em nenhuma fonte pública e entra por registro manual da equipe (ver `docs/pesquisa/estagio-oficial-cop.md`). | COP | RF-01, RNF-04 |

## 2. Decisões do dono do produto (Gate 0)

| Nº | Decisão | Proposta do arquiteto | Onde |
|---|---|---|---|
| D-01 | Aprovar a matriz PRD × código | — | `docs/matriz-prd-codigo.md` |
| D-02 | Política de dados reais, públicos e agregados; exemplo só em teste | Aprovar | ADR 0010 |
| D-03 | Chaves `FUNC_LANDING_PUBLICA` e `FUNC_COMUNICADOS` desligadas por padrão; `/` leva a `/entrar` | Aprovar | ADR 0011 |
| D-04 | Pastas por agente, com os complementos (pastas sem dono, divisão dos testes) | Aprovar; corrigir `backend/alembic/` para `backend/migrations/` em `.claude/agents/backend-api.md` | ADR 0012 |
| D-05 | Legado de vacinação no Neon (`silver.vacinados`, `public.silver_vacinados_legado_etl_avd`), microdados individuais | Apagar ou mover para fora do banco do produto | ADR 0010 |
| D-06 | Hospedagem provisória em nuvem gerenciada para dados públicos | Aprovar como hipótese | ADR 0013 |
| D-07 | `GET /boletim/texto` (resumo do boletim para WhatsApp) | Manter: nada é enviado e ajuda o relatório | Matriz §4 |
| D-08 | Tirar do produto o painel antigo, o mapa portátil e as estatísticas de séries | Aprovar | Matriz §4 |
| D-09 | O PRD diz que só há geometria de distrito; a malha de bairros existe em `data/territorio/` | Corrigir o PRD (§8.4 e §13) | Matriz §5 |
| D-10 | Hooks da estratégia §9 em `.claude/settings.json` (bloquear `git commit` e `git push`, lint depois de editar) | Criar na Onda 1 pela sessão principal | — |
| D-11 | `CLAUDE.md` foi copiado sem alteração da estratégia e diz "próximo número: 0010"; agora é 0014 | Atualizar a linha | `CLAUDE.md` |
| D-12 | Adotar `scripts/exportar_openapi.py` e `docs/api/openapi.json` como cópia do contrato, com verificação no CI | Aprovar; CI só com aprovação | RNF-11 |
