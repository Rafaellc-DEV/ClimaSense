"""Cenários de alagamento (RF-09): reúne os insumos reais, chama o estimador e guarda a previsão emitida
exatamente como foi mostrada (RF-09.8)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import cenario
from climasense.infra import cache
from climasense.modelos.estimador import EstimadorAlagamento, EstimadorReferencia

FONTE_PREVISAO = "open-meteo-previsao"
FONTE_MARE = "open-meteo-mare"
EMISSOES_PARA_FAIXA = 4


def _territorios_previsao(territorio_id: str) -> list[str]:
    # a previsão é por distrito; “recife” é a média dos 8 pontos, hora a hora
    return [f"ds-{i}" for i in range(1, 9)] if territorio_id == "recife" else [territorio_id]


def previsao_por_emissao(
    db: Session, territorio_id: str, desde: datetime
) -> dict[datetime, list[tuple[datetime, float | None]]]:
    """Últimas emissões da previsão de chuva: emissão → [(hora, mm)], média entre distritos quando “recife”."""
    ts = _territorios_previsao(territorio_id)
    emissoes = [
        e
        for (e,) in db.execute(
            text(
                "select distinct emitido_em from silver.observacoes where fonte_id = :f and emitido_em is not null "
                "and territorio_id = any(:ts) order by emitido_em desc limit :n"
            ),
            {"f": FONTE_PREVISAO, "ts": ts, "n": EMISSOES_PARA_FAIXA},
        )
    ]
    linhas = db.execute(
        text(
            "select emitido_em, observado_em, avg(valor) as valor, count(valor) as n, count(*) as total "
            "from silver.observacoes where fonte_id = :f and emitido_em = any(:e) and territorio_id = any(:ts) "
            "and observado_em >= :d group by emitido_em, observado_em order by emitido_em, observado_em"
        ),
        {"f": FONTE_PREVISAO, "ts": ts, "e": emissoes, "d": desde},
    ).all()
    por_emissao: dict[datetime, list[tuple[datetime, float | None]]] = defaultdict(list)
    for emitido, hora, valor, n, total in linhas:
        por_emissao[emitido].append((hora, valor if n == total else None))
    return dict(por_emissao)


def previsao_por_emissao_distritos(
    db: Session, distritos: list[str], desde: datetime
) -> dict[str, dict[datetime, list[tuple[datetime, float | None]]]]:
    """`previsao_por_emissao` de vários distritos em 1 consulta (a de cada distrito custava 2): por distrito, as
    últimas `EMISSOES_PARA_FAIXA` emissões dele, hora a hora. Hora com algum valor nulo sai nula (RN-02)."""
    if not distritos:
        return {}
    linhas = db.execute(
        text(
            "with e as (select territorio_id, emitido_em, dense_rank() over (partition by territorio_id "
            "order by emitido_em desc) as ordem from (select distinct territorio_id, emitido_em "
            "from silver.observacoes where fonte_id = :f and emitido_em is not null and territorio_id = any(:ts)) x) "
            "select o.territorio_id, o.emitido_em, o.observado_em, avg(o.valor) as valor, count(o.valor) as n, "
            "count(*) as total from silver.observacoes o join e on e.territorio_id = o.territorio_id "
            "and e.emitido_em = o.emitido_em where o.fonte_id = :f and e.ordem <= :n and o.observado_em >= :d "
            "group by o.territorio_id, o.emitido_em, o.observado_em order by o.emitido_em, o.observado_em"
        ),
        {"f": FONTE_PREVISAO, "ts": list(distritos), "n": EMISSOES_PARA_FAIXA, "d": desde},
    ).all()
    saida: dict[str, dict[datetime, list[tuple[datetime, float | None]]]] = {}
    for ds, emitido, hora, valor, n, total in linhas:
        saida.setdefault(ds, defaultdict(list))[emitido].append((hora, valor if n == total else None))
    return {ds: dict(v) for ds, v in saida.items()}


def mare_prevista(
    db: Session, desde: datetime
) -> tuple[datetime | None, list[tuple[datetime, float | None]]]:
    """Maré da emissão mais recente a partir de `desde`. Guardada por `cache.VIVO_S` (a coleta é diária)."""
    return cache.obter("mare", desde, cache.VIVO_S, lambda: _ler_mare(db, desde))


def _ler_mare(db: Session, desde: datetime) -> tuple[datetime | None, list[tuple[datetime, float | None]]]:
    emitido = db.execute(
        text("select max(emitido_em) from silver.observacoes where fonte_id = :f"), {"f": FONTE_MARE}
    ).scalar()
    if not emitido:
        return None, []
    linhas = db.execute(
        text(
            "select observado_em, valor from silver.observacoes where fonte_id = :f and emitido_em = :e "
            "and observado_em >= :d order by observado_em"
        ),
        {"f": FONTE_MARE, "e": emitido, "d": desde},
    ).all()
    return emitido, [(t, v) for t, v in linhas]


def chuva_historica(db: Session, territorio_id: str) -> list[float]:
    return [
        v
        for (v,) in db.execute(
            text(
                "select acumulado_mm from gold.chuva_diaria where territorio_id = :t and tipo = 'derivada' "
                "and acumulado_mm is not null"
            ),
            {"t": territorio_id},
        )
    ]


def ocorrencias(db: Session, territorio_id: str) -> int | None:
    """None enquanto o conector de ocorrências não tiver nenhuma carga bem-sucedida. Guardado por `cache.MEDIO_S`."""
    return cache.obter(
        "ocorrencias", ("total", territorio_id), cache.MEDIO_S, lambda: _ler_ocorrencias(db, territorio_id)
    )


def _ler_ocorrencias(db: Session, territorio_id: str) -> int | None:
    carregou = db.execute(
        text(
            "select 1 from app.etl_execucoes where fonte_id = 'recife-alagamento' and status = 'sucesso' limit 1"
        )
    ).first()
    if not carregou:
        return None
    return db.execute(
        text(
            "select count(*) from silver.ocorrencias where tipo = 'alagamento' and (territorio_id = :t "
            "or territorio_id in (select id from app.territorios where pai_id = :t))"
        ),
        {"t": territorio_id},
    ).scalar()


def faixa(
    por_emissao: dict[datetime, list[tuple[datetime, float | None]]],
) -> dict[datetime, tuple[float, float]]:
    """Faixa de incerteza = menor e maior valor previsto para a mesma hora nas emissões recentes."""
    valores: dict[datetime, list[float]] = defaultdict(list)
    for serie in por_emissao.values():
        for hora, v in serie:
            if v is not None:
                valores[hora].append(v)
    return {h: (min(v), max(v)) for h, v in valores.items() if len(v) >= 2}


def emitir(
    db: Session,
    territorio_id: str,
    horizonte_h: int,
    agora: datetime,
    estimador: EstimadorAlagamento | None = None,
    registrar: bool = True,
) -> dict:
    """`registrar=False` calcula sem gravar em silver.previsoes_emitidas (usado por rankings e painéis, que
    consultam vários territórios de uma vez; só o cenário exibido ao usuário vira registro, RF-09.8)."""
    estimador = estimador or EstimadorReferencia()
    inicio_hora = agora.replace(minute=0, second=0, microsecond=0)
    por_emissao = previsao_por_emissao(db, territorio_id, inicio_hora)
    ultima = max(por_emissao) if por_emissao else None
    chuva = por_emissao.get(ultima, []) if ultima else []
    emitido_mare, mare = mare_prevista(db, inicio_hora)
    historico = chuva_historica(db, territorio_id)
    insumos = cenario.Insumos(
        chuva_prevista=chuva,
        mare_prevista=mare,
        chuva_historica_diaria=historico,
        ocorrencias_historicas=ocorrencias(db, territorio_id),
    )
    est = estimador.estimar(territorio_id, horizonte_h, insumos, inicio_hora)
    limite = inicio_hora + timedelta(hours=horizonte_h)
    faixas = faixa(por_emissao)
    resultado = {
        "chuva": [
            {"t": t, "valor": v, "min": faixas.get(t, (None, None))[0], "max": faixas.get(t, (None, None))[1]}
            for t, v in chuva
            if t < limite
        ],
        "mare": [{"t": t, "valor": v} for t, v in mare if t < limite],
        "previsao_emitida_em": ultima,
        "mare_emitida_em": emitido_mare,
        "emissoes_na_faixa": len(por_emissao),
        "dias_historico": len(historico),
        "estimativa": est,
    }
    if not registrar:
        resultado["registro_id"] = None
        return resultado
    saida = {
        "prioridade": est.prioridade,
        "qualidade": est.qualidade,
        "janela_atencao": [est.janela_atencao.inicio.isoformat(), est.janela_atencao.fim.isoformat()]
        if est.janela_atencao
        else None,
        "fatores": est.fatores,
        "limitacoes": est.limitacoes,
        "acumulado_previsto_mm": est.acumulado_previsto_mm,
    }
    insumos_gravados = {
        "previsao_emitida_em": ultima.isoformat() if ultima else None,
        "mare_emitida_em": emitido_mare.isoformat() if emitido_mare else None,
        "horas_chuva": len(resultado["chuva"]),
        "horas_mare": len(resultado["mare"]),
        "dias_historico": len(historico),
        "p95_mm": est.p95_mm,
        "p99_mm": est.p99_mm,
        "ocorrencias_historicas": insumos.ocorrencias_historicas,
    }
    resultado["registro_id"] = db.execute(
        text(
            "insert into silver.previsoes_emitidas (territorio_id, horizonte_h, emitida_em, metodo, versao_metodo, saida, insumos) "
            "values (:t, :h, :e, :m, :v, cast(:s as jsonb), cast(:i as jsonb)) returning id"
        ),
        {
            "t": territorio_id,
            "h": horizonte_h,
            "e": agora,
            "m": estimador.metodo,
            "v": estimador.versao,
            "s": json.dumps(saida, ensure_ascii=False),
            "i": json.dumps(insumos_gravados),
        },
    ).scalar_one()
    db.commit()
    return resultado
