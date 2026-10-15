"""Repositório da auditoria (RF-14). Só inclui e consulta: alterar ou apagar é barrado no banco (migração 0003)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from climasense.infra.modelos_sql import RegistroAuditoria

# Chaves que nunca podem ir para a auditoria, mesmo por engano.
_PROIBIDAS = {
    "senha",
    "senha_atual",
    "nova_senha",
    "senha_hash",
    "token",
    "csrf",
    "mongo_uri",
    "database_url",
}


def _limpar(detalhes: dict[str, Any]) -> dict[str, Any]:
    return {k: ("[omitido]" if k.lower() in _PROIBIDAS else v) for k, v in detalhes.items()}


class RepositorioAuditoria:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def registrar(
        self,
        acao: str,
        *,
        usuario_id: uuid.UUID | None = None,
        alvo_tipo: str | None = None,
        alvo_id: str | None = None,
        detalhes: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> RegistroAuditoria:
        """Adiciona à transação corrente: a auditoria é gravada junto com a ação, ou não é gravada."""
        registro = RegistroAuditoria(
            acao=acao,
            usuario_id=usuario_id,
            alvo_tipo=alvo_tipo,
            alvo_id=alvo_id,
            detalhes=_limpar(detalhes or {}),
            ip=ip,
        )
        self.sessao.add(registro)
        return registro

    def listar(
        self,
        *,
        usuario_id: uuid.UUID | None = None,
        acao: str | None = None,
        inicio: datetime | None = None,
        fim: datetime | None = None,
        limite: int = 100,
        deslocamento: int = 0,
    ) -> list[RegistroAuditoria]:
        consulta = select(RegistroAuditoria).order_by(
            RegistroAuditoria.em.desc(), RegistroAuditoria.id.desc()
        )
        if usuario_id:
            consulta = consulta.where(RegistroAuditoria.usuario_id == usuario_id)
        if acao:
            consulta = consulta.where(RegistroAuditoria.acao == acao)
        if inicio:
            consulta = consulta.where(RegistroAuditoria.em >= inicio)
        if fim:
            consulta = consulta.where(RegistroAuditoria.em < fim)
        return list(self.sessao.scalars(consulta.limit(min(limite, 500)).offset(deslocamento)))
