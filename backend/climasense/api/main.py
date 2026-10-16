"""Aplicação FastAPI do ClimaSense (T2.2). Rode com: uvicorn climasense.api.main:app --reload"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from climasense import __version__
from climasense.api.erros import registrar_tratadores
from climasense.api.routers import (
    admin_sistema,
    admin_usuarios,
    auth,
    avaliacoes,
    cenarios,
    comunicados,
    fontes,
    painel,
    publico,
    saude,
    saude_agregada,
    series,
    territorios,
)
from climasense.api.seguranca import CabecalhosSeguranca
from climasense.config import Configuracao, obter_configuracao

PREFIXO = "/api/v1"
# Ordem de inclusão sob /api/v1. Também lida pelo teste da matriz de autorização.
ROTEADORES = [
    saude.router,
    auth.router,
    admin_usuarios.router,
    territorios.router,
    territorios.publico,
    publico.router,
    fontes.router,
    series.router,
    cenarios.router,
    saude_agregada.router,
    avaliacoes.router,
    comunicados.router,
    painel.router,
    admin_sistema.router,
]
log = logging.getLogger("climasense.api")


async def _expirar_periodicamente(config: Configuracao) -> None:
    """A cada minuto, encerra os comunicados vencidos (T7.5). A landing já filtra pela validade, então um
    atraso aqui nunca mostra aviso vencido."""
    from climasense.infra.postgres import engine_da_configuracao, fabrica_sessoes
    from climasense.servicos.comunicados import expirar_vencidos

    while True:
        try:
            with fabrica_sessoes(engine_da_configuracao(config))() as db:
                n = await asyncio.to_thread(expirar_vencidos, db, datetime.now(UTC))
            if n:
                log.info("%s comunicado(s) encerrado(s) por fim da validade", n)
        except Exception as erro:  # noqa: BLE001 — só o tipo: mensagens de driver podem ter a URI
            log.warning("Expiração de comunicados falhou (%s)", type(erro).__name__)
        await asyncio.sleep(60)


def criar_app(config: Configuracao | None = None) -> FastAPI:
    config = config or obter_configuracao()

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI):
        tarefa = None
        if config.ambiente != "teste" and config.database_url is not None:
            tarefa = asyncio.create_task(_expirar_periodicamente(config))
        yield
        if tarefa:
            tarefa.cancel()

    app = FastAPI(
        lifespan=ciclo_de_vida,
        title="ClimaSense API",
        version=__version__,
        description="Inteligência climática para a Vigilância em Saúde do Recife. Somente dados reais e identificados.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.config = config
    registrar_tratadores(app)
    app.add_middleware(CabecalhosSeguranca, producao=config.em_producao)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    v1 = APIRouter(prefix=PREFIXO)
    for roteador in ROTEADORES:
        v1.include_router(roteador)
    app.include_router(v1)
    return app


app = criar_app()
