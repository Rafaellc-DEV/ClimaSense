"""Extract — porte da classe do Projeto-ETL_AVD (mesmos métodos: ler_api e ler_bronze)."""

from __future__ import annotations

import pandas as pd
import requests


class Extract:
    """Lê os dados: da API da Prefeitura (CKAN) ou da camada BRONZE (MongoDB Atlas)."""

    def __init__(self, url_api: str, resource_id: str, limite: int, por_pagina: int = 500, http=None) -> None:
        self.url_api = url_api
        self.resource_id = resource_id
        self.limite = limite
        self.por_pagina = por_pagina
        self.http = http or requests.Session()
        self.total_fonte: int | None = None

    def ler_api(self) -> list[dict]:
        registros: list[dict] = []
        offset = 0
        # a API devolve no máximo 500 registros por vez, então pedimos página por página
        while len(registros) < self.limite:
            params = {
                "resource_id": self.resource_id,
                "limit": min(self.por_pagina, self.limite - len(registros)),
                "offset": offset,
            }
            resposta = self.http.get(self.url_api, params=params, timeout=60)
            resposta.raise_for_status()
            resultado = resposta.json()["result"]
            self.total_fonte = resultado.get("total", self.total_fonte)
            pagina = resultado["records"]
            if len(pagina) == 0:
                break
            registros.extend(pagina)
            offset += self.por_pagina
            print(f"[extract] {len(registros)} registros baixados da API")
        return registros

    def ler_bronze(self, colecao, execucao_id: str) -> pd.DataFrame:
        """Só o lote da execução pedida, sem as colunas técnicas (como no original)."""
        documentos = list(
            colecao.find(
                {"_execucao_id": execucao_id}, {"_id": 0, "_data_carga": 0, "_execucao_id": 0, "_fonte": 0}
            )
        )
        print(f"[extract] {len(documentos)} documentos lidos da bronze")
        return pd.DataFrame(documentos)
