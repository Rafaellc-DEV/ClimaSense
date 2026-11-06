# ADR 0014 — Papel de banco da aplicação sem poder de dono

- **Situação:** aceita
- **Data:** 06/11/2026
- **Base:** RNF-01, RNF-12; achado de segurança 4 (a API conectava como dono do banco); ADR 0010 decisão 7

## Contexto

A API conectava ao Neon com `neondb_owner`: dono de todas as tabelas, capaz de DDL, de apagar a auditoria (os gatilhos
de somente-inclusão são a única barreira) e de ler ou alterar qualquer coisa. Um vazamento da URL ou uma injeção de
SQL teria alcance total.

## Decisão

1. Papel `climasense_app`: LOGIN, sem SUPERUSER, CREATEDB, CREATEROLE nem BYPASSRLS, dono de nada.
2. A migração **0014** cria o papel sem senha (se faltar) e concede o mínimo:
   - USAGE em `app`, `silver`, `gold`, `public`; SELECT em tudo isso; sem CREATE;
   - `app.*`: SELECT, INSERT, UPDATE, DELETE, exceto nas tabelas somente-inclusão (`auditoria`, `estagio_parametros`,
     `estagio_declaracoes`, `abrigo_atualizacoes`, `acao_eventos`, `liberacoes_login`), onde só SELECT e INSERT;
     UPDATE, DELETE e TRUNCATE são revogados de forma explícita, além dos gatilhos;
   - `silver.previsoes_emitidas`: também INSERT; o resto de silver e gold é lido apenas;
   - sequências: USAGE e SELECT em `app` e `silver`;
   - tabelas futuras do dono: `app` recebe SELECT e INSERT; `silver`, `gold` e `public`, SELECT. Quem precisar de UPDATE
     ou DELETE numa tabela nova concede na própria migração (padrão seguro: o que não foi pensado não é alterável).
3. A senha é definida por `python -m climasense.admin criar-papel-app` (gerada com `secrets.token_urlsafe(32)`, nunca
   impressa), que grava no `.env` `DATABASE_URL` (papel da aplicação) e `DATABASE_URL_MIGRACOES` (dono).
4. `DATABASE_URL_MIGRACOES` é usada por Alembic (`backend/migrations/env.py`), pelo ETL (`python -m climasense.etl`) e
   pela execução de ETL disparada pela API (`POST /etl/execucoes`, que escreve em silver e gold). Sem ela, cai em
   `DATABASE_URL` (desenvolvimento e testes com um só usuário).
5. Os testes de integração rodam como dono para migrar e podem rodar as rotas como `climasense_app`
   (`TESTES_COMO_APP=1`; 80 passam, 11 falham só porque semeiam silver e gold, que o papel não escreve);
   `test_papel_aplicacao.py` prova as negações.

## Consequências

- A API em produção não deve ter `DATABASE_URL_MIGRACOES` no ambiente; sem ela, `POST /etl/execucoes` falha por
  permissão (o ETL passa a rodar fora da API, por agendamento). Enquanto a API e o ETL compartilharem o `.env`, o dono
  continua ao alcance da API: risco residual registrado em `docs/perguntas-abertas.md` pela sessão principal.
- Papéis são do servidor: o `downgrade` da 0014 revoga os privilégios, mas não apaga o papel.
- Trocar a senha: rodar `criar-papel-app` de novo.
