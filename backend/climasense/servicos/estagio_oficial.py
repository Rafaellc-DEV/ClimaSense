"""Estágio oficial da cidade dado pelo COP (RF-01, RN-01).

Registro manual da equipe até haver feed do COP. É um dado informado, não uma decisão do ClimaSense: a sugestão
nunca grava aqui (RF-29, RF-30). Histórico somente-inclusão; o vigente é o de `informado_em` mais recente.
Sem registro, não há estágio oficial (`None`): a tela mostra "Dados insuficientes", nunca "observação" (RN-01).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import estagio as dom
from climasense.dominio.evento import RegistroInvalido
from climasense.infra.modelos_sql import Usuario
from climasense.servicos import fluxo

ALVO = "estagio_oficial"
FONTE = "COP (informado pela equipe)"
MAX_OBSERVACAO = 500
TOLERANCIA_FUTURO = timedelta(minutes=5)

_SQL = (
    "select o.id, o.estagio, o.informado_em, o.registrado_em, o.observacao, u.nome as autor_nome "
    "from app.estagio_oficial o join app.usuarios u on u.id = o.autor_id "
)


def _linha(r) -> dict:
    return {
        "estagio": r["estagio"],
        "informado_em": r["informado_em"],
        "registrado_em": r["registrado_em"],
        "autor_nome": r["autor_nome"],
        "observacao": r["observacao"],
        "fonte": FONTE,
    }


def vigente(db: Session) -> dict | None:
    r = (
        db.execute(text(_SQL + "order by o.informado_em desc, o.registrado_em desc limit 1"))
        .mappings()
        .first()
    )
    return _linha(r) if r else None


def historico(db: Session, limite: int = 200) -> list[dict]:
    rs = db.execute(
        text(_SQL + "order by o.informado_em desc, o.registrado_em desc limit :n"), {"n": limite}
    ).mappings()
    return [_linha(r) for r in rs]


def registrar(
    db: Session,
    estagio: str,
    informado_em: datetime | None,
    observacao: str | None,
    autor: Usuario,
    ip: str | None,
    agora: datetime,
) -> dict:
    if estagio not in dom.DECLARAVEIS:
        raise RegistroInvalido(422, "Escolha o estágio: observação, atenção, alerta ou crítico.")
    quando = informado_em or agora
    if quando.tzinfo is None:
        raise RegistroInvalido(422, "Informe a hora do COP com fuso horário.")
    if quando > agora + TOLERANCIA_FUTURO:
        raise RegistroInvalido(422, "A hora informada pelo COP não pode estar no futuro.")
    obs = re.sub(r"\s+", " ", observacao or "").strip() or None
    if obs and len(obs) > MAX_OBSERVACAO:
        raise RegistroInvalido(422, f"A observação passou de {MAX_OBSERVACAO} caracteres.")
    try:
        oid = db.execute(
            text(
                "insert into app.estagio_oficial (estagio, informado_em, observacao, autor_id, registrado_em) "
                "values (:e, :i, :o, :a, :r) returning id"
            ),
            {"e": estagio, "i": quando, "o": obs, "a": autor.id, "r": agora},
        ).scalar_one()
        fluxo.auditar(db, "estagio_oficial_registrado", autor, ALVO, uuid.UUID(str(oid)), ip, estagio=estagio)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return vigente_por_id(db, oid)


def vigente_por_id(db: Session, oid) -> dict:
    r = db.execute(text(_SQL + "where o.id = :i"), {"i": oid}).mappings().one()
    return _linha(r)
