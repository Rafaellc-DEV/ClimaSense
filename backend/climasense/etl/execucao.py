"""Executa um conector e registra a execução em app.etl_execucoes (RF-12.5). Falhas viram status “falha”
com uma mensagem sem segredos; a bronze e a silver anteriores ficam intactas (RF-12.8)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from climasense.config import Configuracao
from climasense.etl.conectores import CONECTORES
from climasense.etl.conectores.base import ConectorPlanejado, ExecucaoCtx

MENSAGENS = {
    "ConnectionError": "A fonte não respondeu. Confira a internet e tente de novo.",
    "HTTPError": "A fonte respondeu com erro. Tente de novo mais tarde.",
    "Timeout": "A fonte demorou demais para responder.",
    "IntegrityError": "Os dados não puderam ser gravados: rode antes a carga territorial (python -m climasense.territorio carregar).",
    "ServerSelectionTimeoutError": "O MongoDB Atlas não respondeu. Confira MONGO_URI e o acesso de rede no Atlas.",
    "NetworkTimeout": "O MongoDB Atlas demorou demais para gravar. Tente de novo; se repetir, use --limite menor.",
}


log = logging.getLogger(__name__)
FONTE_TERRITORIO = "territorio-oficial"  # carga pelo módulo territorio, sem conector do ETL


def iniciar(engine: Engine, fonte_id: str, disparado_por: uuid.UUID | None = None) -> str:
    if fonte_id not in CONECTORES and fonte_id != FONTE_TERRITORIO:
        raise KeyError(f"Fonte “{fonte_id}” não existe. Fontes: {', '.join(sorted(CONECTORES))}.")
    with engine.begin() as c:
        return str(
            c.execute(
                text(
                    "insert into app.etl_execucoes (fonte_id, status, disparado_por) values (:f, 'em_andamento', :u) "
                    "returning id"
                ),
                {"f": fonte_id, "u": disparado_por},
            ).scalar_one()
        )


def concluir(
    engine: Engine, execucao_id: str, lidos: int = 0, gravados: int = 0, erro: str | None = None
) -> None:
    """Fecha uma execução feita fora de um conector (ex.: a carga territorial pelo terminal)."""
    with engine.begin() as c:
        c.execute(
            text(
                "update app.etl_execucoes set fim = now(), status = :s, lidos = :l, gravados = :g, erro = :e "
                "where id = :i"
            ),
            {"s": "falha" if erro else "sucesso", "l": lidos, "g": gravados, "e": erro, "i": execucao_id},
        )


def executar(
    engine: Engine,
    mongo,
    config: Configuracao,
    fonte_id: str,
    execucao_id: str,
    limite: int | None = None,
    conector=None,
) -> dict:
    conector = conector or CONECTORES[fonte_id]()
    ctx = ExecucaoCtx(
        execucao_id=execucao_id,
        config=config,
        mongo=mongo,
        engine=engine,
        agora=datetime.now(UTC),
        limite=limite,
    )
    try:
        r = conector.executar(ctx)
        status, erro, dados = "sucesso", None, (r.lidos, r.gravados, r.descartados, r.motivos)
    except ConectorPlanejado as e:
        status, erro, dados = "falha", str(e), (0, 0, 0, {})
    except Exception as e:  # noqa: BLE001 — só o tipo e uma mensagem amigável; nunca a string de conexão
        log.warning("Execução %s de %s falhou: %s", execucao_id, fonte_id, type(e).__name__)
        status, erro, dados = (
            "falha",
            MENSAGENS.get(type(e).__name__, f"Falha inesperada ({type(e).__name__})."),
            (0, 0, 0, {}),
        )
    with engine.begin() as c:
        c.execute(
            text(
                "update app.etl_execucoes set fim = now(), status = :s, lidos = :l, gravados = :g, descartados = :d, "
                "motivos_descarte = cast(:m as jsonb), erro = :e where id = :i"
            ),
            {
                "s": status,
                "l": dados[0],
                "g": dados[1],
                "d": dados[2],
                "m": json.dumps(dados[3]),
                "e": erro,
                "i": execucao_id,
            },
        )
    return {
        "execucao_id": execucao_id,
        "status": status,
        "lidos": dados[0],
        "gravados": dados[1],
        "descartados": dados[2],
        "erro": erro,
    }
