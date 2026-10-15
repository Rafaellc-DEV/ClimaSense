"""A regra de dependência das camadas (design §2.2) verificada no código:
o domínio é puro e não importa frameworks, bancos nem as outras camadas."""

import ast
from pathlib import Path

import pytest

PACOTE = Path(__file__).resolve().parents[2] / "climasense"
PROIBIDOS_NO_DOMINIO = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "pymongo",
    "requests",
    "pandas",
    "alembic",
    "climasense.api",
    "climasense.infra",
    "climasense.servicos",
    "climasense.etl",
    "climasense.auth",
}


def _imports(arquivo: Path) -> set[str]:
    nomes = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes |= {a.name for a in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
    return nomes


@pytest.mark.parametrize("arquivo", sorted((PACOTE / "dominio").glob("*.py")), ids=lambda p: p.name)
def test_dominio_nao_depende_de_infraestrutura(arquivo):
    violacoes = {
        i for i in _imports(arquivo) for p in PROIBIDOS_NO_DOMINIO if i == p or i.startswith(p + ".")
    }
    assert not violacoes, f"{arquivo.name} importa {violacoes}"


@pytest.mark.parametrize("arquivo", sorted((PACOTE / "infra").rglob("*.py")), ids=lambda p: p.name)
def test_infra_nao_depende_da_api(arquivo):
    assert not {i for i in _imports(arquivo) if i.startswith("climasense.api")}
