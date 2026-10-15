"""Cabeçalhos de segurança aplicados a todas as respostas (RNF-SEG)."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CSP = (
    "default-src 'self'; img-src 'self' data: https://server.arcgisonline.com; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
    "font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


class CabecalhosSeguranca(BaseHTTPMiddleware):
    def __init__(self, app, producao: bool) -> None:
        super().__init__(app)
        self.producao = producao

    async def dispatch(self, request: Request, call_next) -> Response:
        resposta = await call_next(request)
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        if not request.url.path.startswith("/api/docs"):
            resposta.headers.setdefault("Content-Security-Policy", CSP)
        if self.producao:
            resposta.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resposta
