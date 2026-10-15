"""Conexão e índices do Atlas. O cliente do Atlas é substituído pelo mongomock (banco em memória),
mas os documentos usados são os distritos REAIS de data/territorio."""

import copy

import mongomock
import pytest
from pymongo.errors import DuplicateKeyError

from climasense.infra import mongo
from tests.conftest import configuracao_teste

URI = "mongodb+srv://usuario:segredo@cluster.exemplo.invalid/"


def test_conectar_usa_o_mesmo_padrao_do_mapa_da_aula_07():
    chamadas = {}

    def fabrica(uri, **kw):
        chamadas.update(uri=uri, **kw)
        return "cliente"

    assert mongo.conectar(configuracao_teste(mongo_uri=URI), fabrica=fabrica) == "cliente"
    assert chamadas["uri"] == URI
    assert chamadas["server_api"].version == "1"
    assert chamadas["tlsCAFile"].endswith(".pem")
    assert chamadas["serverSelectionTimeoutMS"] == 15000


def test_conectar_sem_uri_explica_o_que_fazer():
    with pytest.raises(Exception, match="Configure MONGO_URI no arquivo .env."):
        mongo.conectar(configuracao_teste(), fabrica=lambda *a, **k: None)


def test_indice_unico_por_codigo_impede_distrito_duplicado(distritos_oficiais):
    cfg = configuracao_teste()
    cliente = mongomock.MongoClient()
    mongo.criar_indices(cliente, cfg)
    colecao = cliente[cfg.mongo_db_territorio][mongo.COLECAO_DISTRITOS]
    colecao.insert_many(copy.deepcopy(distritos_oficiais))
    assert colecao.count_documents({}) == 8
    with pytest.raises(DuplicateKeyError):
        colecao.insert_one(copy.deepcopy(distritos_oficiais[0]))
