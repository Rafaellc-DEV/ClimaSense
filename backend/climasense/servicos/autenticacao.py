"""Caso de uso: entrar, sair e trocar a senha (RF-02), com auditoria na mesma transação (RF-14.1)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from climasense.auth import senhas
from climasense.auth.sessoes import GerenciadorSessoes, NovaSessao
from climasense.config import Configuracao
from climasense.dominio.bloqueio import (
    DURACAO_BLOQUEIO,
    FALHAS_LIVRES,
    FALHAS_LIVRES_IP,
    JANELA,
    LIMITE_FALHAS_IP,
    TETO_ESPERA_IP_S,
    TETO_ESPERA_S,
    Tentativa,
    bloqueado_ate,
    espera_ate,
)
from climasense.dominio.recorte import para_recife
from climasense.dominio.senha import problemas_da_senha
from climasense.infra.modelos_sql import Sessao, Usuario
from climasense.infra.repositorios.auditoria import RepositorioAuditoria
from climasense.infra.repositorios.usuarios import (
    RepositorioLiberacoes,
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
        self.liberacoes = RepositorioLiberacoes(db)
        self.auditoria = RepositorioAuditoria(db)
        self.sessoes = GerenciadorSessoes(RepositorioSessoes(db), self.usuarios, config)

    def entrar(
        self, email: str, senha: str, agora: datetime, ip: str | None, user_agent: str | None
    ) -> ResultadoEntrada:
        email = email.strip().lower()
        self._barrar_se_preciso(email, ip, agora)

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

    def _historicos(self, email: str, ip: str | None, agora: datetime):
        """Tentativas que ainda contam: do par e-mail+IP e do IP, depois da última liberação do administrador."""
        desde = agora - JANELA_CONSULTA
        lib_email = self.liberacoes.ultima_do_email(email)
        lib_ip = self.liberacoes.ultima_do_ip(ip) if ip else None
        corte_par = max((c for c in (lib_email, lib_ip) if c), default=None)

        def vale(t, corte) -> bool:
            return corte is None or t.em > corte

        par = [
            Tentativa(t.em, t.sucesso)
            for t in self.tentativas.recentes(email, desde)
            # só as falhas vindas do mesmo IP contam para o e-mail: outro IP não consegue travar a conta
            if (str(t.ip) if t.ip is not None else None) == ip and vale(t, corte_par)
        ]
        do_ip = (
            [Tentativa(t.em, t.sucesso) for t in self.tentativas.recentes_do_ip(ip, desde) if vale(t, lib_ip)]
            if ip
            else []
        )
        return par, do_ip

    def _barrar_se_preciso(self, email: str, ip: str | None, agora: datetime) -> None:
        par, do_ip = self._historicos(email, ip, agora)
        fim_ip = bloqueado_ate(do_ip, agora, LIMITE_FALHAS_IP) if ip else None
        fim_par = bloqueado_ate(par, agora)
        if fim_ip or fim_par:
            escopo = "ip" if fim_ip else "email_ip"
            self.auditoria.registrar("login_bloqueado", detalhes={"email": email, "escopo": escopo}, ip=ip)
            self.db.commit()
            hora = para_recife(fim_ip or fim_par).strftime("%Hh%M")
            quem = "a partir deste acesso" if fim_ip else "a esta conta a partir deste acesso"
            raise FalhaAutenticacao(
                429,
                f"Muitas tentativas sem sucesso. Por segurança, o acesso {quem} está pausado por 15 minutos. "
                f"Tente de novo a partir das {hora}. Se for urgente, peça ao administrador para liberar.",
            )
        espera_ip = espera_ate(do_ip, agora, FALHAS_LIVRES_IP, TETO_ESPERA_IP_S) if ip else None
        espera_par = espera_ate(par, agora, FALHAS_LIVRES, TETO_ESPERA_S)
        fim = max((e for e in (espera_ip, espera_par) if e), default=None)
        if fim:
            segundos = max(1, math.ceil((fim - agora).total_seconds()))
            raise FalhaAutenticacao(
                429, f"Muitas tentativas seguidas. Aguarde {segundos} segundos e tente de novo."
            )

    def liberar_login(
        self, admin: Usuario, email: str | None, ip: str | None, agora: datetime, ip_admin: str | None
    ) -> None:
        """Libera um e-mail e/ou um IP bloqueados (ou em espera). Ato do administrador, auditado."""
        email = email.strip().lower() if email else None
        if not email and not ip:
            raise FalhaAutenticacao(400, "Informe o e-mail e/ou o IP que deve ser liberado.")
        if email:
            self.liberacoes.registrar(email, None, agora, admin.id)
        if ip:
            self.liberacoes.registrar(None, ip, agora, admin.id)
        self.auditoria.registrar(
            "login_liberado",
            usuario_id=admin.id,
            alvo_tipo="login",
            alvo_id=email or ip,
            detalhes={"email": email, "ip": ip},
            ip=ip_admin,
        )
        self.db.commit()

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
