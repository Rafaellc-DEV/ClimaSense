"""Registros no formato da API CKAN do conjunto “perfil das pessoas vacinadas — COVID-19” (Dados Abertos do Recife).
Os valores seguem os exemplos documentados no próprio ETL original (Projeto-ETL_AVD/src/transformer.py)."""

REGISTROS = [
    {
        "_id": 1,
        "faixa_etaria": " 60 a 69 anos ",
        "idade": "64",
        "sexo": "feminino",
        "raca_cor": "PARDA",
        "municipio": "RECIFE",
        "grupo": "IDOSOS",
        "categoria": "Faixa Etária",
        "lote": "fp8743",
        "vacina_fabricante": "3 - COMIRNATY (PFIZER)",
        "descricao_dose": "3",
        "cnes": "DS 4: CNES: 0000639 - UBS JOAQUIM CAVALCANTE",
        "sistema_origem": "conecta recife",
        "data_vacinacao": "2022-03-15",
    },
    {
        "_id": 2,
        "faixa_etaria": "30 a 39 anos",
        "idade": "",
        "sexo": "MASCULINO",
        "raca_cor": "",
        "municipio": "RECIFE",
        "grupo": "",
        "categoria": "",
        "lote": "",
        "vacina_fabricante": "3 - COMIRNATY (PFIZER)",
        "descricao_dose": "1",
        "cnes": "DS 4: CNES: 0000639 - UBS JOAQUIM CAVALCANTE",
        "sistema_origem": "conecta recife",
        "data_vacinacao": "2022-03-15",
    },
    {
        "_id": 3,
        "faixa_etaria": " 60 a 69 anos ",
        "idade": "64",
        "sexo": "feminino",
        "raca_cor": "PARDA",
        "municipio": "RECIFE",
        "grupo": "IDOSOS",
        "categoria": "Faixa Etária",
        "lote": "fp8743",
        "vacina_fabricante": "3 - COMIRNATY (PFIZER)",
        "descricao_dose": "3",
        "cnes": "DS 4: CNES: 0000639 - UBS JOAQUIM CAVALCANTE",
        "sistema_origem": "conecta recife",
        "data_vacinacao": "2022-03-15",
    },
    {
        "_id": 4,
        "faixa_etaria": "18 a 29 anos",
        "idade": "25",
        "sexo": "MASCULINO",
        "raca_cor": "PRETA",
        "municipio": "RECIFE",
        "grupo": "ADULTOS",
        "categoria": "Faixa Etária",
        "lote": "ab1234",
        "vacina_fabricante": "3 - COMIRNATY (PFIZER)",
        "descricao_dose": "2",
        "cnes": "DS 4: CNES: 0000639 - UBS JOAQUIM CAVALCANTE",
        "sistema_origem": "conecta recife",
        "data_vacinacao": "data inválida",
    },
]


class HttpCkan:
    """Responde como a API CKAN (paginação por offset). Dublê de rede: a internet não é usada nos testes."""

    def __init__(self, registros, total=None):
        self.registros, self.total, self.pedidos = registros, total or len(registros), []

    def get(self, url, params, timeout):
        self.pedidos.append(params)
        pagina = self.registros[params["offset"] : params["offset"] + params["limit"]]
        corpo = {"result": {"records": pagina, "total": self.total}}
        return type("R", (), {"json": lambda s: corpo, "raise_for_status": lambda s: None})()
