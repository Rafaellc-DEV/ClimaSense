"""Boletim situacional (F5): retrato de uma página do evento e o resumo em texto para WhatsApp.

Junta estágio por distrito, territórios em atenção, chuva, maré e ações em andamento. O que faltar
aparece como ausente, nunca como zero (RN-01, RN-02).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from climasense.dominio import estagio as dom
from climasense.dominio.mensagem import texto_boletim, wa_me_url
from climasense.dominio.recorte import inicio_do_dia_utc
from climasense.infra.postgres import em_paralelo
from climasense.servicos import acoes, estagio_oficial, estagios, saude_agravos

NIVEIS_ATENCAO = {"atencao", "alerta", "critico"}
CHUVAS = ("chuva_24h", "chuva_prev_24h", "chuva_prev_72h")


def _efetivo(item: dict) -> tuple[str, str]:
    """Estágio que vale para a equipe: o declarado, se houver; senão, o sugerido."""
    if item["declarado"]:
        return item["declarado"]["estagio"], "declarado"
    return item["sugerido"]["estagio"], "sugerido"


def _subiu(estagio: str, referencia: str) -> bool:
    if estagio not in dom.ESCADA:
        return False
    return referencia not in dom.ESCADA or dom.ESCADA.index(estagio) > dom.ESCADA.index(referencia)


def em_atencao(itens: list[dict]) -> list[dict]:
    """Distritos em atenção ou acima e só os bairros que se destacam do distrito (declaração própria ou
    sugestão maior que a do distrito, por ocorrências ou modelo): sem repetir os 94 bairros herdados."""
    por_ds = {i["territorio_id"]: i for i in itens if i["nivel"] == "distrito"}
    saida = []
    for it in itens:
        estagio, origem = _efetivo(it)
        if estagio not in NIVEIS_ATENCAO:
            continue
        if it["nivel"] == "bairro":
            proprio = it["declarado"] and not it["declarado"]["herdado"]
            ds = por_ds.get(it["distrito_id"])
            if not proprio and not (ds and _subiu(it["sugerido"]["estagio"], ds["sugerido"]["estagio"])):
                continue
        motivo = (
            it["declarado"]["justificativa"]
            if origem == "declarado"
            else (it["sugerido"]["motivos"] or [""])[0]
        )
        saida.append(
            {
                "territorio_id": it["territorio_id"],
                "territorio_nome": it["territorio_nome"],
                "nivel": it["nivel"],
                "distrito_id": it["distrito_id"],
                "estagio": estagio,
                "rotulo": dom.ROTULO[estagio],
                "origem": origem,
                "motivo": motivo,
            }
        )
    return sorted(saida, key=lambda x: (-dom.ESCADA.index(x["estagio"]), x["nivel"], x["territorio_nome"]))


def _resumo_chuva(distritos: list[dict]) -> dict:
    """Maior valor entre os distritos para cada janela, com o nome de onde veio."""
    resumo = {}
    for chave in CHUVAS:
        valores = [
            (d["sugerido"]["insumos"].get(f"{chave}_mm"), d["territorio_nome"])
            for d in distritos
            if d["sugerido"]["insumos"].get(f"{chave}_mm") is not None
        ]
        resumo[chave] = max(valores) if valores else (None, None)
    return resumo


DIAS_PERIODO = 7


def periodo(agora: datetime, desde: date | None, ate: date | None) -> tuple[date, date]:
    """Período do relatório (datas do Recife). Padrão: os últimos 7 dias, incluindo hoje."""
    fim = ate or saude_agravos.hoje_recife(agora)
    return desde or fim - timedelta(days=DIAS_PERIODO - 1), fim


def montar(
    db: Session,
    distrito_id: str | None,
    agora: datetime,
    desde: date | None = None,
    ate: date | None = None,
) -> dict:
    ini, fim = periodo(agora, desde, ate)
    limite_ini, limite_fim = inicio_do_dia_utc(ini), inicio_do_dia_utc(fim + timedelta(days=1))
    # leituras independentes ao mesmo tempo: o tempo total é o da mais lenta, não a soma (banco remoto)
    itens, andamento_r, do_periodo, oficial, saude = em_paralelo(
        db,
        [
            lambda s: estagios.listar(s, "todos", agora, distrito_id),
            lambda s: acoes.listar(s, distrito_id, "em_andamento", ordem="prioridade"),
            lambda s: acoes.listar(s, distrito_id, None, ini, fim),
            lambda s: estagio_oficial.vigente(s),
            lambda s: saude_agravos.resumo_agravos(s, agora),
        ],
    )
    distritos = [i for i in itens if i["nivel"] == "distrito"]
    chuva = _resumo_chuva(distritos)
    ins = distritos[0]["sugerido"]["insumos"] if distritos else {}
    andamento = andamento_r["itens"]
    concluidas = [
        a
        for a in do_periodo["itens"]
        if a["situacao"] == "concluida" and a["fim_em"] and limite_ini <= a["fim_em"] < limite_fim
    ]
    return {
        "gerado_em": agora,
        "periodo": {"desde": ini, "ate": fim},
        "estagio_oficial": oficial,
        "saude": saude,
        "acoes_concluidas": concluidas,
        "acoes_por_distrito": do_periodo["por_distrito"],
        "estagios": [
            {
                "territorio_id": d["territorio_id"],
                "territorio_nome": d["territorio_nome"],
                "estagio": _efetivo(d)[0],
                "rotulo": dom.ROTULO[_efetivo(d)[0]],
                "origem": _efetivo(d)[1],
                "sugerido": d["sugerido"],
                "declarado": d["declarado"],
            }
            for d in distritos
        ],
        "territorios_em_atencao": em_atencao(itens),
        "chuva": {f"{c}_mm": chuva[c][0] for c in CHUVAS}
        | {f"{c}_territorio": chuva[c][1] for c in CHUVAS}
        | {
            "previsao_emitida_em": max(
                (
                    d["sugerido"]["insumos"].get("previsao_emitida_em")
                    for d in distritos
                    if d["sugerido"]["insumos"].get("previsao_emitida_em")
                ),
                default=None,
            )
        },
        "mare": {
            "maxima_m": ins.get("mare_max_m"),
            "maxima_em": ins.get("mare_max_em"),
            "emitida_em": ins.get("mare_emitida_em"),
        },
        "acoes_em_andamento": andamento,
    }


def texto(b: dict, territorio_nome: str) -> dict:
    mare = b["mare"]
    corpo = texto_boletim(
        territorio_nome,
        b["gerado_em"],
        [(e["territorio_nome"], e["estagio"], e["origem"]) for e in b["estagios"]],
        {c: (b["chuva"][f"{c}_mm"], b["chuva"][f"{c}_territorio"]) for c in CHUVAS},
        (mare["maxima_m"], mare["maxima_em"]) if mare["maxima_m"] is not None and mare["maxima_em"] else None,
        len(b["acoes_em_andamento"]),
        oficial=b["estagio_oficial"],
        acoes_concluidas=len(b["acoes_concluidas"]),
        periodo=(b["periodo"]["desde"], b["periodo"]["ate"]),
        saude=b["saude"],
    )
    return {"texto": corpo, "wa_me_url": wa_me_url(corpo)}
