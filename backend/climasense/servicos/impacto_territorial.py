"""RF-23–25, RF-36–38, RF-42: análise da previsão por distrito, sem treinar ou gravar na requisição.

O cenário manual permanece em simulador.simular. Aqui cada bairro herda só a previsão do
seu distrito. Suscetibilidade e exposição são contexto; ML reprovado não altera as regras.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from climasense.dominio import estagio as dom_estagio
from climasense.dominio import simulador as dom
from climasense.ml.alagamento import servico as ml
from climasense.servicos import arboviroses_cenario, cenarios, chuva_preventiva, estagios, simulador

log = logging.getLogger(__name__)

METODO = "regras-previsao-distrital"
VERSAO = "1.0.0"
FONTE_SGB = "sgb-suscetibilidade-deslizamento"
LIMITACOES = [
    "Experimental: gatilhos ainda dependem de validação humana; não é alerta oficial.",
    "O bairro herda a chuva do ponto representativo do seu distrito (RN-07).",
    "Atendimentos registrados não comprovam todos os eventos; ausência de registro não é ausência de impacto.",
    "População residente e equipamentos são exposição potencial, não pessoas ou unidades atingidas.",
    "Na integração atual Open-Meteo, emitido_em é a captura do snapshot pelo ETL, não o horário de inicialização do modelo meteorológico.",
]


def acumulado_completo(serie: list, inicio: datetime, horas: int) -> float | None:
    """Exige exatamente cada hora da janela: faltantes/duplicadas/inválidas nunca viram zero."""
    fim = inicio + timedelta(hours=horas)
    linhas = [(t, v) for t, v in serie if inicio <= t < fim]
    esperadas = {inicio + timedelta(hours=h) for h in range(horas)}
    if len(linhas) != horas or {t for t, _ in linhas} != esperadas:
        return None
    if any(v is None or not isfinite(v) or v < 0 for _, v in linhas):
        return None
    return round(sum(v for _, v in linhas), 3)


def observada_72h(db: Session, agora: datetime) -> dict[str, dict]:
    """Acumulado móvel medido; sem herdar estação de outro distrito nem usar leituras futuras."""
    linhas = db.execute(
        text(
            "select d, max(v) as mm, max(lida_em) as lida_em, count(*) as estacoes from ("
            "select distinct on (l.estacao_id) l.estacao_id, l.valor_mm as v, l.lida_em, "
            "case when t.tipo = 'distrito' then t.id when t.tipo = 'bairro' then t.pai_id end as d "
            "from silver.apac_chuva_leituras l join silver.estacoes e on e.id = l.estacao_id "
            "join app.territorios t on t.id = e.territorio_id where l.janela_h = 72 "
            "and l.lida_em between :desde and :agora and l.visto_em <= :agora "
            "and l.valor_mm is not null order by l.estacao_id, l.lida_em desc) x "
            "where d is not null group by d"
        ),
        {"desde": agora - timedelta(hours=2), "agora": agora},
    ).mappings()
    return {
        r["d"]: {"mm": float(r["mm"]), "lida_em": r["lida_em"], "estacoes": r["estacoes"]} for r in linhas
    }


def suscetibilidade(db: Session) -> dict[str, dict]:
    try:
        with db.begin_nested():
            linhas = db.execute(
                text("select bairro_id, classe, fracao from silver.suscetibilidade_deslizamento")
            ).all()
    except ProgrammingError as erro:
        if getattr(erro.orig, "pgcode", None) == "42P01":
            return {}  # migração territorial ainda ausente: não presume carta disponível
        raise
    saida: dict[str, dict] = {}
    for b, classe, fracao in linhas:
        saida.setdefault(b, {})[classe] = float(fracao)
    return saida


def preparar(serie, emitida, mare, emitida_mare, obs, agora, horizonte, parametros):
    """Prepara insumos locais auditáveis. As janelas de 24/72 h são explícitas, além do horizonte."""
    serie = [(t, v if v is not None and isfinite(v) and v >= 0 else None) for t, v in serie]
    mare = [(t, v if v is not None and isfinite(v) else None) for t, v in mare]
    if obs.get("mm") is not None and (not isfinite(obs["mm"]) or obs["mm"] < 0):
        obs = {}
    inicio = agora.replace(minute=0, second=0, microsecond=0)
    faltas = []
    if emitida is None or not timedelta(0) <= agora - emitida <= timedelta(hours=6):
        faltas.append("previsão de chuva recente do próprio distrito")
        serie = []
    acumulados = {str(h): acumulado_completo(serie, inicio, h) for h in (6, 12, 24, 72)}
    mm = acumulado_completo(serie, inicio, horizonte)
    if mm is None:
        faltas.append(f"previsão horária completa de chuva nas próximas {horizonte} h")
    if emitida_mare is None or not timedelta(0) <= agora - emitida_mare <= timedelta(hours=24):
        mare = []
    horas_mare = [(t, v) for t, v in mare if inicio <= t < inicio + timedelta(hours=horizonte)]
    completas = {t for t, v in horas_mare if v is not None and isfinite(v)}
    esperadas = {inicio + timedelta(hours=h) for h in range(horizonte)}
    if completas != esperadas or len(horas_mare) != horizonte:
        faltas.append("previsão de maré completa e recente")
    # Maré perto do pico, como no domínio de estágios; máxima geral não implica coincidência.
    pico = dom_estagio.pico(serie, inicio, horizonte) if serie else None
    no_pico = dom_estagio.mare_perto_do_pico(horas_mare, pico, parametros.mare_janela_h)
    avaliacao = {
        "metodo": METODO,
        "versao": VERSAO,
        "horizonte_h": horizonte,
        "inicio_validade": inicio,
        "fim_validade": inicio + timedelta(hours=horizonte),
        "emitido_em_fonte": emitida,
        "mare_emitida_em": emitida_mare,
        "fonte_meteorologica": cenarios.FONTE_PREVISAO,
        "fonte_mare": cenarios.FONTE_MARE,
        "fonte_observada": simulador.FONTE_APAC,
        "acumulados_previstos_mm": acumulados,
        "chuva_no_horizonte_mm": mm,
        "chuva_observada_72h_mm": obs.get("mm"),
        "observada_em": obs.get("lida_em"),
        "estacoes_validas": obs.get("estacoes", 0),
        "mare_no_pico_m": no_pico,
        "faltando": faltas,
        "limitacoes": list(LIMITACOES),
        "parametros": asdict(parametros),
        "serie_chuva": [(t, v) for t, v in serie if inicio <= t < inicio + timedelta(hours=horizonte)],
        "serie_mare": horas_mare,
    }
    maior24 = None
    if mm is not None:
        janela = min(24, horizonte)
        maior24 = max(
            acumulado_completo(serie, inicio + timedelta(hours=k), janela)
            for k in range(max(1, horizonte - janela + 1))
        )
    p = None if faltas else dom.Premissas(mm, horizonte, obs.get("mm"), no_pico, horizonte, (maior24, mm))
    return p, avaliacao


def preparar_dia(dia, distrito, serie, mare, emitida_mare, agora, parametros):
    """Reutiliza o domínio territorial sem exigir maré nem carregar solo atual para dias futuros."""
    inicio, fim, horas = dia["inicio"], dia["fim"], dia["horas_periodo"]
    serie = [
        (t, v if v is not None and isfinite(v) and v >= 0 else None) for t, v in serie if inicio <= t < fim
    ]
    mare_valida = emitida_mare is not None and timedelta(0) <= agora - emitida_mare <= timedelta(hours=24)
    mare = [(t, v) for t, v in mare if v is not None and isfinite(v)] if mare_valida else []
    horas_mare = [t for t, _ in mare if inicio <= t < fim]
    completas = len(horas_mare) == horas and set(horas_mare) == {
        inicio + timedelta(hours=h) for h in range(horas)
    }
    pico = dom_estagio.pico(serie, inicio, horas)
    no_pico = dom_estagio.mare_perto_do_pico(mare, pico, parametros.mare_janela_h) if completas else None
    p = chuva_preventiva.premissas_do_dia(dia, distrito, no_pico)
    return p, {
        "metodo": METODO,
        "versao": VERSAO,
        "horizonte_h": horas,
        "inicio_validade": inicio,
        "fim_validade": fim,
        "emitido_em_fonte": distrito["referencia_em"],
        "mare_emitida_em": emitida_mare,
        "fonte_meteorologica": cenarios.FONTE_PREVISAO,
        "fonte_mare": cenarios.FONTE_MARE,
        "fonte_observada": simulador.FONTE_APAC,
        "acumulados_previstos_mm": {},
        "chuva_no_horizonte_mm": distrito["chuva_prevista_mm"],
        "chuva_observada_72h_mm": None,
        "observada_em": None,
        "estacoes_validas": 0,
        "mare_no_pico_m": no_pico,
        "serie_chuva": serie,
        "serie_mare": [(t, v) for t, v in mare if inicio <= t < fim],
        "faltando": [] if p else ["chuva horária completa e recente no período selecionado"],
        "limitacoes": [
            *LIMITACOES,
            "Período diário limitado às próximas 72 h; sem extrapolar horas. Observação atual não representa solo futuro.",
        ],
        "parametros": asdict(parametros),
    }


def comparacoes_recentes(db: Session, agora: datetime) -> list[dict]:
    """Uma leitura APAC de 1 h por distrito; só pareia previsão arquivada ANTES da janela.

    Não arredonda horários de estação e não compara acumulados móveis com dias futuros.
    O ponto Open-Meteo e o pluviômetro têm representatividade espacial distinta.
    """
    linhas = db.execute(
        text(
            "with l as (select case when t.tipo='distrito' then t.id else t.pai_id end as distrito_id, "
            "e.nome as estacao, l.lida_em, l.visto_em, l.valor_mm, row_number() over (partition by "
            "case when t.tipo='distrito' then t.id else t.pai_id end order by l.lida_em desc, "
            "l.valor_mm desc, e.id) as ordem from silver.apac_chuva_leituras l "
            "join silver.estacoes e on e.id=l.estacao_id join app.territorios t on t.id=e.territorio_id "
            "where l.janela_h=1 and l.lida_em between :desde and :agora and l.visto_em<=:agora "
            "and l.valor_mm>=0 and l.valor_mm<'Infinity'::float8 and t.tipo in ('bairro','distrito')) "
            "select l.*, p.valor as prevista_mm, p.emitido_em from l left join lateral ("
            "select o.valor,o.emitido_em from silver.observacoes o where o.fonte_id=:fonte "
            "and o.variavel='chuva_mm' and o.territorio_id=l.distrito_id "
            "and o.observado_em=l.lida_em-interval '1 hour' "
            "and o.emitido_em<=l.lida_em-interval '1 hour' and o.coletado_em<=l.lida_em-interval '1 hour' "
            "and o.valor>=0 and o.valor<'Infinity'::float8 order by o.emitido_em desc limit 1) p on true "
            "where l.ordem=1 order by l.distrito_id"
        ),
        {"desde": agora - timedelta(hours=2), "agora": agora, "fonte": cenarios.FONTE_PREVISAO},
    ).mappings()
    saida = []
    for r in linhas:
        alinhada = r["lida_em"] == r["lida_em"].replace(minute=0, second=0, microsecond=0)
        compativel = alinhada and r["prevista_mm"] is not None
        saida.append(
            {
                "territorio_id": r["distrito_id"],
                "inicio": r["lida_em"] - timedelta(hours=1),
                "fim": r["lida_em"],
                "observada_mm": float(r["valor_mm"]),
                "estacao": r["estacao"],
                "atualizada_em": r["visto_em"],
                "previsao_referencia_em": r["emitido_em"] if compativel else None,
                "prevista_mm": float(r["prevista_mm"]) if compativel else None,
                "compativel": compativel,
                "motivo": None
                if compativel
                else "Sem previsão arquivada anterior para a mesma hora exata; não comparar como acurácia.",
            }
        )
    return saida


def risco_no_periodo(db, agora, dia, parcial):
    if parcial:
        return {
            "disponivel": False,
            "motivo": "ML avalia o dia local completo; o recorte selecionado é parcial.",
            "modelo": None,
            "itens": [],
        }
    try:
        return ml.payload(db, agora, dia=dia) if dia else ml.payload(db, agora)
    except Exception as erro:  # noqa: BLE001 — falha do experimento preserva as regras
        log.warning("Inferência de alagamento indisponível (%s)", type(erro).__name__)
        return {
            "disponivel": False,
            "motivo": "Inferência indisponível neste momento.",
            "modelo": None,
            "itens": [],
        }


def analisar(db: Session, agora: datetime, horizonte_h: int = 24, *, dia: date | None = None) -> dict:
    if not 1 <= horizonte_h <= 72:
        raise ValueError("Horizonte deve estar entre 1 e 72 horas.")
    agora = agora.replace(tzinfo=UTC) if agora.tzinfo is None else agora.astimezone(UTC)
    inicio_dias = chuva_preventiva.inicio_janela(agora)
    primeira = ml.hoje_recife(inicio_dias)
    ultima = ml.hoje_recife(inicio_dias + timedelta(hours=71))
    if dia is not None and not primeira <= dia <= ultima:
        raise ValueError("Data fora dos dias cobertos pelas próximas 72 horas.")
    tempo = perf_counter()
    est = simulador._estatico(db)
    parametros = estagios.parametros_atuais(db)["parametros"]
    inicio = agora.replace(minute=0, second=0, microsecond=0)
    previsoes = cenarios.previsao_por_emissao_distritos(db, list(est["distritos"]), inicio, agora)
    dias = chuva_preventiva.resumir(previsoes, est["distritos"], agora, parametros)
    selecionado = next((d for d in dias if d["data"] == dia), None)
    distritos_dia = {d["territorio_id"]: d for d in selecionado["distritos"]} if selecionado else {}
    comparacoes = comparacoes_recentes(db, agora)
    emitida_mare, mare = cenarios.mare_prevista(db, inicio)
    observadas = observada_72h(db, agora) if selecionado is None else {}
    sgb = suscetibilidade(db)
    vul = simulador.vulneraveis_por_territorio(db)
    risco = risco_no_periodo(db, agora, dia, selecionado and selecionado["periodo_parcial"])
    riscos = {r["territorio_id"]: r for r in risco["itens"]} if risco["disponivel"] else {}
    insumos = {}
    for ds in est["distritos"]:
        emissoes = previsoes.get(ds, {})
        emitida = max(emissoes) if emissoes else None
        if selecionado:
            insumos[ds] = preparar_dia(
                selecionado,
                distritos_dia[ds],
                emissoes.get(emitida, []),
                mare,
                emitida_mare,
                agora,
                parametros,
            )
        else:
            insumos[ds] = preparar(
                emissoes.get(emitida, []),
                emitida,
                mare,
                emitida_mare,
                observadas.get(ds, {}),
                agora,
                horizonte_h,
                parametros,
            )
    itens, por_ds, resultados_bairro = [], {}, {}
    for bid, nome, ds in est["bairros"]:
        p, avaliacao = insumos[ds]
        r = (
            dom.classificar_bairro(p, parametros, est["historico"][bid])
            if p
            else dom.Resultado(
                "sem_dados",
                "sem_dados",
                "sem_dados",
                "insuficiente",
                ["Dados insuficientes: " + ", ".join(avaliacao["faltando"])],
            )
        )
        # ML é um resultado paralelo; não muda a escala existente nem o estágio oficial.
        item = simulador._item(bid, nome, "bairro", ds, r, vul)
        terreno = sgb.get(bid)
        contexto = "Dados insuficientes: falta a carta SGB neste bairro."
        if terreno:
            contexto = "Suscetibilidade do terreno (SGB, 2012–2014), não previsão de deslizamento."
            if (
                terreno.get("alta", 0) > 0
                and p
                and any(g.nivel != "observacao" for g in dom.gatilhos(p, parametros))
            ):
                contexto += " Chuva sugere atenção em território com área de alta suscetibilidade; não confirma ocorrência."
            if terreno.get("coberta", 0) < 1:
                contexto += " Cobertura parcial da carta: a área restante não foi classificada."
        item["avaliacao"] = {
            **avaliacao,
            "suscetibilidade": terreno,
            "contexto_deslizamento": contexto,
            "fonte_territorial": FONTE_SGB,
            "fonte_ocorrencias": simulador.FONTE_OCORRENCIAS,
            "historico_ocorrencias": asdict(est["historico"][bid]),
        }
        item["ml_alagamento"] = riscos.get(bid)
        item["sinalizacao_preventiva"] = distritos_dia[ds]["sinalizacao"] if selecionado else None
        itens.append(item)
        resultados_bairro[bid] = r
        por_ds.setdefault(ds, []).append((nome, r))
    arbo = arboviroses_cenario.montar(db, est["distritos"], agora)
    distritos = {ds: dom.agregar_distrito(por_ds.get(ds, [])) for ds in est["distritos"]}
    for ds, nome in est["distritos"].items():
        item = simulador._item(ds, nome, "distrito", ds, distritos[ds], vul)
        item["avaliacao"] = insumos[ds][1]
        item["sinalizacao_preventiva"] = distritos_dia[ds]["sinalizacao"] if selecionado else None
        item["arboviroses"] = arbo["por_distrito"][ds]
        itens.append(item)
    return {
        "contexto": "previsao_atual",
        "dia_selecionado": dia,
        "dias": dias,
        "comparacoes_recentes": comparacoes,
        "itens": itens,
        "ml_alagamento": risco,
        "experimental": True,
        "calculado_em": agora,
        "tempo_calculo_ms": round((perf_counter() - tempo) * 1000),
        "resumo": {
            "por_classe": dom.resumo_por_classe(list(resultados_bairro.values())),
            "impacto_pessoas_aviso": dom.MOTIVO_IMPACTO_PENDENTE if vul is None else None,
            "pessoas_vulneraveis_em_alerta": dom.pessoas_em_alerta(
                {b: r.estagio_sugerido for b, r in resultados_bairro.items()}, vul
            ),
            "arboviroses": arbo["resumo"],
            "ordem_de_atencao_distritos": simulador._ordem_distritos(
                est["distritos"], distritos, arbo["por_distrito"]
            ),
        },
    }
