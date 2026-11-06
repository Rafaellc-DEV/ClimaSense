"""Privilégios do papel de banco da aplicação `climasense_app` (RNF-01, RNF-12, ADR 0014).

O papel é criado aqui SEM senha (não entra até alguém definir uma): a senha é definida por
`python -m climasense.admin criar-papel-app`, que a grava só no .env. Se quem roda a migração não puder criar papéis,
nada é concedido e a migração avisa (sem falhar), para não travar ambientes sem esse poder.

Regras:
- USAGE nos esquemas app, silver, gold e public; SELECT em todas as tabelas e views deles; sem CREATE em nenhum.
- app.*: SELECT, INSERT, UPDATE e DELETE; mas nas tabelas somente-inclusão (as que têm o gatilho
  `auditoria_imutavel` ou `somente_inclusao_evento`, mais `app.liberacoes_login`) só SELECT e INSERT.
  UPDATE, DELETE e TRUNCATE são revogados de forma explícita (os gatilhos continuam como segunda barreira).
- silver.previsoes_emitidas: também INSERT (a API grava as previsões emitidas). O resto de silver e gold é do ETL.
- Sequências: USAGE e SELECT em app e silver.
- Tabelas futuras criadas pelo dono: app recebe SELECT e INSERT; silver, gold e public, SELECT. Quem precisar de
  UPDATE ou DELETE numa tabela nova concede na própria migração.

Revisão: 0014
Anterior: 0013
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

UPGRADE = f"""
do $$
declare
  t record;
begin
  if not exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    begin
      create role {PAPEL} login nosuperuser nocreatedb nocreaterole noinherit nobypassrls;
    exception when insufficient_privilege then
      raise notice 'Sem permissão para criar o papel {PAPEL}: privilégios não concedidos.';
      return;
    end;
  end if;

  -- Nenhum papel comum cria objetos no esquema public (PostgreSQL < 15 permitia).
  execute 'revoke create on schema public from public';
  execute 'revoke create on schema public from {PAPEL}';
  execute 'grant usage on schema app, silver, gold, public to {PAPEL}';

  execute 'grant select on all tables in schema app, silver, gold, public to {PAPEL}';
  execute 'grant insert, update, delete on all tables in schema app to {PAPEL}';
  execute 'grant insert on silver.previsoes_emitidas to {PAPEL}';
  execute 'grant usage, select on all sequences in schema app, silver to {PAPEL}';

  -- Somente-inclusão: tudo que tem gatilho de imutabilidade, mais o registro de liberações de login.
  for t in
    select distinct c.oid::regclass::text as tabela
    from pg_trigger g
    join pg_class c on c.oid = g.tgrelid
    join pg_proc p on p.oid = g.tgfoid
    where not g.tgisinternal
      and p.proname in ('auditoria_imutavel', 'somente_inclusao_evento')
    union
    select 'app.liberacoes_login'
  loop
    execute format('revoke update, delete, truncate on %s from {PAPEL}', t.tabela);
  end loop;

  -- Sem DDL: o papel não é dono de nada e não recebe TRUNCATE, REFERENCES nem TRIGGER em tabela alguma.
  execute 'revoke truncate, references, trigger on all tables in schema app, silver, gold, public from {PAPEL}';

  execute 'alter default privileges in schema app grant select, insert on tables to {PAPEL}';
  execute 'alter default privileges in schema app grant usage, select on sequences to {PAPEL}';
  execute 'alter default privileges in schema silver, gold, public grant select on tables to {PAPEL}';
end $$;
"""

DOWNGRADE = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'alter default privileges in schema app revoke all on tables from {PAPEL}';
    execute 'alter default privileges in schema app revoke all on sequences from {PAPEL}';
    execute 'alter default privileges in schema silver, gold, public revoke all on tables from {PAPEL}';
    execute 'revoke all on all tables in schema app, silver, gold, public from {PAPEL}';
    execute 'revoke all on all sequences in schema app, silver from {PAPEL}';
    execute 'revoke all on schema app, silver, gold, public from {PAPEL}';
  end if;
end $$;
-- O papel em si fica (papéis são do servidor, não do banco); apague com DROP ROLE se quiser.
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
