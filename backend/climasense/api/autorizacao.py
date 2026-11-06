"""Dependências de autenticação, CSRF e autorização da API (RF-02, RF-03, RNF-SEG-04).

Toda rota protegida declara a permissão com `exige(Permissao.X)`. O teste de matriz
(`tests/integration/test_matriz_autorizacao.py`) lê essa marcação em todas as rotas.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from climasense.api.deps import configuracao
from climasense.api.erros import ErroClimaSense
from climasense.auth.sessoes import COOKIE_CSRF, COOKIE_SESSAO, GerenciadorSessoes, SessaoInvalida
from climasense.config import Configuracao
from climasense.dominio.papeis import MENSAGEM_SEM_PERMISSAO, Permissao, pode
from climasense.infra.modelos_sql import Sessao, Usuario
from climasense.infra.postgres import obter_sessao
from climasense.infra.repositorios.usuarios import RepositorioSessoes, RepositorioUsuarios

METODOS_QUE_ALTERAM = {"POST", "PUT", "PATCH", "DELETE"}
CABECALHO_CSRF = "X-CSRF-Token"


def relogio() -> datetime:
    """Hora atual em UTC. Substituível nos testes (sessão de 60 min, bloqueio de 15 min)."""
    return datetime.now(UTC)


def _ip_valido(texto: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(texto.strip()) if texto and texto.strip() else None
    except ValueError:
        return None


def resolver_ip(
    host: str | None, encaminhado: str | None, proxies: list[ipaddress.IPv4Network | ipaddress.IPv6Network]
) -> str | None:
    """IP do cliente. X-Forwarded-For só vale quando o par direto é um proxy confiável (config
    PROXIES_CONFIAVEIS); então se lê a lista da direita para a esquerda e fica o primeiro IP que não é
    proxy confiável (o que está à esquerda pode ser forjado pelo cliente)."""
    par = _ip_valido(host)
    if par is None:
        return None
    if not proxies or not encaminhado or not any(par in rede for rede in proxies):
        return str(par)
    for item in reversed(encaminhado.split(",")):
        ip = _ip_valido(item)
        if ip is None:
            return str(par)  # cabeçalho malformado: não confie
        if not any(ip in rede for rede in proxies):
            return str(ip)
    return str(par)


def ip_cliente(request: Request) -> str | None:
    config = getattr(request.app.state, "config", None)
    proxies = config.redes_proxy if config is not None else []
    host = request.client.host if request.client else None
    return resolver_ip(host, request.headers.get("x-forwarded-for"), proxies)


@dataclass
class Contexto:
    usuario: Usuario
    sessao: Sessao
    ip: str | None


def _contexto(
    request: Request, db: Session, config: Configuracao, agora: datetime, exigir_senha_trocada: bool
) -> Contexto:
    gerenciador = GerenciadorSessoes(RepositorioSessoes(db), RepositorioUsuarios(db), config)
    try:
        sessao, usuario = gerenciador.validar(request.cookies.get(COOKIE_SESSAO), agora)
    except SessaoInvalida as erro:
        raise ErroClimaSense(401, erro.mensagem) from None
    if request.method in METODOS_QUE_ALTERAM:
        enviado = request.headers.get(CABECALHO_CSRF)
        if enviado != request.cookies.get(COOKIE_CSRF) or not gerenciador.csrf_confere(sessao, enviado):
            raise ErroClimaSense(
                403, "Não foi possível confirmar a origem do pedido. Recarregue a página e tente de novo."
            )
    if exigir_senha_trocada and usuario.troca_senha_obrigatoria:
        raise ErroClimaSense(
            403, "Troque a sua senha temporária para continuar.", titulo="Troca de senha obrigatória"
        )
    db.commit()  # grava a renovação da inatividade
    return Contexto(usuario=usuario, sessao=sessao, ip=ip_cliente(request))


def contexto_autenticado(
    request: Request,
    db: Session = Depends(obter_sessao),
    config: Configuracao = Depends(configuracao),
    agora: datetime = Depends(relogio),
) -> Contexto:
    """Qualquer conta autenticada, mesmo com a troca de senha pendente (usada por /auth/eu, /sair, /trocar-senha)."""
    return _contexto(request, db, config, agora, exigir_senha_trocada=False)


def exige(permissao: Permissao) -> Callable[..., Contexto]:
    def dependencia(
        request: Request,
        db: Session = Depends(obter_sessao),
        config: Configuracao = Depends(configuracao),
        agora: datetime = Depends(relogio),
    ) -> Contexto:
        ctx = _contexto(request, db, config, agora, exigir_senha_trocada=True)
        if not pode(ctx.usuario.papeis, permissao):
            raise ErroClimaSense(403, MENSAGEM_SEM_PERMISSAO)
        return ctx

    dependencia.permissao = permissao  # type: ignore[attr-defined]  — lida pelo teste de matriz
    dependencia.__name__ = f"exige_{permissao.value}"
    return dependencia
