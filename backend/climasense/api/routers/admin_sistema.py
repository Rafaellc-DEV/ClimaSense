"""Administração do sistema (RF-14.3, RF-16.2, RF-16.3): auditoria, execuções do ETL e limites das fontes."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige
from climasense.api.erros import ErroClimaSense
from climasense.dominio.papeis import Permissao
from climasense.dominio.recorte import inicio_do_dia_utc
from climasense.infra.postgres import obter_sessao
from climasense.infra.repositorios.auditoria import RepositorioAuditoria

router = APIRouter(prefix="/admin", tags=["Administração"])
admin = exige(Permissao.ADMINISTRAR)


class RegistroAuditoria(BaseModel):
    id: int
    em: datetime
    usuario_id: uuid.UUID | None
    usuario_nome: str | None
    acao: str
    alvo_tipo: str | None
    alvo_id: str | None
    detalhes: dict


class PaginaAuditoria(BaseModel):
    itens: list[RegistroAuditoria]
    acoes: list[str]
    pagina: int
    por_pagina: int


class ExecucaoAdmin(BaseModel):
    id: uuid.UUID
    fonte_id: str
    fonte_nome: str
    inicio: datetime
    fim: datetime | None
    status: str
    lidos: int
    gravados: int
    descartados: int
    motivos_descarte: dict
    erro: str | None
    disparado_por_nome: str | None


class AjusteFonte(BaseModel):
    limite_desatualizacao_h: int | None = Field(default=None, ge=1, le=24 * 400)
    min_observacoes: int | None = Field(default=None, ge=1, le=100_000)


class LimitesFonte(BaseModel):
    id: str
    limite_desatualizacao_h: int
    min_observacoes: int


@router.get("/auditoria", response_model=PaginaAuditoria, summary="Consultar a auditoria (somente leitura)")
def auditoria(
    usuario_id: uuid.UUID | None = None,
    acao: str | None = Query(default=None, max_length=60),
    inicio: date | None = None,
    fim: date | None = None,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=50, ge=1, le=200),
    _: Contexto = Depends(admin),
    db: Session = Depends(obter_sessao),
) -> PaginaAuditoria:
    registros = RepositorioAuditoria(db).listar(
        usuario_id=usuario_id,
        acao=acao or None,
        inicio=inicio_do_dia_utc(inicio) if inicio else None,
        fim=inicio_do_dia_utc(fim + timedelta(days=1)) if fim else None,
        limite=por_pagina,
        deslocamento=(pagina - 1) * por_pagina,
    )
    nomes = dict(
        db.execute(
            text("select id, nome from app.usuarios where id = any(:i)"),
            {"i": [r.usuario_id for r in registros if r.usuario_id]},
        ).all()
    )
    acoes = [a for (a,) in db.execute(text("select distinct acao from app.auditoria order by acao"))]
    return PaginaAuditoria(
        itens=[
            RegistroAuditoria(
                id=r.id,
                em=r.em,
                usuario_id=r.usuario_id,
                usuario_nome=nomes.get(r.usuario_id),
                acao=r.acao,
                alvo_tipo=r.alvo_tipo,
                alvo_id=r.alvo_id,
                detalhes=r.detalhes or {},
            )
            for r in registros
        ],
        acoes=acoes,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get(
    "/etl/execucoes",
    response_model=list[ExecucaoAdmin],
    summary="Últimas execuções do ETL, de todas as fontes",
)
def execucoes(
    fonte_id: str | None = None, _: Contexto = Depends(admin), db: Session = Depends(obter_sessao)
) -> list[ExecucaoAdmin]:
    linhas = db.execute(
        text(
            "select e.*, f.nome as fonte_nome, u.nome as disparado_por_nome from app.etl_execucoes e "
            "join app.fontes f on f.id = e.fonte_id left join app.usuarios u on u.id = e.disparado_por "
            "where (cast(:f as varchar) is null or e.fonte_id = :f) order by e.inicio desc limit 100"
        ),
        {"f": fonte_id},
    ).mappings()
    return [ExecucaoAdmin(**r) for r in linhas]


@router.patch("/fontes/{fonte_id}", response_model=LimitesFonte, summary="Ajustar limites de uma fonte")
def ajustar_fonte(
    fonte_id: str, pedido: AjusteFonte, ctx: Contexto = Depends(admin), db: Session = Depends(obter_sessao)
) -> LimitesFonte:
    atual = (
        db.execute(
            text("select id, limite_desatualizacao_h, min_observacoes from app.fontes where id = :i"),
            {"i": fonte_id},
        )
        .mappings()
        .first()
    )
    if not atual:
        raise ErroClimaSense(404, "Fonte não encontrada.")
    novo = {
        "limite_desatualizacao_h": pedido.limite_desatualizacao_h or atual["limite_desatualizacao_h"],
        "min_observacoes": pedido.min_observacoes or atual["min_observacoes"],
    }
    db.execute(
        text("update app.fontes set limite_desatualizacao_h = :l, min_observacoes = :m where id = :i"),
        {"l": novo["limite_desatualizacao_h"], "m": novo["min_observacoes"], "i": fonte_id},
    )
    RepositorioAuditoria(db).registrar(
        "fonte_ajustada",
        usuario_id=ctx.usuario.id,
        alvo_tipo="fonte",
        alvo_id=fonte_id,
        detalhes={"antes": dict(atual), "depois": novo},
        ip=ctx.ip,
    )
    db.commit()
    return LimitesFonte(id=fonte_id, **novo)
