import pytest
from sqlalchemy import text

from tests.conftest import precisa_postgres
from tests.integration.apoio import SENHA, Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]


@pytest.fixture
def relogio():
    return Relogio()


@pytest.fixture
def c(sessao, relogio):
    return cliente(sessao, relogio)


def test_entrar_define_cookies_seguros_e_devolve_a_conta(sessao, c):
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"], nome="Ana Souza")
    r = entrar(c, "  Ana@Recife.pe.gov.br ")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["email"] == "ana@recife.pe.gov.br"
    assert corpo["papeis"] == ["analista"] and "publicar" not in corpo["permissoes"]
    cookies = r.headers.get_list("set-cookie")
    sessao_cookie = next(x for x in cookies if x.startswith("cs_sessao="))
    assert "HttpOnly" in sessao_cookie and "SameSite=lax" in sessao_cookie and "Path=/api" in sessao_cookie
    csrf_cookie = next(x for x in cookies if x.startswith("cs_csrf="))
    assert "HttpOnly" not in csrf_cookie
    assert c.get("/api/v1/auth/eu").json()["nome"] == "Ana Souza"


def test_token_da_sessao_nao_fica_no_banco(sessao, c):
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    entrar(c, "ana@recife.pe.gov.br")
    token = c.cookies.get("cs_sessao")
    guardado = sessao.execute(text("select id_hash from app.sessoes")).scalar_one()
    assert token not in guardado and len(guardado) == 64


def test_credencial_errada_tem_mensagem_unica_e_nao_revela_se_o_email_existe(sessao, c):
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    errada = entrar(c, "ana@recife.pe.gov.br", "senha errada qualquer")
    inexistente = entrar(c, "ninguem@recife.pe.gov.br", "senha errada qualquer")
    assert errada.status_code == inexistente.status_code == 401
    assert (
        errada.json()["detail"]
        == inexistente.json()["detail"]
        == "E-mail ou senha incorretos. Confira e tente de novo."
    )


def test_quinta_falha_bloqueia_por_15_minutos_e_depois_libera(sessao, c, relogio):
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    for _ in range(5):
        assert entrar(c, "ana@recife.pe.gov.br", "senha errada qualquer").status_code == 401
        relogio.avancar(seconds=30)
    bloqueio = entrar(c, "ana@recife.pe.gov.br")  # até a senha certa é recusada durante o bloqueio
    assert bloqueio.status_code == 429
    assert "pausado por 15 minutos" in bloqueio.json()["detail"]
    assert "17h17" in bloqueio.json()["detail"]  # 20h02 UTC + 15 min = 17h17 no Recife
    relogio.avancar(minutes=15)
    assert entrar(c, "ana@recife.pe.gov.br").status_code == 200


def test_sessao_expira_apos_60_minutos_sem_uso_e_uso_renova(sessao, c, relogio):
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    entrar(c, "ana@recife.pe.gov.br")
    relogio.avancar(minutes=59)
    assert c.get("/api/v1/auth/eu").status_code == 200  # uso renova
    relogio.avancar(minutes=59)
    assert c.post("/api/v1/auth/renovar").status_code == 200  # “Continuar conectado”
    relogio.avancar(minutes=61)
    r = c.get("/api/v1/auth/eu")
    assert r.status_code == 401
    assert r.json()["detail"] == "Sua sessão terminou por inatividade. Entre novamente."


def test_sair_revoga_a_sessao(sessao, c):
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    entrar(c, "ana@recife.pe.gov.br")
    token = c.cookies.get("cs_sessao")
    assert c.post("/api/v1/auth/sair").status_code == 204
    c.cookies.set("cs_sessao", token, path="/api")
    assert c.get("/api/v1/auth/eu").status_code == 401


def test_csrf_obrigatorio_em_alteracoes(sessao, c):
    criar_conta(sessao, "admin@recife.pe.gov.br", ["administrador"])
    entrar(c, "admin@recife.pe.gov.br")
    del c.headers["X-CSRF-Token"]
    r = c.post("/api/v1/auth/renovar")
    assert r.status_code == 403
    assert "confirmar a origem do pedido" in r.json()["detail"]
    c.headers["X-CSRF-Token"] = "valor-forjado"
    assert c.post("/api/v1/auth/renovar").status_code == 403
    assert c.get("/api/v1/auth/eu").status_code == 200  # leitura não exige CSRF


def test_troca_de_senha_obrigatoria_bloqueia_o_resto_ate_trocar(sessao, c):
    criar_conta(
        sessao, "admin@recife.pe.gov.br", ["administrador"], troca_obrigatoria=True, nome="Rafael Costa"
    )
    entrar(c, "admin@recife.pe.gov.br")
    assert c.get("/api/v1/auth/eu").json()["troca_senha_obrigatoria"] is True
    r = c.get("/api/v1/admin/usuarios")
    assert r.status_code == 403 and r.json()["detail"] == "Troque a sua senha temporária para continuar."

    curta = c.post("/api/v1/auth/trocar-senha", json={"senha_atual": SENHA, "nova_senha": "curta"})
    assert curta.status_code == 400 and "10 caracteres" in curta.json()["detail"]
    com_nome = c.post(
        "/api/v1/auth/trocar-senha", json={"senha_atual": SENHA, "nova_senha": "rafael na ponte da boa vista"}
    )
    assert "Não use o seu nome" in com_nome.json()["detail"]
    errada = c.post(
        "/api/v1/auth/trocar-senha",
        json={"senha_atual": "não é esta", "nova_senha": "ponte da boa vista ao sol"},
    )
    assert errada.status_code == 400

    assert (
        c.post(
            "/api/v1/auth/trocar-senha",
            json={"senha_atual": SENHA, "nova_senha": "ponte da boa vista ao sol"},
        ).status_code
        == 204
    )
    assert c.get("/api/v1/admin/usuarios").status_code == 200


def test_conta_desativada_nao_entra(sessao, c):
    u = criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    u.ativo = False
    sessao.commit()
    r = entrar(c, "ana@recife.pe.gov.br")
    assert r.status_code == 403
    assert "desativada" in r.json()["detail"]


def test_auditoria_registra_logins_sem_senha(sessao, c):
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    entrar(c, "ana@recife.pe.gov.br", "senha errada qualquer")
    entrar(c, "ana@recife.pe.gov.br")
    acoes = sessao.execute(text("select acao, detalhes::text from app.auditoria order by id")).all()
    assert [a for a, _ in acoes][-2:] == ["login_falha", "login_sucesso"]
    assert all(SENHA not in d and "senha errada" not in d for _, d in acoes)


def test_sem_sessao_responde_401_em_portugues(c):
    r = c.get("/api/v1/auth/eu")
    assert r.status_code == 401
    assert r.json() == {
        "type": "about:blank",
        "title": "Entre para continuar",
        "status": 401,
        "detail": "Entre para continuar.",
    }
