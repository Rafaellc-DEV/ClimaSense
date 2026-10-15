"""Dependências comuns da API. A configuração vem da própria aplicação (app.state), não de um global:
assim testes e ambientes diferentes não se misturam."""

from __future__ import annotations

from fastapi import Request

from climasense.config import Configuracao


def configuracao(request: Request) -> Configuracao:
    return request.app.state.config
