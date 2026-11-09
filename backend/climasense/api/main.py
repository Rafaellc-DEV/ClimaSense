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
    acoes,
    admin_login,
    admin_sistema,
    admin_usuarios,
    auth,
    avaliacoes,
    boletim,
    cenarios,
    comunicados,
    estagios,
    eventos,
    fontes,
    painel,
    publico,
    risco_alagamento,
    saude,
    saude_agravos,
    series,
    situacao,
    territorios,
)
from climasense.api.seguranca import CabecalhosSeguranca
from climasense.config import Configuracao, obter_configuracao

PREFIXO = "/api/v1"
# Ordem de inclusão sob /api/v1. Também lida pelo teste da matriz de autorização: lista TODOS os roteadores,
# inclusive os que ficam atrás de chave de funcionalidade (veja FUNCOES e `roteadores_ativos`).
ROTEADORES = [
    saude.router,
    auth.router,
    admin_usuarios.router,
    admin_login.router,
    territorios.router,
    territorios.mapa_portatil_router,
    territorios.publico,
    publico.router,
    fontes.router,
    series.router,
    series.estatisticas_router,
    cenarios.router,
    avaliacoes.router,
    comunicados.router,
    painel.router,
    admin_sistema.router,
    estagios.router,
    acoes.router,
    eventos.router,
    boletim.router,
    risco_alagamento.router,
    saude_agravos.router,
    situacao.router,
    saude_agravos.ocorrencias,
]
# Chaves de funcionalidade (ADR 0011, RNF-02): campo da Configuracao -> roteadores que ela liga. Desligada
# (padrão) = a rota nem é registrada: 404 e fora do OpenAPI.
FUNCOES: dict[str, list[APIRouter]] = {
    "func_landing_publica": [publico.router, territorios.publico],
    "func_comunicados": [comunicados.router],
    "func_avaliacoes": [avaliacoes.router],
    "func_mapa_portatil": [territorios.mapa_portatil_router],
    "func_estatisticas_series": [series.estatisticas_router],
}
log = logging.getLogger("climasense.api")


def roteadores_ativos(config: Configuracao) -> list[APIRouter]:
    desligados = {id(r) for campo, rs in FUNCOES.items() if not getattr(config, campo) for r in rs}
    return [r for r in ROTEADORES if id(r) not in desligados]


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


async def _aquecer_periodicamente(config: Configuracao) -> None:
    """Renova em segundo plano o cache das leituras que as telas pedem primeiro (servicos/aquecimento.py): ninguém
    paga a leitura fria depois que o cache vence."""
    from climasense.infra.postgres import engine_da_configuracao, fabrica_sessoes
    from climasense.servicos import aquecimento

    fabrica = fabrica_sessoes(engine_da_configuracao(config))
    while True:
        try:
            await asyncio.to_thread(aquecimento.aquecer, fabrica, datetime.now(UTC))
        except Exception as erro:  # noqa: BLE001 — só o tipo: mensagens de driver podem ter a URI
            log.warning("Aquecimento do cache falhou (%s)", type(erro).__name__)
        await asyncio.sleep(aquecimento.INTERVALO_S)


def criar_app(config: Configuracao | None = None) -> FastAPI:
    config = config or obter_configuracao()

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI):
        tarefas = []
        if config.ambiente != "teste" and config.database_url is not None:
            tarefas.append(asyncio.create_task(_expirar_periodicamente(config)))
            tarefas.append(asyncio.create_task(_aquecer_periodicamente(config)))
        yield
        for t in tarefas:
            t.cancel()

    app = FastAPI(
        lifespan=ciclo_de_vida,
        title="ClimaSense API",
        version=__version__,
        description="Inteligência climática para a Vigilância em Saúde do Recife. Somente dados reais e identificados.",
        # Em produção a documentação interativa e o contrato não ficam no ar (RNF-02);
        # scripts/exportar_openapi.py gera o contrato sem servidor.
        docs_url=None if config.em_producao else "/api/docs",
        redoc_url=None,
        openapi_url=None if config.em_producao else "/api/openapi.json",
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
    for roteador in roteadores_ativos(config):
        v1.include_router(roteador)
    app.include_router(v1)
    return app


app = criar_app()
