"""Território no recorte das consultas: nomes de exibição e a granularidade disponível (RN-07)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio.recorte import RecorteInvalido, granularidade, validar_territorio
from climasense.territorio.carga import slug
from climasense.territorio.geometria import carregar_malha_bairros, simplificar_web


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


TOLERANCIA_MALHA_GRAUS = 0.0001  # ~11 m: a malha de 94 bairros cai de ~2 MB para menos de 100 KB


@lru_cache(maxsize=1)
def _malha_simplificada() -> tuple[tuple[str, dict], ...] | None:
    malha = carregar_malha_bairros(baixar=False)
    if malha is None:
        return None
    saida = []
    for f in malha["features"]:
        p = f["properties"]
        nome = p.get("EBAIRRNOME") or p.get("EBAIRRNOMEOF") or ""
        saida.append((f"bairro-{slug(nome)}", simplificar_web(f["geometry"], TOLERANCIA_MALHA_GRAUS)))
    return tuple(saida)


def malha_bairros(db: Session) -> dict | None:
    """FeatureCollection dos bairros com `id` (igual ao de `/estagios?nivel=bairro`), `nome` e `distrito_id`.
    None sem o arquivo da malha. Bairro que não está em `app.territorios` fica de fora."""
    geometrias = _malha_simplificada()
    if geometrias is None:
        return None
    cadastro = {
        i: (n, pai)
        for i, n, pai in db.execute(
            text("select id, nome_exibicao, pai_id from app.territorios where tipo = 'bairro'")
        )
    }
    features = [
        {
            "type": "Feature",
            "properties": {"id": i, "nome": cadastro[i][0], "distrito_id": cadastro[i][1]},
            "geometry": g,
        }
        for i, g in geometrias
        if i in cadastro
    ]
    return {"type": "FeatureCollection", "features": features}
