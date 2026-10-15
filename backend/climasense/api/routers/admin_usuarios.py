"""Administração de contas: /admin/usuarios (T3.8, RF-16.1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige
from climasense.api.erros import ErroClimaSense
from climasense.dominio.papeis import DESCRICOES, Papel, Permissao
from climasense.infra.modelos_sql import Usuario
from climasense.infra.postgres import obter_sessao
from climasense.infra.repositorios.usuarios import RepositorioUsuarios
from climasense.servicos.usuarios import ErroUsuarios, ServicoUsuarios

router = APIRouter(prefix="/admin/usuarios", tags=["Administração"])
admin = exige(Permissao.ADMINISTRAR)


class Conta(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    papeis: list[str]
    ativo: bool
    troca_senha_obrigatoria: bool
    criado_em: datetime


class NovaConta(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    papeis: list[str] = Field(min_length=1)


class AlteracaoConta(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    papeis: list[str] | None = Field(default=None, min_length=1)
    ativo: bool | None = None


class ContaComSenha(BaseModel):
    conta: Conta
    senha_temporaria: str = Field(
        description="Mostrada uma única vez. A troca é obrigatória no primeiro acesso."
    )


class SenhaTemporaria(BaseModel):
    senha_temporaria: str


class PapelDescrito(BaseModel):
    papel: str
    descricao: str


def _conta(u: Usuario) -> Conta:
    return Conta.model_validate(u, from_attributes=True)


def _executar(funcao):
    try:
        return funcao()
    except ErroUsuarios as erro:
        raise ErroClimaSense(erro.status, erro.mensagem) from None


@router.get("/papeis", response_model=list[PapelDescrito], summary="Papéis disponíveis, em linguagem simples")
def listar_papeis(_: Contexto = Depends(admin)) -> list[PapelDescrito]:
    return [PapelDescrito(papel=p.value, descricao=DESCRICOES[p]) for p in Papel]


@router.get("", response_model=list[Conta], summary="Listar contas")
def listar(_: Contexto = Depends(admin), db: Session = Depends(obter_sessao)) -> list[Conta]:
    return [_conta(u) for u in RepositorioUsuarios(db).listar()]


@router.post("", response_model=ContaComSenha, status_code=201, summary="Criar conta com senha temporária")
def criar(
    pedido: NovaConta, ctx: Contexto = Depends(admin), db: Session = Depends(obter_sessao)
) -> ContaComSenha:
    criada = _executar(
        lambda: ServicoUsuarios(db).criar(pedido.nome, pedido.email, pedido.papeis, ctx.usuario, ctx.ip)
    )
    return ContaComSenha(conta=_conta(criada.usuario), senha_temporaria=criada.senha_temporaria)


@router.patch("/{usuario_id}", response_model=Conta, summary="Alterar nome, papéis ou ativar/desativar")
def alterar(
    usuario_id: uuid.UUID,
    pedido: AlteracaoConta,
    ctx: Contexto = Depends(admin),
    db: Session = Depends(obter_sessao),
) -> Conta:
    u = _executar(
        lambda: ServicoUsuarios(db).atualizar(
            usuario_id, ctx.usuario, ctx.ip, nome=pedido.nome, papeis=pedido.papeis, ativo=pedido.ativo
        )
    )
    return _conta(u)


@router.post(
    "/{usuario_id}/redefinir-senha",
    response_model=SenhaTemporaria,
    summary="Redefinir a senha (gera senha temporária)",
)
def redefinir_senha(
    usuario_id: uuid.UUID, ctx: Contexto = Depends(admin), db: Session = Depends(obter_sessao)
) -> SenhaTemporaria:
    return SenhaTemporaria(
        senha_temporaria=_executar(
            lambda: ServicoUsuarios(db).redefinir_senha(usuario_id, ctx.usuario, ctx.ip)
        )
    )
