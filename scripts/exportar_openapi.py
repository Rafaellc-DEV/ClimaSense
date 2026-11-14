"""Exporta o contrato OpenAPI gerado pelo FastAPI para docs/api/openapi.json.

O contrato é o que a própria API gera, com todas as funcionalidades opcionais ligadas
para gerar os tipos do frontend sem depender das flags locais. A publicação real da API
continua respeitando suas flags. Não conecta a banco nem sobe servidor.

Uso (a partir da raiz do repositório):
    .venv\\Scripts\\python scripts/exportar_openapi.py            grava docs/api/openapi.json
    .venv\\Scripts\\python scripts/exportar_openapi.py --verificar  falha (código 1) se o arquivo estiver desatualizado
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
os.environ.setdefault("AMBIENTE", "teste")
warnings.filterwarnings("ignore")

from climasense.api.main import FUNCOES, criar_app  # noqa: E402
from climasense.config import Configuracao  # noqa: E402

SAIDA = RAIZ / "docs" / "api" / "openapi.json"


def gerar() -> str:
    app = criar_app(Configuracao(_env_file=None, ambiente="teste", **dict.fromkeys(FUNCOES, True)))
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main() -> int:
    conteudo = gerar()
    if "--verificar" in sys.argv:
        atual = SAIDA.read_text(encoding="utf-8") if SAIDA.exists() else ""
        if atual != conteudo:
            print(f"{SAIDA.relative_to(RAIZ)} está desatualizado. Rode scripts/exportar_openapi.py.")
            return 1
        print("Contrato OpenAPI em dia.")
        return 0
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(conteudo, encoding="utf-8", newline="\n")
    rotas = sum(len(v) for v in json.loads(conteudo)["paths"].values())
    print(f"{SAIDA.relative_to(RAIZ)}: {rotas} operações.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
