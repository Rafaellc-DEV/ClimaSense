"""Arquivo do modelo treinado (joblib), fora do Git. A API só LÊ este arquivo; nunca treina na requisição.

Local padrão: `tmp/modelos/risco-alagamento-v{versao}.joblib` na raiz do repositório (pasta `tmp/` já é
ignorada). Pode ser trocado pela variável de ambiente `CLIMASENSE_MODELO_ALAGAMENTO` (caminho do arquivo).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import joblib

from climasense.config import RAIZ_REPOSITORIO
from climasense.ml.alagamento.modelo import VERSAO, Artefato

VARIAVEL_AMBIENTE = "CLIMASENSE_MODELO_ALAGAMENTO"


def caminho_padrao() -> Path:
    escolhido = os.environ.get(VARIAVEL_AMBIENTE)
    if escolhido:
        return Path(escolhido)
    return RAIZ_REPOSITORIO / "tmp" / "modelos" / f"risco-alagamento-v{VERSAO}.joblib"


def salvar(artefato: Artefato, caminho: Path | None = None) -> Path:
    caminho = Path(caminho or caminho_padrao())
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefato, caminho)
    _cache.cache_clear()
    return caminho


def carregar(caminho: Path | None = None) -> Artefato | None:
    """None quando não há modelo treinado (o produto mostra `disponivel: false`)."""
    caminho = Path(caminho or caminho_padrao())
    if not caminho.exists():
        return None
    artefato = joblib.load(caminho)
    return artefato if isinstance(artefato, Artefato) else None


@lru_cache(maxsize=4)
def _cache(caminho: str, mtime: float) -> Artefato | None:
    return carregar(Path(caminho))


def carregar_em_cache(caminho: Path | None = None) -> Artefato | None:
    """Recarrega só quando o arquivo muda (data de modificação)."""
    caminho = Path(caminho or caminho_padrao())
    if not caminho.exists():
        return None
    return _cache(str(caminho), caminho.stat().st_mtime)
