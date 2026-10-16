"""Rotas de autenticação: /auth/entrar, /sair, /eu, /renovar, /trocar-senha (T3.5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, contexto_autenticado, ip_cliente, relogio
from climasense.api.deps import configuracao
from climasense.api.erros import ErroClimaSense
from climasense.auth.sessoes import COOKIE_CSRF, COOKIE_SESSAO
from climasense.config import Configuracao
from climasense.dominio.papeis import permissoes
from climasense.infra.modelos_sql import Usuario
from climasense.infra.postgres import obter_sessao
from climasense.servicos.autenticacao import FalhaAutenticacao, ServicoAutenticacao

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class PedidoEntrada(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=200)


class PedidoTrocaSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=200)
    nova_senha: str = Field(min_length=1, max_length=200)


class UsuarioAtual(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    papeis: list[str]
    permissoes: list[str]
    troca_senha_obrigatoria: bool
    expira_em: datetime
    ambiente: str
    inatividade_min: int
    mapa_tiles_url: str


def _usuario_atual(usuario: Usuario, expira_em: datetime, config: Configuracao) -> UsuarioAtual:
    return UsuarioAtual(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papeis=usuario.papeis,
        permissoes=sorted(p.value for p in permissoes(usuario.papeis)),
        troca_senha_obrigatoria=usuario.troca_senha_obrigatoria,
        expira_em=expira_em,
        ambiente=config.ambiente,
        inatividade_min=config.sessao_inatividade_min,
        mapa_tiles_url=config.map_tiles_url,
    )


def _cookies(resposta: Response, config: Configuracao, token: str, csrf: str) -> None:
    seguro = config.em_producao
    resposta.set_cookie(COOKIE_SESSAO, token, httponly=True, secure=seguro, samesite="lax", path="/api")
    resposta.set_cookie(COOKIE_CSRF, csrf, httponly=False, secure=seguro, samesite="lax", path="/")


def _servico(db: Session, config: Configuracao) -> ServicoAutenticacao:
    return ServicoAutenticacao(db, config)


@router.post("/entrar", response_model=UsuarioAtual, summary="Entrar com e-mail e senha")
def entrar(
    pedido: PedidoEntrada,
    request: Request,
    resposta: Response,
    db: Session = Depends(obter_sessao),
    config: Configuracao = Depends(configuracao),
    agora: datetime = Depends(relogio),
) -> UsuarioAtual:
    try:
        r = _servico(db, config).entrar(
            pedido.email, pedido.senha, agora, ip_cliente(request), request.headers.get("user-agent")
        )
    except FalhaAutenticacao as erro:
        raise ErroClimaSense(erro.status, erro.mensagem) from None
    _cookies(resposta, config, r.sessao.token, r.sessao.csrf)
    return _usuario_atual(r.usuario, r.sessao.expira_em, config)


@router.post("/sair", status_code=204, summary="Sair")
def sair(
    resposta: Response,
    ctx: Contexto = Depends(contexto_autenticado),
    db: Session = Depends(obter_sessao),
    config: Configuracao = Depends(configuracao),
) -> Response:
    _servico(db, config).sair(ctx.sessao, ctx.usuario, ctx.ip)
    resposta.status_code = 204
    resposta.delete_cookie(COOKIE_SESSAO, path="/api")
    resposta.delete_cookie(COOKIE_CSRF, path="/")
    return resposta


@router.get("/eu", response_model=UsuarioAtual, summary="Conta atual e expiração da sessão")
def eu(
    ctx: Contexto = Depends(contexto_autenticado), config: Configuracao = Depends(configuracao)
) -> UsuarioAtual:
    return _usuario_atual(ctx.usuario, ctx.sessao.expira_em, config)


@router.post("/renovar", response_model=UsuarioAtual, summary="Continuar conectado")
def renovar(
    ctx: Contexto = Depends(contexto_autenticado), config: Configuracao = Depends(configuracao)
) -> UsuarioAtual:
    # A própria validação renova a inatividade; este endpoint existe para o botão “Continuar conectado”.
    return _usuario_atual(ctx.usuario, ctx.sessao.expira_em, config)


@router.post("/trocar-senha", status_code=204, summary="Trocar a senha")
def trocar_senha(
    pedido: PedidoTrocaSenha,
    resposta: Response,
    ctx: Contexto = Depends(contexto_autenticado),
    db: Session = Depends(obter_sessao),
    config: Configuracao = Depends(configuracao),
) -> Response:
    try:
        _servico(db, config).trocar_senha(
            ctx.sessao, ctx.usuario, pedido.senha_atual, pedido.nova_senha, ctx.ip
        )
    except FalhaAutenticacao as erro:
        raise ErroClimaSense(erro.status, erro.mensagem) from None
    resposta.status_code = 204
    return resposta
