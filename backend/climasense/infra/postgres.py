"""Conexão com o Postgres (Neon na nuvem ou local) — T2.3."""

from __future__ import annotations

import contextvars
import time
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event, exc, text
from sqlalchemy.orm import Session, sessionmaker

from climasense.config import Configuracao, obter_configuracao


def normalizar_url(url: str) -> str:
    """Aceita `postgres://` e `postgresql://` (formato do Neon) e usa o driver psycopg2 do ETL anterior."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


# Com o banco a ~150 ms de distância, o `pre_ping` a cada empréstimo custa uma ida e volta por requisição. A
# conexão só é testada se ficou parada mais que isto (o Neon derruba conexões ociosas); em uso contínuo, não.
PING_APOS_OCIOSA_S = 20.0
RECICLAR_APOS_S = 1800


def _ping_se_ociosa(dbapi_conexao, registro, proxy) -> None:
    ultimo = registro.info.get("ultimo_uso")
    if ultimo is not None and time.monotonic() - ultimo < PING_APOS_OCIOSA_S:
        return
    try:
        cursor = dbapi_conexao.cursor()
        try:
            cursor.execute("select 1")
        finally:
            cursor.close()
        dbapi_conexao.rollback()
    except Exception as erro:  # noqa: BLE001 — conexão morta: o pool descarta e abre outra
        raise exc.DisconnectionError() from erro


def _marcar_uso(dbapi_conexao, registro) -> None:
    registro.info["ultimo_uso"] = time.monotonic()


def criar_engine(url: str) -> Engine:
    engine = create_engine(
        normalizar_url(url),
        pool_pre_ping=False,  # substituído por `_ping_se_ociosa` (só testa conexão parada há mais de 20 s)
        pool_size=5,
        max_overflow=5,
        pool_recycle=RECICLAR_APOS_S,
        connect_args={"connect_timeout": 15},
    )
    event.listen(engine, "checkout", _ping_se_ociosa)
    event.listen(engine, "checkin", _marcar_uso)
    event.listen(
        engine, "connect", _marcar_uso
    )  # conexão recém-aberta já está viva: sem ping no primeiro uso
    return engine


@lru_cache
def _engine_padrao(url: str) -> Engine:
    return criar_engine(url)


def engine_da_configuracao(config: Configuracao | None = None) -> Engine:
    config = config or obter_configuracao()
    return _engine_padrao(config.exigir("database_url"))


def url_do_dono(config: Configuracao) -> str:
    """URL de quem é dono do esquema (Alembic, ETL, carga do território). Sem ela, usa a da aplicação (ADR 0014)."""
    if config.database_url_migracoes is not None:
        return config.database_url_migracoes.get_secret_value()
    return config.exigir("database_url")


def engine_do_dono(config: Configuracao | None = None) -> Engine:
    """Engine com a URL do dono: escreve em silver/gold e altera o esquema. Não use nas rotas da API."""
    return _engine_padrao(url_do_dono(config or obter_configuracao()))


def fabrica_sessoes(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao() -> Iterator[Session]:
    """Dependência FastAPI: uma sessão por requisição, com commit explícito nos serviços."""
    sessao = fabrica_sessoes(engine_da_configuracao())()
    try:
        yield sessao
    finally:
        sessao.close()


def verificar(engine: Engine) -> bool:
    with engine.connect() as conexao:
        return conexao.execute(text("select 1")).scalar() == 1


def em_paralelo(db: Session, tarefas: list):
    """Executa tarefas de LEITURA independentes e devolve os resultados na mesma ordem. Cada tarefa recebe uma
    `Session` e devolve algo; com o banco a ~150 ms por consulta, rodar as leituras ao mesmo tempo custa o tempo da
    mais lenta, não a soma.

    Só paraleliza quando a sessão da requisição está ligada a um `Engine` (produção): cada tarefa usa a própria
    conexão do pool. Com a sessão ligada a uma conexão única (testes, que desfazem a transação no fim) ou com uma
    só tarefa, roda em sequência na própria `db`. Nunca use com escrita."""
    if len(tarefas) < 2 or not isinstance(db.get_bind(), Engine) or db.info.get("em_paralelo"):
        return [t(db) for t in tarefas]  # (sessão de tarefa paralela não abre outro nível: esgotaria o pool)
    from concurrent.futures import ThreadPoolExecutor

    engine = db.get_bind()

    def executar(tarefa):
        with fabrica_sessoes(engine)() as sessao:
            sessao.info["em_paralelo"] = True
            return tarefa(sessao)

    with ThreadPoolExecutor(max_workers=min(len(tarefas), 4)) as pool:
        # cada tarefa herda o contexto de quem chamou (ex.: o modo "renovando" do cache)
        futuros = [pool.submit(contextvars.copy_context().run, executar, t) for t in tarefas]
        return [f.result() for f in futuros]
