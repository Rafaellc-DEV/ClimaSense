"""Conexão com o MongoDB Atlas — porte de `conectar()` do `load_mongo.py` (Desktop/AVD) — T2.5."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import certifi
from pymongo import ASCENDING, MongoClient
from pymongo.server_api import ServerApi

from climasense.config import Configuracao, obter_configuracao

COLECAO_DISTRITOS = "DistritosSanitarios"
COLECAO_HIDROGRAFIA = "FaixasHidricas"
COLECAO_BRONZE_VACINACAO = "bronze_vacinados"


def conectar(config: Configuracao | None = None, fabrica: Callable[..., Any] = MongoClient) -> Any:
    """Mesmo padrão testado no mapa da Aula 07: Server API 1, certificados do certifi e timeouts curtos."""
    config = config or obter_configuracao()
    return fabrica(
        config.exigir("mongo_uri"),
        server_api=ServerApi("1"),
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=15000,
        connectTimeoutMS=15000,
        socketTimeoutMS=30000,
    )


def criar_indices(cliente: Any, config: Configuracao | None = None) -> list[str]:
    """Índices usados pela carga territorial (upsert por código) e pela bronze acumulativa (por execução)."""
    config = config or obter_configuracao()
    territorio = cliente[config.mongo_db_territorio]
    criados = [
        territorio[COLECAO_DISTRITOS].create_index(
            [("properties.cdistscodi", ASCENDING)], unique=True, name="codigo_distrito_unico"
        ),
        cliente[config.mongo_db_bronze_vacinacao][COLECAO_BRONZE_VACINACAO].create_index(
            [("_execucao_id", ASCENDING)], name="por_execucao"
        ),
    ]
    return criados


def verificar(cliente: Any) -> bool:
    return bool(cliente.admin.command("ping").get("ok"))
