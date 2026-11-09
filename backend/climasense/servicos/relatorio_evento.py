"""Relatório executivo de um evento de chuva (RF-19, RN-01, RN-02, RN-13).

Montado SÓ com dados reais que já existem: o registro da equipe (evento, linha do tempo, ações, estágios
declarados) e as tabelas de chuva APAC, maré e saúde. Cada bloco traz a fonte e a hora da última atualização. Bloco
sem dado vem com `suficiente = false` e o motivo em "Dados insuficientes" (nunca zero, nunca "sem risco").
Contagens de agravo entre 1 e `supressao_minima - 1` saem nulas (RN-13). Não há abrigos (ADR 0016) nem texto
narrativo gerado: só frases fixas.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import estagio as dom_estagio
from climasense.dominio.distritos import nome_distrito
from climasense.dominio.recorte import dia_no_recife, inicio_do_dia_utc
from climasense.dominio.supressao import deve_suprimir, suprimir
from climasense.servicos import acoes, eventos_chuva, saude_agravos

FONTE_EQUIPE = "Registro da equipe (ClimaSense)"
FONTE_ESTAGIOS = "Declarações de estágio da equipe (ClimaSense)"
FONTE_COP = "COP (informado pela equipe)"
FONTE_CHUVA = "APAC e Cemaden: chuva medida nos pluviômetros (apac-chuva)"
FONTE_MARE = "Open-Meteo Marine: nível do mar previsto pelo modelo, não é medição (open-meteo-mare)"
FONTES_SAUDE = {
    "dengue": "InfoDengue (infodengue)",
    "chikungunya": "InfoDengue (infodengue)",
    "leptospirose": "SINAN, leptospirose (sinan-leptospirose)",
}


def _bloco(fonte: str, atualizado_em: datetime | None, suficiente: bool, motivo: str | None = None) -> dict:
    return {
        "fonte": fonte,
        "atualizado_em": atualizado_em,
        "suficiente": suficiente,
        "motivo": None if suficiente else motivo,
    }


def _ate(ev: dict, agora: datetime) -> datetime:
    return ev["fim_em"] or agora


# ------------------------------------------------------------------ registro da equipe
def _identificacao(ev: dict) -> dict:
    marcas = [ev["aberto_em"], ev["encerrado_em"], ev["aprovado_em"]]
    return {
        **_bloco(FONTE_EQUIPE, max(m for m in marcas if m), True),
        "id": ev["id"],
        "nome": ev["nome"],
        "situacao": ev["situacao"],
        "situacao_rotulo": ev["situacao_rotulo"],
        "retrospectivo": ev["retrospectivo"],
        "inicio_em": ev["inicio_em"],
        "fim_em": ev["fim_em"],
        "duracao_horas": ev["duracao_horas"],
        "aberto_por_nome": ev["aberto_por_nome"],
        "aberto_em": ev["aberto_em"],
        "encerrado_por_nome": ev["encerrado_por_nome"],
        "encerrado_em": ev["encerrado_em"],
        "aprovado_por_nome": ev["aprovado_por_nome"],
        "aprovado_em": ev["aprovado_em"],
        "aprovado": ev["situacao"] == "aprovado",
    }


def _comunicados(ev: dict, itens: list[dict]) -> dict:
    lista = [i for i in itens if i["tipo"] == "comunicado"]
    if not lista:
        motivo = (
            "Não disponível nesta fonte: evento retrospectivo, sem comunicados registrados."
            if ev["retrospectivo"]
            else "Dados insuficientes: nenhum comunicado registrado pela equipe neste evento."
        )
        return {**_bloco(FONTE_EQUIPE, None, False, motivo), "itens": []}
    return {
        **_bloco(FONTE_EQUIPE, max(i["registrado_em"] for i in lista), True),
        "itens": [
            {
                "ocorrido_em": i["ocorrido_em"],
                "texto": i["texto"],
                "fonte": i["fonte"],
                "autor_nome": i["autor_nome"],
            }
            for i in lista
        ],
    }


def _equipes(ev: dict, itens: list[dict]) -> dict:
    lista = [i for i in itens if i["equipes_mobilizadas"] is not None]
    if not lista:
        motivo = "Dados insuficientes: nenhum número de equipes mobilizadas registrado pela equipe."
        return {**_bloco(FONTE_EQUIPE, None, False, motivo), "maior_numero": None, "registros": []}
    return {
        **_bloco(FONTE_EQUIPE, max(i["registrado_em"] for i in lista), True),
        "maior_numero": max(i["equipes_mobilizadas"] for i in lista),  # agregado; nada que identifique pessoa
        "registros": [
            {
                "ocorrido_em": i["ocorrido_em"],
                "equipes_mobilizadas": i["equipes_mobilizadas"],
                "fonte": i["fonte"],
            }
            for i in lista
        ],
    }


def _situacao_final(ev: dict) -> dict:
    if not ev["situacao_final"]:
        motivo = "Dados insuficientes: o evento ainda não foi encerrado, sem situação final registrada."
        return {**_bloco(FONTE_EQUIPE, None, False, motivo), "situacao_final": None, "pendencias": None}
    return {
        **_bloco(FONTE_EQUIPE, ev["encerrado_em"], True),
        "situacao_final": ev["situacao_final"],
        "pendencias": ev["pendencias"],
        "encerrado_por_nome": ev["encerrado_por_nome"],
        "aprovada": ev["situacao"] == "aprovado",
        "aprovado_por_nome": ev["aprovado_por_nome"],
        "aprovado_em": ev["aprovado_em"],
    }


# ------------------------------------------------------------------ estágios e distritos
def _declaracoes(db: Session, ini: datetime, fim: datetime) -> list[dict]:
    return [
        dict(r)
        for r in db.execute(
            text(
                "select d.id, d.estagio, d.justificativa, d.declarado_em, d.territorio_id, t.nome_exibicao "
                "as territorio_nome, case when t.tipo = 'bairro' then t.pai_id else t.id end as distrito_id, "
                "u.nome as autor_nome from app.estagio_declaracoes d join app.territorios t on t.id = d.territorio_id "
                "join app.usuarios u on u.id = d.autor_id where d.declarado_em >= :i and d.declarado_em <= :f "
                "order by d.declarado_em, d.id"
            ),
            {"i": ini, "f": fim},
        ).mappings()
    ]


def _distritos(db: Session, ev: dict, declaracoes: list[dict]) -> dict:
    por: dict[str, dict] = {}
    for d in declaracoes:
        x = por.setdefault(
            d["distrito_id"],
            {"distrito_id": d["distrito_id"], "n_declaracoes": 0, "maior": None, "ultima_em": None},
        )
        x["n_declaracoes"] += 1
        if x["maior"] is None or dom_estagio.ESCADA.index(d["estagio"]) > dom_estagio.ESCADA.index(
            x["maior"]
        ):
            x["maior"] = d["estagio"]
        x["ultima_em"] = d["declarado_em"]
    nomes = {
        i: n
        for i, n in db.execute(text("select id, nome_exibicao from app.territorios where tipo <> 'bairro'"))
    }
    com_estagio = [
        {
            "distrito_id": x["distrito_id"],
            "distrito_nome": "Recife (cidade)"
            if x["distrito_id"] == "recife"
            else nome_distrito(nomes.get(x["distrito_id"])),
            "maior_estagio": x["maior"],
            "maior_estagio_rotulo": dom_estagio.ROTULO[x["maior"]],
            "n_declaracoes": x["n_declaracoes"],
            "ultima_em": x["ultima_em"],
        }
        for x in sorted(por.values(), key=lambda v: v["distrito_id"])
    ]
    registrados = [
        {"distrito_id": i, "distrito_nome": nome_distrito(nomes.get(i, i))} for i in ev["distritos_afetados"]
    ]
    atualizado = max([d["declarado_em"] for d in declaracoes] + [ev["aberto_em"]])
    if not com_estagio and not registrados:
        motivo = (
            "Dados insuficientes: nenhum estágio declarado no período e nenhum distrito marcado pela equipe."
        )
        return {**_bloco(FONTE_ESTAGIOS, None, False, motivo), "com_estagio_declarado": [], "registrados": []}
    return {
        **_bloco(FONTE_ESTAGIOS, atualizado, True),
        "com_estagio_declarado": com_estagio,
        "registrados": registrados,
    }


# ------------------------------------------------------------------ chuva e maré
def _chuva(db: Session, d_ini: date, d_fim: date) -> dict:
    linhas = db.execute(
        text(
            "select g.dia, max(g.max_mm) as max_mm, "
            "(array_agg(g.territorio_id order by g.max_mm desc nulls last))[1] as distrito_id, "
            "count(g.max_mm)::int as distritos_com_dado from gold.chuva_apac_diaria g "
            "where g.nivel = 'distrito' and g.dia between :a and :b group by g.dia order by g.dia"
        ),
        {"a": d_ini, "b": d_fim},
    ).mappings()
    dias = [dict(r) for r in linhas]
    visto = db.execute(
        text(
            "select max(coletado_em) from silver.apac_chuva_diaria where dia between :a and :b and qualidade <> 'falha'"
        ),
        {"a": d_ini, "b": d_fim},
    ).scalar()
    com_dado = [d for d in dias if d["max_mm"] is not None]
    if not com_dado:
        motivo = "Dados insuficientes: sem chuva medida pela APAC no período (fonte apac-chuva)."
        return {**_bloco(FONTE_CHUVA, visto, False, motivo), "dias": [], "pico_diario_mm": None}
    nomes = dict(
        db.execute(text("select id, nome_exibicao from app.territorios where tipo = 'distrito'")).all()
    )
    pico = max(com_dado, key=lambda d: d["max_mm"])
    return {
        **_bloco(FONTE_CHUVA, visto, True),
        "pico_diario_mm": round(pico["max_mm"], 1),
        "pico_dia": pico["dia"],
        "pico_distrito_nome": nome_distrito(nomes.get(pico["distrito_id"])),
        "dias": [
            {
                "dia": d["dia"],
                "maximo_mm": None
                if d["max_mm"] is None
                else round(d["max_mm"], 1),  # zero medido é zero (RN-02)
                "distrito_nome": nome_distrito(nomes.get(d["distrito_id"]))
                if d["max_mm"] is not None
                else None,
                "distritos_com_dado": d["distritos_com_dado"],
            }
            for d in dias
        ],
    }


def _mare(db: Session, d_ini: date, d_fim: date) -> dict:
    """Nível do mar do modelo, por dia do Recife: para cada hora vale a emissão mais recente feita até aquela
    hora (previsão, nunca medição: a fonte diz isso)."""
    linhas = [
        dict(r)
        for r in db.execute(
            text(
                "select (observado_em at time zone 'America/Recife')::date as dia, max(valor) as maximo_m, "
                "min(valor) as minimo_m, count(valor)::int as horas, max(coletado_em) as visto from ("
                "select distinct on (observado_em) observado_em, valor, coletado_em from silver.observacoes "
                "where variavel = 'mare_m' and fonte_id = 'open-meteo-mare' and tipo = 'prevista' "
                "and valor is not null and qualidade <> 'ausente' and emitido_em <= observado_em "
                "and observado_em >= :a and observado_em < :b order by observado_em, emitido_em desc) x "
                "group by 1 order by 1"
            ),
            {"a": inicio_do_dia_utc(d_ini), "b": inicio_do_dia_utc(d_fim + timedelta(days=1))},
        ).mappings()
    ]
    if not linhas:
        motivo = "Dados insuficientes: sem nível do mar da fonte open-meteo-mare no período."
        return {**_bloco(FONTE_MARE, None, False, motivo), "dias": [], "maximo_m": None}
    return {
        **_bloco(FONTE_MARE, max(r["visto"] for r in linhas), True),
        "maximo_m": round(max(r["maximo_m"] for r in linhas), 2),
        "dias": [
            {
                "dia": r["dia"],
                "maximo_m": round(r["maximo_m"], 2),
                "minimo_m": round(r["minimo_m"], 2),
                "horas_com_dado": r["horas"],
            }
            for r in linhas
        ],
    }


# ------------------------------------------------------------------ saúde
def _semanas_saude(db: Session, d_ini: date, d_fim: date) -> list[dict]:
    return [
        dict(r)
        for r in db.execute(
            text(
                "select agravo, ano, semana, inicio, casos, confirmados, casos_estimados, ic_inf, ic_sup, "
                "nivel_alerta, rt, incompleta from gold.saude_semanal where inicio >= :a and inicio <= :b "
                "order by agravo, inicio"
            ),
            {"a": saude_agravos.domingo(d_ini), "b": d_fim},
        ).mappings()
    ]


def _visto_saude(db: Session, d_ini: date, d_fim: date) -> dict[str, datetime | None]:
    args = {"a": saude_agravos.domingo(d_ini), "b": d_fim}
    dengue = db.execute(
        text("select max(coletado_em) from silver.infodengue_semanal where inicio >= :a and inicio <= :b"),
        args,
    ).scalar()
    lepto = db.execute(
        text("select max(coletado_em) from silver.leptospirose_semanal where inicio >= :a and inicio <= :b"),
        args,
    ).scalar()
    return {"dengue": dengue, "chikungunya": dengue, "leptospirose": lepto}


def agravo_na_janela(agravo: str, semanas: list[dict], minimo: int, visto: datetime | None) -> dict:
    """Um agravo na janela. Semana sem `casos` é ausência (não zero). Semana com 1 a `minimo - 1` casos sai nula
    e some junto com as estimativas (que a revelariam); o total some se alguma semana foi suprimida (RN-13)."""
    nome = {"dengue": "Dengue", "chikungunya": "Chikungunya", "leptospirose": "Leptospirose"}[agravo]
    fonte_id = FONTES_SAUDE[agravo]
    com_dado = [s for s in semanas if s["casos"] is not None]
    if not com_dado:
        motivo = f"Dados insuficientes: {fonte_id} não tem semana com dado nesta janela."
        return {
            **_bloco(fonte_id, visto, False, motivo),
            "agravo": agravo,
            "nome": nome,
            "semanas": [],
            "total_casos": None,
            "suprimido": False,
        }
    saida, houve = [], False
    for s in com_dado:
        casos, sup = suprimir(s["casos"], minimo)
        confirmados, sup_c = suprimir(s["confirmados"], minimo)
        oculto = sup or sup_c
        houve = houve or oculto
        saida.append(
            {
                "ano": s["ano"],
                "semana": s["semana"],
                "inicio": s["inicio"],
                "casos": casos,
                "confirmados": confirmados,
                "casos_estimados": None if oculto else s["casos_estimados"],
                "ic_inf": None if oculto else s["ic_inf"],
                "ic_sup": None if oculto else s["ic_sup"],
                "nivel_alerta": s["nivel_alerta"],
                "incompleta": bool(s["incompleta"]),
                "suprimido": oculto,
            }
        )
    total = sum(s["casos"] for s in com_dado)
    total_oculto = houve or deve_suprimir(total, minimo)
    return {
        **_bloco(fonte_id, visto, True),
        "agravo": agravo,
        "nome": nome,
        "semanas": saida,
        "total_casos": None if total_oculto else total,
        "suprimido": total_oculto,
    }


def _saude(db: Session, d_ini: date, d_fim: date, minimo: int) -> dict:
    semanas = _semanas_saude(db, d_ini, d_fim)
    visto = _visto_saude(db, d_ini, d_fim)
    itens = [
        agravo_na_janela(a, [s for s in semanas if s["agravo"] == a], minimo, visto[a])
        for a in saude_agravos.AGRAVOS
    ]
    return {
        "supressao_minima": minimo,
        "itens": itens,
        "suficiente": any(i["suficiente"] for i in itens),
    }


# ------------------------------------------------------------------ ações e linha do tempo
def _acoes(db: Session, d_ini: date, d_fim: date) -> tuple[dict, list[dict]]:
    todas = acoes.listar(db, None, None, d_ini, d_fim)["itens"]
    if not todas:
        motivo = "Dados insuficientes: nenhuma ação registrada pela equipe no período (não significa que não houve)."
        return {**_bloco(FONTE_EQUIPE, None, False, motivo), "contagens": {}, "itens": []}, []
    itens = [
        {  # sem `responsavel`: pode ser nome de pessoa (RN-13)
            "id": a["id"],
            "territorio_nome": a["territorio_nome"],
            "distrito_nome": a["distrito_nome"],
            "tipo": a["tipo"],
            "tipo_rotulo": a["tipo_rotulo"],
            "descricao": a["descricao"],
            "situacao": a["situacao"],
            "situacao_rotulo": a["situacao_rotulo"],
            "inicio_em": a["inicio_em"],
            "fim_em": a["fim_em"],
            "registrada_em": a["criada_em"],
        }
        for a in todas
    ]
    contagens: dict[str, int] = {}
    for a in todas:
        contagens[a["situacao"]] = contagens.get(a["situacao"], 0) + 1
    bloco = {
        **_bloco("Registro da equipe (tela Ações)", max(a["atualizada_em"] for a in todas), True),
        "contagens": contagens,
        "itens": itens,
    }
    return bloco, todas


def _oficiais(db: Session, ini: datetime, fim: datetime) -> list[dict]:
    return [
        dict(r)
        for r in db.execute(
            text(
                "select o.estagio, o.informado_em, o.observacao from app.estagio_oficial o "
                "where o.informado_em >= :i and o.informado_em <= :f order by o.informado_em"
            ),
            {"i": ini, "f": fim},
        ).mappings()
    ]


def _linha_do_tempo(
    ev: dict, itens: list[dict], decl: list[dict], acoes_: list[dict], oficiais: list[dict]
) -> dict:
    marcos: list[dict] = [
        {"em": i["ocorrido_em"], "tipo": i["tipo"], "texto": i["texto"], "fonte": i["fonte"]} for i in itens
    ]
    marcos += [
        {
            "em": d["declarado_em"],
            "tipo": "estagio",
            "texto": f"Estágio {dom_estagio.ROTULO[d['estagio']]} declarado para {nome_distrito(d['territorio_nome'])}.",
            "fonte": FONTE_ESTAGIOS,
        }
        for d in decl
    ]
    marcos += [
        {
            "em": o["informado_em"],
            "tipo": "estagio",
            "texto": f"Estágio oficial da cidade informado pelo COP: {dom_estagio.ROTULO[o['estagio']]}.",
            "fonte": FONTE_COP,
        }
        for o in oficiais
    ]
    marcos += [
        {
            "em": a["inicio_em"] or a["criada_em"],
            "tipo": "acao",
            "texto": f"Ação ({a['tipo_rotulo'].lower()}) em {a['territorio_nome']}: {a['descricao']}",
            "fonte": "Registro da equipe (tela Ações)",
        }
        for a in acoes_
    ]
    marcos.sort(key=lambda m: m["em"])
    if not marcos:
        motivo = (
            "Não disponível nesta fonte: evento retrospectivo, sem linha do tempo horária."
            if ev["retrospectivo"]
            else "Dados insuficientes: nada registrado na linha do tempo, nos estágios nem nas ações do período."
        )
        return {**_bloco(FONTE_EQUIPE, None, False, motivo), "itens": []}
    return {
        **_bloco("Registros da equipe e do COP (ClimaSense)", max(m["em"] for m in marcos), True),
        "itens": marcos,
    }


# ------------------------------------------------------------------ consolidado
def montar(db: Session, evento_id: uuid.UUID, agora: datetime, supressao_minima: int) -> dict:
    ev = eventos_chuva.basico(db, evento_id)
    itens = eventos_chuva.itens(db, evento_id)
    ini, fim = ev["inicio_em"], _ate(ev, agora)
    d_ini, d_fim = dia_no_recife(ini), dia_no_recife(fim)
    decl = _declaracoes(db, ini, fim)
    bloco_acoes, acoes_lista = _acoes(db, d_ini, d_fim)
    return {
        "gerado_em": agora,
        "periodo": {
            "inicio_em": ini,
            "fim_em": ev["fim_em"],
            "desde": d_ini,
            "ate": d_fim,
            "em_andamento": ev["fim_em"] is None,
        },
        "aviso": None
        if ev["situacao"] == "aprovado"
        else "Rascunho: a situação final ainda não foi aprovada por uma segunda pessoa (RN-05).",
        "evento": _identificacao(ev),
        "comunicados": _comunicados(ev, itens),
        "equipes_mobilizadas": _equipes(ev, itens),
        "distritos_afetados": _distritos(db, ev, decl),
        "chuva": _chuva(db, d_ini, d_fim),
        "mare": _mare(db, d_ini, d_fim),
        "saude": _saude(db, d_ini, d_fim, supressao_minima),
        "acoes": bloco_acoes,
        "linha_do_tempo": _linha_do_tempo(ev, itens, decl, acoes_lista, _oficiais(db, ini, fim)),
        "situacao_final": _situacao_final(ev),
    }
