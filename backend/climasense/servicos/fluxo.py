"""Partes comuns de avaliações e comunicados: evidências, revisões e auditoria na mesma transação."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio.fluxo_revisao import Acao, TransicaoNegada
from climasense.infra.modelos_sql import Revisao, Usuario
from climasense.infra.repositorios.auditoria import RepositorioAuditoria

# nome da ação na auditoria: comunicado_enviado, avaliacao_aprovado…
PARTICIPIO = {
    Acao.ENVIAR: "enviado",
    Acao.APROVAR: "aprovado",
    Acao.DEVOLVER: "devolvido",
    Acao.PUBLICAR: "publicado",
    Acao.ENCERRAR: "encerrado",
}


def acao_auditoria(alvo: str, acao: Acao) -> str:
    """comunicado_publicado, avaliacao_aprovada… (a avaliação concorda no feminino)."""
    participio = PARTICIPIO[acao]
    return f"{alvo}_{participio[:-1] + 'a' if alvo == 'avaliacao' else participio}"


TIPOS_EVIDENCIA = {"mapa", "serie", "cenario", "fonte", "vacinacao"}


def validar_evidencias(db: Session, evidencias: list[dict]) -> list[dict]:
    """RN-19: toda evidência aponta para uma fonte real cadastrada e diz quando foi capturada."""
    fontes = {f for (f,) in db.execute(text("select id from app.fontes"))}
    limpas = []
    for i, ev in enumerate(evidencias, start=1):
        if ev.get("tipo") not in TIPOS_EVIDENCIA:
            raise TransicaoNegada(422, f"A evidência {i} tem um tipo desconhecido.")
        if ev.get("fonte_id") not in fontes:
            raise TransicaoNegada(422, f"A evidência {i} não aponta para uma fonte real do ClimaSense.")
        if not str(ev.get("descricao", "")).strip() or not ev.get("capturada_em"):
            raise TransicaoNegada(
                422, f"A evidência {i} precisa de descrição e do horário em que foi capturada."
            )
        limpas.append(
            {
                k: ev[k]
                for k in ("tipo", "descricao", "fonte_id", "capturada_em", "valor", "endereco")
                if ev.get(k) not in (None, "")
            }
        )
    return limpas


def validar_territorios(db: Session, territorios: list[str]) -> None:
    existentes = {
        t
        for (t,) in db.execute(text("select id from app.territorios where id = any(:t)"), {"t": territorios})
    }
    faltam = [t for t in territorios if t not in existentes]
    if faltam:
        raise TransicaoNegada(422, f"Território não encontrado: {', '.join(faltam)}.")


def registrar_revisao(
    db: Session,
    alvo: str,
    versao_id: uuid.UUID,
    revisor: Usuario,
    acao: Acao,
    justificativa: str | None,
    agora: datetime,
) -> None:
    if acao in (Acao.APROVAR, Acao.DEVOLVER):
        db.add(
            Revisao(
                alvo=alvo,
                versao_id=versao_id,
                revisor_id=revisor.id,
                decisao=acao.value,
                justificativa=(justificativa or "").strip() or None,
                em=agora,
            )
        )


def auditar(
    db: Session, acao: str, ator: Usuario | None, alvo_tipo: str, alvo_id, ip: str | None, **detalhes
) -> None:
    RepositorioAuditoria(db).registrar(
        acao,
        usuario_id=ator.id if ator else None,
        alvo_tipo=alvo_tipo,
        alvo_id=str(alvo_id),
        detalhes=detalhes,
        ip=ip,
    )


def nomes_usuarios(db: Session, ids) -> dict:
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    return {
        u: n for u, n in db.execute(text("select id, nome from app.usuarios where id = any(:i)"), {"i": ids})
    }


def linha_do_tempo(db: Session, alvo: str, versoes: list[dict]) -> list[dict]:
    """Versões e decisões em ordem, com autor e horário (RF-10.3, RF-11.7)."""
    por_id = {v["id"]: v for v in versoes}
    revisoes = db.execute(
        text(
            "select r.versao_id, r.decisao, r.justificativa, r.em, u.nome from app.revisoes r "
            "join app.usuarios u on u.id = r.revisor_id where r.alvo = :a and r.versao_id = any(:v)"
        ),
        {"a": alvo, "v": list(por_id)},
    ).all()
    eventos = [
        {"tipo": "versao", "numero": v["numero"], "em": v["criado_em"], "por": v["autor_nome"], "texto": None}
        for v in versoes
    ]
    eventos += [
        {
            "tipo": decisao,
            "numero": por_id[versao_id]["numero"],
            "em": em,
            "por": nome,
            "texto": justificativa,
        }
        for versao_id, decisao, justificativa, em, nome in revisoes
    ]
    return sorted(eventos, key=lambda e: e["em"])
