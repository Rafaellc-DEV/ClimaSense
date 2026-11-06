from fastapi.testclient import TestClient

from climasense.api.main import criar_app
from tests.conftest import configuracao_teste


def test_mensagens_de_validacao_em_portugues_e_limites_de_abrigo():
    from pydantic import ValidationError

    from climasense.api.erros import _mensagem
    from climasense.api.routers.abrigos import PedidoAbrigo

    try:
        PedidoAbrigo(nome="x", bairro_id="b", capacidade=100_001, observacao="a" * 1001)
    except ValidationError as erro:
        msgs = {e["loc"][0]: _mensagem(e) for e in erro.errors()}
    assert msgs["capacidade"] == "O valor não pode ser maior que 100000."
    assert msgs["observacao"] == "O texto não pode ter mais de 1000 caracteres."
    assert (
        PedidoAbrigo(nome="x", bairro_id="b", capacidade=100_000, pessoas_abrigadas=0).capacidade == 100_000
    )


def test_resposta_422_traz_mensagem_em_portugues():
    c = TestClient(criar_app(configuracao_teste()))
    r = c.post("/api/v1/auth/entrar", json={"email": "a@b.co"})
    assert r.status_code == 422
    assert r.json()["campos"][0]["mensagem"] == "Campo obrigatório."
