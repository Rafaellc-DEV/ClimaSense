"""Dependências comuns da API. A configuração vem da própria aplicação (app.state), não de um global:
assim testes e ambientes diferentes não se misturam."""

from __future__ import annotations

from fastapi import Request

from climasense.config import Configuracao


def configuracao(request: Request) -> Configuracao:
    return request.app.state.config


def mongo(request: Request):
    """Cliente do Atlas compartilhado pela aplicação (criado no primeiro uso). Substituível nos testes."""
    if getattr(request.app.state, "mongo", None) is None:
        from climasense.infra.mongo import conectar

        request.app.state.mongo = conectar(request.app.state.config)
    return request.app.state.mongo
