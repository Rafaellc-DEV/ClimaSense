"""Ações de resposta em campo (F4): situação, linha do tempo e lição aprendida. specs/foco-chuvas.md §4."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.erros import ErroClimaSense
from climasense.api.routers.estagios import erro_de_negocio
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos import acoes as servico

router = APIRouter(prefix="/acoes", tags=["Evento de chuva"])
consultar = exige(Permissao.CONSULTAR)
editar = exige(Permissao.EDITAR)

Tipo = Literal["orientacao", "visita", "distribuicao_insumos", "vigilancia_agravo", "articulacao", "outro"]
Situacao = Literal["planejada", "em_andamento", "concluida", "cancelada"]


class Acao(BaseModel):
    id: uuid.UUID
    territorio_id: str = Field(description="Município (recife), distrito ou bairro onde a ação acontece")
    territorio_nome: str
    territorio_nivel: Literal["municipio", "distrito", "bairro"]
    distrito_id: str = Field(description="Distrito do território (o próprio, se for distrito ou município)")
    distrito_nome: str
    tipo: Tipo
    tipo_rotulo: str
    descricao: str
    responsavel: str | None
    situacao: Situacao
    situacao_rotulo: str
    inicio_em: datetime | None
    fim_em: datetime | None
    licao_aprendida: str | None = Field(
        default=None, deprecated=True, description="Obsoleto: lições aprendidas estão fora do escopo (PRD §5)"
    )
    criada_em: datetime
    atualizada_em: datetime
    autor_nome: str
    atualizado_por_nome: str


class EventoAcao(BaseModel):
    id: int
    em: datetime
    autor_nome: str
    situacao: Situacao
    texto: str
    alteracoes: dict


class DetalheAcao(Acao):
    linha_do_tempo: list[EventoAcao]


class AndamentoDistrito(BaseModel):
    distrito_id: str
    distrito_nome: str
    contagens: dict[str, int] = Field(description="Ações por situação neste distrito (RF-16)")


class ListaAcoes(BaseModel):
    itens: list[Acao]
    contagens: dict[str, int]
    total: int
    por_distrito: list[AndamentoDistrito]
    ordenado_por_prioridade: bool = Field(
        description="true quando `ordem=prioridade` foi aplicada (distritos mais vulneráveis primeiro, RF-22)"
    )


class PedidoAcao(BaseModel):
    territorio_id: str = Field(description="recife, um distrito (ds-1 a ds-8) ou um bairro; precisa existir")
    tipo: Tipo
    descricao: str = Field(max_length=2000)
    responsavel: str | None = Field(default=None, max_length=160, description="Órgão ou pessoa responsável")
    situacao: Situacao = "planejada"
    inicio_em: datetime | None = None
    fim_em: datetime | None = None
    licao_aprendida: str | None = Field(
        default=None, max_length=2000, deprecated=True, description="Obsoleto (PRD §5): não usar"
    )


class PedidoAtualizacaoAcao(BaseModel):
    descricao: str | None = Field(default=None, max_length=2000)
    responsavel: str | None = Field(default=None, max_length=160)
    situacao: Situacao | None = None
    inicio_em: datetime | None = None
    fim_em: datetime | None = None
    licao_aprendida: str | None = Field(
        default=None, max_length=2000, deprecated=True, description="Obsoleto (PRD §5): não usar"
    )


@router.get(
    "", response_model=ListaAcoes, summary="Linha do tempo das ações por território, situação e período"
)
def listar(
    territorio_id: str | None = None,
    situacao: Situacao | None = None,
    desde: date | None = None,
    ate: date | None = None,
    ordem: Literal["recente", "prioridade"] = Query(
        default="recente",
        description="prioridade: distritos mais vulneráveis primeiro (ordem de /territorios/prioridade)",
    ),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
) -> ListaAcoes:
    if desde and ate and desde > ate:
        raise ErroClimaSense(422, "A data inicial precisa ser antes da final.")
    return erro_de_negocio(lambda: servico.listar(db, territorio_id, situacao, desde, ate, ordem))


@router.post("", response_model=DetalheAcao, status_code=201, summary="Registrar ação de resposta")
def criar(
    pedido: PedidoAcao,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheAcao:
    return erro_de_negocio(lambda: servico.criar(db, pedido.model_dump(), ctx.usuario, ctx.ip, agora))


@router.get("/{acao_id}", response_model=DetalheAcao, summary="Detalhe da ação com a linha do tempo")
def detalhe(
    acao_id: uuid.UUID, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> DetalheAcao:
    return erro_de_negocio(lambda: servico.obter(db, acao_id))


@router.patch(
    "/{acao_id}", response_model=DetalheAcao, summary="Atualizar situação, descrição ou lição aprendida"
)
def atualizar(
    acao_id: uuid.UUID,
    pedido: PedidoAtualizacaoAcao,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheAcao:
    dados = pedido.model_dump(exclude_unset=True)
    return erro_de_negocio(lambda: servico.atualizar(db, acao_id, dados, ctx.usuario, ctx.ip, agora))


@router.delete(
    "/{acao_id}",
    status_code=204,
    summary="Excluir ação em qualquer situação (auditado: quem, quando e o que foi excluído)",
)
def excluir(
    acao_id: uuid.UUID,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
) -> Response:
    erro_de_negocio(lambda: servico.excluir(db, acao_id, ctx.usuario, ctx.ip))
    return Response(status_code=204)
