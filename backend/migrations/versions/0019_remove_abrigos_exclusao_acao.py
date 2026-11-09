"""Remove os abrigos do produto e libera a exclusão de ações (escopo novo do dono do projeto).

O que sai: `app.abrigos`, `app.abrigo_atualizacoes` (com gatilhos e privilégios do papel `climasense_app`, que
somem junto com as tabelas), a fonte `recife-abrigos` de `app.fontes` e as execuções de ETL dela.

Exclusão de ação (RF-15/RF-16): `app.acoes_resposta` já é editável pelo papel da aplicação (insert, update e
delete da 0014); o que impedia o DELETE era a chave estrangeira de `app.acao_eventos`, que é somente-inclusão.
A chave sai: o histórico da ação excluída fica guardado (sem apagar linha) e a exclusão é registrada na auditoria.
O papel continua sem UPDATE, DELETE nem TRUNCATE em `app.acao_eventos`.

`downgrade` recria as estruturas vazias (os registros de abrigo não voltam) e a chave como `not valid`.

Revisão: 0019
Anterior: 0018
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

UPGRADE = f"""
drop table if exists app.abrigo_atualizacoes;
drop table if exists app.abrigos;
delete from app.etl_execucoes where fonte_id = 'recife-abrigos';
delete from app.fontes where id = 'recife-abrigos';

alter table app.acao_eventos drop constraint if exists acao_eventos_acao_id_fkey;

do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select, insert, update, delete on app.acoes_resposta to {PAPEL}';
    execute 'revoke update, delete, truncate on app.acao_eventos from {PAPEL}';
  end if;
end $$;
"""

DOWNGRADE = f"""
alter table app.acao_eventos
  add constraint acao_eventos_acao_id_fkey foreign key (acao_id) references app.acoes_resposta(id) not valid;

create table app.abrigos (
  id uuid primary key default gen_random_uuid(),
  nome varchar(160) not null check (length(trim(nome)) > 0),
  bairro_id varchar(80) not null references app.territorios(id),
  endereco varchar(300),
  capacidade integer check (capacidade >= 0),
  aberto boolean not null default false,
  pessoas_abrigadas integer check (pessoas_abrigadas >= 0),
  desabrigados integer check (desabrigados >= 0),
  observacao varchar(1000),
  latitude double precision check (latitude between -90 and 90),
  longitude double precision check (longitude between -180 and 180),
  origem varchar(15) not null default 'manual' check (origem in ('manual','dados-abertos')),
  codigo_fonte varchar(80),
  criado_por uuid references app.usuarios(id),
  criado_em timestamptz not null default now(),
  atualizado_por uuid references app.usuarios(id),
  atualizado_em timestamptz not null default now(),
  fonte_url text,
  fonte_data date,
  tipo_local varchar(40),
  capacidade_fonte integer check (capacidade_fonte >= 0),
  status_origem varchar(10) check (status_origem in ('manual', 'cop')),
  status_lido_em timestamptz,
  constraint abrigos_manual_tem_autor check (origem <> 'manual' or criado_por is not null),
  constraint abrigos_coordenada_completa check ((latitude is null) = (longitude is null)),
  constraint abrigos_codigo_fonte_unico unique (origem, codigo_fonte)
);
create index abrigos_bairro on app.abrigos (bairro_id);

create table app.abrigo_atualizacoes (
  id bigserial primary key,
  abrigo_id uuid not null references app.abrigos(id),
  em timestamptz not null default now(),
  autor_id uuid references app.usuarios(id),
  aberto boolean not null,
  capacidade integer,
  pessoas_abrigadas integer,
  desabrigados integer,
  observacao varchar(1000),
  alteracoes jsonb not null default '{{}}'::jsonb
);
create index abrigo_atualizacoes_abrigo on app.abrigo_atualizacoes (abrigo_id, em desc);
create trigger abrigo_atualizacoes_somente_inclusao before update or delete on app.abrigo_atualizacoes
  for each row execute function app.somente_inclusao_evento();
create trigger abrigo_atualizacoes_sem_truncate before truncate on app.abrigo_atualizacoes
  for each statement execute function app.somente_inclusao_evento();

insert into app.fontes (id, nome, orgao, url, tipo, licenca, conector, limite_desatualizacao_h, min_observacoes,
                        implementada)
values ('recife-abrigos', 'Abrigos e pontos de apoio (Ação Inverno)', 'Prefeitura do Recife (Dados Abertos)',
        'https://dados.recife.pe.gov.br/dataset/abrigos-temporarios-disponiveis', 'observada', 'ODbL',
        'ConectorRecifeAbrigos', 8760, 1, true)
on conflict (id) do nothing;

do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select, insert, update, delete on app.abrigos to {PAPEL}';
    execute 'grant select, insert on app.abrigo_atualizacoes to {PAPEL}';
    execute 'grant usage, select on all sequences in schema app to {PAPEL}';
  end if;
end $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
