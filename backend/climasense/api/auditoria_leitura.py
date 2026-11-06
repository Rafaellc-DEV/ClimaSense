"""Auditoria da leitura de dados de saúde (RNF-01, ADR 0010 item 5): quem, quando e qual rota.

Uma inserção em `app.auditoria` por requisição, na mesma sessão da requisição. Nunca grava o corpo da resposta nem
dados de pessoas: só o método, o caminho e os nomes e valores da consulta (filtros como agravo e ano).
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.infra.repositorios.auditoria import RepositorioAuditoria

LEITURA_DADOS_SAUDE = "leitura_dados_saude"
LEITURA_BOLETIM = "leitura_boletim"
_consultar = exige(Permissao.CONSULTAR)


def auditar_leitura(acao: str) -> Callable[..., None]:
    def dependencia(
        request: Request, ctx: Contexto = Depends(_consultar), db: Session = Depends(obter_sessao)
    ) -> None:
        RepositorioAuditoria(db).registrar(
            acao,
            usuario_id=ctx.usuario.id,
            alvo_tipo="rota",
            alvo_id=request.url.path[:200],
            detalhes={
                "metodo": request.method,
                "consulta": {k: v[:100] for k, v in request.query_params.items()},
            },
            ip=ctx.ip,
        )
        db.commit()

    dependencia.__name__ = f"auditar_{acao}"
    return dependencia
