"""Evento de chuva (specs/foco-chuvas.md): estágio operacional por território, limiares com histórico,
abrigos com histórico de atualizações e ações de resposta com linha do tempo (F1, F3, F4).

Tudo é só inclusão onde é histórico: declarações de estágio, versões de limiares, atualizações de abrigo e
eventos de ação não são alterados nem apagados (triggers, como a auditoria da 0003).

Revisão: 0007
Anterior: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SQL = """
create table app.estagio_parametros (
  versao serial primary key,
  limiares jsonb not null,
  justificativa text,
  autor_id uuid references app.usuarios(id),
  criado_em timestamptz not null default now()
);

create table app.estagio_declaracoes (
  id uuid primary key default gen_random_uuid(),
  territorio_id varchar(80) not null references app.territorios(id),
  estagio varchar(12) not null check (estagio in ('observacao','atencao','alerta','critico')),
  justificativa text not null check (length(trim(justificativa)) > 0),
  sugerido jsonb not null default '{}'::jsonb,
  lote_id uuid not null,
  autor_id uuid not null references app.usuarios(id),
  declarado_em timestamptz not null default now()
);
create index estagio_declaracoes_territorio on app.estagio_declaracoes (territorio_id, declarado_em desc);
create index estagio_declaracoes_em on app.estagio_declaracoes (declarado_em desc);

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
  -- registro manual sempre tem autor; a pré-carga do CKAN (abrigos-temporarios-disponiveis) vem sem pessoa
  constraint abrigos_manual_tem_autor check (origem <> 'manual' or criado_por is not null),
  constraint abrigos_coordenada_completa check ((latitude is null) = (longitude is null)),
  constraint abrigos_codigo_fonte_unico unique (origem, codigo_fonte)
);
create index abrigos_bairro on app.abrigos (bairro_id);

create table app.abrigo_atualizacoes (
  id bigserial primary key,
  abrigo_id uuid not null references app.abrigos(id),
  em timestamptz not null default now(),
  autor_id uuid references app.usuarios(id),  -- null só em carga automática (origem dados-abertos)
  aberto boolean not null,
  capacidade integer,
  pessoas_abrigadas integer,
  desabrigados integer,
  observacao varchar(1000),
  alteracoes jsonb not null default '{}'::jsonb
);
create index abrigo_atualizacoes_abrigo on app.abrigo_atualizacoes (abrigo_id, em desc);

create table app.acoes_resposta (
  id uuid primary key default gen_random_uuid(),
  territorio_id varchar(80) not null references app.territorios(id),
  tipo varchar(30) not null check (tipo in
    ('orientacao','visita','distribuicao_insumos','vigilancia_agravo','articulacao','outro')),
  descricao varchar(2000) not null check (length(trim(descricao)) > 0),
  responsavel varchar(160),
  situacao varchar(15) not null check (situacao in ('planejada','em_andamento','concluida','cancelada')),
  inicio_em timestamptz,
  fim_em timestamptz,
  licao_aprendida varchar(2000),
  criado_por uuid not null references app.usuarios(id),
  criado_em timestamptz not null default now(),
  atualizado_por uuid not null references app.usuarios(id),
  atualizado_em timestamptz not null default now(),
  constraint acoes_resposta_fim_depois_do_inicio check (fim_em is null or inicio_em is null or fim_em >= inicio_em)
);
create index acoes_resposta_territorio on app.acoes_resposta (territorio_id, situacao);

create table app.acao_eventos (
  id bigserial primary key,
  acao_id uuid not null references app.acoes_resposta(id),
  em timestamptz not null default now(),
  autor_id uuid not null references app.usuarios(id),
  situacao varchar(15) not null,
  texto varchar(400) not null,
  alteracoes jsonb not null default '{}'::jsonb
);
create index acao_eventos_acao on app.acao_eventos (acao_id, em);

create or replace function app.somente_inclusao_evento() returns trigger language plpgsql as $$
begin
  raise exception 'Histórico do evento só aceita inclusões (%).', tg_table_name;
end $$;
"""

HISTORICOS = ("estagio_parametros", "estagio_declaracoes", "abrigo_atualizacoes", "acao_eventos")


def upgrade() -> None:
    op.execute(SQL)
    for t in HISTORICOS:
        op.execute(
            f"create trigger {t}_somente_inclusao before update or delete on app.{t} "
            "for each row execute function app.somente_inclusao_evento()"
        )
        op.execute(
            f"create trigger {t}_sem_truncate before truncate on app.{t} "
            "for each statement execute function app.somente_inclusao_evento()"
        )


def downgrade() -> None:
    op.execute(
        """
        drop table if exists app.acao_eventos;
        drop table if exists app.acoes_resposta;
        drop table if exists app.abrigo_atualizacoes;
        drop table if exists app.abrigos;
        drop table if exists app.estagio_declaracoes;
        drop table if exists app.estagio_parametros;
        drop function if exists app.somente_inclusao_evento();
        """
    )
