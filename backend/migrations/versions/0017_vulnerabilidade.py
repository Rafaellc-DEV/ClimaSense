"""Vulnerabilidade por bairro (PRD §7.1, RF-02, RF-03, RF-04, RF-25): equipamentos de saúde, população por faixa etária
e áreas de risco.

Só dados agregados e públicos (RN-13, RNF-03): equipamento é estabelecimento (não pessoa), população é contagem por
bairro e faixa, área de risco é polígono. `pessoas` nulo com `suprimido` = o IBGE ocultou a célula; nulo sem
`suprimido` = sem dado (RN-01). Quem grava é o ETL (conectores `cnes-equipamentos`, `ibge-censo-2022-bairro` e
`recife-areas-risco`); a aplicação só lê (ADR 0014).

Revisão: 0017
Anterior: 0016
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

SQL = """
create table silver.equipamentos_saude (
  cnes text primary key,
  nome text not null,
  tipo text,
  esfera text,
  bairro_id text,
  distrito_id text,
  latitude double precision check (latitude is null or latitude between -90 and 90),
  longitude double precision check (longitude is null or longitude between -180 and 180),
  fonte_id text not null references app.fontes(id),
  execucao_id uuid references app.etl_execucoes(id)
);
create index equipamentos_saude_bairro on silver.equipamentos_saude (bairro_id);
create index equipamentos_saude_distrito on silver.equipamentos_saude (distrito_id);

create table silver.populacao_bairro (
  bairro_id text not null,
  ano integer not null,
  faixa text not null check (faixa in ('0-4', '0-14', '60+', '80+', 'total')),
  pessoas integer check (pessoas is null or pessoas >= 0),
  suprimido boolean not null default false,
  fonte_id text not null references app.fontes(id),
  execucao_id uuid references app.etl_execucoes(id),
  primary key (bairro_id, ano, faixa)
);

create table silver.areas_risco (
  id text primary key,
  tipo text,
  grau text,
  regional text,
  bairro_id text,
  geometria jsonb not null,
  fonte_id text not null references app.fontes(id),
  execucao_id uuid references app.etl_execucoes(id)
);
create index areas_risco_bairro on silver.areas_risco (bairro_id);
"""

FONTES = [
    (
        "cnes-equipamentos",
        "Equipamentos de saúde do Recife (CNES)",
        "Ministério da Saúde / DATASUS (CNES)",
        "https://cnes.datasus.gov.br/",
        "observada",
        "Dados abertos (DATASUS)",
        "ConectorCnesEquipamentos",
        24 * 60,
        1,
    ),
    (
        "ibge-censo-2022-bairro",
        "População por faixa etária e bairro (Censo 2022)",
        "IBGE",
        "https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html",
        "observada",
        "CC BY 4.0",
        "ConectorIbgeCensoBairro",
        24 * 365 * 2,
        1,
    ),
    (
        "recife-areas-risco",
        "Áreas de risco de deslizamento e alagamento (Prefeitura do Recife)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/areas-de-risco",
        "observada",
        "ODbL",
        "ConectorRecifeAreasRisco",
        24 * 365,
        1,
    ),
]

GRANTS = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select on silver.equipamentos_saude, silver.populacao_bairro, silver.areas_risco to {PAPEL}';
  end if;
end $$;
"""


def upgrade() -> None:
    from sqlalchemy import text

    op.execute(SQL)
    conexao = op.get_bind()
    for f in FONTES:
        conexao.execute(
            text(
                "insert into app.fontes (id, nome, orgao, url, tipo, licenca, conector, limite_desatualizacao_h, "
                "min_observacoes, implementada) values (:a,:b,:c,:d,:e,:f,:g,:h,:i, true) "
                "on conflict (id) do update set nome = excluded.nome, orgao = excluded.orgao, url = excluded.url, "
                "licenca = excluded.licenca, conector = excluded.conector, "
                "limite_desatualizacao_h = excluded.limite_desatualizacao_h, "
                "min_observacoes = excluded.min_observacoes, implementada = true"
            ),
            dict(zip("abcdefghi", f, strict=True)),
        )
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute(
        "drop table if exists silver.areas_risco; drop table if exists silver.populacao_bairro; "
        "drop table if exists silver.equipamentos_saude"
    )
    op.execute(
        "delete from app.fontes f where f.id in ('cnes-equipamentos', 'ibge-censo-2022-bairro', "
        "'recife-areas-risco') and not exists (select 1 from app.etl_execucoes e where e.fonte_id = f.id)"
    )
