"""Território no recorte das consultas: nomes de exibição e a granularidade disponível (RN-07)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio.recorte import RecorteInvalido, granularidade, validar_territorio


@dataclass
class TerritorioUsado:
    pedido: str
    usado: str
    nome: str
    avisos: list[str] = field(default_factory=list)


def nome(db: Session, territorio_id: str) -> str:
    return (
        db.execute(
            text("select nome_exibicao from app.territorios where id = :i"), {"i": territorio_id}
        ).scalar()
        or territorio_id
    )


def no_maximo_distrito(db: Session, territorio_id: str) -> TerritorioUsado:
    """Dados por distrito: um bairro pedido vira o distrito dele, com aviso explícito (RF-05.5, RN-07)."""
    validar_territorio(territorio_id)
    if granularidade(territorio_id) != "bairro":
        return TerritorioUsado(territorio_id, territorio_id, nome(db, territorio_id))
    linha = db.execute(
        text("select nome_exibicao, pai_id from app.territorios where id = :i"), {"i": territorio_id}
    ).first()
    if not linha or not linha[1]:
        raise RecorteInvalido(f"Território “{territorio_id}” não existe.")
    nome_distrito = nome(db, linha[1])
    return TerritorioUsado(
        territorio_id,
        linha[1],
        nome_distrito,
        [f"Este dado existe só por distrito. Mostrando o {nome_distrito}, onde fica {linha[0]}."],
    )
