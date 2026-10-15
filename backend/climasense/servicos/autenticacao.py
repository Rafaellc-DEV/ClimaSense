"""Caso de uso: entrar, sair e trocar a senha (RF-02), com auditoria na mesma transação (RF-14.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from climasense.auth import senhas
from climasense.auth.sessoes import GerenciadorSessoes, NovaSessao
from climasense.config import Configuracao
from climasense.dominio.bloqueio import DURACAO_BLOQUEIO, JANELA, Tentativa, bloqueado_ate
from climasense.dominio.recorte import para_recife
from climasense.dominio.senha import problemas_da_senha
from climasense.infra.modelos_sql import Sessao, Usuario
from climasense.infra.repositorios.auditoria import RepositorioAuditoria
from climasense.infra.repositorios.usuarios import (
    RepositorioSessoes,
    RepositorioTentativas,
    RepositorioUsuarios,
)

JANELA_CONSULTA: timedelta = JANELA + DURACAO_BLOQUEIO
CREDENCIAIS_INVALIDAS = "E-mail ou senha incorretos. Confira e tente de novo."


class FalhaAutenticacao(Exception):
    def __init__(self, status: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


@dataclass(frozen=True)
class ResultadoEntrada:
    usuario: Usuario
    sessao: NovaSessao


class ServicoAutenticacao:
    def __init__(self, db: Session, config: Configuracao) -> None:
        self.db = db
        self.usuarios = RepositorioUsuarios(db)
        self.tentativas = RepositorioTentativas(db)
        self.auditoria = RepositorioAuditoria(db)
        self.sessoes = GerenciadorSessoes(RepositorioSessoes(db), self.usuarios, config)

    def entrar(
        self, email: str, senha: str, agora: datetime, ip: str | None, user_agent: str | None
    ) -> ResultadoEntrada:
        email = email.strip().lower()
        historico = [
            Tentativa(t.em, t.sucesso) for t in self.tentativas.recentes(email, agora - JANELA_CONSULTA)
        ]
        fim_bloqueio = bloqueado_ate(historico, agora)
        if fim_bloqueio:
            self.auditoria.registrar("login_bloqueado", detalhes={"email": email}, ip=ip)
            self.db.commit()
            hora = para_recife(fim_bloqueio).strftime("%Hh%M")
            raise FalhaAutenticacao(
                429,
                "Muitas tentativas sem sucesso. Por segurança, o acesso a esta conta está pausado por 15 minutos. "
                f"Tente de novo a partir das {hora}.",
            )

        usuario = self.usuarios.por_email(email)
        senha_ok = senhas.conferir(senha, usuario.senha_hash if usuario else None)
        if not usuario or not senha_ok or not usuario.ativo:
            self.tentativas.registrar(email, ip, agora, sucesso=False)
            motivo = "conta_desativada" if (usuario and senha_ok and not usuario.ativo) else "credenciais"
            self.auditoria.registrar(
                "login_falha",
                usuario_id=usuario.id if usuario else None,
                detalhes={"email": email, "motivo": motivo},
                ip=ip,
            )
            self.db.commit()
            if motivo == "conta_desativada":
                raise FalhaAutenticacao(
                    403, "Esta conta está desativada. Fale com o administrador do ClimaSense."
                )
            raise FalhaAutenticacao(401, CREDENCIAIS_INVALIDAS)

        self.tentativas.registrar(email, ip, agora, sucesso=True)
        nova = self.sessoes.criar(usuario, agora, ip, user_agent)
        self.auditoria.registrar("login_sucesso", usuario_id=usuario.id, detalhes={"email": email}, ip=ip)
        self.db.commit()
        return ResultadoEntrada(usuario, nova)

    def sair(self, sessao: Sessao, usuario: Usuario, ip: str | None) -> None:
        self.sessoes.revogar(sessao)
        self.auditoria.registrar("logout", usuario_id=usuario.id, ip=ip)
        self.db.commit()

    def trocar_senha(self, sessao: Sessao, usuario: Usuario, atual: str, nova: str, ip: str | None) -> None:
        if not senhas.conferir(atual, usuario.senha_hash):
            raise FalhaAutenticacao(400, "A senha atual não confere. Confira e tente de novo.")
        if atual == nova:
            raise FalhaAutenticacao(400, "A nova senha precisa ser diferente da atual.")
        problemas = problemas_da_senha(nova, usuario.email, usuario.nome)
        if problemas:
            raise FalhaAutenticacao(400, " ".join(problemas))
        usuario.senha_hash = senhas.gerar_hash(nova)
        usuario.troca_senha_obrigatoria = False
        # Outras sessões abertas com a senha antiga deixam de valer.
        RepositorioSessoes(self.db).revogar_do_usuario(usuario.id, exceto=sessao.id_hash)
        self.auditoria.registrar("senha_trocada", usuario_id=usuario.id, ip=ip)
        self.db.commit()
