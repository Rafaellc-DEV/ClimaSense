"""Cache em memória com TTL curto para leituras caras contra o banco remoto (latência alta por consulta).

Regras de uso (RF-19, RN-01, RN-02, RN-13):
- só entram aqui dados AGREGADOS e iguais para todos os usuários (nunca algo que dependa de quem pergunta);
- a chave leva todos os parâmetros que mudam o resultado;
- dado ausente (None) também é guardado, mas pelo mesmo TTL curto: assim "Dados insuficientes" some assim que a
  carga chega, e nunca vira zero;
- o valor guardado é o mesmo objeto devolvido; quem chama não deve alterá-lo (devolva cópias ao mudar);
- dado que a própria API grava (declarações, ações, estágio oficial) NÃO passa por aqui, ou o serviço de escrita
  chama `limpar` do espaço dele.

TTLs: `VIVO_S` para o que muda por coleta (chuva, alertas, status das fontes); `CARGA_S` para o que só muda quando
o ETL carrega (população, malha, equipamentos, prioridade histórica, território).
"""

from __future__ import annotations

import contextvars
import threading
import time
from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

T = TypeVar("T")

VIVO_S = 60.0  # muda por coleta (chuva, alertas, status das fontes)
MEDIO_S = 180.0  # muda por carga do ETL que roda algumas vezes ao dia (ocorrências, saúde semanal)
CARGA_S = (
    600.0  # só muda quando alguém recarrega a base (território, população, equipamentos, áreas de risco)
)
MAX_ENTRADAS = 256

# Chave geral: os testes de integração desligam o cache (cada teste desfaz o banco, e o dado do anterior não pode
# aparecer no seguinte); os testes do próprio cache ligam de volta.
ativo = True

_relogio: Callable[[], float] = time.monotonic
_trava = threading.RLock()
_espacos: dict[str, dict[Hashable, tuple[float, Any]]] = {}


_renovando: contextvars.ContextVar[bool] = contextvars.ContextVar("cache_renovando", default=False)


@contextmanager
def renovando() -> Iterator[None]:
    """Dentro do bloco, `obter` ignora o que está guardado e recalcula (o aquecimento em segundo plano usa isto para
    renovar o cache ANTES de ele vencer). Vale só para quem roda dentro do bloco, inclusive as tarefas de
    `em_paralelo`, que herdam o contexto."""
    marca = _renovando.set(True)
    try:
        yield
    finally:
        _renovando.reset(marca)


def obter[T](espaco: str, chave: Hashable, ttl_s: float, fabrica: Callable[[], T]) -> T:
    """Devolve o valor guardado em (`espaco`, `chave`) se ainda vale; senão chama `fabrica` e guarda.
    `ttl_s <= 0` desliga o cache. Falha da fábrica não guarda nada."""
    if ttl_s <= 0 or not ativo:
        return fabrica()
    agora = _relogio()
    with _trava:
        guardado = _espacos.get(espaco, {}).get(chave)
    if guardado is not None and agora - guardado[0] < ttl_s and not _renovando.get():
        return guardado[1]
    valor = fabrica()
    with _trava:
        entradas = _espacos.setdefault(espaco, {})
        if len(entradas) >= MAX_ENTRADAS:
            entradas.clear()
        entradas[chave] = (_relogio(), valor)
    return valor


def limpar(espaco: str | None = None) -> None:
    """Esquece um espaço (ou tudo). Usado depois de escrita e entre testes."""
    with _trava:
        if espaco is None:
            _espacos.clear()
        else:
            _espacos.pop(espaco, None)
