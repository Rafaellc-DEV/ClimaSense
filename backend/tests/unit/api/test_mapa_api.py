"""O mapa interno da API é reproduzível e cobre as rotas de apoio à decisão."""

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]


def test_gerador_cobre_rotas_novas_e_e_deterministico():
    spec = importlib.util.spec_from_file_location("gerar_mapa_api", RAIZ / "scripts" / "gerar_mapa_api.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    texto = modulo.gerar()
    for rota in ("/api/v1/painel/resumo", "/api/v1/territorios/prioridades"):
        assert f"`{rota}`" in texto
    assert texto == modulo.gerar()
