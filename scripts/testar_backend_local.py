r"""pytest isolado: nunca lê .env nem herda URLs de bancos do grupo.

Uso: .venv\Scripts\python scripts/testar_backend_local.py [--postgres-local] [argumentos do pytest]
--postgres-local usa SOMENTE climasense_teste em 127.0.0.1:55432 (descartável).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
for variavel in (
    "DATABASE_URL",
    "DATABASE_URL_MIGRACOES",
    "DATABASE_URL_TESTE",
    "NEON_URL",
    "MONGO_URI",
):
    os.environ.pop(variavel, None)
os.environ["AMBIENTE"] = "teste"
argumentos = sys.argv[1:]
if "--postgres-local" in argumentos:
    argumentos.remove("--postgres-local")
    os.environ["DATABASE_URL_TESTE"] = (
        "postgresql://climasense@127.0.0.1:55432/climasense_teste"
    )

from climasense.config import Configuracao

Configuracao.model_config["env_file"] = None

import pytest

if __name__ == "__main__":
    os.chdir(RAIZ / "backend")
    raise SystemExit(pytest.main(argumentos or ["-q"]))
