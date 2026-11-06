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
# Bronze acumulativa do ETL: banco "bronze", uma coleção por fonte (id com "_" no lugar de "-").
COLECOES_BRONZE = (
    ("bronze", "open_meteo_historico"),
    ("bronze", "open_meteo_previsao"),
    ("bronze", "open_meteo_mare"),
    ("bronze", "apac_chuva"),
    ("bronze", "apac_chuva_historico"),
    ("bronze", "alertas_oficiais"),
    ("bronze", "recife_alagamento"),
    ("bronze", "recife_abrigos"),
    ("bronze", "infodengue"),
    ("bronze", "sinan_leptospirose"),  # só contagens por semana; nenhuma linha individual
    ("bronze", "recife_arboviroses"),  # só contagens por bairro e ano; sem endereço, CEP ou nascimento
    ("bronze", "cnes_equipamentos"),  # só unidades públicas/SUS; sem telefone, e-mail, CNPJ ou razão social
    ("bronze", "ibge_censo_2022_bairro"),  # só contagens por bairro
    ("bronze", "recife_areas_risco"),  # polígonos de setores de risco da Sedec (cobertura parcial)
)


def conectar(config: Configuracao | None = None, fabrica: Callable[..., Any] = MongoClient) -> Any:
    """Mesmo padrão testado no mapa da Aula 07: Server API 1, certificados do certifi e timeouts curtos."""
    config = config or obter_configuracao()
    uri = config.exigir("mongo_uri")
    # Atlas (mongodb+srv) usa TLS; um Mongo local de desenvolvimento (mongodb://localhost) não.
    tls = uri.startswith("mongodb+srv://") or "tls=true" in uri.lower() or "ssl=true" in uri.lower()
    return fabrica(
        uri,
        server_api=ServerApi("1"),
        **({"tlsCAFile": certifi.where()} if tls else {}),
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
    ]
    for banco, colecao in COLECOES_BRONZE:
        criados.append(
            cliente[banco][colecao].create_index([("_execucao_id", ASCENDING)], name="por_execucao")
        )
    return criados


def verificar(cliente: Any) -> bool:
    return bool(cliente.admin.command("ping").get("ok"))
