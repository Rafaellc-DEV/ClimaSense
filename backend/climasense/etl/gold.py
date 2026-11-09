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

# ------------------------------------------------------------------ meteorologia observada (migração 0021)
# Uma leitura de estação vale como "com leitura" se for no máximo 120 min mais velha que a coleta mais recente.
# Distrito sem pluviômetro próprio NUNCA herda o dado do Recife: fica sem valor (RN-01, RN-02).
LEITURAS_POR_HORA_COMPLETA = (
    4  # coleta a cada 10-15 min: com menos que isto a soma da hora é só um mínimo medido
)

_ULTIMA_APAC = (
    "with ref as (select max(visto_em) as referencia_em from silver.apac_chuva_leituras),"
    + _ESTACOES_APAC
    + """,
ultima as (
  select distinct on (estacao_id) estacao_id, lida_em from silver.apac_chuva_leituras
  order by estacao_id, lida_em desc
), est as (
  select ea.id, ea.bairro_id, ea.distrito_id, u.lida_em,
         max(l.valor_mm) filter (where l.janela_h = 72) as v72,
         coalesce((select referencia_em from ref) - u.lida_em <= interval '120 minutes', false) as recente
  from ultima u join est_apac ea on ea.id = u.estacao_id
  join silver.apac_chuva_leituras l on l.estacao_id = u.estacao_id and l.lida_em = u.lida_em
  group by ea.id, ea.bairro_id, ea.distrito_id, u.lida_em
)"""
)

# Hora = a que termina na leitura (leitura das 22:00 fecha a hora 21:00). Soma só leituras medidas; hora sem leitura
# não tem linha. O valor do distrito é o maior entre as estações; `n_completas` < `n_com_leitura` = mínimo medido.
CHUVA_OBS_HORA_DISTRITO = (
    "with"
    + _ESTACOES_APAC
    + f""",
total as (
  select ea.distrito_id, count(*)::integer as n
  from est_apac ea where exists (select 1 from silver.apac_chuva_passos p where p.estacao_id = ea.id)
  group by ea.distrito_id
), por_estacao as (
  select ea.id, ea.distrito_id, date_trunc('hour', p.lida_em - interval '1 second') as hora,
         round(sum(p.valor_mm)::numeric, 2)::double precision as mm, count(p.valor_mm)::integer as n,
         min(p.lida_em) as primeira, max(p.lida_em) as ultima
  from silver.apac_chuva_passos p join est_apac ea on ea.id = p.estacao_id
  where p.valor_mm is not null group by ea.id, ea.distrito_id, 3
)
select h.distrito_id, h.hora, max(h.mm), percentile_cont(0.5) within group (order by h.mm),
       max(t.n), count(*)::integer, (count(*) filter (where h.n >= {LEITURAS_POR_HORA_COMPLETA}))::integer,
       min(h.primeira), max(h.ultima), array_agg(h.id order by h.id)::text[]
from por_estacao h join total t on t.distrito_id = h.distrito_id
group by h.distrito_id, h.hora
"""
)

CHUVA_OBS_72H_DISTRITO = (
    _ULTIMA_APAC
    + """,
agg as (
  select distrito_id, count(*)::integer as n, (count(*) filter (where recente and v72 is not null))::integer as nok,
         max(v72) filter (where recente) as mx,
         percentile_cont(0.5) within group (order by v72) filter (where recente) as med,
         max(lida_em) filter (where recente and v72 is not null) as lida, array_agg(id order by id)::text[] as ests
  from est group by distrito_id
)
select * from (
select t.id, 'distrito'::varchar,
       case when a.n is null then 'sem_pluviometro' when a.nok > 0 then 'com_leitura' else 'sem_leitura' end,
       case when a.nok > 0 then a.mx end, case when a.nok > 0 then a.med end,
       coalesce(a.n, 0), coalesce(a.nok, 0), coalesce(a.n, 0) - coalesce(a.nok, 0), a.lida,
       (select referencia_em from ref), coalesce(a.ests, '{}'::text[])
from app.territorios t left join agg a on a.distrito_id = t.id where t.tipo = 'distrito'
union all
select t.id, 'municipio'::varchar,
       case when count(e.id) = 0 then 'sem_pluviometro'
            when count(*) filter (where e.recente and e.v72 is not null) > 0 then 'com_leitura' else 'sem_leitura' end,
       max(e.v72) filter (where e.recente and e.v72 is not null),
       percentile_cont(0.5) within group (order by e.v72) filter (where e.recente and e.v72 is not null),
       count(e.id)::integer, (count(*) filter (where e.recente and e.v72 is not null))::integer,
       (count(e.id) - count(*) filter (where e.recente and e.v72 is not null))::integer,
       max(e.lida_em) filter (where e.recente and e.v72 is not null), (select referencia_em from ref),
       coalesce(array_agg(e.id order by e.id) filter (where e.id is not null), '{}'::text[])
from app.territorios t left join est e on true where t.tipo = 'municipio' group by t.id
) u where exists (select 1 from silver.apac_chuva_leituras)  -- sem nenhuma coleta, nem "sem pluviômetro" se afirma
"""
)

ESTACOES_CHUVA_STATUS = (
    _ULTIMA_APAC
    + """
select e.id, s.nome, e.distrito_id, e.bairro_id,
       case when e.recente and e.v72 is not null then 'com_leitura' when e.recente then 'sem_valor'
            else 'leitura_antiga' end,
       e.lida_em, (select referencia_em from ref), c.status_dados, c.tempo_min
from est e join silver.estacoes s on s.id = e.id
left join silver.apac_estacoes_cadastro c on c.codigo_fonte = s.codigo_fonte
"""
)

# Umidade do solo = MODELO (Experimental, RN-11). Média das últimas 24 h do ponto comparada com o histórico diário
# do PRÓPRIO ponto (percentil). Com menos de 365 dias de histórico ou 20 h de modelo, sem classe.
SOLO_MODELO_DISTRITO = """
with ref as (select max(emitido_em) as r from silver.solo_modelo_horario),
atual as (
  select h.territorio_id, h.camada, avg(h.valor_m3m3) as v, count(h.valor_m3m3)::integer as n
  from silver.solo_modelo_horario h, ref
  where h.observado_em > ref.r - interval '24 hours' and h.observado_em <= ref.r
  group by h.territorio_id, h.camada
), hist as (
  select territorio_id, camada, count(*)::integer as n,
         percentile_cont(0.25) within group (order by media_m3m3) as p25,
         percentile_cont(0.75) within group (order by media_m3m3) as p75,
         percentile_cont(0.90) within group (order by media_m3m3) as p90
  from silver.solo_modelo_diario group by territorio_id, camada
), calc as (
  select a.territorio_id, a.camada, a.n as n_horas, case when a.n >= 20 then a.v end as v,
         coalesce(h.n, 0) as n_hist, h.p25, h.p75, h.p90,
         case when a.n >= 20 and coalesce(h.n, 0) >= 365 then
           round((100.0 * (select count(*) from silver.solo_modelo_diario d
                           where d.territorio_id = a.territorio_id and d.camada = a.camada and d.media_m3m3 <= a.v)
                  / h.n)::numeric, 1)::double precision end as pct
  from atual a left join hist h on h.territorio_id = a.territorio_id and h.camada = a.camada
)
select territorio_id, camada, (select r from ref), v, n_horas, pct, p25, p75, p90, n_hist,
       case when pct is null then null when pct < 25 then 'seco' when pct < 75 then 'normal'
            when pct < 90 then 'umido' else 'muito_umido' end,
       'modelo'::varchar, 'experimental'::varchar
from calc
"""

# ------------------------------------------------------------------ hidrologia (rios e reservatórios do Capibaribe)
# Classe do rio por estação a partir dos limiares OFICIAIS da APAC (nunca percentual, RN-06). Nível = leitura mais
# recente entre APAC e ANA; limiares = última leitura da APAC que os trouxe. Idade medida contra a última coleta
# (`max(visto_em)`), não contra `now()`, para a gold ser reproduzível. Leitura com mais de 12 h (720 min) ou sem
# limiares válidos = `dados_insuficientes`, com o motivo; "desatualizada" = mais de 2 h (a tela avisa).
RIOS_SITUACAO = """
with ref as (select max(visto_em) as r from silver.rios_leituras),
ultima as (
  select distinct on (estacao_codigo) estacao_codigo, fonte, lida_em, nivel_cm
  from silver.rios_leituras where nivel_cm is not null
  order by estacao_codigo, lida_em desc, (fonte = 'apac') desc
), lim as (
  select distinct on (estacao_codigo) estacao_codigo, pre_alerta_cm as pre, alerta_cm as al, enchente_cm as en
  from silver.rios_leituras where fonte = 'apac' and pre_alerta_cm is not null
  order by estacao_codigo, lida_em desc
), fon as (
  select estacao_codigo, array_agg(distinct fonte order by fonte)::text[] as fontes
  from silver.rios_leituras where nivel_cm is not null group by estacao_codigo
), base as (
  select e.codigo, e.nome, e.rio, e.bacia, e.municipios, e.inclui_recife, e.lat, e.lon,
         u.nivel_cm, l.pre, l.al, l.en, u.lida_em, u.fonte, f.fontes, (select r from ref) as referencia_em,
         floor(extract(epoch from (select r from ref) - u.lida_em) / 60)::integer as idade_min
  from silver.rios_estacoes e
  left join ultima u on u.estacao_codigo = e.codigo
  left join lim l on l.estacao_codigo = e.codigo
  left join fon f on f.estacao_codigo = e.codigo
)
select codigo, nome, rio, bacia, municipios, inclui_recife, lat, lon,
       case when lida_em is null or idade_min > 720 or pre is null then 'dados_insuficientes'
            when nivel_cm >= en then 'enchente' when nivel_cm >= al then 'alerta'
            when nivel_cm >= pre then 'pre_alerta' else 'abaixo_pre_alerta' end,
       case when lida_em is null then 'sem_leitura' when idade_min > 720 then 'leitura_antiga'
            when pre is null then 'sem_limiares' end,
       nivel_cm, pre, al, en, lida_em, fonte, fontes, referencia_em, idade_min, idade_min > 120
from base
"""

# Situação dos reservatórios de interesse: status oficial da APAC; leitura com mais de 3 dias = dados insuficientes.
RESERVATORIO_SITUACAO = """
with ref as (select max(visto_em) as r from silver.reservatorios_leituras),
ultima as (
  select distinct on (codigo_estacao) codigo_estacao, data_leitura, cota_m, volume_pct, status
  from silver.reservatorios_leituras order by codigo_estacao, data_leitura desc
), base as (
  select c.codigo_estacao, c.nome, c.municipio, c.bacia, c.capacidade_m3, u.data_leitura, u.cota_m, u.volume_pct,
         u.status, (select r from ref) as referencia_em,
         ((select r from ref) at time zone 'America/Recife')::date - u.data_leitura as idade_dias,
         case upper(u.status) when 'VERTENDO' then 'vertendo' when 'ENTRE 80% E 100%' then 'entre_80_e_100'
              when 'ENTRE 30% E 80%' then 'entre_30_e_80' when 'ENTRE 10% E 30%' then 'entre_10_e_30'
              when 'COLAPSO' then 'colapso' end as classe
  from silver.reservatorios c left join ultima u on u.codigo_estacao = c.codigo_estacao
)
select codigo_estacao, nome, municipio, bacia, capacidade_m3, data_leitura, cota_m, volume_pct, status,
       case when data_leitura is null or idade_dias > 3 or classe is null then 'dados_insuficientes'
            else classe end,
       case when data_leitura is null then 'sem_leitura' when idade_dias > 3 then 'leitura_antiga'
            when classe is null then 'status_desconhecido' end,
       referencia_em, idade_dias
from base
"""

# ------------------------------------------------------------------ saúde durante o evento e histórico (0023)
# Demanda de urgência (SAMU): chamados por semana (domingo), grupo e território. Bairro e distrito só somam o que casou
# com um bairro oficial; o município soma TUDO que o SAMU do Recife atendeu (inclusive bairro sem correspondência).
# A contagem fica inteira aqui: a supressão de células de 1 a 4 (RN-13) acontece ao servir, na API.
SAMU_DEMANDA_SEMANA = """
with base as (
  select s.inicio, s.grupo, s.territorio_id, t.pai_id as distrito_id, s.chamados, s.incompleta,
         s.ultimo_dia_dado, s.coletado_em
  from silver.samu_demanda_semana s left join app.territorios t on t.id = s.territorio_id
)
select territorio_id, 'bairro'::varchar as nivel, inicio, grupo, sum(chamados)::integer, bool_or(incompleta),
       max(ultimo_dia_dado), max(coletado_em)
from base where territorio_id is not null group by territorio_id, inicio, grupo
union all
select distrito_id, 'distrito', inicio, grupo, sum(chamados)::integer, bool_or(incompleta),
       max(ultimo_dia_dado), max(coletado_em)
from base where distrito_id is not null group by distrito_id, inicio, grupo
union all
select 'recife', 'municipio', inicio, grupo, sum(chamados)::integer, bool_or(incompleta),
       max(ultimo_dia_dado), max(coletado_em)
from base group by inicio, grupo
"""

# Qualidade da água (SISAGUA): análises e positivos por semana, motivo e território. Sem amostra = sem linha.
AGUA_VIGILANCIA_SEMANA = """
with base as (
  select s.*, t.pai_id as distrito_id from silver.agua_vigilancia_semana s
  left join app.territorios t on t.id = s.territorio_id
)
select territorio_id, 'bairro'::varchar as nivel, inicio, motivo_grupo,
       sum(analises_ecoli)::integer, sum(ecoli_presente)::integer, sum(analises_cloro)::integer,
       sum(cloro_fora_padrao)::integer, bool_or(incompleta), max(ultima_coleta), max(ultimo_registro),
       max(coletado_em)
from base where territorio_id is not null group by territorio_id, inicio, motivo_grupo
union all
select distrito_id, 'distrito', inicio, motivo_grupo,
       sum(analises_ecoli)::integer, sum(ecoli_presente)::integer, sum(analises_cloro)::integer,
       sum(cloro_fora_padrao)::integer, bool_or(incompleta), max(ultima_coleta), max(ultimo_registro),
       max(coletado_em)
from base where distrito_id is not null group by distrito_id, inicio, motivo_grupo
union all
select 'recife', 'municipio', inicio, motivo_grupo,
       sum(analises_ecoli)::integer, sum(ecoli_presente)::integer, sum(analises_cloro)::integer,
       sum(cloro_fora_padrao)::integer, bool_or(incompleta), max(ultima_coleta), max(ultimo_registro),
       max(coletado_em)
from base group by inicio, motivo_grupo
"""

# Histórico de desastres do Recife (Atlas Digital): um evento por protocolo, na ordem do mais recente
DESASTRES_HISTORICO = """
select protocolo, data_evento, data_registro, cobrade, tipologia, status, mortos, feridos, desabrigados,
       desalojados, outros_afetados, danos_humanos_total, danos_materiais_rs, prejuizo_publico_rs,
       prejuizo_privado_rs, chuva_relacionada, versao_fonte, consolidado_em, coletado_em
from silver.desastres_atlas
"""

TABELAS_SAMU = {"gold.samu_demanda_semana": SAMU_DEMANDA_SEMANA}
TABELAS_AGUA = {"gold.agua_vigilancia_semana": AGUA_VIGILANCIA_SEMANA}
TABELAS_DESASTRES = {"gold.desastres_historico": DESASTRES_HISTORICO}
TABELAS_APAC_AGORA = {"gold.chuva_apac_agora": CHUVA_APAC_AGORA}
TABELAS_APAC_DIARIA = {"gold.chuva_apac_diaria": CHUVA_APAC_DIARIA}
TABELAS_ALAGAMENTO = {"gold.alagamento_bairro_dia": ALAGAMENTO_BAIRRO_DIA}
TABELAS_OCORRENCIAS = {"gold.ocorrencias_bairro": OCORRENCIAS_BAIRRO}
TABELAS_SAUDE = {"gold.saude_semanal": SAUDE_SEMANAL}
TABELAS_ARBOVIROSES = {"gold.arboviroses_bairro_ano": ARBOVIROSES_BAIRRO_ANO}
TABELAS_CHUVA_OBS = {
    "gold.chuva_obs_hora_distrito": CHUVA_OBS_HORA_DISTRITO,
    "gold.chuva_obs_72h_distrito": CHUVA_OBS_72H_DISTRITO,
    "gold.estacoes_chuva_status": ESTACOES_CHUVA_STATUS,
}
TABELAS_SOLO = {"gold.solo_modelo_distrito": SOLO_MODELO_DISTRITO}
TABELAS_RIOS = {"gold.rio_situacao": RIOS_SITUACAO}
TABELAS_RESERVATORIOS = {"gold.reservatorio_situacao": RESERVATORIO_SITUACAO}
VERIFICADAS = {
    **TABELAS,
    **TABELAS_APAC_AGORA,
    **TABELAS_APAC_DIARIA,
    **TABELAS_ALAGAMENTO,
    **TABELAS_OCORRENCIAS,
    **TABELAS_SAUDE,
    **TABELAS_ARBOVIROSES,
    **TABELAS_CHUVA_OBS,
    **TABELAS_SOLO,
    **TABELAS_RIOS,
    **TABELAS_RESERVATORIOS,
    **TABELAS_SAMU,
    **TABELAS_AGUA,
    **TABELAS_DESASTRES,
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
