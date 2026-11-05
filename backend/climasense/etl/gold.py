"""Camada gold: agregados prontos para as telas, gerados SÓ por SQL a partir da silver (reproduzível, CA-04).

`verificar()` recalcula cada consulta e compara com a tabela gold; qualquer diferença é apontada.
"""

from __future__ import annotations

from sqlalchemy import Connection, text

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

# ------------------------------------------------------------------ APAC (pluviômetros observados)
# Estação → bairro (ponto-em-polígono) e distrito do bairro; estação fora da malha de bairros fica no distrito.
_ESTACOES_APAC = """
est_apac as (
  select e.id, case when t.tipo = 'bairro' then t.id end as bairro_id,
         case when t.tipo = 'bairro' then t.pai_id else t.id end as distrito_id
  from silver.estacoes e join app.territorios t on t.id = e.territorio_id
  where e.fonte_id = 'apac-chuva' and t.tipo in ('bairro', 'distrito')
)"""

# Território → própria estatística; sem estação válida, a do distrito; sem ela, a do Recife (RN-07).
_HERANCA = """
from app.territorios t {dias}
left join agg own on own.territorio_id = t.id {dia_own}
left join agg pai on pai.territorio_id = t.pai_id {dia_pai}
left join agg rec on rec.territorio_id = 'recife' {dia_rec}
"""

CHUVA_APAC_AGORA = (
    "with ref as (select max(visto_em) as referencia_em from silver.apac_chuva_leituras),"
    + _ESTACOES_APAC
    + """,
ultima as (
  select distinct on (estacao_id) estacao_id, lida_em from silver.apac_chuva_leituras
  order by estacao_id, lida_em desc
), est as (
  select ea.id, ea.bairro_id, ea.distrito_id, u.lida_em,
         (select referencia_em from ref) - u.lida_em <= interval '120 minutes' as atualizada,
         max(l.valor_mm) filter (where l.janela_h = 24) as v24,
         max(l.valor_mm) filter (where l.janela_h = 1) as v1
  from ultima u join est_apac ea on ea.id = u.estacao_id
  join silver.apac_chuva_leituras l on l.estacao_id = u.estacao_id and l.lida_em = u.lida_em
  group by ea.id, ea.bairro_id, ea.distrito_id, u.lida_em
), por_territorio as (
  select distrito_id as territorio_id, est.* from est
  union all select bairro_id, est.* from est where bairro_id is not null
  union all select 'recife', est.* from est
), agg as (
  select territorio_id,
         max(v24) filter (where atualizada) as max24,
         percentile_cont(0.5) within group (order by v24) filter (where atualizada) as med24,
         max(v1) filter (where atualizada) as max1,
         count(*)::integer as n, count(v24) filter (where atualizada)::integer as nat,
         max(lida_em) filter (where atualizada) as lida,
         array_agg(id order by id)::text[] as estacoes
  from por_territorio group by territorio_id
), escolha as (
  select t.id, t.tipo,
         case when own.nat > 0 then own.territorio_id when pai.nat > 0 then pai.territorio_id
              when rec.nat > 0 then rec.territorio_id
              else coalesce(own.territorio_id, pai.territorio_id, rec.territorio_id) end as origem
"""
    + _HERANCA.format(dias="", dia_own="", dia_pai="", dia_rec="")
    + """  where t.tipo in ('bairro', 'distrito', 'municipio')
)
select e.id, e.tipo, a.max24, a.med24, a.max1, a.n, a.nat, a.lida, (select referencia_em from ref),
       case when a.territorio_id <> e.id then a.territorio_id end, a.estacoes
from escolha e join agg a on a.territorio_id = e.origem
"""
)

CHUVA_APAC_DIARIA = (
    "with"
    + _ESTACOES_APAC
    + """,
d as (
  select ea.id, ea.bairro_id, ea.distrito_id, c.dia, c.valor_mm
  from silver.apac_chuva_diaria c join est_apac ea on ea.id = c.estacao_id where c.valor_mm is not null
), por_territorio as (
  select distrito_id as territorio_id, d.* from d
  union all select bairro_id, d.* from d where bairro_id is not null
  union all select 'recife', d.* from d
), agg as (
  select territorio_id, dia, max(valor_mm) as mx, percentile_cont(0.5) within group (order by valor_mm) as med,
         count(*)::integer as n
  from por_territorio group by territorio_id, dia
), dias as (select distinct dia from agg)
select t.id, dd.dia, t.tipo,
       coalesce(own.mx, pai.mx, rec.mx), coalesce(own.med, pai.med, rec.med), coalesce(own.n, pai.n, rec.n),
       case when own.n is not null then null when pai.n is not null then t.pai_id else 'recife' end
"""
    + _HERANCA.format(
        dias="cross join dias dd",
        dia_own="and own.dia = dd.dia",
        dia_pai="and pai.dia = dd.dia",
        dia_rec="and rec.dia = dd.dia",
    )
    + "where t.tipo in ('bairro', 'distrito', 'municipio') and coalesce(own.n, pai.n, rec.n) is not null\n"
)

# ------------------------------------------------------------------ alagamento (Defesa Civil)
ALAGAMENTO_BAIRRO_DIA = """
select o.territorio_id, t.pai_id, (o.registrado_em at time zone 'America/Recife')::date as dia,
       count(*)::integer as registros
from silver.ocorrencias o join app.territorios t on t.id = o.territorio_id
where o.fonte_id = 'recife-alagamento' and o.tipo = 'alagamento'  -- deslizamento fica em gold.ocorrencias_bairro
group by o.territorio_id, t.pai_id, (o.registrado_em at time zone 'America/Recife')::date
"""

# "Onde já aconteceu": atendimentos por tipo (alagamento, deslizamento) e bairro, com o primeiro e o último dia
OCORRENCIAS_BAIRRO = """
select o.tipo, o.territorio_id, t.pai_id, count(*)::integer as registros,
       count(distinct (o.registrado_em at time zone 'America/Recife')::date)::integer as dias_com_registro,
       min((o.registrado_em at time zone 'America/Recife')::date) as primeiro_dia,
       max((o.registrado_em at time zone 'America/Recife')::date) as ultimo_dia
from silver.ocorrencias o join app.territorios t on t.id = o.territorio_id
where t.tipo = 'bairro'
group by o.tipo, o.territorio_id, t.pai_id
"""

# ------------------------------------------------------------------ saúde depois da chuva
# Série semanal única para as telas: InfoDengue (dengue, chikungunya) e SINAN (leptospirose, sem nowcasting).
SAUDE_SEMANAL = """
select agravo, 'infodengue'::varchar as fonte_id, ano, semana, inicio, casos, null::integer as confirmados,
       casos_est, casos_est_min, casos_est_max, nivel, rt, incompleta
from silver.infodengue_semanal
union all
select 'leptospirose', 'sinan-leptospirose', ano, semana, inicio, notificados, confirmados,
       null, null, null, null, null, incompleta
from silver.leptospirose_semanal
"""

# Por bairro oficial (o que não casou com um bairro fica só na silver e entra no total da rota)
ARBOVIROSES_BAIRRO_ANO = """
select a.agravo, a.ano, a.territorio_id, t.pai_id, sum(a.confirmados)::integer, sum(a.notificados)::integer
from silver.arboviroses_bairro_ano a join app.territorios t on t.id = a.territorio_id
group by a.agravo, a.ano, a.territorio_id, t.pai_id
"""

TABELAS_APAC_AGORA = {"gold.chuva_apac_agora": CHUVA_APAC_AGORA}
TABELAS_APAC_DIARIA = {"gold.chuva_apac_diaria": CHUVA_APAC_DIARIA}
TABELAS_ALAGAMENTO = {"gold.alagamento_bairro_dia": ALAGAMENTO_BAIRRO_DIA}
TABELAS_OCORRENCIAS = {"gold.ocorrencias_bairro": OCORRENCIAS_BAIRRO}
TABELAS_SAUDE = {"gold.saude_semanal": SAUDE_SEMANAL}
TABELAS_ARBOVIROSES = {"gold.arboviroses_bairro_ano": ARBOVIROSES_BAIRRO_ANO}
VERIFICADAS = {
    **TABELAS,
    **TABELAS_APAC_AGORA,
    **TABELAS_APAC_DIARIA,
    **TABELAS_ALAGAMENTO,
    **TABELAS_OCORRENCIAS,
    **TABELAS_SAUDE,
    **TABELAS_ARBOVIROSES,
}


def recalcular(c: Connection, tabelas: dict[str, str]) -> None:
    for tabela, consulta in tabelas.items():  # na ordem do dicionário (ex.: diária → mensal → referência)
        c.execute(text(f"delete from {tabela}"))  # noqa: S608 — nomes fixos acima
        c.execute(text(f"insert into {tabela} {consulta}"))  # noqa: S608


def chuva(c: Connection) -> None:
    recalcular(c, TABELAS)


def verificar(c: Connection) -> dict[str, int]:
    """Quantas linhas diferem entre a gold gravada e o recálculo a partir da silver (0 = reproduzível)."""
    diferencas = {}
    for tabela, consulta in VERIFICADAS.items():
        n = c.execute(
            text(f"select count(*) from (({consulta}) except all (select * from {tabela})) a")
        ).scalar()  # noqa: S608
        n += c.execute(
            text(f"select count(*) from ((select * from {tabela}) except all ({consulta})) b")
        ).scalar()  # noqa: S608
        diferencas[tabela] = n
    return diferencas
