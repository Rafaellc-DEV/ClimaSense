"""Comandos de administração.

    python -m climasense.admin criar-admin

Cria o primeiro administrador com ADMIN_EMAIL e ADMIN_SENHA_INICIAL do .env (T3.7).
A senha nunca é impressa. A troca é obrigatória no primeiro acesso. Rodar de novo não duplica.
"""

from __future__ import annotations

import argparse
import sys

from climasense.config import ConfiguracaoAusente, obter_configuracao
from climasense.dominio.senha import problemas_da_senha
from climasense.infra.postgres import engine_da_configuracao, fabrica_sessoes
from climasense.infra.repositorios.usuarios import RepositorioUsuarios
from climasense.servicos.usuarios import ServicoUsuarios


def criar_admin(sessao, email: str, senha: str, nome: str = "Administrador do ClimaSense") -> str:
    email = email.strip().lower()
    if RepositorioUsuarios(sessao).por_email(email):
        return f"Já existe uma conta para {email}. Nada foi alterado."
    problemas = problemas_da_senha(senha, email, nome)
    if problemas:
        raise ValueError("ADMIN_SENHA_INICIAL não atende à política: " + " ".join(problemas))
    ServicoUsuarios(sessao).criar(nome, email, ["administrador"], autor=None, senha_inicial=senha)
    return f"Administrador {email} criado. Entre com a senha do .env e troque-a no primeiro acesso."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m climasense.admin",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("criar-admin", help="Cria o primeiro administrador a partir do .env")
    parser.parse_args(argv)
    config = obter_configuracao()
    try:
        email = config.exigir("admin_email")
        senha = config.exigir("admin_senha_inicial")
        with fabrica_sessoes(engine_da_configuracao(config))() as sessao:
            print(criar_admin(sessao, email, senha))
    except (ConfiguracaoAusente, ValueError) as erro:
        print(f"Não foi possível criar o administrador: {erro}", file=sys.stderr)
        return 1
    except Exception as erro:  # noqa: BLE001
        print(
            f"Não foi possível criar o administrador ({type(erro).__name__}). Confira DATABASE_URL e rode "
            "'alembic upgrade head' antes.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
