import pytest
from sqlalchemy import text

from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]


@pytest.fixture
def admin(sessao):
    c = cliente(sessao, Relogio())
    criar_conta(sessao, "admin@recife.pe.gov.br", ["administrador"])
    entrar(c, "admin@recife.pe.gov.br")
    return c


def test_criar_conta_mostra_senha_temporaria_uma_vez_e_exige_troca(sessao, admin):
    r = admin.post(
        "/api/v1/admin/usuarios",
        json={"nome": "Ana Souza", "email": "Ana@Recife.pe.gov.br", "papeis": ["analista"]},
    )
    assert r.status_code == 201
    temporaria = r.json()["senha_temporaria"]
    assert r.json()["conta"]["email"] == "ana@recife.pe.gov.br"
    assert r.json()["conta"]["troca_senha_obrigatoria"] is True
    assert "senha_temporaria" not in str(admin.get("/api/v1/admin/usuarios").json())
    nova = cliente(sessao, Relogio())
    assert entrar(nova, "ana@recife.pe.gov.br", temporaria).json()["troca_senha_obrigatoria"] is True
    assert temporaria not in str(
        sessao.execute(text("select detalhes::text from app.auditoria")).scalars().all()
    )


def test_email_repetido_e_papel_invalido(admin):
    corpo = {"nome": "Ana", "email": "ana@recife.pe.gov.br", "papeis": ["analista"]}
    assert admin.post("/api/v1/admin/usuarios", json=corpo).status_code == 201
    repetido = admin.post("/api/v1/admin/usuarios", json=corpo)
    assert repetido.status_code == 409 and repetido.json()["detail"] == "Já existe uma conta com este e-mail."
    ruim = admin.post(
        "/api/v1/admin/usuarios", json={**corpo, "email": "b@recife.pe.gov.br", "papeis": ["dono"]}
    )
    assert ruim.status_code == 422 and "não existe" in ruim.json()["detail"]


def test_alterar_papeis_e_desativar_revoga_sessoes(sessao, admin):
    ana = criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    sessao_ana = cliente(sessao, Relogio())
    entrar(sessao_ana, "ana@recife.pe.gov.br")
    r = admin.patch(f"/api/v1/admin/usuarios/{ana.id}", json={"papeis": ["revisor", "analista"]})
    assert r.json()["papeis"] == ["analista", "revisor"]
    assert admin.patch(f"/api/v1/admin/usuarios/{ana.id}", json={"ativo": False}).json()["ativo"] is False
    assert sessao_ana.get("/api/v1/auth/eu").status_code == 401
    assert admin.patch(f"/api/v1/admin/usuarios/{ana.id}", json={"ativo": True}).json()["ativo"] is True


def test_nao_desativa_a_propria_conta_nem_o_ultimo_administrador(sessao, admin):
    eu = admin.get("/api/v1/auth/eu").json()["id"]
    r = admin.patch(f"/api/v1/admin/usuarios/{eu}", json={"ativo": False})
    assert r.status_code == 409 and "própria conta" in r.json()["detail"]
    r = admin.patch(f"/api/v1/admin/usuarios/{eu}", json={"papeis": ["analista"]})
    assert r.status_code == 409 and "pelo menos um administrador" in r.json()["detail"]
    criar_conta(sessao, "outro.admin@recife.pe.gov.br", ["administrador"])
    assert (
        admin.patch(
            f"/api/v1/admin/usuarios/{eu}", json={"papeis": ["administrador", "coordenacao"]}
        ).status_code
        == 200
    )


def test_redefinir_senha_forca_troca_e_derruba_sessoes(sessao, admin):
    ana = criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    sessao_ana = cliente(sessao, Relogio())
    entrar(sessao_ana, "ana@recife.pe.gov.br")
    temporaria = admin.post(f"/api/v1/admin/usuarios/{ana.id}/redefinir-senha").json()["senha_temporaria"]
    assert sessao_ana.get("/api/v1/auth/eu").status_code == 401
    assert (
        entrar(cliente(sessao, Relogio()), "ana@recife.pe.gov.br", temporaria).json()[
            "troca_senha_obrigatoria"
        ]
        is True
    )


def test_papeis_descritos_em_linguagem_simples(admin):
    papeis = {p["papel"]: p["descricao"] for p in admin.get("/api/v1/admin/usuarios/papeis").json()}
    assert set(papeis) == {"analista", "revisor", "coordenacao", "administrador"}
    assert "publica" in papeis["coordenacao"]


def test_alteracoes_ficam_na_auditoria(sessao, admin):
    r = admin.post(
        "/api/v1/admin/usuarios",
        json={"nome": "Ana", "email": "ana@recife.pe.gov.br", "papeis": ["analista"]},
    )
    admin.patch(f"/api/v1/admin/usuarios/{r.json()['conta']['id']}", json={"ativo": False})
    acoes = sessao.execute(text("select acao from app.auditoria order by id")).scalars().all()
    assert {"usuario_criado", "usuario_alterado"} <= set(acoes)
