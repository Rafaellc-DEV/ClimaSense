"""Fontes de dados e execuções do ETL (T5.9, T5.11)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.deps import mongo
from climasense.api.erros import ErroClimaSense
from climasense.dominio.papeis import Permissao
from climasense.etl import execucao
from climasense.etl.conectores import CONECTORES
from climasense.infra.postgres import engine_da_configuracao, obter_sessao
from climasense.servicos import fontes as servico_fontes

router = APIRouter(tags=["Fontes de dados"])
consultar = exige(Permissao.CONSULTAR)
executar_etl = exige(Permissao.EXECUTAR_ETL)


class Fonte(BaseModel):
    id: str
    nome: str
    orgao: str
    url: str
    tipo: str
    licenca: str | None
    status: str
    ultima_atualizacao: datetime | None
    limite_desatualizacao_h: int


class Execucao(BaseModel):
    id: uuid.UUID
    fonte_id: str
    inicio: datetime
    fim: datetime | None
    status: str
    lidos: int
    gravados: int
    descartados: int
    motivos_descarte: dict
    erro: str | None


class PedidoExecucao(BaseModel):
    fonte_id: str
    limite: int | None = Field(default=None, ge=1)


def _fontes(db: Session, agora: datetime, fonte_id: str | None = None) -> list[Fonte]:
    return [
        Fonte(**r, ultima_atualizacao=r["ultimo_sucesso"]) for r in servico_fontes.linhas(db, agora, fonte_id)
    ]


@router.get(
    "/fontes",
    response_model=list[Fonte],
    summary="Fontes com status (atualizada, desatualizada, com falha, planejada)",
)
def listar(
    _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao), agora: datetime = Depends(relogio)
) -> list[Fonte]:
    return _fontes(db, agora)


@router.get("/fontes/{fonte_id}", response_model=Fonte, summary="Detalhe de uma fonte")
def detalhe(
    fonte_id: str,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> Fonte:
    encontradas = _fontes(db, agora, fonte_id)
    if not encontradas:
        raise ErroClimaSense(404, "Fonte não encontrada.")
    return encontradas[0]


@router.get(
    "/fontes/{fonte_id}/execucoes", response_model=list[Execucao], summary="Histórico de execuções do ETL"
)
def execucoes(
    fonte_id: str, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> list[Execucao]:
    linhas = db.execute(
        text("select * from app.etl_execucoes where fonte_id = :f order by inicio desc limit 50"),
        {"f": fonte_id},
    )
    return [Execucao(**r) for r in linhas.mappings()]


def executor_em_segundo_plano(request: Request):
    """Roda o conector depois da resposta. Substituível nos testes."""
    config = request.app.state.config

    def rodar(fonte_id: str, execucao_id: str, limite: int | None) -> None:
        execucao.executar(
            engine_da_configuracao(config), mongo(request), config, fonte_id, execucao_id, limite
        )

    return rodar


@router.post(
    "/etl/execucoes",
    response_model=Execucao,
    status_code=202,
    summary="Atualizar uma fonte agora (administrador)",
)
def disparar(
    pedido: PedidoExecucao,
    tarefas: BackgroundTasks,
    ctx: Contexto = Depends(executar_etl),
    db: Session = Depends(obter_sessao),
    rodar=Depends(executor_em_segundo_plano),
) -> Execucao:
    if pedido.fonte_id not in CONECTORES:
        raise ErroClimaSense(404, f"Fonte “{pedido.fonte_id}” não existe.")
    novo = (
        db.execute(
            text(
                "insert into app.etl_execucoes (fonte_id, status, disparado_por) values (:f, 'em_andamento', :u) returning *"
            ),
            {"f": pedido.fonte_id, "u": ctx.usuario.id},
        )
        .mappings()
        .one()
    )
    db.execute(
        text(
            "insert into app.auditoria (usuario_id, acao, alvo_tipo, alvo_id, ip) values (:u, 'etl_disparado', 'fonte', :f, :ip)"
        ),
        {"u": ctx.usuario.id, "f": pedido.fonte_id, "ip": ctx.ip},
    )
    db.commit()
    tarefas.add_task(rodar, pedido.fonte_id, str(novo["id"]), pedido.limite)
    return Execucao(**novo)


@router.get("/etl/execucoes/{execucao_id}", response_model=Execucao, summary="Status de uma execução")
def status(
    execucao_id: uuid.UUID, _: Contexto = Depends(executar_etl), db: Session = Depends(obter_sessao)
) -> Execucao:
    r = (
        db.execute(text("select * from app.etl_execucoes where id = :i"), {"i": execucao_id})
        .mappings()
        .first()
    )
    if not r:
        raise ErroClimaSense(404, "Execução não encontrada.")
    return Execucao(**r)
