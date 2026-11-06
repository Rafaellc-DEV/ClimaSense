"""Desbloqueio de login pelo administrador: /admin/login/liberar (RNF-01, T0.4)."""

from __future__ import annotations

import ipaddress
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.deps import configuracao
from climasense.api.erros import ErroClimaSense
from climasense.config import Configuracao
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos.autenticacao import FalhaAutenticacao, ServicoAutenticacao

router = APIRouter(prefix="/admin/login", tags=["Administração"])
admin = exige(Permissao.ADMINISTRAR)


class PedidoLiberacao(BaseModel):
    email: EmailStr | None = None
    ip: str | None = Field(default=None, max_length=45)

    @field_validator("ip")
    @classmethod
    def _ip_valido(cls, valor: str | None) -> str | None:
        if valor is None or not valor.strip():
            return None
        try:
            return str(ipaddress.ip_address(valor.strip()))
        except ValueError:
            raise ValueError("Informe um endereço IP válido.") from None


class Liberacao(BaseModel):
    email: str | None
    ip: str | None


@router.post(
    "/liberar",
    response_model=Liberacao,
    summary="Liberar um e-mail e/ou IP bloqueados no login (auditado)",
)
def liberar(
    pedido: PedidoLiberacao,
    ctx: Contexto = Depends(admin),
    db: Session = Depends(obter_sessao),
    config: Configuracao = Depends(configuracao),
    agora: datetime = Depends(relogio),
) -> Liberacao:
    try:
        ServicoAutenticacao(db, config).liberar_login(ctx.usuario, pedido.email, pedido.ip, agora, ctx.ip)
    except FalhaAutenticacao as erro:
        raise ErroClimaSense(erro.status, erro.mensagem) from None
    return Liberacao(email=pedido.email.lower() if pedido.email else None, ip=pedido.ip)
