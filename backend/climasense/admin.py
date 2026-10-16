"""Comandos de administração.

    python -m climasense.admin criar-admin
    python -m climasense.admin criar-equipe equipe.csv [--senhas-em tmp/senhas-equipe.txt]

criar-admin: cria o primeiro administrador com ADMIN_EMAIL e ADMIN_SENHA_INICIAL do .env (T3.7).
criar-equipe: cria as contas listadas num CSV `nome;email;papeis` (papéis separados por vírgula) (T7.7).
  As senhas temporárias vão SÓ para o arquivo indicado (em tmp/, fora do Git), para entrega individual.
  Não cria avaliações nem comunicados: a demonstração usa o fluxo de verdade.
Nenhuma senha é impressa. A troca é obrigatória no primeiro acesso. Rodar de novo não duplica.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from email_validator import EmailNotValidError, validate_email

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


def criar_equipe(sessao, linhas: list[dict[str, str]]) -> tuple[list[str], dict[str, str]]:
    """Cria as contas que ainda não existem. Devolve as mensagens (sem senha) e {e-mail: senha temporária}."""
    mensagens: list[str] = []
    senhas: dict[str, str] = {}
    usuarios = RepositorioUsuarios(sessao)
    servico = ServicoUsuarios(sessao)
    for linha in linhas:
        try:  # a mesma validação do login: um e-mail que não entra não deve virar conta
            email = validate_email(linha["email"].strip(), check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            mensagens.append(f"{linha['email'].strip()}: e-mail inválido, conta não criada.")
            continue
        if usuarios.por_email(email):
            mensagens.append(f"{email}: já existe, nada foi alterado.")
            continue
        papeis = [p.strip() for p in linha["papeis"].split(",") if p.strip()]
        conta = servico.criar(linha["nome"].strip(), email, papeis, autor=None)
        senhas[email] = conta.senha_temporaria
        mensagens.append(f"{email}: conta criada ({', '.join(conta.usuario.papeis)}).")
    return mensagens, senhas


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo, delimiter=";"))
    faltando = {"nome", "email", "papeis"} - set(linhas[0] if linhas else {})
    if faltando:
        raise ValueError(
            f"O CSV precisa das colunas nome;email;papeis (faltam: {', '.join(sorted(faltando))})."
        )
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m climasense.admin",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("criar-admin", help="Cria o primeiro administrador a partir do .env")
    eq = sub.add_parser("criar-equipe", help="Cria as contas da equipe a partir de um CSV nome;email;papeis")
    eq.add_argument("arquivo", type=Path)
    eq.add_argument("--senhas-em", type=Path, default=Path("tmp/senhas-equipe.txt"))
    args = parser.parse_args(argv)
    config = obter_configuracao()
    if args.comando == "criar-equipe":
        try:
            linhas = ler_csv(args.arquivo)
            with fabrica_sessoes(engine_da_configuracao(config))() as sessao:
                mensagens, senhas = criar_equipe(sessao, linhas)
            if senhas:
                args.senhas_em.parent.mkdir(parents=True, exist_ok=True)
                with args.senhas_em.open("a", encoding="utf-8") as saida:
                    saida.writelines(f"{email};{senha}\n" for email, senha in senhas.items())
            print("\n".join(mensagens))
            if senhas:
                print(
                    f"Senhas temporárias de {len(senhas)} conta(s) em {args.senhas_em}. "
                    "Entregue a cada pessoa e apague o arquivo."
                )
        except (OSError, ValueError, KeyError) as erro:
            print(f"Não foi possível criar a equipe: {erro}", file=sys.stderr)
            return 1
        except Exception as erro:  # noqa: BLE001
            print(f"Não foi possível criar a equipe ({type(erro).__name__}).", file=sys.stderr)
            return 1
        return 0
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
