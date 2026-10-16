"""Status de uma fonte (RF-06, design §7.2). Domínio puro."""

from __future__ import annotations

from datetime import datetime, timedelta


def status_fonte(
    implementada: bool,
    ultima_status: str | None,
    ultimo_sucesso: datetime | None,
    limite_h: int,
    agora: datetime,
) -> str:
    if not implementada:
        return "planejada"
    if ultima_status == "falha":
        return "com_falha"
    if ultimo_sucesso is None or agora - ultimo_sucesso > timedelta(hours=limite_h):
        return "desatualizada"
    return "atualizada"
