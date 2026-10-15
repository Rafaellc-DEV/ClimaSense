"""Caso de uso: administração de contas (RF-16.1). Contas não são apagadas, só desativadas,
para preservar a auditoria. Senhas temporárias aparecem uma única vez e exigem troca no 1º acesso."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from climasense.auth import senhas
from climasense.dominio.papeis import Papel, PapelInvalido, normalizar
from climasense.infra.modelos_sql import Usuario
from climasense.infra.repositorios.auditoria import RepositorioAuditoria
from climasense.infra.repositorios.usuarios import RepositorioSessoes, RepositorioUsuarios


class ErroUsuarios(Exception):
    def __init__(self, status: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


@dataclass(frozen=True)
class ContaCriada:
    usuario: Usuario
    senha_temporaria: str


class ServicoUsuarios:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.usuarios = RepositorioUsuarios(db)
        self.auditoria = RepositorioAuditoria(db)

    def _papeis(self, papeis: list[str]) -> list[str]:
        try:
            return [p.value for p in normalizar(papeis)]
        except PapelInvalido as erro:
            raise ErroUsuarios(422, str(erro)) from None

    def criar(
        self,
        nome: str,
        email: str,
        papeis: list[str],
        autor: Usuario | None,
        ip: str | None = None,
        senha_inicial: str | None = None,
    ) -> ContaCriada:
        email = email.strip().lower()
        if self.usuarios.por_email(email):
            raise ErroUsuarios(409, "Já existe uma conta com este e-mail.")
        senha = senha_inicial or senhas.senha_temporaria()
        usuario = self.usuarios.adicionar(
            Usuario(
                nome=nome.strip(),
                email=email,
                senha_hash=senhas.gerar_hash(senha),
                papeis=self._papeis(papeis),
                ativo=True,
                troca_senha_obrigatoria=True,
            )
        )
        self.auditoria.registrar(
            "usuario_criado",
            usuario_id=autor.id if autor else None,
            alvo_tipo="usuario",
            alvo_id=str(usuario.id),
            detalhes={"email": email, "papeis": usuario.papeis},
            ip=ip,
        )
        self.db.commit()
        return ContaCriada(usuario, senha)

    def atualizar(
        self,
        alvo_id: uuid.UUID,
        autor: Usuario,
        ip: str | None,
        *,
        nome: str | None = None,
        papeis: list[str] | None = None,
        ativo: bool | None = None,
    ) -> Usuario:
        usuario = self._obter(alvo_id)
        mudancas: dict[str, object] = {}
        if nome is not None and nome.strip() != usuario.nome:
            mudancas["nome"] = usuario.nome = nome.strip()
        if papeis is not None:
            novos = self._papeis(papeis)
            if novos != usuario.papeis:
                if Papel.ADMINISTRADOR.value in usuario.papeis and Papel.ADMINISTRADOR.value not in novos:
                    self._garantir_outro_admin(usuario, "remover o papel de administrador")
                mudancas["papeis"] = usuario.papeis = novos
        if ativo is not None and ativo != usuario.ativo:
            if not ativo:
                if usuario.id == autor.id:
                    raise ErroUsuarios(409, "Você não pode desativar a sua própria conta.")
                if Papel.ADMINISTRADOR.value in usuario.papeis:
                    self._garantir_outro_admin(usuario, "desativar")
                RepositorioSessoes(self.db).revogar_do_usuario(usuario.id)
            mudancas["ativo"] = usuario.ativo = ativo
        if mudancas:
            self.auditoria.registrar(
                "usuario_alterado",
                usuario_id=autor.id,
                alvo_tipo="usuario",
                alvo_id=str(usuario.id),
                detalhes={"mudancas": mudancas},
                ip=ip,
            )
            self.db.commit()
        return usuario

    def redefinir_senha(self, alvo_id: uuid.UUID, autor: Usuario, ip: str | None) -> str:
        usuario = self._obter(alvo_id)
        temporaria = senhas.senha_temporaria()
        usuario.senha_hash = senhas.gerar_hash(temporaria)
        usuario.troca_senha_obrigatoria = True
        RepositorioSessoes(self.db).revogar_do_usuario(usuario.id)
        self.auditoria.registrar(
            "senha_redefinida", usuario_id=autor.id, alvo_tipo="usuario", alvo_id=str(usuario.id), ip=ip
        )
        self.db.commit()
        return temporaria

    def _obter(self, alvo_id: uuid.UUID) -> Usuario:
        usuario = self.usuarios.por_id(alvo_id)
        if usuario is None:
            raise ErroUsuarios(404, "Conta não encontrada.")
        return usuario

    def _garantir_outro_admin(self, usuario: Usuario, acao: str) -> None:
        if usuario.ativo and self.usuarios.administradores_ativos() <= 1:
            raise ErroUsuarios(
                409, f"Não é possível {acao}: o ClimaSense precisa de pelo menos um administrador ativo."
            )
