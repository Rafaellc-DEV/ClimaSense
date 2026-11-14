"""Contrato para geração offline de tipos, sem banco e independente das flags locais."""

import json
import runpy

from climasense.api.main import FUNCOES
from climasense.config import RAIZ_REPOSITORIO


def test_contrato_versionado_corresponde_ao_exportador(monkeypatch):
    for campo in FUNCOES:
        monkeypatch.setenv(campo.upper(), "false")
    exportador = runpy.run_path(str(RAIZ_REPOSITORIO / "scripts" / "exportar_openapi.py"))
    contrato = json.loads(exportador["gerar"]())
    arquivo = RAIZ_REPOSITORIO / "docs" / "api" / "openapi.json"
    assert contrato == json.loads(arquivo.read_text(encoding="utf-8"))
    assert "/api/v1/risco-alagamento/previa-local" in contrato["paths"]
    assert "/api/v1/cenarios/impacto-previsto" in contrato["paths"]
    assert "/api/v1/publico/avisos" in contrato["paths"]
