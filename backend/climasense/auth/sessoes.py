"""Sessões no servidor (D7, RF-02.5): token aleatório no cookie HttpOnly, só o HMAC guardado no banco,
expiração por inatividade e revogação."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from climasense.config import Configuracao, ConfiguracaoAusente
from climasense.infra.modelos_sql import Sessao, Usuario
from climasense.infra.repositorios.usuarios import RepositorioSessoes, RepositorioUsuarios

COOKIE_SESSAO = "cs_sessao"
COOKIE_CSRF = "cs_csrf"
DURACAO_MAXIMA = timedelta(hours=12)  # mesmo em uso contínuo, pede novo login após 12 h

_CHAVE_DESENVOLVIMENTO = "climasense-desenvolvimento-local-nao-use-em-producao"


class SessaoInvalida(Exception):
    def __init__(self, mensagem: str = "Entre para continuar.") -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


@dataclass(frozen=True)
class NovaSessao:
    token: str
    csrf: str
    expira_em: datetime


def _chave(config: Configuracao) -> bytes:
    if config.session_secret:
        return config.session_secret.get_secret_value().encode()
    if config.em_producao:
        raise ConfiguracaoAusente("Configure SESSION_SECRET no arquivo .env.")
    return _CHAVE_DESENVOLVIMENTO.encode()


def resumo(config: Configuracao, valor: str) -> str:
    return hmac.new(_chave(config), valor.encode(), hashlib.sha256).hexdigest()


class GerenciadorSessoes:
    def __init__(
        self, sessoes: RepositorioSessoes, usuarios: RepositorioUsuarios, config: Configuracao
    ) -> None:
        self.sessoes = sessoes
        self.usuarios = usuarios
        self.config = config
        self.inatividade = timedelta(minutes=config.sessao_inatividade_min)

    def criar(self, usuario: Usuario, agora: datetime, ip: str | None, user_agent: str | None) -> NovaSessao:
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expira = agora + self.inatividade
        self.sessoes.adicionar(
            Sessao(
                id_hash=resumo(self.config, token),
                usuario_id=usuario.id,
                csrf_hash=resumo(self.config, csrf),
                criada_em=agora,
                ultimo_uso=agora,
                expira_em=expira,
                ip=ip,
                user_agent=(user_agent or "")[:300] or None,
            )
        )
        return NovaSessao(token=token, csrf=csrf, expira_em=expira)

    def validar(self, token: str | None, agora: datetime, renovar: bool = True) -> tuple[Sessao, Usuario]:
        if not token:
            raise SessaoInvalida()
        sessao = self.sessoes.por_hash(resumo(self.config, token))
        if sessao is None or sessao.revogada:
            raise SessaoInvalida()
        if agora >= sessao.expira_em:
            raise SessaoInvalida("Sua sessão terminou por inatividade. Entre novamente.")
        if agora - sessao.criada_em >= DURACAO_MAXIMA:
            raise SessaoInvalida("Por segurança, entre novamente. A sessão dura no máximo 12 horas.")
        usuario = self.usuarios.por_id(sessao.usuario_id)
        if usuario is None or not usuario.ativo:
            raise SessaoInvalida("Esta conta está desativada. Fale com o administrador do ClimaSense.")
        if renovar:
            sessao.ultimo_uso = agora
            sessao.expira_em = min(agora + self.inatividade, sessao.criada_em + DURACAO_MAXIMA)
        return sessao, usuario

    def csrf_confere(self, sessao: Sessao, csrf: str | None) -> bool:
        return bool(csrf) and hmac.compare_digest(sessao.csrf_hash, resumo(self.config, csrf))

    def revogar(self, sessao: Sessao) -> None:
        sessao.revogada = True
