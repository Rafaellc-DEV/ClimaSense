"""Prioridade por vulnerabilidade (RF-06, RF-22): onde já houve mais atendimentos da Defesa Civil.

Ordena distritos e bairros pelo histórico real de ocorrências (`silver.ocorrencias`, por tipo), sem inventar dado.
Não é probabilidade (RN-06): só posição e contagem. Idosos e crianças (IBGE, Etapa 6) aparecem nos itens para
exibição, mas NÃO entram na ordem: como combinar os dois critérios é a pergunta P-22 do cliente. O texto de
`criterio` vem de `CRITERIOS`.
Sem carga bem-sucedida da fonte, não há ordenação (RN-01); zero medido continua zero (RN-02).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.servicos import cenarios, vulnerabilidade

FONTE = "recife-alagamento"
# Componentes do critério, em ordem de peso (só o histórico; população vulnerável aguarda a P-22).
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


def _populacao(vul: dict, territorio_id: str) -> dict:
    """Idosos 60+ e crianças 0-14 residentes, só para exibir; nulo = sem dado ou suprimido."""
    v = vul.get(territorio_id)
    return {"idosos_60_mais": v.idosos if v else None, "criancas_0_14": v.criancas if v else None}


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
    vul = vulnerabilidade.vulneraveis_por_territorio(db) or {}
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
            **_populacao(vul, b["territorio_id"]),
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
            **_populacao(vul, ds),
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
