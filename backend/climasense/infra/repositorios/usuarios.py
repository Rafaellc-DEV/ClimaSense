"""Repositório de usuários, sessões e tentativas de login (M3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from climasense.infra.modelos_sql import Sessao, TentativaLogin, Usuario


class RepositorioUsuarios:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def por_email(self, email: str) -> Usuario | None:
        return self.sessao.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))

    def por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self.sessao.get(Usuario, usuario_id)

    def listar(self) -> list[Usuario]:
        return list(self.sessao.scalars(select(Usuario).order_by(Usuario.ativo.desc(), Usuario.nome)))

    def adicionar(self, usuario: Usuario) -> Usuario:
        self.sessao.add(usuario)
        self.sessao.flush()
        return usuario

    def administradores_ativos(self) -> int:
        return self.sessao.scalar(
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.ativo, Usuario.papeis.any("administrador"))
        )


class RepositorioSessoes:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def adicionar(self, s: Sessao) -> None:
        self.sessao.add(s)

    def por_hash(self, id_hash: str) -> Sessao | None:
        return self.sessao.get(Sessao, id_hash)

    def revogar_do_usuario(self, usuario_id: uuid.UUID, exceto: str | None = None) -> None:
        consulta = update(Sessao).where(Sessao.usuario_id == usuario_id, Sessao.revogada.is_(False))
        if exceto:
            consulta = consulta.where(Sessao.id_hash != exceto)
        self.sessao.execute(consulta.values(revogada=True))


class RepositorioTentativas:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def registrar(self, email: str, ip: str | None, em: datetime, sucesso: bool) -> None:
        self.sessao.add(TentativaLogin(email=email, ip=ip, em=em, sucesso=sucesso))

    def recentes(self, email: str, desde: datetime) -> list[TentativaLogin]:
        consulta = (
            select(TentativaLogin)
            .where(TentativaLogin.email == email, TentativaLogin.em >= desde)
            .order_by(TentativaLogin.em)
        )
        return list(self.sessao.scalars(consulta))
