"""Ações de resposta em campo (F4): registro, situação, linha do tempo e lição aprendida."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import acoes as dom
from climasense.dominio.evento import RegistroInvalido
from climasense.dominio.recorte import inicio_do_dia_utc
from climasense.infra.modelos_sql import Usuario
from climasense.servicos import fluxo, prioridade_vulnerabilidade

ALVO = "acao_resposta"
EDITAVEIS = ("descricao", "responsavel", "situacao", "inicio_em", "fim_em", "licao_aprendida")

SQL_LISTA = """
select a.id, a.territorio_id, t.nome_exibicao as territorio_nome, coalesce(t.pai_id, a.territorio_id) as distrito_id,
       a.tipo, a.descricao, a.responsavel, a.situacao, a.inicio_em, a.fim_em, a.licao_aprendida,
       a.criado_em as criada_em, a.atualizado_em as atualizada_em, u.nome as autor_nome,
       ua.nome as atualizado_por_nome
from app.acoes_resposta a join app.territorios t on t.id = a.territorio_id
join app.usuarios u on u.id = a.criado_por join app.usuarios ua on ua.id = a.atualizado_por
where (cast(:id as uuid) is null or a.id = :id)
  and (cast(:t as varchar) is null or :t = 'recife' or a.territorio_id = :t or t.pai_id = :t)
  and (cast(:s as varchar) is null or a.situacao = :s)
  and (cast(:d as timestamptz) is null or coalesce(a.fim_em, 'infinity'::timestamptz) >= :d)
  and (cast(:a as timestamptz) is null or coalesce(a.inicio_em, a.criado_em) < :a)
order by coalesce(a.inicio_em, a.criado_em) desc, a.criado_em desc
"""


def _rotulos(r: dict) -> dict:
    return {
        **r,
        "tipo_rotulo": dom.TIPOS.get(r["tipo"], r["tipo"]),
        "situacao_rotulo": dom.SITUACOES[r["situacao"]],
    }


def listar(
    db: Session,
    territorio_id: str | None = None,
    situacao: str | None = None,
    desde: date | None = None,
    ate: date | None = None,
    ordem: str = "recente",
) -> dict:
    """Linha do tempo por território e período; `situacao=em_andamento` é o filtro “em andamento agora”.
    `territorio_id` de distrito inclui os bairros dele. O período pega ações que se cruzam com ele.
    `ordem="prioridade"` põe os distritos mais vulneráveis primeiro (RF-22, ordem de /territorios/prioridade);
    dentro do distrito, a mais recente primeiro. Sem carga da fonte de prioridade, cai em "recente"."""
    if situacao is not None:
        dom.validar_situacao(situacao)
    todas = [
        _rotulos(dict(r))
        for r in db.execute(
            text(SQL_LISTA),
            {
                "id": None,
                "t": territorio_id,
                "s": None,
                "d": inicio_do_dia_utc(desde) if desde else None,
                "a": inicio_do_dia_utc(ate + timedelta(days=1)) if ate else None,
            },
        ).mappings()
    ]
    contagens: dict[str, int] = {}
    for a in todas:
        contagens[a["situacao"]] = contagens.get(a["situacao"], 0) + 1
    itens = [a for a in todas if situacao is None or a["situacao"] == situacao]
    por_distrito: dict[str, dict] = {}
    for a in todas:
        d = por_distrito.setdefault(
            a["distrito_id"], {"distrito_id": a["distrito_id"], "distrito_nome": None, "contagens": {}}
        )
        d["contagens"][a["situacao"]] = d["contagens"].get(a["situacao"], 0) + 1
    prio = prioridade_vulnerabilidade.listar(db, "distrito") if ordem == "prioridade" else None
    posicao = {i["territorio_id"]: i["posicao"] for i in prio["itens"]} if prio else {}
    nomes = {i["territorio_id"]: i["nome"] for i in prio["itens"]} if prio else {}
    if not nomes and por_distrito:
        nomes = dict(
            db.execute(
                text("select id, nome_exibicao from app.territorios where id = any(:i)"),
                {"i": list(por_distrito)},
            ).all()
        )
    for d in por_distrito.values():
        d["distrito_nome"] = nomes.get(d["distrito_id"], d["distrito_id"])
    if posicao:  # sort estável: dentro do distrito segue a ordem recente da consulta
        itens = sorted(itens, key=lambda a: posicao.get(a["distrito_id"], 10_000))
    return {
        "itens": itens,
        "contagens": contagens,
        "total": len(todas),
        "por_distrito": sorted(por_distrito.values(), key=lambda d: d["distrito_id"]),
        "ordenado_por_prioridade": bool(posicao),
    }


def eventos(db: Session, acao_id: uuid.UUID) -> list[dict]:
    return [
        dict(r)
        for r in db.execute(
            text(
                "select e.id, e.em, u.nome as autor_nome, e.situacao, e.texto, e.alteracoes from app.acao_eventos e "
                "join app.usuarios u on u.id = e.autor_id where e.acao_id = :a order by e.em, e.id"
            ),
            {"a": acao_id},
        ).mappings()
    ]


def obter(db: Session, acao_id: uuid.UUID) -> dict:
    linha = (
        db.execute(text(SQL_LISTA), {"id": acao_id, "t": None, "s": None, "d": None, "a": None})
        .mappings()
        .first()
    )
    if not linha:
        raise RegistroInvalido(404, "Ação não encontrada.")
    return {**_rotulos(dict(linha)), "linha_do_tempo": eventos(db, acao_id)}


def _evento(
    db: Session, acao_id, autor: Usuario, agora: datetime, situacao: str, texto_: str, alt: dict
) -> None:
    db.execute(
        text(
            "insert into app.acao_eventos (acao_id, em, autor_id, situacao, texto, alteracoes) "
            "values (:a, :em, :u, :s, :t, cast(:alt as jsonb))"
        ),
        {
            "a": acao_id,
            "em": agora,
            "u": autor.id,
            "s": situacao,
            "t": texto_[:400],
            "alt": json.dumps(alt, ensure_ascii=False, default=str),
        },
    )


def _texto(v: str | None) -> str | None:
    return (v or "").strip() or None


def criar(db: Session, dados: dict, autor: Usuario, ip: str | None, agora: datetime) -> dict:
    dom.validar_tipo(dados.get("tipo") or "")
    situacao = dados.get("situacao") or "planejada"
    dom.validar_situacao(situacao)
    descricao = _texto(dados.get("descricao"))
    if not descricao:
        raise RegistroInvalido(422, "Descreva a ação.")
    dom.validar_licao(situacao, dados.get("licao_aprendida"))
    inicio, fim = dom.horarios(situacao, dados.get("inicio_em"), dados.get("fim_em"), agora)
    fluxo.validar_territorios(db, [dados.get("territorio_id") or ""])
    try:
        acao_id = uuid.uuid4()
        db.execute(
            text(
                "insert into app.acoes_resposta (id, territorio_id, tipo, descricao, responsavel, situacao, inicio_em, "
                "fim_em, licao_aprendida, criado_por, criado_em, atualizado_por, atualizado_em) values "
                "(:id, :t, :tipo, :d, :r, :s, :i, :f, :l, :u, :em, :u, :em)"
            ),
            {
                "id": acao_id,
                "t": dados["territorio_id"],
                "tipo": dados["tipo"],
                "d": descricao,
                "r": _texto(dados.get("responsavel")),
                "s": situacao,
                "i": inicio,
                "f": fim,
                "l": _texto(dados.get("licao_aprendida")),
                "u": autor.id,
                "em": agora,
            },
        )
        _evento(
            db,
            acao_id,
            autor,
            agora,
            situacao,
            f"Ação registrada como {dom.SITUACOES[situacao].lower()}.",
            {},
        )
        fluxo.auditar(
            db,
            "acao_resposta_registrada",
            autor,
            ALVO,
            acao_id,
            ip,
            territorio_id=dados["territorio_id"],
            tipo=dados["tipo"],
            situacao=situacao,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, acao_id)


def atualizar(
    db: Session, acao_id: uuid.UUID, dados: dict, autor: Usuario, ip: str | None, agora: datetime
) -> dict:
    antes = obter(db, acao_id)
    dados = {k: v for k, v in dados.items() if k in EDITAVEIS}
    situacao = dados.get("situacao") or antes["situacao"]
    dom.validar_transicao(antes["situacao"], situacao)
    if "descricao" in dados and not _texto(dados["descricao"]):
        raise RegistroInvalido(422, "A descrição não pode ficar vazia.")
    licao = dados.get("licao_aprendida", antes["licao_aprendida"])
    dom.validar_licao(situacao, licao)
    inicio, fim = dom.horarios(
        situacao, dados.get("inicio_em", antes["inicio_em"]), dados.get("fim_em", antes["fim_em"]), agora
    )
    depois = {
        "descricao": _texto(dados.get("descricao", antes["descricao"])),
        "responsavel": _texto(dados.get("responsavel", antes["responsavel"])),
        "situacao": situacao,
        "inicio_em": inicio,
        "fim_em": fim,
        "licao_aprendida": _texto(licao),
    }
    mudou = {k: {"de": antes[k], "para": v} for k, v in depois.items() if antes[k] != v}
    if not mudou:
        return antes
    if antes["situacao"] in dom.FINAIS and set(mudou) - {"licao_aprendida"}:
        raise RegistroInvalido(
            409, "A ação já foi encerrada: só a lição aprendida pode ser registrada agora."
        )
    partes = []
    if "situacao" in mudou:
        partes.append(f"Situação: {dom.SITUACOES[situacao].lower()}.")
    if "licao_aprendida" in mudou:
        partes.append("Lição aprendida registrada.")
    outros = [k for k in mudou if k not in ("situacao", "licao_aprendida")]
    if outros:
        partes.append("Atualizou " + ", ".join(k.replace("_", " ") for k in outros) + ".")
    try:
        db.execute(
            text(
                "update app.acoes_resposta set descricao = :descricao, responsavel = :responsavel, "
                "situacao = :situacao, inicio_em = :inicio_em, fim_em = :fim_em, licao_aprendida = :licao_aprendida, "
                "atualizado_por = :u, atualizado_em = :em where id = :id"
            ),
            {**depois, "id": acao_id, "u": autor.id, "em": agora},
        )
        _evento(db, acao_id, autor, agora, situacao, " ".join(partes), mudou)
        fluxo.auditar(db, "acao_resposta_atualizada", autor, ALVO, acao_id, ip, alteracoes=list(mudou))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, acao_id)
