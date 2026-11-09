"""Vulnerabilidade por território (PRD §7.1, RF-02, RF-03, RF-04, RF-07, RF-25).

Camadas do mapa (equipamentos de saúde, idosos e crianças por bairro, áreas de risco) e o cruzamento do RF-04.
Lê `silver.equipamentos_saude`, `silver.populacao_bairro` e `silver.areas_risco`, que o ETL grava (a aplicação só
lê, ADR 0014). Tabela vazia = "Dados insuficientes" com a fonte que falta (RN-01), nunca zero. Só contagens por bairro
(RN-13); "área de risco" é polígono e equipamento é estabelecimento, nada identifica pessoa.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import simulador as dom_sim
from climasense.dominio import vulnerabilidade as dom
from climasense.infra import cache
from climasense.territorio.geometria import simplificar_web

FONTE_EQUIPAMENTOS = "cnes-equipamentos"
FONTE_POPULACAO = "ibge-censo-2022-bairro"
FONTE_RISCO = "recife-areas-risco"
SUPRESSAO_MINIMA = 5
TOLERANCIA_RISCO_GRAUS = 0.00003  # ~3 m: o polígono leve só desenha; o cruzamento usa o original


def falta(fonte_id: str) -> str:
    return f"Dados insuficientes: falta a fonte {fonte_id}"


def _bairros(db: Session) -> list[tuple[str, str, str]]:
    return cache.obter("territorios", "bairros_por_nome", cache.CARGA_S, lambda: _ler_bairros(db))


def _ler_bairros(db: Session) -> list[tuple[str, str, str]]:
    return [
        (i, n, p)
        for i, n, p in db.execute(
            text(
                "select id, nome_exibicao, pai_id from app.territorios where tipo = 'bairro' order by nome_exibicao"
            )
        )
    ]


# ------------------------------------------------------------------ população
def populacao(db: Session) -> tuple[int | None, dict[str, dom.Celulas]]:
    """(ano, células por bairro) do ano mais recente da fonte; (None, {}) com a tabela vazia. Guardado por
    `cache.CARGA_S` (só muda quando o ETL recarrega o Censo)."""
    return cache.obter("populacao", "ultimo_ano", cache.CARGA_S, lambda: _ler_populacao(db))


def _ler_populacao(db: Session) -> tuple[int | None, dict[str, dom.Celulas]]:
    ano = db.execute(text("select max(ano) from silver.populacao_bairro")).scalar()
    if ano is None:
        return None, {}
    por_bairro: dict[str, dom.Celulas] = {}
    for b, faixa, pessoas, supr in db.execute(
        text("select bairro_id, faixa, pessoas, suprimido from silver.populacao_bairro where ano = :a"),
        {"a": ano},
    ):
        por_bairro.setdefault(b, {})[faixa] = (pessoas, bool(supr))
    return ano, por_bairro


def camada_vulneraveis(db: Session, minimo: int = SUPRESSAO_MINIMA) -> dict | None:
    """Itens por bairro com supressão; `None` sem dado de população."""
    ano, por_bairro = populacao(db)
    if ano is None:
        return None
    itens = []
    for bid, nome, ds in _bairros(db):
        valores, marcas = dom.publicar_bairro(por_bairro.get(bid), minimo)
        itens.append(
            {
                "bairro_id": bid,
                "nome": nome,
                "distrito_id": ds,
                **valores,
                "suprimido": marcas,
                "deficiencia": None,
            }
        )
    return {"ano": ano, "itens": itens}


# ------------------------------------------------------------------ equipamentos
def _equipamentos(db: Session, territorio_id: str | None = None) -> list[dict]:
    """Equipamentos com o distrito resolvido (coluna própria ou, na falta, o pai do bairro)."""
    sql = (
        "select e.cnes, e.nome, e.tipo, e.esfera, e.bairro_id, coalesce(e.distrito_id, t.pai_id) as distrito_id, "
        "e.latitude, e.longitude from silver.equipamentos_saude e left join app.territorios t on t.id = e.bairro_id "
    )
    filtro = ""
    if territorio_id and territorio_id != "recife":
        filtro = "where e.bairro_id = :t or coalesce(e.distrito_id, t.pai_id) = :t "
    return cache.obter(
        "equipamentos",
        territorio_id if filtro else "todos",
        cache.CARGA_S,
        lambda: [
            dict(r)
            for r in db.execute(text(sql + filtro + "order by e.nome"), {"t": territorio_id}).mappings()
        ],
    )


def camada_equipamentos(db: Session) -> dict | None:
    """FeatureCollection de pontos; `None` com a tabela vazia. Equipamento sem coordenada não vira ponto."""
    linhas = _equipamentos(db)
    if not linhas:
        return None
    features = [
        {
            "type": "Feature",
            "properties": {k: r[k] for k in ("cnes", "nome", "tipo", "esfera", "bairro_id", "distrito_id")},
            "geometry": {"type": "Point", "coordinates": [r["longitude"], r["latitude"]]},
        }
        for r in linhas
        if r["latitude"] is not None and r["longitude"] is not None
    ]
    return {"type": "FeatureCollection", "features": features}


# ------------------------------------------------------------------ áreas de risco
def _areas(db: Session) -> list[dict]:
    sql = "select id, tipo, grau, regional, bairro_id, geometria from silver.areas_risco order by id"
    return cache.obter(
        "areas_risco", "todas", cache.CARGA_S, lambda: [dict(r) for r in db.execute(text(sql)).mappings()]
    )


def cobertura_risco(areas: list[dict]) -> dict:
    """Quais regionais e quantos bairros têm área de risco mapeada. Bairro sem área mapeada não é bairro sem risco:
    enquanto a cobertura for parcial, o texto diz isso (RN-01)."""
    regionais = sorted({a["regional"] for a in areas if a["regional"]})
    bairros = len({a["bairro_id"] for a in areas if a["bairro_id"]})
    parcial = bairros < dom.TOTAL_BAIRROS
    texto = (
        f"Áreas de risco mapeadas em {bairros} de {dom.TOTAL_BAIRROS} bairros"
        + (f" (regionais: {', '.join(regionais)})" if regionais else "")
        + ". "
        + (
            "Cobertura parcial: bairro sem área mapeada não significa bairro sem risco."
            if parcial
            else "Cobertura de todos os bairros."
        )
    )
    return {
        "regionais_com_dado": regionais,
        "bairros_com_dado": bairros,
        "total_bairros": dom.TOTAL_BAIRROS,
        "parcial": parcial,
        "texto": texto,
    }


def camada_areas_risco(db: Session) -> tuple[dict, dict] | None:
    """(FeatureCollection, cobertura); `None` com a tabela vazia."""
    areas = _areas(db)
    if not areas:
        return None
    features = [
        {
            "type": "Feature",
            "properties": {k: a[k] for k in ("id", "tipo", "grau", "regional", "bairro_id")},
            "geometry": simplificar_web(a["geometria"], TOLERANCIA_RISCO_GRAUS),
        }
        for a in areas
    ]
    return {"type": "FeatureCollection", "features": features}, cobertura_risco(areas)


def em_area_de_risco(pontos: list[tuple[float, float]], areas: list[dict]) -> int:
    """Quantos pontos (lon, lat) caem dentro de alguma área de risco (ponto-em-polígono, geometria original)."""
    if not pontos or not areas:
        return 0
    import shapely
    from shapely import STRtree
    from shapely.geometry import shape

    poligonos = [g if g.is_valid else shapely.make_valid(g) for g in (shape(a["geometria"]) for a in areas)]
    arvore = STRtree(poligonos)
    alvo = shapely.points([p[0] for p in pontos], [p[1] for p in pontos])
    achados = arvore.query(alvo, predicate="intersects")
    return len({int(i) for i in achados[0]})


# ------------------------------------------------------------------ cruzamento (RF-04, RF-07)
def resumo_territorio(db: Session, territorio_id: str, minimo: int = SUPRESSAO_MINIMA) -> dict:
    """Idosos, crianças, equipamentos e áreas de risco de um bairro, distrito ou do município."""
    ids = [b for b, _, ds in _bairros(db) if territorio_id in ("recife", b, ds)]
    ano, por_bairro = populacao(db)
    idosos = criancas = None
    if ano is not None and ids:
        if len(ids) == 1:
            valores, _ = dom.publicar_bairro(por_bairro.get(ids[0]), minimo)
        else:
            valores = dom.somar_bairros([por_bairro.get(b) for b in ids])
        idosos, criancas = valores["idosos_60_mais"], valores["criancas_0_14"]
    equipamentos = _equipamentos(db, territorio_id)
    areas = _areas(db)
    pontos = [(e["longitude"], e["latitude"]) for e in equipamentos if e["latitude"] is not None]
    todos = bool(_equipamentos(db))
    return {
        "idosos_60_mais": idosos,
        "criancas_0_14": criancas,
        "equipamentos": [{"cnes": e["cnes"], "nome": e["nome"], "tipo": e["tipo"]} for e in equipamentos],
        "equipamentos_em_area_de_risco": em_area_de_risco(pontos, areas) if areas else None,
        "areas_risco": sum(1 for a in areas if a["bairro_id"] in ids) if areas else None,
        "cobertura_risco_parcial": cobertura_risco(areas)["parcial"] if areas else True,
        "_ano": ano,
        "_fontes_com_dado": {
            FONTE_POPULACAO: ano is not None,
            FONTE_EQUIPAMENTOS: todos,
            FONTE_RISCO: bool(areas),
        },
    }


# ------------------------------------------------------------------ gancho do simulador (RF-25)
def vulneraveis_por_territorio(
    db: Session, minimo: int = SUPRESSAO_MINIMA
) -> dict[str, dom_sim.Vulneraveis] | None:
    """Idosos (60+), crianças (0-14) e equipamentos de saúde por bairro e distrito. `None` sem nenhuma das fontes.
    Campo sem fonte ou oculto fica `None`; o distrito soma os valores reais dos bairros (nulo se faltar algum)."""
    ano, por_bairro = populacao(db)
    equipamentos = _equipamentos(db)
    if ano is None and not equipamentos:
        return None
    por_ds: dict[str, list[str]] = {}
    bairros = _bairros(db)
    for b, _, ds in bairros:
        por_ds.setdefault(ds, []).append(b)
    n_bairro: dict[str, int] = {}
    n_ds: dict[str, int] = {}
    for e in equipamentos:
        if e["bairro_id"]:
            n_bairro[e["bairro_id"]] = n_bairro.get(e["bairro_id"], 0) + 1
        if e["distrito_id"]:
            n_ds[e["distrito_id"]] = n_ds.get(e["distrito_id"], 0) + 1
    tem_eq = bool(equipamentos)
    saida: dict[str, dom_sim.Vulneraveis] = {}
    for b, _, _ in bairros:
        v = dom.publicar_bairro(por_bairro.get(b), minimo)[0] if ano is not None else {}
        saida[b] = dom_sim.Vulneraveis(
            idosos=v.get("idosos_60_mais"),
            criancas=v.get("criancas_0_14"),
            equipamentos_saude=n_bairro.get(b, 0) if tem_eq else None,
        )
    for ds, filhos in por_ds.items():
        v = dom.somar_bairros([por_bairro.get(b) for b in filhos]) if ano is not None else {}
        saida[ds] = dom_sim.Vulneraveis(
            idosos=v.get("idosos_60_mais"),
            criancas=v.get("criancas_0_14"),
            equipamentos_saude=n_ds.get(ds, 0) if tem_eq else None,
        )
    return saida
