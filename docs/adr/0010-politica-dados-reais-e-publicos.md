# ADR 0010 — Política de dados: reais, públicos e agregados; exemplo só em teste

- **Situação:** proposta (Gate 0)
- **Data:** 06/11/2026
- **Requisitos:** RNF-10, RNF-03, RNF-12, RF-03, RF-19
- **Reafirma:** ADR 0008 (somente dados reais). Regras de negócio: RN-01, RN-02, RN-13.
- **Nota (06/11/2026):** os trechos sobre abrigos foram superados; ver ADR 0016.

## Contexto

O PRD v2 confirma o ADR 0008 e o `legado:RF-12.10`: o produto não contém dado simulado (RNF-10). Ao mesmo tempo, o
PRD pede dados que ainda não têm fonte (estágio oficial do COP, ocupação e desabrigados, atendimentos nos abrigos,
peçonhentos, unidades danificadas, população vulnerável, áreas de risco) e exige que dados de pessoas vulneráveis
sejam só agregados e com acesso restrito (RNF-03). O RNF-12 lembra que Atlas e Neon são serviços de terceiros,
adequados a dados públicos.

Hoje o Atlas e o Neon guardam **dados públicos reais e agregados** e nenhum dado pessoal novo; os conectores descartam
campos pessoais antes da bronze (contatos de coordenadores no feed de abrigos do COP; endereço, CEP e nascimento nas
arboviroses). Não há exceção. O legado do projeto antigo com microdados de vacinação linha a linha (idade, sexo, raça/cor,
unidade, data, sem nome) — `silver.vacinados`, `public.silver_vacinados_legado_etl_avd` e `public.gold_previsoes`
no Neon, e a coleção `vacinacao.bronze_vacinados` no Atlas — sai dos serviços de terceiros (decisão 7).

## Decisão

1. **Só dado real no produto, em todos os ambientes que usam o Atlas ou o Neon.** Nenhum seed, fixture ou exemplo
   é carregado nesses bancos. Sem fonte, a tela mostra "Dados insuficientes" e diz qual fonte falta (RN-01).
2. **Dado de exemplo só em testes automatizados**: fixtures em `backend/tests/**/fixtures/` e respostas simuladas da
   API em `frontend/tests/e2e/`, usando Postgres descartável (`DATABASE_URL_TESTE`) e mongomock. Fixtures são recortes
   pequenos de fonte pública ou registros obviamente artificiais, e nunca dado pessoal.
3. **Classes de dado aceitas na plataforma:**

   | Classe | Exemplos | Onde pode ficar |
   |---|---|---|
   | Público agregado | Open-Meteo, APAC, INMET, Cemaden, IDAP, CKAN do Recife, InfoDengue, SINAN por semana, IBGE por bairro, CNES de estabelecimentos | Atlas e Neon (RNF-12) |
   | Registro da equipe | Estágio declarado, ações, ocupação de abrigo, cenário salvo, lançamentos manuais, importações | Neon, com autor e hora; é dado real informado por quem usa |
   | Não público do cliente, agregado | Extrato da vigilância, dados da Assistência Social, contagens de cadastros municipais | **Só depois da hospedagem definitiva** (ADR 0013, RNF-12); agregado por bairro ou distrito, com supressão de células pequenas (`supressao_minima = 5` já existe em `config.py`, RN-13) |
   | Pessoal | Nome, CPF, CNS, endereço, telefone, nascimento, contato de coordenadores, nome de profissional de consultório pessoa física no CNES | **Nunca**: nem na bronze, nem na API, nem no repositório |

4. **Campos pessoais são descartados na extração**, antes da bronze, como os conectores já fazem. Cada conector novo
   tem teste que prova que nenhum campo da classe "Pessoal" chega à bronze.
5. **População vulnerável só agregada** por bairro (ou setor censitário) e por grupo (deficiência, idosos, crianças),
   com leitura registrada na auditoria (RNF-01, RNF-03).
6. **Arquivos versionados no git**: só os oficiais pequenos já existentes (`data/territorio/` com `MANIFEST.sha256`,
   `data/abrigos/abrigos-curados.csv` com a origem de cada linha) e fixtures de teste.
7. **Legado de vacinação (decidido pelo dono no Gate 0, 06/11/2026):** exportar para um arquivo cifrado local do
   dono, fora do repositório, e depois apagar do Neon (`silver.vacinados`, a view `public.silver_vacinados`,
   `public.silver_vacinados_legado_etl_avd` e `public.gold_previsoes`) por migração, e do Atlas (banco `vacinacao`,
   coleção `bronze_vacinados`). Remover também `MONGO_DB_BRONZE_VACINACAO` e `ETL_LIMITE_VACINACAO` do `.env`.
   A exceção antes admitida para esse legado deixa de existir.

## Alternativas consideradas

- **Seed fictício em desenvolvimento** (proposta inicial da estratégia v1): descartada; contraria RNF-10 e o ADR 0008,
  e esconderia os problemas reais das fontes (atraso, lacunas), que o RF-19 precisa mostrar.
- **Aceitar dado não público no Neon desde já**: descartada até a hospedagem definitiva (RNF-12).

## Consequências

- A demonstração às usuárias usa o banco com dados reais e, para o que não tem fonte, "Dados insuficientes" ou
  registros feitos pela própria equipe.
- Hook proposto (pre-commit e `.claude/settings.json`): bloquear commit de `*.csv`, `*.json`, `*.geojson`, `*.dbc`,
  `*.xlsx` fora de `data/territorio/`, `data/abrigos/`, `docs/api/` e `backend/tests/**/fixtures/`.
- O agente `seguranca-lgpd` revisa cada conector novo contra a classe "Pessoal".
