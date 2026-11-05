r"""Recalcula a gold a partir da silver e compara com o gravado (CA-04). Sai com 0 se tudo bate.

Uso (da raiz):  .venv\Scripts\python scripts/verificar_gold.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from climasense.config import obter_configuracao  # noqa: E402
from climasense.etl import gold  # noqa: E402
from climasense.infra.postgres import engine_da_configuracao  # noqa: E402


def main() -> int:
    engine = engine_da_configuracao(obter_configuracao())
    with engine.connect() as c:
        diferencas = gold.verificar(c)
    for tabela, n in diferencas.items():
        print(f"{tabela}: {'ok' if n == 0 else f'{n} linhas diferentes'}")
    return 0 if not any(diferencas.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
