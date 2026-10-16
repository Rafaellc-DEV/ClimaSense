import pytest
from sqlalchemy import text

from climasense.admin import criar_admin
from tests.conftest import precisa_postgres

pytestmark = [precisa_postgres, pytest.mark.integracao]
SENHA = "ponte giratória do recife"


def test_criar_admin_e_idempotente_e_nao_mostra_a_senha(sessao):
    primeira = criar_admin(sessao, "Admin@Recife.pe.gov.br", SENHA)
    segunda = criar_admin(sessao, "admin@recife.pe.gov.br", SENHA)
    assert "criado" in primeira and "Já existe" in segunda
    assert SENHA not in primeira + segunda
    linhas = sessao.execute(text("select papeis, troca_senha_obrigatoria from app.usuarios")).all()
    assert linhas == [(["administrador"], True)]


def test_criar_admin_recusa_senha_fraca(sessao):
    with pytest.raises(ValueError, match="10 caracteres"):
        criar_admin(sessao, "admin@recife.pe.gov.br", "curta")


def test_criar_equipe_e_idempotente_e_nenhuma_senha_aparece_na_saida(sessao):
    from climasense.admin import criar_equipe

    linhas = [
        {"nome": "Ana Lima", "email": "Ana@recife.pe.gov.br", "papeis": "analista"},
        {"nome": "Rui Souza", "email": "rui@recife.pe.gov.br", "papeis": "revisor, analista"},
    ]
    mensagens, senhas = criar_equipe(sessao, linhas)
    de_novo, sem_senhas = criar_equipe(sessao, linhas)
    assert len(senhas) == 2 and sem_senhas == {}
    saida = "\n".join(mensagens + de_novo)
    assert all(s not in saida for s in senhas.values())
    assert "rui@recife.pe.gov.br: conta criada (analista, revisor)." in mensagens
    assert (
        sessao.execute(text("select count(*) from app.usuarios where troca_senha_obrigatoria")).scalar() == 2
    )
    assert sessao.execute(text("select count(*) from app.comunicados")).scalar() == 0
