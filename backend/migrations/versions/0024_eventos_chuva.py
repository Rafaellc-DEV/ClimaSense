"""Histórico de eventos de chuva e relatório executivo (RN-05, RN-01, RN-13, RF-19).

Duas tabelas em `app`:
- `eventos_chuva`: o evento (início, término, situação aberto -> encerrado -> aprovado, distritos afetados,
  situação final e pendências em texto curto, quem abriu, quem encerrou, quem aprovou e as horas). RN-05: quem
  abriu ou encerrou não aprova (restrição de banco, além da regra do serviço). Um evento aprovado não muda mais e
  nenhum evento é apagado (gatilho). O papel `climasense_app` ganha UPDATE só aqui (encerrar e aprovar); sem DELETE
  nem TRUNCATE.
- `evento_chuva_itens`: linha do tempo do evento (comunicado, estágio, ação ou observação), com fonte, hora,
  autor e número AGREGADO de equipes mobilizadas (nunca nomes de pessoas, RN-13). Somente-inclusão (gatilhos de
  `somente_inclusao_evento`); o papel só tem SELECT e INSERT.

Eventos antigos entram como retrospectivos (`retrospectivo`), sem linha do tempo horária.

Revisão: 0024
Anterior: a mais recente que existir na pasta (0023 quando as migrações 0020 a 0023 estiverem aplicadas)
"""

from pathlib import Path

from alembic import op


def _anterior() -> str:
    """Última revisão numerada abaixo de 0024 na pasta: a cadeia 0020 a 0023 é de outras frentes e pode chegar
    depois; assim esta migração nunca cria uma segunda cabeça. Com todas presentes, resulta em "0023"."""
    numeros = sorted(
        p.name[:4] for p in Path(__file__).parent.glob("[0-9][0-9][0-9][0-9]_*.py") if p.name[:4] < "0024"
    )
    return numeros[-1]


revision = "0024"
down_revision = _anterior()
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

SQL = """
create table app.eventos_chuva (
  id uuid primary key default gen_random_uuid(),
  nome varchar(160) not null check (length(trim(nome)) > 0),
  inicio_em timestamptz not null,
  fim_em timestamptz,
  situacao varchar(10) not null default 'aberto' check (situacao in ('aberto', 'encerrado', 'aprovado')),
  retrospectivo boolean not null default false,
  distritos_afetados varchar(80)[] not null default '{}',
  situacao_final varchar(1000),
  pendencias varchar(1000),
  aberto_por uuid not null references app.usuarios(id),
  aberto_em timestamptz not null default now(),
  encerrado_por uuid references app.usuarios(id),
  encerrado_em timestamptz,
  aprovado_por uuid references app.usuarios(id),
  aprovado_em timestamptz,
  constraint evento_chuva_fim_depois_do_inicio check (fim_em is null or fim_em >= inicio_em),
  constraint evento_chuva_situacao_coerente check (
    (situacao = 'aberto' and fim_em is null and encerrado_por is null and encerrado_em is null
       and aprovado_por is null and aprovado_em is null)
    or (situacao = 'encerrado' and fim_em is not null and encerrado_por is not null and encerrado_em is not null
       and length(trim(coalesce(situacao_final, ''))) > 0 and aprovado_por is null and aprovado_em is null)
    or (situacao = 'aprovado' and fim_em is not null and encerrado_por is not null and encerrado_em is not null
       and length(trim(coalesce(situacao_final, ''))) > 0 and aprovado_por is not null and aprovado_em is not null)
  ),
  -- RN-05: quem registra não aprova.
  constraint evento_chuva_ninguem_aprova_o_proprio check (
    aprovado_por is null or (aprovado_por <> aberto_por and aprovado_por <> encerrado_por)
  )
);
create index eventos_chuva_inicio on app.eventos_chuva (inicio_em desc);
create index eventos_chuva_situacao on app.eventos_chuva (situacao, inicio_em desc);

create table app.evento_chuva_itens (
  id bigserial primary key,
  evento_id uuid not null references app.eventos_chuva(id),
  tipo varchar(12) not null check (tipo in ('comunicado', 'estagio', 'acao', 'observacao')),
  texto varchar(500) not null check (length(trim(texto)) > 0),
  fonte varchar(160) not null check (length(trim(fonte)) > 0),
  estagio varchar(12) check (estagio is null or estagio in ('observacao', 'atencao', 'alerta', 'critico')),
  equipes_mobilizadas integer check (equipes_mobilizadas is null or equipes_mobilizadas >= 0),
  ocorrido_em timestamptz not null,
  autor_id uuid not null references app.usuarios(id),
  registrado_em timestamptz not null default now()
);
create index evento_chuva_itens_evento on app.evento_chuva_itens (evento_id, ocorrido_em, id);

create trigger evento_chuva_itens_somente_inclusao before update or delete on app.evento_chuva_itens
  for each row execute function app.somente_inclusao_evento();
create trigger evento_chuva_itens_sem_truncate before truncate on app.evento_chuva_itens
  for each statement execute function app.somente_inclusao_evento();

-- Evento: nunca apagado; aprovado não muda; só avança aberto -> encerrado -> aprovado; a abertura não se reescreve.
create or replace function app.evento_chuva_protege() returns trigger language plpgsql as $$
begin
  if tg_op <> 'UPDATE' then
    raise exception 'Evento de chuva não pode ser apagado.';
  end if;
  if old.situacao = 'aprovado' then
    raise exception 'Evento de chuva aprovado não pode mais ser alterado.';
  end if;
  if new.aberto_por <> old.aberto_por or new.aberto_em <> old.aberto_em or new.retrospectivo <> old.retrospectivo then
    raise exception 'A abertura do evento de chuva não pode ser reescrita.';
  end if;
  if (old.situacao = 'encerrado' and new.situacao = 'aberto') then
    raise exception 'Evento de chuva encerrado não volta a ficar aberto.';
  end if;
  return new;
end $$;
create trigger eventos_chuva_protege before update or delete on app.eventos_chuva
  for each row execute function app.evento_chuva_protege();
create trigger eventos_chuva_sem_truncate before truncate on app.eventos_chuva
  for each statement execute function app.evento_chuva_protege();
"""

GRANTS = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select, insert, update on app.eventos_chuva to {PAPEL}';
    execute 'revoke delete, truncate on app.eventos_chuva from {PAPEL}';
    execute 'grant select, insert on app.evento_chuva_itens to {PAPEL}';
    execute 'revoke update, delete, truncate on app.evento_chuva_itens from {PAPEL}';
    execute 'grant usage, select on all sequences in schema app to {PAPEL}';
  end if;
end $$;
"""


def upgrade() -> None:
    op.execute(SQL)
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute(
        """
        drop table if exists app.evento_chuva_itens;
        drop table if exists app.eventos_chuva;
        drop function if exists app.evento_chuva_protege();
        """
    )
