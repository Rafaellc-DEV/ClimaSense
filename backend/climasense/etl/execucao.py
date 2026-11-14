"""Executa um conector e registra a execução em app.etl_execucoes (RF-12.5). Falhas viram status “falha”
com uma mensagem sem segredos; a bronze e a silver anteriores ficam intactas (RF-12.8)."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime

import requests
from sqlalchemy import Engine, text

from climasense.config import Configuracao
from climasense.etl.conectores import CONECTORES
from climasense.etl.conectores.base import ConectorPlanejado, ExecucaoCtx, FonteSemDados

MENSAGENS = {
    "ConnectionError": "A fonte não respondeu. Confira a internet e tente de novo.",
    "HTTPError": "A fonte respondeu com erro. Tente de novo mais tarde.",
    "Timeout": "A fonte demorou demais para responder.",
    "IntegrityError": "Os dados não puderam ser gravados: rode antes a carga territorial (python -m climasense.territorio carregar).",
    "ServerSelectionTimeoutError": "O MongoDB Atlas não respondeu. Confira MONGO_URI e o acesso de rede no Atlas.",
    "NetworkTimeout": "O MongoDB Atlas demorou demais para gravar. Tente de novo; se repetir, use --limite menor.",
    "RetryError": "A fonte continuou indisponível após as tentativas limitadas. Tente mais tarde.",
    "OperationalError": "O PostgreSQL não está disponível ou recusou o acesso. Confira a conexão e as permissões.",
}


log = logging.getLogger(__name__)
FONTE_TERRITORIO = "territorio-oficial"  # carga pelo módulo territorio, sem conector do ETL
TRAVA_ETL = 1129072973
TRAVA_FONTE = 1129072974
TRAVA_TRABALHO = 1129072975


class ExecucaoEmAndamento(RuntimeError):
    """Não cria outra carga enquanto a anterior desta fonte não foi encerrada."""


def reservar(db, fonte_id: str, disparado_por: uuid.UUID | None = None) -> dict:
    """Reserva por fonte na transação do chamador; serve à API e ao terminal.

    Execuções abandonadas exigem recuperação explícita, nunca expiração automática.
    """
    chave = int.from_bytes(hashlib.sha256(fonte_id.encode()).digest()[:4], signed=True)
    livre = db.execute(
        text("select pg_try_advisory_xact_lock(:n, :f)"), {"n": TRAVA_FONTE, "f": chave}
    ).scalar_one()
    if (
        not livre
        or db.execute(
            text(
                "select exists(select 1 from app.etl_execucoes where fonte_id=:f and status='em_andamento')"
            ),
            {"f": fonte_id},
        ).scalar_one()
    ):
        raise ExecucaoEmAndamento(
            "Esta fonte já tem uma execução em andamento. Consulte o histórico antes de repetir."
        )
    return dict(
        db.execute(
            text(
                "insert into app.etl_execucoes (fonte_id,status,disparado_por) "
                "values (:f,'em_andamento',:u) returning *"
            ),
            {"f": fonte_id, "u": disparado_por},
        )
        .mappings()
        .one()
    )


@contextmanager
def exclusividade(engine: Engine, execucao_id: str):
    """Uma carga por banco, também entre processos. Trava transacional compatível com pooler.

    A transação dedicada só mantém a trava; gravações do conector usam suas próprias transações.
    """
    with engine.begin() as c:
        c.execute(text("set local idle_in_transaction_session_timeout = 0"))
        chave = int.from_bytes(hashlib.sha256(execucao_id.encode()).digest()[:4], signed=True)
        trabalho_livre = c.execute(
            text("select pg_try_advisory_xact_lock(:n, :i)"), {"n": TRAVA_TRABALHO, "i": chave}
        ).scalar_one()
        if not trabalho_livre:
            yield None  # a mesma tarefa já está sendo executada; não muda seu status
            return
        livre = c.execute(text("select pg_try_advisory_xact_lock(:n, 0)"), {"n": TRAVA_ETL}).scalar_one()
        if not livre:
            raise ExecucaoEmAndamento("Outra coleta está em execução. Aguarde a conclusão e tente novamente.")
        yield c


def mensagem_segura(erro: Exception) -> str:
    if isinstance(erro, (ConectorPlanejado, FonteSemDados, ExecucaoEmAndamento)):
        return str(erro)
    if isinstance(erro, requests.Timeout):
        return MENSAGENS["Timeout"]
    if isinstance(erro, requests.HTTPError) and erro.response is not None:
        return f"A fonte respondeu com HTTP {erro.response.status_code}. Tente novamente mais tarde."
    codigo = getattr(getattr(erro, "orig", None), "pgcode", None)
    if codigo == "42501":
        return "O PostgreSQL negou a gravação. Confira as permissões do executor do ETL."
    if codigo == "42P01":
        return "Uma tabela necessária não existe. Confira as migrações antes da carga."
    return MENSAGENS.get(type(erro).__name__, f"Falha inesperada ({type(erro).__name__}).")


def iniciar(engine: Engine, fonte_id: str, disparado_por: uuid.UUID | None = None) -> str:
    if fonte_id not in CONECTORES and fonte_id != FONTE_TERRITORIO:
        raise KeyError(f"Fonte “{fonte_id}” não existe. Fontes: {', '.join(sorted(CONECTORES))}.")
    with engine.begin() as c:
        return str(reservar(c, fonte_id, disparado_por)["id"])


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
    modo: str | None = None,
) -> dict:
    try:
        with exclusividade(engine, execucao_id) as c:
            if c is None:
                with engine.connect() as leitura:
                    anterior = (
                        leitura.execute(
                            text(
                                "select status,lidos,gravados,descartados,erro from app.etl_execucoes where id=:i"
                            ),
                            {"i": execucao_id},
                        )
                        .mappings()
                        .one()
                    )
                return {"execucao_id": execucao_id, **dict(anterior)}
            anterior = (
                c.execute(
                    text("select status,lidos,gravados,descartados,erro from app.etl_execucoes where id=:i"),
                    {"i": execucao_id},
                )
                .mappings()
                .one()
            )
            if anterior["status"] != "em_andamento":
                return {
                    "execucao_id": execucao_id,
                    **dict(anterior),
                }  # repetir o mesmo trabalho não duplica dados
            conector = conector or CONECTORES[fonte_id]()
            ctx = ExecucaoCtx(execucao_id, config, mongo, engine, datetime.now(UTC), limite, modo)
            try:
                r = conector.executar(ctx)
            finally:
                http = getattr(conector, "http", None)
                if hasattr(http, "close"):
                    http.close()
            status, erro, dados = "sucesso", None, (r.lidos, r.gravados, r.descartados, r.motivos)
            _registrar(engine, execucao_id, status, erro, dados)
            invalidar_leituras()
            return _resultado(execucao_id, status, erro, dados)
    except Exception as e:  # noqa: BLE001 — só o tipo e uma mensagem amigável; nunca a string de conexão
        log.warning("Execução %s de %s falhou: %s", execucao_id, fonte_id, type(e).__name__)
        status, erro, dados = (
            "falha",
            mensagem_segura(e),
            (0, 0, 0, {}),
        )
        parcial = getattr(conector, "resultado_execucao", None)
        if parcial is not None:
            dados = (parcial.lidos, parcial.gravados, parcial.descartados, parcial.motivos)
    _registrar(engine, execucao_id, status, erro, dados)
    invalidar_leituras()
    return _resultado(execucao_id, status, erro, dados)


def _registrar(engine, execucao_id, status, erro, dados):
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


def _resultado(execucao_id, status, erro, dados):
    return {
        "execucao_id": execucao_id,
        "status": status,
        "lidos": dados[0],
        "gravados": dados[1],
        "descartados": dados[2],
        "erro": erro,
    }


def invalidar_leituras() -> None:
    """Invalida este processo. Outras instâncias renovam pelos TTLs existentes (até 60 s para clima)."""
    from climasense.infra import cache
    from climasense.servicos import simulador

    cache.limpar()
    simulador.limpar_cache()


def executar_preparado(config, fonte_id, execucao_id, limite=None, obter_mongo=None):
    """Inclui inicialização dos clientes no tratamento de falhas da tarefa da API."""
    from climasense.infra.postgres import engine_da_configuracao, engine_do_dono

    try:
        engine = engine_do_dono(config)
        mongo = obter_mongo()
        return executar(engine, mongo, config, fonte_id, execucao_id, limite)
    except Exception as erro:  # noqa: BLE001 — não expõe URI nem detalhes de autenticação
        log.warning("Inicialização/finalização do ETL falhou: %s", type(erro).__name__)
        try:
            concluir(engine_da_configuracao(config), execucao_id, erro=mensagem_segura(erro))
            invalidar_leituras()
        except Exception as falha:  # noqa: BLE001 — banco indisponível exige recuperação pelo operador
            log.error("Não foi possível encerrar execução %s (%s).", execucao_id, type(falha).__name__)
