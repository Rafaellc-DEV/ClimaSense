"""Avaliações territoriais (T7.2, RF-10)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.erros import ErroClimaSense
from climasense.dominio.fluxo_revisao import Acao, TransicaoNegada
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos.avaliacoes import ConteudoAvaliacao, ServicoAvaliacoes
from climasense.servicos.territorio import nome

router = APIRouter(prefix="/avaliacoes", tags=["Avaliações"])
consultar = exige(Permissao.CONSULTAR)
editar = exige(Permissao.EDITAR)
revisar = exige(Permissao.REVISAR)
publicar = exige(Permissao.PUBLICAR)


class Evidencia(BaseModel):
    tipo: str = Field(description="mapa | serie | cenario | fonte | vacinacao")
    descricao: str = Field(max_length=300)
    fonte_id: str
    capturada_em: datetime
    valor: str | None = Field(default=None, max_length=120)
    endereco: str | None = Field(
        default=None, max_length=300, description="Caminho da tela com o recorte usado"
    )


class PedidoAvaliacao(BaseModel):
    territorio_id: str
    periodo_inicio: date
    periodo_fim: date
    prioridade: str = Field(description="sem_indicacao | atencao | alerta | critico")
    justificativa: str = Field(max_length=4000)
    limitacoes: str | None = Field(default=None, max_length=2000)
    evidencias: list[Evidencia] = Field(default_factory=list, max_length=20)


class PedidoVersaoAvaliacao(BaseModel):
    prioridade: str
    justificativa: str = Field(max_length=4000)
    limitacoes: str | None = Field(default=None, max_length=2000)
    evidencias: list[Evidencia] = Field(default_factory=list, max_length=20)


class Decisao(BaseModel):
    justificativa: str | None = Field(default=None, max_length=2000)


class ResumoAvaliacao(BaseModel):
    id: uuid.UUID
    estado: str
    territorio_id: str
    territorio_nome: str
    periodo_inicio: date
    periodo_fim: date
    prioridade: str
    versao_atual: int
    autor_id: uuid.UUID
    autor_nome: str
    atualizado_em: datetime


class ListaAvaliacoes(BaseModel):
    itens: list[ResumoAvaliacao]
    contagens: dict[str, int]
    total: int


class EventoLinhaTempo(BaseModel):
    tipo: str
    numero: int
    em: datetime
    por: str
    texto: str | None


class VersaoAvaliacao(BaseModel):
    numero: int
    prioridade: str
    justificativa: str
    limitacoes: str | None
    evidencias: list[dict]
    autor_id: uuid.UUID
    autor_nome: str
    criado_em: datetime


class DetalheAvaliacao(BaseModel):
    id: uuid.UUID
    estado: str
    territorio_id: str
    territorio_nome: str
    periodo_inicio: date
    periodo_fim: date
    versao_atual: int
    versao: VersaoAvaliacao
    linha_do_tempo: list[EventoLinhaTempo]
    acoes: list[str]


def _erro(funcao):
    try:
        return funcao()
    except TransicaoNegada as e:
        raise ErroClimaSense(e.status, e.mensagem) from None


def _detalhe(db: Session, avaliacao_id: uuid.UUID, ctx: Contexto, agora: datetime) -> DetalheAvaliacao:
    d = _erro(lambda: ServicoAvaliacoes(db).detalhe(avaliacao_id, ctx.usuario, agora))
    a, v = d["avaliacao"], d["versao"]
    return DetalheAvaliacao(
        id=a.id,
        estado=a.estado,
        territorio_id=a.territorio_id,
        territorio_nome=nome(db, a.territorio_id),
        periodo_inicio=a.periodo_inicio,
        periodo_fim=a.periodo_fim,
        versao_atual=a.versao_atual,
        versao=VersaoAvaliacao(
            numero=v.numero,
            prioridade=v.prioridade,
            justificativa=v.justificativa,
            limitacoes=v.limitacoes,
            evidencias=v.evidencias,
            autor_id=v.autor_id,
            autor_nome=d["autor_nome"],
            criado_em=v.criado_em,
        ),
        linha_do_tempo=[EventoLinhaTempo(**e) for e in d["linha_do_tempo"]],
        acoes=d["acoes"],
    )


def _conteudo(p: PedidoAvaliacao | PedidoVersaoAvaliacao) -> ConteudoAvaliacao:
    return ConteudoAvaliacao(
        prioridade=p.prioridade,
        justificativa=p.justificativa,
        limitacoes=p.limitacoes,
        evidencias=[e.model_dump(mode="json") for e in p.evidencias],
    )


@router.get("", response_model=ListaAvaliacoes, summary="Avaliações com filtros e contagem por estado")
def listar(
    estado: str | None = None,
    territorio_id: str | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
) -> ListaAvaliacoes:
    servico = ServicoAvaliacoes(db)
    todas = servico.listar(None, territorio_id, inicio, fim)
    contagens: dict[str, int] = {}
    for a in todas:
        contagens[a["estado"]] = contagens.get(a["estado"], 0) + 1
    itens = [ResumoAvaliacao(**a) for a in todas if estado is None or a["estado"] == estado]
    return ListaAvaliacoes(itens=itens, contagens=contagens, total=len(todas))


@router.post("", response_model=DetalheAvaliacao, status_code=201, summary="Registrar avaliação (rascunho)")
def criar(
    pedido: PedidoAvaliacao,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheAvaliacao:
    a = _erro(
        lambda: ServicoAvaliacoes(db).criar(
            pedido.territorio_id,
            pedido.periodo_inicio,
            pedido.periodo_fim,
            _conteudo(pedido),
            ctx.usuario,
            ctx.ip,
            agora,
        )
    )
    return _detalhe(db, a.id, ctx, agora)


@router.get(
    "/{avaliacao_id}", response_model=DetalheAvaliacao, summary="Detalhe com versão atual e linha do tempo"
)
def detalhe(
    avaliacao_id: uuid.UUID,
    ctx: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheAvaliacao:
    return _detalhe(db, avaliacao_id, ctx, agora)


@router.put("/{avaliacao_id}", response_model=DetalheAvaliacao, summary="Salvar nova versão")
def nova_versao(
    avaliacao_id: uuid.UUID,
    pedido: PedidoVersaoAvaliacao,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheAvaliacao:
    _erro(lambda: ServicoAvaliacoes(db).editar(avaliacao_id, _conteudo(pedido), ctx.usuario, ctx.ip, agora))
    return _detalhe(db, avaliacao_id, ctx, agora)


def _rota_acao(acao: Acao, dependencia, resumo: str):
    def rota(
        avaliacao_id: uuid.UUID,
        pedido: Decisao | None = None,
        ctx: Contexto = Depends(dependencia),
        db: Session = Depends(obter_sessao),
        agora: datetime = Depends(relogio),
    ) -> DetalheAvaliacao:
        justificativa = pedido.justificativa if pedido else None
        _erro(
            lambda: ServicoAvaliacoes(db).transicao(
                avaliacao_id, acao, ctx.usuario, ctx.ip, agora, justificativa
            )
        )
        return _detalhe(db, avaliacao_id, ctx, agora)

    router.add_api_route(
        f"/{{avaliacao_id}}/{acao.value}",
        rota,
        methods=["POST"],
        response_model=DetalheAvaliacao,
        summary=resumo,
        name=f"avaliacao_{acao.value}",
    )


_rota_acao(Acao.ENVIAR, editar, "Enviar para revisão")
_rota_acao(Acao.APROVAR, revisar, "Aprovar a versão atual (revisor diferente do autor)")
_rota_acao(Acao.DEVOLVER, revisar, "Devolver com justificativa")
_rota_acao(Acao.ENCERRAR, publicar, "Encerrar (coordenação)")
