"""Fontes de dados: status calculado (design §7.2) e metadados para o envelope das respostas (CA-02)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.envelope import FonteMeta
from climasense.dominio.qualidade import status_fonte

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


def meta(db: Session, fonte_id: str, agora: datetime) -> FonteMeta:
    """Metadados de uma fonte para `meta.fontes` (nome, tipo, última carga e status)."""
    encontradas = linhas(db, agora, fonte_id)
    if not encontradas:
        return FonteMeta(id=fonte_id, nome=fonte_id, tipo="derivada", status="planejada")
    f = encontradas[0]
    return FonteMeta(
        id=f["id"], nome=f["nome"], tipo=f["tipo"], atualizado_em=f["ultimo_sucesso"], status=f["status"]
    )


def minimo_observacoes(db: Session, fonte_id: str) -> int:
    return (
        db.execute(text("select min_observacoes from app.fontes where id = :i"), {"i": fonte_id}).scalar()
        or 1
    )
