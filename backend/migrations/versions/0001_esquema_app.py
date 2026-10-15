"""Esquema `app`: usuários, sessões, territórios, fontes, ETL, avaliações, comunicados, revisões e auditoria (T2.3).

Revisão: 0001
Anterior: nenhuma
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL = """
create schema if not exists app;

create table app.usuarios (
  id uuid primary key default gen_random_uuid(),
  nome varchar(120) not null check (length(trim(nome)) > 0),
  email varchar(254) not null,
  senha_hash text not null,
  papeis varchar(20)[] not null default '{}',
  ativo boolean not null default true,
  troca_senha_obrigatoria boolean not null default true,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  constraint usuarios_email_minusculo check (email = lower(email)),
  constraint usuarios_papeis_validos check (papeis <@ array['analista','revisor','coordenacao','administrador']::varchar[])
);
create unique index usuarios_email_unico on app.usuarios (email);

create table app.sessoes (
  id_hash char(64) primary key,
  usuario_id uuid not null references app.usuarios(id),
  csrf_hash char(64) not null,
  criada_em timestamptz not null default now(),
  ultimo_uso timestamptz not null,
  expira_em timestamptz not null,
  revogada boolean not null default false,
  ip inet,
  user_agent varchar(300)
);
create index sessoes_usuario on app.sessoes (usuario_id);

create table app.tentativas_login (
  id bigserial primary key,
  email varchar(254) not null,
  ip inet,
  em timestamptz not null,
  sucesso boolean not null
);
create index tentativas_login_email_em on app.tentativas_login (email, em desc);

create table app.territorios (
  id varchar(80) primary key,
  tipo varchar(10) not null check (tipo in ('municipio','distrito','bairro')),
  nome_oficial varchar(120) not null,
  nome_exibicao varchar(120) not null,
  pai_id varchar(80) references app.territorios(id),
  codigo_oficial varchar(20)
);

create table app.fontes (
  id varchar(60) primary key,
  nome varchar(160) not null,
  orgao varchar(160) not null,
  url text not null,
  tipo varchar(10) not null check (tipo in ('observada','prevista','derivada')),
  licenca varchar(120),
  conector varchar(120) not null,
  limite_desatualizacao_h integer not null default 24 check (limite_desatualizacao_h > 0),
  min_observacoes integer not null default 30 check (min_observacoes > 0),
  implementada boolean not null default false,
  ativa boolean not null default true
);

create table app.etl_execucoes (
  id uuid primary key default gen_random_uuid(),
  fonte_id varchar(60) not null references app.fontes(id),
  inicio timestamptz not null default now(),
  fim timestamptz,
  status varchar(15) not null check (status in ('em_andamento','sucesso','falha')),
  lidos integer not null default 0,
  gravados integer not null default 0,
  descartados integer not null default 0,
  motivos_descarte jsonb not null default '{}',
  erro text,
  disparado_por uuid references app.usuarios(id)
);
create index etl_execucoes_fonte_inicio on app.etl_execucoes (fonte_id, inicio desc);

create table app.avaliacoes (
  id uuid primary key default gen_random_uuid(),
  territorio_id varchar(80) not null references app.territorios(id),
  periodo_inicio date not null,
  periodo_fim date not null,
  estado varchar(15) not null check (estado in ('rascunho','em_revisao','aprovado','devolvido','encerrado')),
  versao_atual integer not null default 1,
  criado_por uuid not null references app.usuarios(id),
  criado_em timestamptz not null default now(),
  constraint avaliacoes_periodo check (periodo_inicio <= periodo_fim)
);

create table app.avaliacao_versoes (
  id uuid primary key default gen_random_uuid(),
  avaliacao_id uuid not null references app.avaliacoes(id),
  numero integer not null check (numero >= 1),
  prioridade varchar(20) not null check (prioridade in ('sem_indicacao','atencao','alerta','critico')),
  justificativa text not null check (length(trim(justificativa)) > 0),
  limitacoes text,
  evidencias jsonb not null default '[]',
  autor_id uuid not null references app.usuarios(id),
  criado_em timestamptz not null default now(),
  unique (avaliacao_id, numero)
);

create table app.comunicados (
  id uuid primary key default gen_random_uuid(),
  estado varchar(15) not null check (estado in ('rascunho','em_revisao','aprovado','devolvido','publicado','encerrado')),
  territorios varchar(80)[] not null check (cardinality(territorios) > 0),
  publico varchar(40) not null,
  nivel varchar(15) not null check (nivel in ('informativo','atencao','alerta','critico')),
  validade_inicio timestamptz not null,
  validade_fim timestamptz not null,
  versao_atual integer not null default 1,
  versao_aprovada integer,
  publicado_em timestamptz,
  publicado_por uuid references app.usuarios(id),
  avaliacao_id uuid references app.avaliacoes(id),
  constraint comunicados_validade check (validade_inicio < validade_fim),
  constraint comunicados_publicado_aprovado check (estado <> 'publicado' or versao_aprovada = versao_atual)
);
create index comunicados_publicados on app.comunicados (estado, validade_fim);

create table app.comunicado_versoes (
  id uuid primary key default gen_random_uuid(),
  comunicado_id uuid not null references app.comunicados(id),
  numero integer not null check (numero >= 1),
  titulo varchar(120) not null check (length(trim(titulo)) > 0),
  texto varchar(1200) not null,
  orientacoes varchar(300)[] not null default '{}' check (cardinality(orientacoes) <= 5),
  evidencias jsonb not null default '[]',
  autor_id uuid not null references app.usuarios(id),
  criado_em timestamptz not null default now(),
  hash_conteudo char(64) not null,
  unique (comunicado_id, numero)
);

create table app.revisoes (
  id uuid primary key default gen_random_uuid(),
  alvo varchar(12) not null check (alvo in ('avaliacao','comunicado')),
  versao_id uuid not null,
  revisor_id uuid not null references app.usuarios(id),
  decisao varchar(10) not null check (decisao in ('aprovar','devolver')),
  justificativa text,
  em timestamptz not null default now(),
  constraint revisoes_devolver_justificado check (decisao <> 'devolver' or length(trim(coalesce(justificativa,''))) > 0)
);

-- RN-05: ninguém aprova o próprio conteúdo. Garantido também no banco, não só no serviço.
create function app.revisor_diferente_do_autor() returns trigger language plpgsql as $$
declare autor uuid;
begin
  if new.alvo = 'avaliacao' then
    select autor_id into autor from app.avaliacao_versoes where id = new.versao_id;
  else
    select autor_id into autor from app.comunicado_versoes where id = new.versao_id;
  end if;
  if autor is null then
    raise exception 'Versão % não encontrada para revisão.', new.versao_id;
  end if;
  if autor = new.revisor_id then
    raise exception 'RN-05: o autor de uma versão não pode revisá-la.' using errcode = 'check_violation';
  end if;
  return new;
end $$;
create trigger revisoes_rn05 before insert on app.revisoes for each row execute function app.revisor_diferente_do_autor();

create table app.auditoria (
  id bigserial primary key,
  em timestamptz not null default now(),
  usuario_id uuid,
  acao varchar(60) not null,
  alvo_tipo varchar(40),
  alvo_id varchar(80),
  detalhes jsonb not null default '{}',
  ip inet
);
create index auditoria_em on app.auditoria (em desc);
create index auditoria_usuario_acao on app.auditoria (usuario_id, acao);
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute("drop schema if exists app cascade;")
