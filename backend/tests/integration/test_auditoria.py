import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from climasense.infra.repositorios.auditoria import RepositorioAuditoria
from tests.conftest import precisa_postgres

pytestmark = [precisa_postgres, pytest.mark.integracao]


def test_registra_e_lista_sem_gravar_segredos(sessao):
    repo = RepositorioAuditoria(sessao)
    repo.registrar(
        "login_sucesso", detalhes={"email": "ana@recife.pe.gov.br", "senha": "nunca-gravar"}, ip="10.0.0.1"
    )
    repo.registrar("login_falha", detalhes={"email": "ana@recife.pe.gov.br"})
    sessao.flush()
    registros = repo.listar()
    assert [r.acao for r in registros][:2] == ["login_falha", "login_sucesso"]
    assert registros[1].detalhes["senha"] == "[omitido]"
    assert repo.listar(acao="login_falha")[0].acao == "login_falha"


def test_auditoria_nao_pode_ser_alterada_nem_apagada(sessao):
    RepositorioAuditoria(sessao).registrar("teste")
    sessao.flush()
    for comando in (
        "update app.auditoria set acao = 'adulterado'",
        "delete from app.auditoria",
        "truncate app.auditoria",
    ):
        with pytest.raises(DBAPIError, match="apenas inclusões"), sessao.begin_nested():
            sessao.execute(text(comando))
