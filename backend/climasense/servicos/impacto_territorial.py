"""RF-23–25, RF-36–38, RF-42: análise da previsão por distrito, sem treinar ou gravar na requisição.

O cenário manual permanece em simulador.simular. Aqui cada bairro herda só a previsão do
seu distrito. Suscetibilidade e exposição são contexto; ML reprovado não altera as regras.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from math import isfinite
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from climasense.dominio import estagio as dom_estagio
from climasense.dominio import simulador as dom
from climasense.ml.alagamento import servico as ml
from climasense.servicos import arboviroses_cenario, cenarios, estagios, simulador

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


def analisar(db: Session, agora: datetime, horizonte_h: int = 24) -> dict:
    if not 1 <= horizonte_h <= 72:
        raise ValueError("Horizonte deve estar entre 1 e 72 horas.")
    agora = agora.replace(tzinfo=UTC) if agora.tzinfo is None else agora.astimezone(UTC)
    tempo = perf_counter()
    est = simulador._estatico(db)
    parametros = estagios.parametros_atuais(db)["parametros"]
    inicio = agora.replace(minute=0, second=0, microsecond=0)
    previsoes = cenarios.previsao_por_emissao_distritos(db, list(est["distritos"]), inicio, agora)
    emitida_mare, mare = cenarios.mare_prevista(db, inicio)
    observadas = observada_72h(db, agora)
    sgb = suscetibilidade(db)
    vul = simulador.vulneraveis_por_territorio(db)
    try:
        risco = ml.payload(db, agora)
    except Exception:  # noqa: BLE001 — falha do experimento preserva as regras
        risco = {
            "disponivel": False,
            "motivo": "Inferência indisponível neste momento.",
            "modelo": None,
            "itens": [],
        }
    riscos = {r["territorio_id"]: r for r in risco["itens"]} if risco["disponivel"] else {}
    insumos = {}
    for ds in est["distritos"]:
        emissoes = previsoes.get(ds, {})
        emitida = max(emissoes) if emissoes else None
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
        itens.append(item)
        resultados_bairro[bid] = r
        por_ds.setdefault(ds, []).append((nome, r))
    arbo = arboviroses_cenario.montar(db, est["distritos"], agora)
    distritos = {ds: dom.agregar_distrito(por_ds.get(ds, [])) for ds in est["distritos"]}
    for ds, nome in est["distritos"].items():
        item = simulador._item(ds, nome, "distrito", ds, distritos[ds], vul)
        item["avaliacao"] = insumos[ds][1]
        item["arboviroses"] = arbo["por_distrito"][ds]
        itens.append(item)
    return {
        "contexto": "previsao_atual",
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
