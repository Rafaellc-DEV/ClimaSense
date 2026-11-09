"""Histórico de eventos de chuva: abrir, registrar na linha do tempo, encerrar e aprovar (RN-05, RF-19, RN-13).

Toda escrita é auditada na mesma transação. Aprovar exige outra pessoa (RN-05). O consolidado para leitura
fica em `servicos/relatorio_evento.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import eventos_chuva as dom
from climasense.dominio.distritos import nome_distrito
from climasense.dominio.evento import RegistroInvalido
from climasense.infra.modelos_sql import Usuario
from climasense.servicos import fluxo

ALVO = "evento_chuva"

SQL_EVENTO = """
select e.id, e.nome, e.inicio_em, e.fim_em, e.situacao, e.retrospectivo, e.distritos_afetados,
       e.situacao_final, e.pendencias,
       e.aberto_por, ua.nome as aberto_por_nome, e.aberto_em,
       e.encerrado_por, ue.nome as encerrado_por_nome, e.encerrado_em,
       e.aprovado_por, up.nome as aprovado_por_nome, e.aprovado_em
from app.eventos_chuva e
join app.usuarios ua on ua.id = e.aberto_por
left join app.usuarios ue on ue.id = e.encerrado_por
left join app.usuarios up on up.id = e.aprovado_por
"""


def _rotulos(r: dict) -> dict:
    return {
        **r,
        "situacao_rotulo": dom.SITUACOES[r["situacao"]],
        "duracao_horas": dom.duracao_horas(r["inicio_em"], r["fim_em"]),
        "distritos_afetados": list(r["distritos_afetados"] or []),
        "aguarda_aprovacao": r["situacao"] == "encerrado",
    }


def _nomes_distritos(db: Session, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    nomes = {
        i: n
        for i, n in db.execute(
            text("select id, nome_exibicao from app.territorios where id = any(:i)"), {"i": ids}
        )
    }
    return [{"id": i, "nome": nome_distrito(nomes.get(i, i))} for i in ids]


def itens(db: Session, evento_id: uuid.UUID) -> list[dict]:
    return [
        {**dict(r), "tipo_rotulo": dom.TIPOS_ITEM[r["tipo"]]}
        for r in db.execute(
            text(
                "select i.id, i.tipo, i.texto, i.fonte, i.estagio, i.equipes_mobilizadas, i.ocorrido_em, "
                "i.registrado_em, u.nome as autor_nome from app.evento_chuva_itens i "
                "join app.usuarios u on u.id = i.autor_id where i.evento_id = :e order by i.ocorrido_em, i.id"
            ),
            {"e": evento_id},
        ).mappings()
    ]


def basico(db: Session, evento_id: uuid.UUID) -> dict:
    linha = db.execute(text(SQL_EVENTO + " where e.id = :i"), {"i": evento_id}).mappings().first()
    if not linha:
        raise RegistroInvalido(404, "Evento não encontrado.")
    return _rotulos(dict(linha))


def obter(db: Session, evento_id: uuid.UUID) -> dict:
    ev = basico(db, evento_id)
    return {
        **ev,
        "distritos": _nomes_distritos(db, ev["distritos_afetados"]),
        "linha_do_tempo": itens(db, evento_id),
    }


def listar(db: Session, situacao: str | None = None) -> dict:
    if situacao is not None and situacao not in dom.SITUACOES:
        raise RegistroInvalido(422, "Situação desconhecida. Use: " + ", ".join(dom.SITUACOES) + ".")
    todos = [
        _rotulos(dict(r))
        for r in db.execute(text(SQL_EVENTO + " order by e.inicio_em desc, e.aberto_em desc")).mappings()
    ]
    contagens: dict[str, int] = {}
    for e in todos:
        contagens[e["situacao"]] = contagens.get(e["situacao"], 0) + 1
    return {
        "itens": [e for e in todos if situacao is None or e["situacao"] == situacao],
        "contagens": contagens,
        "total": len(todos),
    }


def _validar_distritos(db: Session, ids: list[str]) -> list[str]:
    ids = list(dict.fromkeys(ids))
    ok = {
        i
        for (i,) in db.execute(
            text("select id from app.territorios where tipo = 'distrito' and id = any(:i)"), {"i": ids}
        )
    }
    faltam = [i for i in ids if i not in ok]
    if faltam:
        raise RegistroInvalido(422, f"Distrito não encontrado: {', '.join(faltam)} (use ds-1 a ds-8).")
    return ids


def abrir(db: Session, dados: dict, autor: Usuario, ip: str | None, agora: datetime) -> dict:
    """Evento novo. Retrospectivo (evento antigo): exige início, término e situação final, e já nasce encerrado,
    esperando a aprovação de outra pessoa; não tem linha do tempo horária."""
    retro = bool(dados.get("retrospectivo"))
    inicio = dados.get("inicio_em") or agora
    fim = dados.get("fim_em")
    dom.validar_periodo(inicio, fim)
    if inicio > agora + timedelta(minutes=dom.TOLERANCIA_FUTURO_MIN):
        raise RegistroInvalido(422, "O início do evento não pode estar no futuro.")
    if retro:
        if fim is None:
            raise RegistroInvalido(422, "Evento retrospectivo precisa do início e do término.")
        if fim > agora + timedelta(minutes=dom.TOLERANCIA_FUTURO_MIN):
            raise RegistroInvalido(422, "O término do evento não pode estar no futuro.")
        final, pend = dom.validar_situacao_final(dados.get("situacao_final"), dados.get("pendencias"))
    else:
        if fim is not None or dados.get("situacao_final") or dados.get("pendencias"):
            raise RegistroInvalido(
                422, "Evento em andamento não tem término nem situação final: encerre depois de abrir."
            )
        final = pend = None
    distritos = _validar_distritos(db, dados.get("distritos_afetados") or [])
    nome = " ".join((dados.get("nome") or "").split()) or dom.nome_padrao(inicio)
    evento_id = uuid.uuid4()
    situacao = "encerrado" if retro else "aberto"
    try:
        db.execute(
            text(
                "insert into app.eventos_chuva (id, nome, inicio_em, fim_em, situacao, retrospectivo, "
                "distritos_afetados, situacao_final, pendencias, aberto_por, aberto_em, encerrado_por, encerrado_em) "
                "values (:id, :n, :i, :f, :s, :r, :d, :sf, :p, :u, :em, :eu, :ee)"
            ),
            {
                "id": evento_id,
                "n": nome[:160],
                "i": inicio,
                "f": fim,
                "s": situacao,
                "r": retro,
                "d": distritos,
                "sf": final,
                "p": pend,
                "u": autor.id,
                "em": agora,
                "eu": autor.id if retro else None,
                "ee": agora if retro else None,
            },
        )
        fluxo.auditar(
            db,
            "evento_chuva_aberto",
            autor,
            ALVO,
            evento_id,
            ip,
            retrospectivo=retro,
            situacao=situacao,
            distritos=distritos,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, evento_id)


def registrar_item(
    db: Session, evento_id: uuid.UUID, dados: dict, autor: Usuario, ip: str | None, agora: datetime
) -> dict:
    ev = basico(db, evento_id)
    if ev["retrospectivo"]:
        raise RegistroInvalido(409, "Evento retrospectivo não tem linha do tempo horária.")
    if ev["situacao"] != "aberto":
        raise RegistroInvalido(409, "O evento já foi encerrado: a linha do tempo não aceita novos registros.")
    item = dom.validar_item(
        dados.get("tipo") or "",
        dados.get("texto"),
        dados.get("fonte"),
        dados.get("equipes_mobilizadas"),
        dados.get("estagio"),
    )
    quando = dados.get("ocorrido_em") or agora
    if quando > agora + timedelta(minutes=dom.TOLERANCIA_FUTURO_MIN):
        raise RegistroInvalido(422, "A hora do registro não pode estar no futuro.")
    if quando < ev["inicio_em"]:
        raise RegistroInvalido(422, "A hora do registro é anterior ao início do evento.")
    try:
        item_id = db.execute(
            text(
                "insert into app.evento_chuva_itens (evento_id, tipo, texto, fonte, estagio, equipes_mobilizadas, "
                "ocorrido_em, autor_id, registrado_em) values (:e, :t, :x, :f, :s, :q, :o, :u, :r) returning id"
            ),
            {
                "e": evento_id,
                "t": item["tipo"],
                "x": item["texto"],
                "f": item["fonte"],
                "s": item["estagio"],
                "q": item["equipes"],
                "o": quando,
                "u": autor.id,
                "r": agora,
            },
        ).scalar_one()
        fluxo.auditar(
            db,
            "evento_chuva_item_registrado",
            autor,
            ALVO,
            evento_id,
            ip,
            item_id=item_id,
            tipo=item["tipo"],
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, evento_id)


def encerrar(
    db: Session, evento_id: uuid.UUID, dados: dict, autor: Usuario, ip: str | None, agora: datetime
) -> dict:
    ev = basico(db, evento_id)
    if ev["situacao"] != "aberto":
        raise RegistroInvalido(409, "O evento já foi encerrado.")
    final, pend = dom.validar_situacao_final(dados.get("situacao_final"), dados.get("pendencias"))
    fim = dados.get("fim_em") or agora
    dom.validar_periodo(ev["inicio_em"], fim)
    if fim > agora + timedelta(minutes=dom.TOLERANCIA_FUTURO_MIN):
        raise RegistroInvalido(422, "O término do evento não pode estar no futuro.")
    try:
        db.execute(
            text(
                "update app.eventos_chuva set situacao = 'encerrado', fim_em = :f, situacao_final = :sf, "
                "pendencias = :p, encerrado_por = :u, encerrado_em = :em where id = :id and situacao = 'aberto'"
            ),
            {"f": fim, "sf": final, "p": pend, "u": autor.id, "em": agora, "id": evento_id},
        )
        fluxo.auditar(db, "evento_chuva_encerrado", autor, ALVO, evento_id, ip, com_pendencias=bool(pend))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, evento_id)


def aprovar(db: Session, evento_id: uuid.UUID, autor: Usuario, ip: str | None, agora: datetime) -> dict:
    """RN-05: aprova outra pessoa que não abriu nem encerrou o evento."""
    ev = basico(db, evento_id)
    dom.validar_aprovador(ev, autor.id)
    try:
        db.execute(
            text(
                "update app.eventos_chuva set situacao = 'aprovado', aprovado_por = :u, aprovado_em = :em "
                "where id = :id and situacao = 'encerrado'"
            ),
            {"u": autor.id, "em": agora, "id": evento_id},
        )
        fluxo.auditar(db, "evento_chuva_aprovado", autor, ALVO, evento_id, ip)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, evento_id)
