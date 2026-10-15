"""GET /health — estado da API e dos bancos, sem detalhes sensíveis (T2.2)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from climasense import __version__
from climasense.api.deps import configuracao
from climasense.config import Configuracao, ConfiguracaoAusente

log = logging.getLogger("climasense.saude")
EstadoBanco = Literal["ok", "indisponivel", "nao_configurado"]

router = APIRouter(tags=["Saúde do sistema"])


class Saude(BaseModel):
    status: Literal["ok", "degradado"]
    versao: str
    ambiente: str
    bancos: dict[str, EstadoBanco]


def _checar(nome: str, verificador: Callable[[], bool]) -> EstadoBanco:
    try:
        return "ok" if verificador() else "indisponivel"
    except ConfiguracaoAusente:
        return "nao_configurado"
    except Exception as erro:  # noqa: BLE001 — qualquer falha de rede vira "indisponível"
        log.warning("Banco %s indisponível (%s)", nome, type(erro).__name__)
        return "indisponivel"


def verificar_postgres() -> bool:
    from climasense.infra import postgres

    return postgres.verificar(postgres.engine_da_configuracao())


def verificar_mongo() -> bool:
    from climasense.infra import mongo

    cliente = mongo.conectar()
    try:
        return mongo.verificar(cliente)
    finally:
        cliente.close()


def verificadores() -> dict[str, Callable[[], bool]]:
    return {"postgres": verificar_postgres, "mongo": verificar_mongo}


@router.get("/health", response_model=Saude, summary="Estado da API e dos bancos")
def health(
    config: Configuracao = Depends(configuracao),
    checagens: dict[str, Callable[[], bool]] = Depends(verificadores),
) -> Saude:
    bancos = {nome: _checar(nome, f) for nome, f in checagens.items()}
    return Saude(
        status="ok" if all(v == "ok" for v in bancos.values()) else "degradado",
        versao=__version__,
        ambiente=config.ambiente,
        bancos=bancos,
    )
