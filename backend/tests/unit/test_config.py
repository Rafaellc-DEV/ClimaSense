import pytest

from climasense.config import ConfiguracaoAusente
from tests.conftest import configuracao_teste

URI = "mongodb+srv://usuario:segredo-real@cluster.exemplo.invalid/"


def test_sem_mongo_uri_a_mensagem_e_clara_e_nao_vaza_nada():
    cfg = configuracao_teste()
    with pytest.raises(ConfiguracaoAusente) as erro:
        cfg.exigir("mongo_uri")
    assert str(erro.value) == "Configure MONGO_URI no arquivo .env."


def test_segredos_nao_aparecem_em_repr_nem_em_str():
    cfg = configuracao_teste(mongo_uri=URI, database_url="postgresql://u:senha-real@h.invalid/db")
    for texto in (repr(cfg), str(cfg), str(cfg.model_dump())):
        assert "segredo-real" not in texto
        assert "senha-real" not in texto
    assert cfg.exigir("mongo_uri") == URI


def test_neon_url_e_sinonimo_de_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("NEON_URL", "postgresql://u:s@neon.invalid/db")
    from climasense.config import Configuracao

    assert Configuracao(_env_file=None).exigir("database_url") == "postgresql://u:s@neon.invalid/db"


def test_variavel_vazia_conta_como_ausente():
    cfg = configuracao_teste(mongo_uri="   ")
    assert cfg.mongo_uri is None


def test_cors_aceita_lista_separada_por_virgula(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://climasense.exemplo")
    from climasense.config import Configuracao

    assert Configuracao(_env_file=None).cors_origins == [
        "http://localhost:5173",
        "https://climasense.exemplo",
    ]
