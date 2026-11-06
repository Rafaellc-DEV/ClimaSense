"""Fontes de dados: status calculado (design §7.2) e metadados para o envelope das respostas (CA-02)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.envelope import FonteMeta
from climasense.dominio.qualidade import status_fonte
from climasense.etl import frescor

SQL_FONTES = """
select f.*, (select status from app.etl_execucoes e where e.fonte_id = f.id and e.status <> 'em_andamento'
             order by inicio desc limit 1) as ultima_status,
       (select max(fim) from app.etl_execucoes e where e.fonte_id = f.id and e.status = 'sucesso') as ultimo_sucesso
from app.fontes f where f.ativa
"""


def linhas(db: Session, agora: datetime, fonte_id: str | None = None) -> list[dict]:
    sql = SQL_FONTES + (" and f.id = :i" if fonte_id else "") + " order by f.implementada desc, f.nome"
    resultado = []
    for r in db.execute(text(sql), {"i": fonte_id}).mappings():
        d = dict(r)
        d["status"] = status_fonte(
            r["implementada"], r["ultima_status"], r["ultimo_sucesso"], r["limite_desatualizacao_h"], agora
        )
        resultado.append(d)
    return resultado


def limite_e_desatualizado(
    fonte_id: str, atualizado_em: datetime | None, agora: datetime
) -> tuple[float | None, bool | None]:
    """Limite de frescor (h) e se o dado passou dele; `None` = sem limite ou sem dado, nunca "em dia" (RF-19, RN-01)."""
    return frescor.limite_frescor_h(fonte_id), frescor.esta_desatualizado(fonte_id, atualizado_em, agora)


def com_frescor(fonte: FonteMeta, agora: datetime) -> FonteMeta:
    """Completa uma `FonteMeta` montada à mão com o limite de frescor e o indicador `desatualizado`."""
    limite, vencido = limite_e_desatualizado(fonte.id, fonte.atualizado_em, agora)
    return fonte.model_copy(update={"limite_frescor_h": limite, "desatualizado": vencido})


def meta(db: Session, fonte_id: str, agora: datetime) -> FonteMeta:
    """Metadados de uma fonte para `meta.fontes` (nome, tipo, última carga, status, limite e desatualizado)."""
    encontradas = linhas(db, agora, fonte_id)
    if not encontradas:
        return FonteMeta(id=fonte_id, nome=fonte_id, tipo="derivada", status="planejada")
    f = encontradas[0]
    limite, vencido = limite_e_desatualizado(f["id"], f["ultimo_sucesso"], agora)
    return FonteMeta(
        id=f["id"],
        nome=f["nome"],
        tipo=f["tipo"],
        atualizado_em=f["ultimo_sucesso"],
        status=f["status"],
        limite_frescor_h=limite,
        desatualizado=vencido,
    )


def minimo_observacoes(db: Session, fonte_id: str) -> int:
    return (
        db.execute(text("select min_observacoes from app.fontes where id = :i"), {"i": fonte_id}).scalar()
        or 1
    )
