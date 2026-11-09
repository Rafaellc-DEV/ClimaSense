"""Hidrologia: nível dos rios e reservatórios do Capibaribe (fontes `apac-rios` e `apac-reservatorios`).

Só tabelas novas (mais as duas linhas de `app.fontes`, que as execuções do ETL exigem):

- silver.rios_estacoes: cadastro das estações de rio monitoradas (rio, bacia, municípios, coordenadas);
- silver.rios_leituras: nível em cm por estação, fonte (apac | ana) e hora da leitura; os limiares oficiais da estação
  (pré-alerta, alerta, enchente) ficam na própria leitura da APAC;
- silver.reservatorios e silver.reservatorios_leituras: cadastro e leitura diária (cota, volume, status oficial);
- silver.rio_referencia_territorio: ligação bairro (território) ↔ estação de rio de referência. NASCE VAZIA de
  propósito: o PRD não traz essa ligação e inferir inundação por território é decisão de ADR futuro, com selo
  "Experimental" (RN-11). Ver docs/perguntas-abertas.md;
- gold.rio_situacao: classe do rio por estação (abaixo_pre_alerta, pre_alerta, alerta, enchente, dados_insuficientes);
- gold.reservatorio_situacao: status do reservatório ou dados_insuficientes.

O papel `climasense_app` só tem SELECT em todas (o ETL grava), de forma explícita, além do privilégio padrão (ADR 0014).

Revisão: 0020
Anterior: 0019
"""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

PAPEL = "climasense_app"
TABELAS = (
    "silver.rios_estacoes",
    "silver.rios_leituras",
    "silver.reservatorios",
    "silver.reservatorios_leituras",
    "silver.rio_referencia_territorio",
    "gold.rio_situacao",
    "gold.reservatorio_situacao",
)

SQL = """
create table silver.rios_estacoes (
  codigo varchar(20) primary key,
  nome varchar(160) not null,
  rio varchar(160),
  bacia varchar(80),
  municipios text,
  codigos_municipio text[] not null default '{}',
  inclui_recife boolean not null default false,
  lat double precision not null check (lat between -90 and 90),
  lon double precision not null check (lon between -180 and 180),
  fonte_id varchar(60) not null references app.fontes(id),
  atualizado_em timestamptz not null
);

create table silver.rios_leituras (
  id bigserial primary key,
  estacao_codigo varchar(20) not null references silver.rios_estacoes(codigo),
  fonte varchar(10) not null check (fonte in ('apac', 'ana')),
  lida_em timestamptz not null,
  nivel_cm double precision check (nivel_cm is null or nivel_cm >= 0),
  pre_alerta_cm double precision,
  alerta_cm double precision,
  enchente_cm double precision,
  vazao_m3s double precision check (vazao_m3s is null or vazao_m3s >= 0),
  alerta_pcd varchar(1) check (alerta_pcd is null or alerta_pcd in ('S', 'N')),
  recente smallint check (recente is null or recente in (0, 1)),
  coletado_em timestamptz not null,
  visto_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  constraint rios_leitura_unica unique (estacao_codigo, fonte, lida_em),
  constraint rios_limiares_completos check (
    (pre_alerta_cm is null and alerta_cm is null and enchente_cm is null)
    or (pre_alerta_cm is not null and alerta_cm is not null and enchente_cm is not null
        and pre_alerta_cm > 0 and pre_alerta_cm < alerta_cm and alerta_cm < enchente_cm)
  )
);
create index rios_leituras_recentes on silver.rios_leituras (estacao_codigo, lida_em desc);

create table silver.reservatorios (
  codigo_estacao integer primary key,
  nome varchar(160) not null,
  municipio varchar(160),
  bacia varchar(80),
  lat double precision check (lat is null or lat between -90 and 90),
  lon double precision check (lon is null or lon between -180 and 180),
  capacidade_m3 double precision check (capacidade_m3 is null or capacidade_m3 >= 0),
  uso_principal varchar(160),
  fonte_id varchar(60) not null references app.fontes(id),
  atualizado_em timestamptz not null
);

create table silver.reservatorios_leituras (
  id bigserial primary key,
  codigo_estacao integer not null references silver.reservatorios(codigo_estacao),
  data_leitura date not null,
  cota_m double precision,
  volume_m3 double precision check (volume_m3 is null or volume_m3 >= 0),
  volume_pct double precision check (volume_pct is null or volume_pct >= 0),
  status varchar(60),
  cor varchar(30),
  coletado_em timestamptz not null,
  visto_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  constraint reservatorio_leitura_unica unique (codigo_estacao, data_leitura)
);

-- Referência bairro ↔ rio: vazia até haver decisão documentada (ADR) e fonte da ligação. Nada é inferido.
create table silver.rio_referencia_territorio (
  territorio_id varchar(80) not null references app.territorios(id),
  estacao_codigo varchar(20) not null references silver.rios_estacoes(codigo),
  base_documental text not null check (length(trim(base_documental)) > 0),
  decidido_em date not null,
  primary key (territorio_id, estacao_codigo)
);

create table gold.rio_situacao (
  estacao_codigo varchar(20) primary key,
  nome varchar(160) not null,
  rio varchar(160),
  bacia varchar(80),
  municipios text,
  inclui_recife boolean not null,
  lat double precision not null,
  lon double precision not null,
  classe varchar(20) not null check (
    classe in ('abaixo_pre_alerta', 'pre_alerta', 'alerta', 'enchente', 'dados_insuficientes')
  ),
  motivo varchar(20) check (motivo is null or motivo in ('sem_leitura', 'leitura_antiga', 'sem_limiares')),
  nivel_cm double precision,
  pre_alerta_cm double precision,
  alerta_cm double precision,
  enchente_cm double precision,
  lida_em timestamptz,
  fonte_leitura varchar(10),
  fontes text[],
  referencia_em timestamptz,
  idade_min integer,
  desatualizada boolean
);

create table gold.reservatorio_situacao (
  codigo_estacao integer primary key,
  nome varchar(160) not null,
  municipio varchar(160),
  bacia varchar(80),
  capacidade_m3 double precision,
  data_leitura date,
  cota_m double precision,
  volume_pct double precision,
  status varchar(60),
  situacao varchar(20) not null check (
    situacao in ('vertendo', 'entre_80_e_100', 'entre_30_e_80', 'entre_10_e_30', 'colapso', 'dados_insuficientes')
  ),
  motivo varchar(20) check (motivo is null or motivo in ('sem_leitura', 'leitura_antiga', 'status_desconhecido')),
  referencia_em timestamptz,
  idade_dias integer
);
"""

FONTES = [
    # id, nome, órgão, url, tipo, licença, conector, limite_h, min_obs
    (
        "apac-rios",
        "Nível dos rios do Capibaribe e vizinhos (APAC, com ANA como segunda fonte)",
        "APAC — Agência Pernambucana de Águas e Clima / ANA (SGB)",
        "https://api.apac.pe.gov.br/api.php",
        "observada",
        None,
        "ConectorApacRios",
        3,
        1,
    ),
    (
        "apac-reservatorios",
        "Reservatórios do Capibaribe (Tapacurá, Goitá, Carpina e Matriz da Luz)",
        "APAC — Agência Pernambucana de Águas e Clima",
        "https://api.apac.pe.gov.br/api.php",
        "observada",
        None,
        "ConectorApacReservatorios",
        30,
        1,
    ),
]

PERMISSOES = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select on {", ".join(TABELAS)} to {PAPEL}';
    execute 'revoke insert, update, delete, truncate, references, trigger on {", ".join(TABELAS)} from {PAPEL}';  end if;
end $$;
"""


def upgrade() -> None:
    from sqlalchemy import text

    conexao = op.get_bind()
    for f in FONTES:
        conexao.execute(
            text(
                "insert into app.fontes (id, nome, orgao, url, tipo, licenca, conector, limite_desatualizacao_h, "
                "min_observacoes, implementada) values (:a,:b,:c,:d,:e,:f,:g,:h,:i, true) "
                "on conflict (id) do update set nome = excluded.nome, orgao = excluded.orgao, url = excluded.url, "
                "conector = excluded.conector, limite_desatualizacao_h = excluded.limite_desatualizacao_h, "
                "min_observacoes = excluded.min_observacoes, implementada = true"
            ),
            dict(zip("abcdefghi", f, strict=True)),
        )
    op.execute(SQL)
    op.execute(PERMISSOES)


def downgrade() -> None:
    op.execute(
        """
        drop table if exists gold.reservatorio_situacao;
        drop table if exists gold.rio_situacao;
        drop table if exists silver.rio_referencia_territorio;
        drop table if exists silver.reservatorios_leituras;
        drop table if exists silver.reservatorios;
        drop table if exists silver.rios_leituras;
        drop table if exists silver.rios_estacoes;
        delete from app.etl_execucoes where fonte_id in ('apac-rios', 'apac-reservatorios');
        delete from app.fontes where id in ('apac-rios', 'apac-reservatorios');
        """
    )
