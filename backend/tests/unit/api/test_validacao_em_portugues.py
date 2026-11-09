from fastapi.testclient import TestClient

from climasense.api.main import criar_app
from tests.conftest import configuracao_teste


def test_mensagens_de_validacao_em_portugues_e_limites_de_acao_e_cenario():
    from pydantic import ValidationError

    from climasense.api.erros import _mensagem
    from climasense.api.routers.acoes import PedidoAcao
    from climasense.api.routers.cenarios import PedidoSimulacao

    try:
        PedidoAcao(territorio_id="b", tipo="visita", descricao="a" * 2001)
    except ValidationError as erro:
        msgs = {e["loc"][0]: _mensagem(e) for e in erro.errors()}
    assert msgs["descricao"] == "O texto não pode ter mais de 2000 caracteres."
    try:
        PedidoSimulacao(
            chuva_prevista_mm=601, duracao_h=1, chuva_acumulada_mm=None, mare_m=None, horizonte_h=24
        )
    except ValidationError as erro:
        msgs = {e["loc"][0]: _mensagem(e) for e in erro.errors()}
    assert msgs["chuva_prevista_mm"] == "O valor não pode ser maior que 600.0."


def test_resposta_422_traz_mensagem_em_portugues():
    c = TestClient(criar_app(configuracao_teste()))
    r = c.post("/api/v1/auth/entrar", json={"email": "a@b.co"})
    assert r.status_code == 422
    assert r.json()["campos"][0]["mensagem"] == "Campo obrigatório."
