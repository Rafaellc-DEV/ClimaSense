"""Camada gold: agregados prontos para as telas, gerados SÓ por SQL a partir da silver (reproduzível, CA-04).

`verificar()` recalcula cada consulta e compara com a tabela gold; qualquer diferença é apontada.
"""

from __future__ import annotations

from sqlalchemy import Connection, text

VACINACAO = """
select substring(distrito_sanitario from '[0-9]+')::smallint as distrito_codigo,
       date_trunc('month', data_vacinacao)::date as mes,
       case when count(*) < :sup then null else count(*) end::integer as doses,
       count(*)::integer as amostra_n,
       cast(:total as integer) as total_fonte,
       count(*) < :sup as suprimido,
       cast(:ex as uuid) as execucao_id
from silver.vacinados
where execucao_id = cast(:ex as uuid) and distrito_sanitario ~ '^DS [1-8]$'
group by 1, 2
"""

CHUVA_DIARIA = """
with ultima as (
  select distinct on (fonte_id, territorio_id, observado_em) territorio_id, observado_em, valor, tipo
  from silver.observacoes where variavel = 'chuva_mm' and tipo in ('observada', 'derivada')
  order by fonte_id, territorio_id, observado_em, coletado_em desc
), distrito as (
  select territorio_id, (observado_em at time zone 'America/Recife')::date as dia,
         case when count(valor) > 0 then sum(valor) end as acumulado_mm,
         count(valor)::integer as n_observacoes,
         least(100, round(count(valor) * 100.0 / 24, 1))::double precision as cobertura_pct, tipo
  from ultima group by territorio_id, 2, tipo
)
select * from distrito
union all
select 'recife', dia, avg(acumulado_mm), sum(n_observacoes)::integer, avg(cobertura_pct), tipo
from distrito where territorio_id <> 'recife' group by dia, tipo
"""

CHUVA_MENSAL = """
select territorio_id, date_trunc('month', dia)::date as mes,
       case when count(acumulado_mm) > 0 then sum(acumulado_mm) end as acumulado_mm,
       count(acumulado_mm)::integer as dias_com_dado,
       round(count(acumulado_mm) * 100.0 / extract(day from (date_trunc('month', dia) + interval '1 month - 1 day')), 1)::double precision
         as cobertura_pct,
       tipo
from gold.chuva_diaria group by territorio_id, date_trunc('month', dia), tipo
"""

REFERENCIA = """
select territorio_id, extract(month from mes)::smallint as mes_do_ano,
       avg(acumulado_mm) as media_mm,
       percentile_cont(0.5) within group (order by acumulado_mm) as mediana_mm,
       array_agg(distinct extract(year from mes)::integer order by extract(year from mes)::integer) as anos_usados,
       avg(cobertura_pct) as cobertura_pct
from gold.chuva_mensal
where cobertura_pct >= 80 and mes < date_trunc('year', now())
group by territorio_id, extract(month from mes)
"""

TABELAS = {
    "gold.chuva_diaria": CHUVA_DIARIA,
    "gold.chuva_mensal": CHUVA_MENSAL,
    "gold.referencia_mensal": REFERENCIA,
}


def vacinacao(c: Connection, execucao_id: str, total_fonte: int | None, supressao: int) -> int:
    c.execute(text("delete from gold.vacinacao_distrito_mes"))
    return c.execute(
        text("insert into gold.vacinacao_distrito_mes " + VACINACAO),
        {"ex": execucao_id, "total": total_fonte, "sup": supressao},
    ).rowcount


def chuva(c: Connection) -> None:
    for tabela, consulta in TABELAS.items():  # em ordem: diária → mensal → referência
        c.execute(text(f"delete from {tabela}"))  # noqa: S608 — nomes fixos acima
        c.execute(text(f"insert into {tabela} {consulta}"))  # noqa: S608


def verificar(c: Connection) -> dict[str, int]:
    """Quantas linhas diferem entre a gold gravada e o recálculo a partir da silver (0 = reproduzível)."""
    diferencas = {}
    for tabela, consulta in TABELAS.items():
        n = c.execute(
            text(f"select count(*) from (({consulta}) except all (select * from {tabela})) a")
        ).scalar()  # noqa: S608
        n += c.execute(
            text(f"select count(*) from ((select * from {tabela}) except all ({consulta})) b")
        ).scalar()  # noqa: S608
        diferencas[tabela] = n
    return diferencas
