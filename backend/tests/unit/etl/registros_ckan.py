"""Registros de exemplo no formato da API CKAN (datastore_search) e um dublê HTTP com paginação por offset.
Dados de exemplo só para testes do extrator (a internet não é usada)."""

REGISTROS = [{"_id": n, "bairro": f"Bairro {n}", "valor": n * 10} for n in range(1, 18)]


class HttpCkan:
    """Responde como a API CKAN (paginação por offset). Dublê de rede: a internet não é usada nos testes."""

    def __init__(self, registros, total=None):
        self.registros, self.total, self.pedidos = registros, total or len(registros), []

    def get(self, url, params, timeout):
        self.pedidos.append(params)
        pagina = self.registros[params["offset"] : params["offset"] + params["limit"]]
        corpo = {"result": {"records": pagina, "total": self.total}}
        return type("R", (), {"json": lambda s: corpo, "raise_for_status": lambda s: None})()
