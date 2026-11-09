"""Cobertura territorial dos 94 bairros (RF-02, RF-04, RF-19): suscetibilidade a deslizamento, grau de risco dos
atendimentos da Defesa Civil e retrato do alagamento de 2026.

Só tabelas novas. Quem grava é o ETL (conectores `sgb-suscetibilidade-deslizamento`,
`recife-atendimentos-grau-risco` e `recife-alagamento-2026`); o papel `climasense_app` só tem SELECT (ADR 0014).

Silver:
- `silver.suscetibilidade_deslizamento`: fração e área de cada bairro por classe da carta SGB/CPRM (alta, media,
  baixa) e a fração coberta pela carta ("coberta"; o resto do bairro é sem dado, nunca "baixa").
- `silver.atendimentos_grau_risco`: contagem de atendimentos com grau R1 a R4 por bairro, ano e grau (agregado; nenhum
  endereço, RN-13).
- `silver.alagamento_2026`: comunidades alagadas (com `qtd_registros`) e, por bairro, lotes e trechos de rua alagados.
  Sem data por registro. Nenhuma coordenada de lote ou trecho (posição de imóvel é dado de residência).
Gold (por bairro, com rótulo, período, fonte e hora de atualização):
- `gold.indicador_territorial`: uma linha por (bairro, indicador) existente. Ausência NÃO vira zero: bairro sem linha
  = "Dados insuficientes" (RN-01, RN-02).
- `gold.cobertura_indicador`: em quantos dos bairros oficiais cada indicador existe (e em quantos o valor é positivo).

As tabelas gold não entram em `gold.verificar` (cada conector refaz as próprias linhas, por `fonte_id`).

Revisão: 0022
Anterior: a mais recente abaixo de 0022 que existir na pasta (0021 quando estiver presente)
"""

from pathlib import Path

from alembic import op


def _anterior() -> str:
    """Última revisão numerada abaixo de 0022: a cadeia 0020 e 0021 é de outras frentes e pode chegar depois; assim
    esta migração nunca cria uma segunda cabeça."""
    numeros = sorted(
        p.name[:4] for p in Path(__file__).parent.glob("[0-9][0-9][0-9][0-9]_*.py") if p.name[:4] < "0022"
    )
    return numeros[-1]


revision = "0022"
down_revision = _anterior()
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

SQL = """
create table silver.suscetibilidade_deslizamento (
  bairro_id text not null,
  classe text not null check (classe in ('alta', 'media', 'baixa', 'coberta')),
  area_km2 double precision not null check (area_km2 >= 0),
  fracao double precision not null check (fracao between 0 and 1),
  fonte_id text not null references app.fontes(id),
  execucao_id uuid references app.etl_execucoes(id),
  primary key (bairro_id, classe)
);

create table silver.atendimentos_grau_risco (
  bairro_id text not null,
  ano integer not null check (ano between 2000 and 2100),
  grau text not null check (grau in ('R1', 'R2', 'R3', 'R4')),
  atendimentos integer not null check (atendimentos > 0),
  fonte_id text not null references app.fontes(id),
  execucao_id uuid references app.etl_execucoes(id),
  primary key (bairro_id, ano, grau)
);

create table silver.alagamento_2026 (
  id text primary key,
  camada text not null check (camada in ('comunidades', 'lotes', 'trechos')),
  bairro_id text not null,
  comunidade text,
  rpa integer,
  itens integer not null check (itens >= 0),
  qtd_registros integer check (qtd_registros is null or qtd_registros >= 0),
  unidades_habitacionais integer check (unidades_habitacionais is null or unidades_habitacionais >= 0),
  fonte_id text not null references app.fontes(id),
  execucao_id uuid references app.etl_execucoes(id)
);
create index alagamento_2026_bairro on silver.alagamento_2026 (bairro_id);

create table gold.indicador_territorial (
  bairro_id text not null,
  indicador text not null,
  valor double precision not null check (valor >= 0),
  unidade text not null,
  rotulo text not null,
  periodo text not null,
  fonte_id text not null references app.fontes(id),
  atualizado_em timestamptz not null,
  primary key (bairro_id, indicador)
);
create index indicador_territorial_indicador on gold.indicador_territorial (indicador);

create table gold.cobertura_indicador (
  indicador text primary key,
  fonte_id text not null references app.fontes(id),
  rotulo text not null,
  periodo text not null,
  observacao text not null,
  bairros_com_dado integer not null check (bairros_com_dado >= 0),
  bairros_com_valor_positivo integer not null check (bairros_com_valor_positivo >= 0),
  bairros_total integer not null check (bairros_total >= 0),
  atualizado_em timestamptz not null
);
"""

FONTES = [
    (
        "sgb-suscetibilidade-deslizamento",
        "Suscetibilidade do terreno a deslizamento (carta SGB/CPRM 2012–2014)",
        "SGB/CPRM, publicada pela Prefeitura do Recife (ESIG)",
        "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted/Suscebilidade_Deslizamento/FeatureServer/0",
        "derivada",
        "Camada pública do portal ESIG Recife (licença não declarada na camada)",
        "ConectorSgbSuscetibilidadeDeslizamento",
        43800,
        1,
    ),
    (
        "recife-atendimentos-grau-risco",
        "Atendimentos da Defesa Civil com grau de risco R1 a R4 (por bairro e ano)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/registro-de-atendimentos-da-defesa-civil",
        "observada",
        "ODbL",
        "ConectorRecifeAtendimentosGrauRisco",
        13140,
        1,
    ),
    (
        "recife-alagamento-2026",
        "Alagamento de 2026: comunidades, lotes e trechos alagados (retrato sem data por registro)",
        "Prefeitura do Recife (ESIG)",
        "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted",
        "observada",
        "Camadas públicas do portal ESIG Recife (licença não declarada nas camadas)",
        "ConectorRecifeAlagamento2026",
        8760,
        1,
    ),
]

GRANTS = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select on silver.suscetibilidade_deslizamento, silver.atendimentos_grau_risco, '
            'silver.alagamento_2026, gold.indicador_territorial, gold.cobertura_indicador to {PAPEL}';
  end if;
end $$;
"""


def upgrade() -> None:
    from sqlalchemy import text

    # as fontes entram antes das tabelas que apontam para elas
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
    op.execute(SQL)
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute(
        "drop table if exists gold.cobertura_indicador; drop table if exists gold.indicador_territorial; "
        "drop table if exists silver.alagamento_2026; drop table if exists silver.atendimentos_grau_risco; "
        "drop table if exists silver.suscetibilidade_deslizamento"
    )
    op.execute(
        "delete from app.fontes f where f.id in ('sgb-suscetibilidade-deslizamento', "
        "'recife-atendimentos-grau-risco', 'recife-alagamento-2026') "
        "and not exists (select 1 from app.etl_execucoes e where e.fonte_id = f.id)"
    )
