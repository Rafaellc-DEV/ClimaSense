"""Erros da API no formato problem+json (RFC 9457), com mensagens em português simples (T2.2).

Nunca devolve a pilha de execução nem detalhes internos (RNF-SEG-05).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from climasense.config import ConfiguracaoAusente
from climasense.dominio.recorte import RecorteInvalido

log = logging.getLogger("climasense.api")
TIPO = "application/problem+json"

TITULOS = {
    400: "Pedido inválido",
    401: "Entre para continuar",
    403: "Sem permissão",
    404: "Não encontrado",
    405: "Ação não permitida",
    409: "Conflito",
    422: "Dados inválidos",
    429: "Muitas tentativas",
    500: "Erro interno",
    503: "Serviço indisponível",
}


class ErroClimaSense(Exception):
    """Erro de negócio com mensagem pronta para a tela."""

    def __init__(
        self, status: int, detalhe: str, titulo: str | None = None, cabecalhos: dict[str, str] | None = None
    ):
        super().__init__(detalhe)
        self.status = status
        self.detalhe = detalhe
        self.titulo = titulo or TITULOS.get(status, "Erro")
        self.cabecalhos = cabecalhos


def problema(status: int, detalhe: str, titulo: str | None = None, **extra: object) -> JSONResponse:
    corpo = {
        "type": "about:blank",
        "title": titulo or TITULOS.get(status, "Erro"),
        "status": status,
        "detail": detalhe,
    }
    corpo.update(extra)
    return JSONResponse(corpo, status_code=status, media_type=TIPO)


def _campo(loc: tuple) -> str:
    partes = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    return ".".join(partes) or "pedido"


def _mensagem(e: dict) -> str:
    """Mensagem de validação em português (os textos do Pydantic vêm em inglês)."""
    ctx = e.get("ctx") or {}
    tipo = e.get("type", "")
    match tipo:
        case "missing":
            return "Campo obrigatório."
        case "greater_than_equal" | "greater_than":
            return f"O valor não pode ser menor que {ctx.get('ge', ctx.get('gt'))}."
        case "less_than_equal" | "less_than":
            return f"O valor não pode ser maior que {ctx.get('le', ctx.get('lt'))}."
        case "string_too_long":
            return f"O texto não pode ter mais de {ctx.get('max_length')} caracteres."
        case "string_too_short":
            return f"O texto precisa ter ao menos {ctx.get('min_length')} caractere(s)."
        case "too_long":
            return f"São aceitos no máximo {ctx.get('max_length')} itens."
        case "too_short":
            return f"Informe ao menos {ctx.get('min_length')} item(ns)."
        case "int_parsing" | "int_type" | "int_from_float":
            return "Informe um número inteiro."
        case "float_parsing" | "float_type":
            return "Informe um número."
        case "bool_parsing" | "bool_type":
            return "Informe sim ou não."
        case _:
            return e["msg"]


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroClimaSense)
    async def _negocio(_: Request, erro: ErroClimaSense) -> JSONResponse:
        resposta = problema(erro.status, erro.detalhe, erro.titulo)
        for k, v in (erro.cabecalhos or {}).items():
            resposta.headers[k] = v
        return resposta

    @app.exception_handler(RecorteInvalido)
    async def _recorte(_: Request, erro: RecorteInvalido) -> JSONResponse:
        return problema(400, str(erro))

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        campos = [{"campo": _campo(tuple(e["loc"])), "mensagem": _mensagem(e)} for e in erro.errors()]
        nomes = ", ".join(c["campo"] for c in campos)
        return problema(422, f"Confira os campos: {nomes}.", campos=campos)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
        detalhe = erro.detail if isinstance(erro.detail, str) and erro.status_code != 404 else None
        if erro.status_code == 404:
            detalhe = "O endereço pedido não existe."
        return problema(erro.status_code, detalhe or TITULOS.get(erro.status_code, "Erro"))

    @app.exception_handler(ConfiguracaoAusente)
    async def _configuracao(_: Request, erro: ConfiguracaoAusente) -> JSONResponse:
        log.error("Configuração ausente: %s", erro)
        return problema(503, "O serviço ainda não foi configurado. Avise o administrador do ClimaSense.")

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, erro: Exception) -> JSONResponse:
        # Só o tipo vai para o log: mensagens de drivers podem conter a string de conexão.
        log.error("Erro inesperado (%s)", type(erro).__name__)
        return problema(500, "Algo deu errado do nosso lado. Tente de novo em alguns minutos.")
