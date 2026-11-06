"""Gravação das URLs no .env e uso da URL do dono (ADR 0014). Só dados de exemplo."""

from climasense.admin import gravar_no_env
from climasense.infra.postgres import url_do_dono
from tests.conftest import configuracao_teste


def test_gravar_no_env_troca_so_as_variaveis_indicadas(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comentario\r\nA=1\r\nDATABASE_URL=velha\r\nB=dois=2\r\n", encoding="utf-8", newline="")
    gravar_no_env(env, {"DATABASE_URL": "nova", "DATABASE_URL_MIGRACOES": "dono"})
    assert env.read_bytes().decode() == (
        "# comentario\r\nA=1\r\nDATABASE_URL=nova\r\nB=dois=2\r\nDATABASE_URL_MIGRACOES=dono\r\n"
    )


def test_gravar_no_env_cria_arquivo_novo(tmp_path):
    env = tmp_path / ".env"
    gravar_no_env(env, {"X": "1"})
    assert env.read_text() == "X=1\n"


def test_gravar_no_env_ignora_comentario_com_o_mesmo_nome(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# DATABASE_URL=exemplo\nDATABASE_URL=a\n")
    gravar_no_env(env, {"DATABASE_URL": "b"})
    assert env.read_text() == "# DATABASE_URL=exemplo\nDATABASE_URL=b\n"


def test_url_do_dono_prefere_migracoes_e_cai_na_da_aplicacao():
    so_app = configuracao_teste(database_url="postgresql://app:x@h.invalid/db")
    assert url_do_dono(so_app) == "postgresql://app:x@h.invalid/db"
    ambas = configuracao_teste(
        database_url="postgresql://app:x@h.invalid/db",
        database_url_migracoes="postgresql://dono:y@h.invalid/db",
    )
    assert url_do_dono(ambas) == "postgresql://dono:y@h.invalid/db"
    assert "dono:y" not in repr(ambas)
