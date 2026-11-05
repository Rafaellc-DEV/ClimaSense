"""Saúde depois da chuva (specs/foco-chuvas.md §9): dengue e chikungunya (InfoDengue), leptospirose (SINAN),
arboviroses por bairro e ano (Dados Abertos do Recife) e deslizamentos da Defesa Civil.

- silver.infodengue_semanal: uma linha por agravo × semana epidemiológica (casos notificados, estimativa de
  nowcasting com IC 95%, Rt, nível de alerta 1–4, `incompleta`);
- silver.leptospirose_semanal: residentes do Recife por semana de início dos sintomas (notificados, confirmados,
  descartados, em investigação, óbitos, expostos a enchente; `incompleta`, `preliminar`);
- gold.saude_semanal: série única para as telas (InfoDengue + SINAN), gerada só por SQL;
- silver.arboviroses_bairro_ano: SOMENTE contagens por bairro escrito na fonte × ano (nenhum campo pessoal);
  `territorio_id` nulo quando o nome não casa com um bairro oficial;
- gold.arboviroses_bairro_ano: por bairro oficial (casos = confirmados);
- gold.ocorrencias_bairro: atendimentos da Defesa Civil por tipo (alagamento, deslizamento) e bairro, com o
  primeiro e o último dia — "onde já aconteceu". `silver.ocorrencias.tipo` já distingue os tipos (0002); aqui só
  ganha a restrição dos valores aceitos;
- app.fontes: `infodengue`, `sinan-leptospirose`, `recife-arboviroses`; `recife-alagamento` passa a se chamar
  "alagamento e deslizamento".

Revisão: 0011
Anterior: 0010
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

SQL = """
create table silver.infodengue_semanal (
  agravo varchar(20) not null check (agravo in ('dengue', 'chikungunya')),
  ano smallint not null,
  semana smallint not null check (semana between 1 and 53),
  inicio date not null,
  casos integer check (casos is null or casos >= 0),
  casos_est double precision check (casos_est is null or casos_est >= 0),
  casos_est_min double precision,
  casos_est_max double precision,
  rt double precision,
  p_rt1 double precision,
  p_inc100k double precision,
  nivel smallint check (nivel is null or nivel between 1 and 4),
  nivel_inc smallint,
  receptivo smallint,
  transmissao smallint,
  versao_modelo varchar(20),
  incompleta boolean not null,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (agravo, ano, semana)
);

create table silver.leptospirose_semanal (
  ano smallint not null,
  semana smallint not null check (semana between 1 and 53),
  inicio date not null,
  notificados integer not null check (notificados >= 0),
  confirmados integer not null check (confirmados >= 0),
  descartados integer not null check (descartados >= 0),
  em_investigacao integer not null check (em_investigacao >= 0),
  obitos integer not null check (obitos >= 0),
  expostos_enchente integer not null check (expostos_enchente >= 0),
  incompleta boolean not null,
  preliminar boolean not null,
  ultima_notificacao date not null,
  versao_fonte varchar(300),
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (ano, semana)
);

create table gold.saude_semanal (
  agravo varchar(20) not null,
  fonte_id varchar(60) not null,
  ano smallint not null,
  semana smallint not null,
  inicio date not null,
  casos integer,
  confirmados integer,
  casos_estimados double precision,
  ic_inf double precision,
  ic_sup double precision,
  nivel_alerta smallint,
  rt double precision,
  incompleta boolean not null,
  primary key (agravo, ano, semana)
);
create index saude_semanal_inicio on gold.saude_semanal (agravo, inicio desc);

create table silver.arboviroses_bairro_ano (
  id bigserial primary key,
  agravo varchar(20) not null check (agravo in ('dengue', 'chikungunya')),
  ano smallint not null,
  bairro_fonte varchar(120) not null,
  territorio_id varchar(80) references app.territorios(id),
  notificados integer not null check (notificados >= 0),
  confirmados integer not null check (confirmados >= 0),
  descartados integer not null check (descartados >= 0),
  outros integer not null check (outros >= 0),
  fonte_atualizada_em date,
  execucao_id uuid not null references app.etl_execucoes(id),
  constraint arbovirose_bairro_ano_unico unique (agravo, ano, bairro_fonte)
);

create table gold.arboviroses_bairro_ano (
  agravo varchar(20) not null,
  ano smallint not null,
  bairro_id varchar(80) not null references app.territorios(id),
  distrito_id varchar(80) references app.territorios(id),
  casos integer not null,
  notificados integer not null,
  primary key (agravo, ano, bairro_id)
);

alter table silver.ocorrencias add constraint ocorrencias_tipo_check
  check (tipo in ('alagamento', 'deslizamento')) not valid;

create table gold.ocorrencias_bairro (
  tipo varchar(20) not null,
  territorio_id varchar(80) not null references app.territorios(id),
  distrito_id varchar(80) references app.territorios(id),
  registros integer not null,
  dias_com_registro integer not null,
  primeiro_dia date not null,
  ultimo_dia date not null,
  primary key (tipo, territorio_id)
);
"""

FONTES = [
    # id, nome, órgão, url, tipo, licença, conector, limite_h, min_obs
    (
        "infodengue",
        "Dengue e chikungunya no Recife por semana (InfoDengue)",
        "InfoDengue — Fiocruz / FGV",
        "https://info.dengue.mat.br/services/api",
        "derivada",
        None,
        "ConectorInfoDengue",
        24 * 10,  # a série muda uma vez por semana
        52,
    ),
    (
        "sinan-leptospirose",
        "Leptospirose no Recife por semana de sintomas (SINAN)",
        "Ministério da Saúde — DATASUS / SINAN",
        "https://datasus.saude.gov.br/transferencia-de-arquivos/",
        "observada",
        None,
        "ConectorSinanLeptospirose",
        24 * 21,  # o DATASUS republica o preliminar a cada 1–3 semanas
        52,
    ),
    (
        "recife-arboviroses",
        "Dengue e chikungunya por bairro e ano (Secretaria de Saúde do Recife)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya",
        "observada",
        "ODbL",
        "ConectorRecifeArboviroses",
        24 * 400,  # publicação anual
        1,
    ),
]


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
    conexao.execute(
        text(
            "update app.fontes set nome = 'Atendimentos de alagamento e deslizamento da Defesa Civil (por bairro e dia)' "
            "where id = 'recife-alagamento'"
        )
    )


def downgrade() -> None:
    op.execute(
        """
        drop table if exists gold.ocorrencias_bairro;
        alter table silver.ocorrencias drop constraint if exists ocorrencias_tipo_check;
        delete from silver.ocorrencias where tipo = 'deslizamento';
        drop table if exists gold.arboviroses_bairro_ano;
        drop table if exists silver.arboviroses_bairro_ano;
        drop table if exists gold.saude_semanal;
        drop table if exists silver.leptospirose_semanal;
        drop table if exists silver.infodengue_semanal;
        update app.fontes set nome = 'Atendimentos de alagamento da Defesa Civil (por bairro e dia)'
          where id = 'recife-alagamento';
        delete from app.fontes f where f.id in ('infodengue', 'sinan-leptospirose', 'recife-arboviroses')
          and not exists (select 1 from app.etl_execucoes e where e.fonte_id = f.id);
        update app.fontes set implementada = false
          where id in ('infodengue', 'sinan-leptospirose', 'recife-arboviroses');
        """
    )
