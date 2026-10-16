"""Comunicados (T7.3, T7.4): versões com hash, prévia igual à landing, diferença entre versões e o fluxo
de revisão e publicação (RF-11)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.erros import ErroClimaSense
from climasense.api.routers.avaliacoes import Decisao, EventoLinhaTempo, Evidencia
from climasense.api.routers.publico import AvisoPublico, aviso_publico
from climasense.dominio import comunicado as dominio
from climasense.dominio.fluxo_revisao import Acao, TransicaoNegada
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos.comunicados import ServicoComunicados

router = APIRouter(prefix="/comunicados", tags=["Comunicados"])
consultar = exige(Permissao.CONSULTAR)
editar = exige(Permissao.EDITAR)
revisar = exige(Permissao.REVISAR)
publicar = exige(Permissao.PUBLICAR)


class PedidoComunicado(BaseModel):
    territorios: list[str] = Field(min_length=1, max_length=20)
    publico: str = "populacao"
    nivel: str
    titulo: str = Field(max_length=dominio.MAX_TITULO)
    texto: str = Field(default="", max_length=dominio.MAX_TEXTO)
    orientacoes: list[str] = Field(default_factory=list, max_length=dominio.MAX_ORIENTACOES)
    validade_inicio: datetime
    validade_fim: datetime
    evidencias: list[Evidencia] = Field(default_factory=list, max_length=20)
    avaliacao_id: uuid.UUID | None = None


class ResumoComunicado(BaseModel):
    id: uuid.UUID
    estado: str
    nivel: str
    titulo: str
    territorios: list[str]
    validade_inicio: datetime
    validade_fim: datetime
    versao_atual: int
    autor_id: uuid.UUID
    autor_nome: str
    atualizado_em: datetime
    publicado_em: datetime | None


class ListaComunicados(BaseModel):
    itens: list[ResumoComunicado]
    contagens: dict[str, int]
    total: int


class VersaoResumo(BaseModel):
    numero: int
    criado_em: datetime
    hash_conteudo: str
    titulo: str
    autor_nome: str


class FraseLonga(BaseModel):
    frase: int
    palavras: int
    inicio: str


class DetalheComunicado(BaseModel):
    id: uuid.UUID
    estado: str
    versao_atual: int
    versao_aprovada: int | None
    publicado_em: datetime | None
    avaliacao_id: uuid.UUID | None
    autor_id: uuid.UUID
    autor_nome: str
    publico: str
    territorios: list[str]
    evidencias: list[dict]
    hash_conteudo: str
    previa: AvisoPublico
    versoes: list[VersaoResumo]
    linha_do_tempo: list[EventoLinhaTempo]
    acoes: list[str]
    frases_longas: list[FraseLonga]


class Trecho(BaseModel):
    tipo: str
    texto: str


class Diferenca(BaseModel):
    de: int
    para: int
    campos: dict[str, list[Trecho]]
    alterados: list[str]
    metadados: dict[str, dict[str, str]]


def _erro(funcao):
    try:
        return funcao()
    except TransicaoNegada as e:
        raise ErroClimaSense(e.status, e.mensagem) from None


def _conteudo(p: PedidoComunicado) -> dominio.Conteudo:
    return dominio.Conteudo(
        titulo=p.titulo,
        texto=p.texto,
        orientacoes=tuple(p.orientacoes),
        territorios=tuple(p.territorios),
        publico=p.publico,
        nivel=p.nivel,
        validade_inicio=p.validade_inicio,
        validade_fim=p.validade_fim,
    )


def _detalhe(db: Session, comunicado_id: uuid.UUID, ctx: Contexto, agora: datetime) -> DetalheComunicado:
    d = _erro(lambda: ServicoComunicados(db).detalhe(comunicado_id, ctx.usuario, agora))
    c, v = d["comunicado"], d["versao"]
    return DetalheComunicado(
        id=c.id,
        estado=c.estado,
        versao_atual=c.versao_atual,
        versao_aprovada=c.versao_aprovada,
        publicado_em=c.publicado_em,
        avaliacao_id=c.avaliacao_id,
        autor_id=v.autor_id,
        autor_nome=d["autor_nome"],
        publico=v.publico,
        territorios=v.territorios,
        evidencias=v.evidencias,
        hash_conteudo=v.hash_conteudo,
        previa=aviso_publico(db, c, v),
        versoes=[VersaoResumo(**x) for x in d["versoes"]],
        linha_do_tempo=[EventoLinhaTempo(**e) for e in d["linha_do_tempo"]],
        acoes=d["acoes"],
        frases_longas=[FraseLonga(**f) for f in d["frases_longas"]],
    )


@router.get("", response_model=ListaComunicados, summary="Comunicados com filtros e contagem por estado")
def listar(
    estado: str | None = None,
    territorio_id: str | None = None,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
) -> ListaComunicados:
    todos = ServicoComunicados(db).listar(None, territorio_id)
    contagens: dict[str, int] = {}
    for c in todos:
        contagens[c["estado"]] = contagens.get(c["estado"], 0) + 1
    return ListaComunicados(
        itens=[ResumoComunicado(**c) for c in todos if estado is None or c["estado"] == estado],
        contagens=contagens,
        total=len(todos),
    )


@router.post("", response_model=DetalheComunicado, status_code=201, summary="Criar rascunho de comunicado")
def criar(
    pedido: PedidoComunicado,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheComunicado:
    evidencias = [e.model_dump(mode="json") for e in pedido.evidencias]
    c = _erro(
        lambda: ServicoComunicados(db).criar(
            _conteudo(pedido), evidencias, ctx.usuario, ctx.ip, agora, pedido.avaliacao_id
        )
    )
    return _detalhe(db, c.id, ctx, agora)


@router.get(
    "/{comunicado_id}", response_model=DetalheComunicado, summary="Detalhe com prévia, versões e ações"
)
def detalhe(
    comunicado_id: uuid.UUID,
    ctx: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheComunicado:
    return _detalhe(db, comunicado_id, ctx, agora)


@router.put("/{comunicado_id}", response_model=DetalheComunicado, summary="Salvar nova versão")
def nova_versao(
    comunicado_id: uuid.UUID,
    pedido: PedidoComunicado,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheComunicado:
    evidencias = [e.model_dump(mode="json") for e in pedido.evidencias]
    _erro(
        lambda: ServicoComunicados(db).editar(
            comunicado_id, _conteudo(pedido), evidencias, ctx.usuario, ctx.ip, agora
        )
    )
    return _detalhe(db, comunicado_id, ctx, agora)


@router.get(
    "/{comunicado_id}/previa", response_model=AvisoPublico, summary="A versão atual como a landing mostrará"
)
def previa(
    comunicado_id: uuid.UUID, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> AvisoPublico:
    servico = ServicoComunicados(db)
    c = _erro(lambda: servico._obter(comunicado_id))
    return aviso_publico(db, c, servico.versao(c))


@router.get("/{comunicado_id}/versoes", response_model=list[VersaoResumo], summary="Histórico de versões")
def versoes(
    comunicado_id: uuid.UUID, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> list[VersaoResumo]:
    _erro(lambda: ServicoComunicados(db)._obter(comunicado_id))
    return [VersaoResumo(**v) for v in ServicoComunicados(db).versoes(comunicado_id)]


@router.get(
    "/{comunicado_id}/versoes/{a}/diferenca/{b}",
    response_model=Diferenca,
    summary="O que mudou entre duas versões",
)
def diferenca(
    comunicado_id: uuid.UUID,
    a: int,
    b: int,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
) -> Diferenca:
    return Diferenca(**_erro(lambda: ServicoComunicados(db).diferenca(comunicado_id, a, b)))


def _rota_acao(acao: Acao, dependencia, resumo: str):
    def rota(
        comunicado_id: uuid.UUID,
        pedido: Decisao | None = None,
        ctx: Contexto = Depends(dependencia),
        db: Session = Depends(obter_sessao),
        agora: datetime = Depends(relogio),
    ) -> DetalheComunicado:
        justificativa = pedido.justificativa if pedido else None
        _erro(
            lambda: ServicoComunicados(db).transicao(
                comunicado_id, acao, ctx.usuario, ctx.ip, agora, justificativa
            )
        )
        return _detalhe(db, comunicado_id, ctx, agora)

    router.add_api_route(
        f"/{{comunicado_id}}/{acao.value}",
        rota,
        methods=["POST"],
        response_model=DetalheComunicado,
        summary=resumo,
        name=f"comunicado_{acao.value}",
    )


_rota_acao(Acao.ENVIAR, editar, "Enviar para revisão")
_rota_acao(Acao.APROVAR, revisar, "Aprovar a versão atual (revisor diferente do autor)")
_rota_acao(Acao.DEVOLVER, revisar, "Devolver com justificativa")
_rota_acao(Acao.PUBLICAR, publicar, "Publicar na página inicial (só a versão aprovada)")
_rota_acao(Acao.ENCERRAR, publicar, "Encerrar: tira o aviso da página inicial")
