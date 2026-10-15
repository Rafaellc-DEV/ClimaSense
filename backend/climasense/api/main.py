"""Aplicação FastAPI do ClimaSense (T2.2). Rode com: uvicorn climasense.api.main:app --reload"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from climasense import __version__
from climasense.api.erros import registrar_tratadores
from climasense.api.routers import saude
from climasense.api.seguranca import CabecalhosSeguranca
from climasense.config import Configuracao, obter_configuracao

PREFIXO = "/api/v1"


def criar_app(config: Configuracao | None = None) -> FastAPI:
    config = config or obter_configuracao()
    app = FastAPI(
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
    v1.include_router(saude.router)
    app.include_router(v1)
    return app


app = criar_app()
