"""Prazo de guarda e frescor das fontes (RNF-03, ADR 0015). Roda com a URL do dono: o papel da aplicação não
apaga auditoria e a limpeza só toca nas tabelas de acesso."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.etl import frescor
from climasense.infra.repositorios.auditoria import RepositorioAuditoria

ACAO_LIMPEZA = "limpeza_retencao"
ACAO_FRESCOR = "sincronizacao_frescor"


def limpar(db: Session, agora: datetime, dias_tentativas: int = 90, dias_sessoes: int = 30) -> dict[str, int]:
    """Apaga tentativas de login com mais de `dias_tentativas` dias e sessões que expiraram há mais de
    `dias_sessoes` dias. Idempotente. Registra na auditoria só as quantidades."""
    tentativas = db.execute(
        text("delete from app.tentativas_login where em < :limite"),
        {"limite": agora - timedelta(days=dias_tentativas)},
    ).rowcount
    sessoes = db.execute(
        text("delete from app.sessoes where expira_em < :limite"),
        {"limite": agora - timedelta(days=dias_sessoes)},
    ).rowcount
    resultado = {"tentativas_login": tentativas, "sessoes": sessoes}
    RepositorioAuditoria(db).registrar(
        ACAO_LIMPEZA,
        alvo_tipo="retencao",
        detalhes={**resultado, "dias_tentativas_login": dias_tentativas, "dias_sessoes": dias_sessoes},
    )
    db.commit()
    return resultado


def sincronizar_frescor(db: Session) -> dict[str, int]:
    """Faz `app.fontes.limite_desatualizacao_h` seguir `etl/frescor.toml` (fonte única do limite, RF-19).
    Arredonda para cima (a coluna é inteira). Fonte sem limite no TOML não é tocada. Idempotente."""
    alteradas = 0
    for fonte_id, horas in frescor.limites().items():
        alteradas += db.execute(
            text(
                "update app.fontes set limite_desatualizacao_h = :h where id = :i and limite_desatualizacao_h <> :h"
            ),
            {"h": max(1, math.ceil(horas)), "i": fonte_id},
        ).rowcount
    if alteradas:
        RepositorioAuditoria(db).registrar(
            ACAO_FRESCOR, alvo_tipo="fontes", detalhes={"fontes_alteradas": alteradas}
        )
    db.commit()
    return {"fontes_alteradas": alteradas}
