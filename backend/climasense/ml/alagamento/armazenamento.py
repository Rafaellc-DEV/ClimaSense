"""Arquivo do modelo treinado (joblib), fora do Git. A API só LÊ este arquivo; nunca treina na requisição.

Local padrão: `tmp/modelos/risco-alagamento-v{versao}.joblib` na raiz do repositório (pasta `tmp/` já é
ignorada). Pode ser trocado pela variável de ambiente `CLIMASENSE_MODELO_ALAGAMENTO` (caminho do arquivo).
"""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import joblib
import sklearn

from climasense.config import RAIZ_REPOSITORIO
from climasense.ml.alagamento.base import ATRIBUTOS, VERSAO_ATRIBUTOS
from climasense.ml.alagamento.modelo import METODO, VERSAO, Artefato, avaliar_publicacao

log = logging.getLogger(__name__)

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
    try:
        # Somente arquivos locais produzidos pela rotina confiável de treinamento.
        artefato = joblib.load(caminho)
        return artefato if compativel(artefato) else None
    except Exception as erro:  # noqa: BLE001 — artefato inválido não derruba a aplicação; sem conteúdo em logs
        log.warning("Artefato de alagamento indisponível (%s)", type(erro).__name__)
        return None


def compativel(art) -> bool:
    """Recusa inclusive artefatos antigos: precisam ser reavaliados com o contrato corrigido."""
    if not isinstance(art, Artefato) or art.__dict__.get("versao_atributos") != VERSAO_ATRIBUTOS:
        return False
    try:
        if not isinstance(art.validacao, dict) or not isinstance(art.motivo, str | type(None)):
            return False
        datetime.fromisoformat(art.treinado_em)
        if art.publicavel:
            perf = {
                "treino": {"positivos": art.validacao["positivos_treino"]},
                "teste": {"positivos": art.validacao["positivos_teste"]},
            }
            ok, _ = avaliar_publicacao(perf, art.validacao["metricas_teste"])
            if not ok or art.validacao.get("avaliacao_operacional") is not True:
                return False
        return (
            art.versao == VERSAO
            and art.metodo == METODO
            and bool(art.atributos)
            and art.atributos == [c for c in ATRIBUTOS if c in art.atributos]
            and list(art.modelo.feature_names_in_) == art.atributos
            and list(art.modelo.classes_) == [0, 1]
            and all(math.isfinite(art.limiares[k]) for k in ("alto", "moderado"))
            and 0 <= art.limiares["moderado"] <= art.limiares["alto"] <= 1
            and bool(art.territorios)
            and art.ambiente.get("scikit-learn") == sklearn.__version__
        )
    except (AttributeError, TypeError, KeyError, ValueError):
        return False


@lru_cache(maxsize=4)
def _cache(caminho: str, mtime: float) -> Artefato | None:
    return carregar(Path(caminho))


def carregar_em_cache(caminho: Path | None = None) -> Artefato | None:
    """Recarrega só quando o arquivo muda (data de modificação)."""
    caminho = Path(caminho or caminho_padrao())
    try:
        mtime = caminho.stat().st_mtime
    except OSError:
        return None
    return _cache(str(caminho), mtime)
