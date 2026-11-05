"""Registros reais no formato da API CKAN (datastore_search) do conjunto “abrigos-temporarios-disponiveis”
(Dados Abertos do Recife), gravados em 04/11/2026 em `fixtures/`, e um dublê HTTP com paginação por offset."""

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
REGISTROS = json.loads((FIXTURES / "ckan_abrigos_datastore_2026-11-04.json").read_text(encoding="utf-8"))[
    "result"
]["records"]


class HttpCkan:
    """Responde como a API CKAN (paginação por offset). Dublê de rede: a internet não é usada nos testes."""

    def __init__(self, registros, total=None):
        self.registros, self.total, self.pedidos = registros, total or len(registros), []

    def get(self, url, params, timeout):
        self.pedidos.append(params)
        pagina = self.registros[params["offset"] : params["offset"] + params["limit"]]
        corpo = {"result": {"records": pagina, "total": self.total}}
        return type("R", (), {"json": lambda s: corpo, "raise_for_status": lambda s: None})()
