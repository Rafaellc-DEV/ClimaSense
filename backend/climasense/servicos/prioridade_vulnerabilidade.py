"""Prioridade por vulnerabilidade (RF-06, RF-22): onde já houve mais atendimentos da Defesa Civil.

Ordena distritos e bairros pelo histórico real de ocorrências (`silver.ocorrencias`, por tipo), sem inventar dado.
Não é probabilidade (RN-06): só posição e contagem. A Etapa 6 soma idosos e crianças (IBGE) acrescentando um
componente em `CRITERIOS` e as colunas na consulta; o texto de `criterio` vem desses componentes.
Sem carga bem-sucedida da fonte, não há ordenação (RN-01); zero medido continua zero (RN-02).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.servicos import cenarios

FONTE = "recife-alagamento"
# Componentes do critério, em ordem de peso. Etapa 6: acrescentar aqui o de população vulnerável (IBGE).
CRITERIOS = ("atendimentos de alagamento e deslizamento",)

_SQL = """
select t.id as territorio_id, t.nome_exibicao as nome, t.tipo as nivel, t.pai_id,
       count(*) filter (where o.tipo = 'alagamento')::integer as alagamento,
       count(*) filter (where o.tipo = 'deslizamento')::integer as deslizamento
from app.territorios t
left join silver.ocorrencias o on o.territorio_id = t.id and o.fonte_id = :f
where t.tipo = 'bairro'
group by t.id, t.nome_exibicao, t.tipo, t.pai_id
"""


def _desde(db: Session) -> int | None:
    return db.execute(
        text(
            "select extract(year from min(registrado_em at time zone 'America/Recife'))::integer "
            "from silver.ocorrencias where fonte_id = :f"
        ),
        {"f": FONTE},
    ).scalar()


def _posicoes(itens: list[dict]) -> list[dict]:
    """Ordena (mais atendimentos primeiro; empate: mais alagamento, depois nome) e numera; empatados dividem a posição."""
    itens.sort(
        key=lambda i: (
            -(i["ocorrencias_alagamento"] + i["ocorrencias_deslizamento"]),
            -i["ocorrencias_alagamento"],
            i["nome"],
        )
    )
    anterior, pos = None, 0
    for n, i in enumerate(itens, start=1):
        total = (i["ocorrencias_alagamento"], i["ocorrencias_deslizamento"])
        if total != anterior:
            pos, anterior = n, total
        i["posicao"] = pos
    return itens


def listar(db: Session, nivel: str | None = None) -> dict | None:
    """`nivel`: distrito, bairro ou None (os dois, cada um com a sua numeração). None sem carga da fonte."""
    if cenarios.ocorrencias(db, "recife") is None:
        return None
    desde = _desde(db)
    criterio = "mais " + " e ".join(CRITERIOS) + (f" desde {desde}" if desde else "")
    nomes = dict(
        db.execute(text("select id, nome_exibicao from app.territorios where tipo = 'distrito'")).all()
    )
    bairros = [dict(r) for r in db.execute(text(_SQL), {"f": FONTE}).mappings()]
    por_bairro = [
        {
            "territorio_id": b["territorio_id"],
            "nome": b["nome"],
            "nivel": "bairro",
            "ocorrencias_alagamento": b["alagamento"],
            "ocorrencias_deslizamento": b["deslizamento"],
            "criterio": criterio,
        }
        for b in bairros
        if b["pai_id"] in nomes
    ]
    por_distrito: dict[str, dict] = {
        ds: {
            "territorio_id": ds,
            "nome": n,
            "nivel": "distrito",
            "ocorrencias_alagamento": 0,
            "ocorrencias_deslizamento": 0,
            "criterio": criterio,
        }
        for ds, n in nomes.items()
    }
    for b in bairros:
        if b["pai_id"] in por_distrito:
            por_distrito[b["pai_id"]]["ocorrencias_alagamento"] += b["alagamento"]
            por_distrito[b["pai_id"]]["ocorrencias_deslizamento"] += b["deslizamento"]
    itens: list[dict] = []
    if nivel in (None, "distrito"):
        itens += _posicoes(list(por_distrito.values()))
    if nivel in (None, "bairro"):
        itens += _posicoes(por_bairro)
    return {"itens": itens, "desde": desde}
