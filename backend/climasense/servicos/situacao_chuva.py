"""Chuva para a tela Situação (RF-19, RN-01, RN-02, RN-07): medida em 24 h e 72 h por distrito, estações sem leitura e a
série de chuva prevista (com faixa de incerteza) e maré para o gráfico.

Só junta o que já existe (gold da APAC e a previsão emitida) e guarda por `cache.VIVO_S`; nada é gravado. Distrito sem
pluviômetro próprio (herda o dado do Recife) NÃO mostra chuva medida: ausência não é zero (RN-01, RN-02).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.infra import cache
from climasense.infra.postgres import em_paralelo
from climasense.servicos import cenarios, estagios

HORIZONTE_H = 72
LEITURA_VELHA_MIN = estagios.APAC_DESATUALIZADA_MIN  # leitura mais velha que isto não vale como "agora"


def _agora_apac(db: Session) -> list[dict]:
    try:
        with db.begin_nested():
            return [
                dict(r)
                for r in db.execute(
                    text(
                        "select territorio_id, nivel, chuva_24h_max_mm, n_estacoes, n_atualizadas, lida_em, "
                        "herdado_de from gold.chuva_apac_agora where nivel in ('distrito', 'municipio')"
                    )
                ).mappings()
            ]
    except Exception:  # noqa: BLE001 — tabela ainda não migrada: sem dado
        return []


def _acumulado_72h(db: Session, hoje) -> dict[str, float]:
    """Soma dos 3 dias locais (hoje e os 2 anteriores) do maior valor diário dos pluviômetros do distrito. Só vale com
    os 3 dias medidos; senão o distrito fica de fora (não é zero)."""
    try:
        with db.begin_nested():
            linhas = db.execute(
                text(
                    "select territorio_id, sum(max_mm), count(max_mm) from gold.chuva_apac_diaria "
                    "where nivel = 'distrito' and herdado_de is null and dia between :a and :b "
                    "group by territorio_id"
                ),
                {"a": hoje - timedelta(days=2), "b": hoje},
            ).all()
    except Exception:  # noqa: BLE001
        return {}
    return {t: round(float(s), 1) for t, s, n in linhas if n == 3 and s is not None}


# distrito de cada estação: o território dela pode ser o distrito ou um bairro (o pai é o distrito)


def _acumulado_72h_pluviometros(db: Session, recente_desde: datetime) -> dict[str, float]:
    """Maior acumulado de 72 h entre as estações do distrito, na última leitura de cada estação (só leituras
    recentes). É o acumulado OBSERVADO pelos pluviômetros, sem somar dias."""
    try:
        with db.begin_nested():
            linhas = db.execute(
                text(
                    "select d, max(v) from (select distinct on (l.estacao_id) l.estacao_id, l.valor_mm as v, "
                    "case when t.tipo = 'distrito' then t.id when t.tipo = 'bairro' then t.pai_id end as d from silver.apac_chuva_leituras l "
                    "join silver.estacoes e on e.id = l.estacao_id "
                    "join app.territorios t on t.id = e.territorio_id "
                    "where l.janela_h = 72 and l.lida_em >= :r order by l.estacao_id, l.lida_em desc) x "
                    "where d is not null and v is not null group by d"
                ),
                {"r": recente_desde},
            ).all()
    except Exception:  # noqa: BLE001 — tabela ainda não migrada: sem dado
        return {}
    return {d: round(float(v), 1) for d, v in linhas}


def _serie_observada(db: Session, desde: datetime) -> list[dict]:
    """Barras observadas: por hora, o maior acumulado de 1 h entre as estações (última leitura de cada estação na
    hora), no município e por distrito. Hora sem nenhuma leitura não aparece (lacuna, nunca zero)."""
    try:
        with db.begin_nested():
            linhas = db.execute(
                text(
                    "select h, estacao_id, v, d from (select date_trunc('hour', l.lida_em) as h, l.estacao_id, "
                    "(array_agg(l.valor_mm order by l.lida_em desc))[1] as v, "
                    "max(case when t.tipo = 'distrito' then t.id when t.tipo = 'bairro' then t.pai_id end) as d from silver.apac_chuva_leituras l "
                    "join silver.estacoes e on e.id = l.estacao_id "
                    "left join app.territorios t on t.id = e.territorio_id "
                    "where l.janela_h = 1 and l.valor_mm is not null and l.lida_em >= :d "
                    "group by 1, 2) x order by h"
                ),
                {"d": desde},
            ).all()
    except Exception:  # noqa: BLE001
        return []
    horas: dict[datetime, dict] = {}
    for h, _estacao, v, d in linhas:
        reg = horas.setdefault(h, {"t": h, "municipio_mm": 0.0, "distritos": {}})
        reg["municipio_mm"] = max(reg["municipio_mm"], float(v))
        if d is not None:
            reg["distritos"][d] = max(reg["distritos"].get(d, 0.0), float(v))
    return [
        {
            "t": h,
            "municipio_mm": round(r["municipio_mm"], 1),
            "distritos": {d: round(v, 1) for d, v in sorted(r["distritos"].items())},
        }
        for h, r in sorted(horas.items())
    ]


def _maior(itens: list[dict], campo: str) -> dict | None:
    com_valor = [i for i in itens if i[campo] is not None]
    if not com_valor:
        return None
    m = max(com_valor, key=lambda i: i[campo])
    return {"territorio_id": m["territorio_id"], "territorio_nome": m["territorio_nome"], "mm": m[campo]}


def montar(db: Session, agora: datetime) -> dict:
    inicio = agora.replace(minute=0, second=0, microsecond=0)
    return cache.obter("situacao_chuva", inicio, cache.VIVO_S, lambda: _montar(db, agora, inicio))


def _montar(db: Session, agora: datetime, inicio: datetime) -> dict:
    hoje = agora.astimezone(ZoneInfo("America/Recife")).date()
    distritos = estagios._territorios(db)[0]
    recente_desde = inicio - timedelta(minutes=LEITURA_VELHA_MIN)
    apac, acumulado_dia, serie, acumulado_obs, observada = em_paralelo(
        db,
        [
            _agora_apac,
            lambda s: _acumulado_72h(s, hoje),
            lambda s: cenarios.emitir(s, "recife", HORIZONTE_H, agora, registrar=False),
            lambda s: _acumulado_72h_pluviometros(s, recente_desde),
            lambda s: _serie_observada(s, inicio - timedelta(hours=HORIZONTE_H)),
        ],
    )
    por_ds = {r["territorio_id"]: r for r in apac if r["nivel"] == "distrito"}
    cidade = next((r for r in apac if r["nivel"] == "municipio"), None)
    itens = []
    for ds, nome in distritos.items():
        r = por_ds.get(ds)
        proprio = r is not None and r["herdado_de"] is None
        herdado = r is not None and r["herdado_de"] is not None  # sem pluviômetro próprio: nada de medição
        recente = bool(
            proprio
            and r["n_atualizadas"] > 0
            and r["lida_em"] is not None
            and r["chuva_24h_max_mm"] is not None
            and inicio - r["lida_em"] <= timedelta(minutes=LEITURA_VELHA_MIN)
        )
        motivo = None
        if r is None:
            motivo = "Dados insuficientes: falta a fonte apac-chuva neste distrito."
        elif not proprio:
            motivo = (
                "Dados insuficientes: o distrito não tem pluviômetro próprio (a chuva medida é do Recife)."
            )
        elif not recente:
            motivo = "Dados insuficientes: sem leitura dos pluviômetros nas últimas 2 h."
        itens.append(
            {
                "territorio_id": ds,
                "territorio_nome": nome,
                "chuva_24h_mm": round(float(r["chuva_24h_max_mm"]), 1) if recente else None,
                "chuva_72h_mm": (acumulado_obs.get(ds, acumulado_dia.get(ds)) if not herdado else None),
                "fonte_chuva": "apac-chuva"
                if not herdado and (recente or ds in acumulado_dia or ds in acumulado_obs)
                else None,
                "lida_em": r["lida_em"] if r else None,
                "estacoes_total": r["n_estacoes"] if proprio else None,
                "estacoes_com_leitura": r["n_atualizadas"] if proprio else None,
                "estacoes_sem_leitura": (r["n_estacoes"] - r["n_atualizadas"]) if proprio else None,
                "medicao_propria": proprio,
                "motivo": motivo,
            }
        )
    return {
        "gerado_em": agora,
        "distritos": itens,
        "maior_24h": _maior(itens, "chuva_24h_mm"),
        "maior_72h": _maior(itens, "chuva_72h_mm"),
        "estacoes": {
            "total": cidade["n_estacoes"] if cidade else None,
            "com_leitura": cidade["n_atualizadas"] if cidade else None,
            "sem_leitura": (cidade["n_estacoes"] - cidade["n_atualizadas"]) if cidade else None,
            "lida_em": cidade["lida_em"] if cidade else None,
        },
        "observada": {
            "fonte": "apac-chuva",
            "janela_h": 1,
            "serie": observada,
            "motivo": None
            if observada
            else "Dados insuficientes: falta a fonte apac-chuva (nenhuma leitura de 1 h nas últimas 72 h).",
        },
        "previsao": {
            "horizonte_h": HORIZONTE_H,
            "previsao_emitida_em": serie["previsao_emitida_em"],
            "mare_emitida_em": serie["mare_emitida_em"],
            "emissoes_na_faixa": serie["emissoes_na_faixa"],
            "faixa_disponivel": serie["emissoes_na_faixa"] >= 2,
            "chuva": serie["chuva"],
            "mare": serie["mare"],
        },
    }
