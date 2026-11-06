"""Abrigos e desabrigados (F3): registro manual da equipe, com hora, autor e histórico. specs/foco-chuvas.md §4."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import FonteMeta, Meta
from climasense.api.routers.estagios import erro_de_negocio
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos import abrigos as servico
from climasense.servicos import fontes as servico_fontes

router = APIRouter(prefix="/abrigos", tags=["Evento de chuva"])
consultar = exige(Permissao.CONSULTAR)
editar = exige(Permissao.EDITAR)
MAX_PESSOAS = 100_000  # teto razoável de capacidade e de pessoas por abrigo (RNF-03)
FONTE_OCUPACAO = "recife-abrigos-ocupacao"  # lançamento manual da equipe, não é conector


class Abrigo(BaseModel):
    id: uuid.UUID
    nome: str
    bairro_id: str
    bairro_nome: str
    distrito_id: str | None
    distrito_nome: str | None
    endereco: str | None
    capacidade: int | None
    aberto: bool
    pessoas_abrigadas: int | None
    desabrigados: int | None
    observacao: str | None
    latitude: float | None
    longitude: float | None
    origem: Literal["manual", "dados-abertos"]
    criado_em: datetime
    atualizado_em: datetime
    atualizado_por_nome: str | None = Field(description="null só em carga automática dos Dados Abertos")
    status_fonte: Literal["equipe", "cop"] | None = Field(
        default=None,
        description="Quem informou se está aberto ou fechado; null = ninguém informou ainda (RN-01)",
    )
    status_informado_em: datetime | None = Field(
        default=None, description="Quando essa informação foi dada; null junto com status_fonte"
    )


class TotaisAbrigos(BaseModel):
    abrigos_abertos: int
    abrigos_cadastrados: int
    pessoas_abrigadas: int | None = Field(
        description="Soma nos abrigos abertos; null se nenhum informou (RN-02)"
    )
    desabrigados: int | None = Field(description="Soma de todos os abrigos, inclusive os já fechados")
    abertos_sem_contagem: int
    atualizado_em: datetime | None


class ListaAbrigos(BaseModel):
    itens: list[Abrigo]
    totais: TotaisAbrigos
    meta: Meta | None = Field(
        default=None,
        description="Fontes com hora e frescor (RF-19): o cadastro dos Dados Abertos e o registro da equipe",
    )


class PedidoAbrigo(BaseModel):
    nome: str = Field(max_length=160)
    bairro_id: str
    endereco: str | None = Field(default=None, max_length=300)
    capacidade: int | None = Field(default=None, ge=0, le=MAX_PESSOAS)
    aberto: bool = False
    pessoas_abrigadas: int | None = Field(default=None, ge=0, le=MAX_PESSOAS)
    desabrigados: int | None = Field(default=None, ge=0, le=MAX_PESSOAS)
    observacao: str | None = Field(default=None, max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PedidoAtualizacaoAbrigo(BaseModel):
    nome: str | None = Field(default=None, max_length=160)
    bairro_id: str | None = None
    endereco: str | None = Field(default=None, max_length=300)
    capacidade: int | None = Field(default=None, ge=0, le=MAX_PESSOAS)
    aberto: bool | None = None
    pessoas_abrigadas: int | None = Field(default=None, ge=0, le=MAX_PESSOAS)
    desabrigados: int | None = Field(default=None, ge=0, le=MAX_PESSOAS)
    observacao: str | None = Field(default=None, max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class AtualizacaoAbrigo(BaseModel):
    id: int
    em: datetime
    autor_nome: str | None
    aberto: bool
    capacidade: int | None
    pessoas_abrigadas: int | None
    desabrigados: int | None
    observacao: str | None
    alteracoes: dict


@router.get(
    "", response_model=ListaAbrigos, summary="Abrigos com os totais de abertos, abrigados e desabrigados"
)
def listar(
    aberto: bool | None = None,
    distrito_id: str | None = Query(default=None, pattern=r"^ds-[1-8]$"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> ListaAbrigos:
    lista = servico.listar(db, aberto, distrito_id)
    em = lista["totais"]["atualizado_em"]
    ocupacao = servico_fontes.com_frescor(
        FonteMeta(
            id=FONTE_OCUPACAO,
            nome="Ocupação e desabrigados lançados pela equipe",
            tipo="observada",
            atualizado_em=em,
            status="planejada" if em is None else "atualizada",
        ),
        agora,
    )
    if ocupacao.desatualizado:
        ocupacao = ocupacao.model_copy(update={"status": "desatualizada"})
    lista["meta"] = Meta(
        fontes=[servico_fontes.meta(db, "recife-abrigos", agora), ocupacao],
        dados_insuficientes=not lista["itens"],
    )
    return lista


@router.post("", response_model=Abrigo, status_code=201, summary="Cadastrar abrigo")
def criar(
    pedido: PedidoAbrigo,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> Abrigo:
    return erro_de_negocio(lambda: servico.criar(db, pedido.model_dump(), ctx.usuario, ctx.ip, agora))


@router.get("/{abrigo_id}", response_model=Abrigo, summary="Detalhe do abrigo")
def detalhe(
    abrigo_id: uuid.UUID, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> Abrigo:
    return erro_de_negocio(lambda: servico.obter(db, abrigo_id))


@router.patch("/{abrigo_id}", response_model=Abrigo, summary="Atualizar abrigo (gera histórico)")
def atualizar(
    abrigo_id: uuid.UUID,
    pedido: PedidoAtualizacaoAbrigo,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> Abrigo:
    dados = pedido.model_dump(exclude_unset=True)
    return erro_de_negocio(lambda: servico.atualizar(db, abrigo_id, dados, ctx.usuario, ctx.ip, agora))


@router.get(
    "/{abrigo_id}/historico",
    response_model=list[AtualizacaoAbrigo],
    summary="Atualizações do abrigo, mais recentes primeiro",
)
def historico(
    abrigo_id: uuid.UUID, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> list[AtualizacaoAbrigo]:
    return erro_de_negocio(lambda: servico.historico(db, abrigo_id))
