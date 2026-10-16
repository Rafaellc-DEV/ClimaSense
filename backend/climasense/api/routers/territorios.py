"""Território: árvore, GeoJSON dos distritos e da hidrografia, indicadores e mapa portátil (M4)."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.deps import configuracao, mongo
from climasense.api.envelope import Amostra, FonteMeta, Meta, RecorteMeta, RespostaDados
from climasense.api.erros import ErroClimaSense
from climasense.config import Configuracao
from climasense.dominio.papeis import Permissao
from climasense.dominio.territorio import normalizar_busca
from climasense.infra.postgres import obter_sessao
from climasense.servicos import cenarios
from climasense.servicos import fontes as servico_fontes
from climasense.territorio import carga, mapa_portatil

router = APIRouter(prefix="/territorios", tags=["Território"])
publico = APIRouter(prefix="/publico", tags=["Público"])
consultar = exige(Permissao.CONSULTAR)

FONTE_TERRITORIO = FonteMeta(
    id="territorio-oficial",
    nome="Dados Abertos do Recife, distritos sanitários",
    tipo="observada",
    status="atualizada",
)
INDICADORES = {"quantidade_bairros", "area_km2", "vacinacao", "ocorrencias", "prioridade"}


class Territorio(BaseModel):
    id: str
    tipo: str
    nome_exibicao: str
    pai_id: str | None


class ValorDistrito(BaseModel):
    territorio_id: str
    valor: float | None


def _geo(cliente, config: Configuracao) -> dict:
    try:
        return carga.ler_atlas(cliente, config.mongo_db_territorio)
    except carga.ErroTerritorio as erro:
        raise ErroClimaSense(503, str(erro)) from None


def _geojson(request: Request, dados: dict) -> Response:
    corpo = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    etag = '"' + hashlib.sha256(corpo.encode()).hexdigest()[:32] + '"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return Response(
        corpo,
        media_type="application/geo+json",
        headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
    )


@router.get("", response_model=list[Territorio], summary="Recife, distritos e bairros")
def listar(_: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)) -> list[Territorio]:
    linhas = db.execute(
        text("select id, tipo, nome_exibicao, pai_id from app.territorios order by tipo desc, id")
    ).mappings()
    return [Territorio(**linha) for linha in linhas]


@router.get("/distritos.geojson", summary="Os 8 distritos sanitários (GeoJSON)")
def distritos(
    request: Request,
    _: Contexto = Depends(consultar),
    cliente=Depends(mongo),
    config: Configuracao = Depends(configuracao),
) -> Response:
    return _geojson(request, _geo(cliente, config))


@router.get("/hidrografia.geojson", summary="Faixas marginais dos recursos hídricos (geometria simplificada)")
def hidrografia(
    request: Request,
    _: Contexto = Depends(consultar),
    cliente=Depends(mongo),
    config: Configuracao = Depends(configuracao),
) -> Response:
    return _geojson(request, carga.ler_hidrografia(cliente, config.mongo_db_territorio))


@router.get(
    "/indicadores",
    response_model=RespostaDados[list[ValorDistrito]],
    summary="Valor por distrito para colorir o mapa",
)
def indicadores(
    indicador: str = Query(
        ..., description="quantidade_bairros | area_km2 | vacinacao | ocorrencias | prioridade"
    ),
    inicio: date | None = None,
    fim: date | None = None,
    _: Contexto = Depends(consultar),
    cliente=Depends(mongo),
    db: Session = Depends(obter_sessao),
    config: Configuracao = Depends(configuracao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[list[ValorDistrito]]:
    if indicador not in INDICADORES:
        raise ErroClimaSense(
            400, f"Indicador “{indicador}” não existe. Use: {', '.join(sorted(INDICADORES))}."
        )
    recorte = RecorteMeta(territorio_id="recife", inicio=inicio, fim=fim, granularidade="distrito")
    if indicador in ("quantidade_bairros", "area_km2"):
        geo = _geo(cliente, config)
        dados = [
            ValorDistrito(
                territorio_id=f"ds-{f['properties']['cdistscodi']}", valor=f["properties"][indicador]
            )
            for f in geo["features"]
        ]
        return RespostaDados(dados=dados, meta=Meta(fontes=[FONTE_TERRITORIO], recorte=recorte))
    if indicador == "vacinacao":
        linhas = (
            db.execute(
                text(
                    "select distrito_codigo, case when bool_or(suprimido) then null else sum(doses) end as doses, "
                    "sum(amostra_n) as n, max(total_fonte) as total from gold.vacinacao_distrito_mes "
                    "where (cast(:i as date) is null or mes >= :i) and (cast(:f as date) is null or mes <= :f) "
                    "group by distrito_codigo"
                ),
                {"i": inicio, "f": fim},
            )
            .mappings()
            .all()
        )
        por_ds = {r["distrito_codigo"]: r for r in linhas}
        dados = [
            ValorDistrito(territorio_id=f"ds-{c}", valor=por_ds[c]["doses"] if c in por_ds else None)
            for c in range(1, 9)
        ]
        n = sum(r["n"] for r in linhas)
        total = max((r["total"] or 0 for r in linhas), default=0) or None
        fonte = FonteMeta(
            id="vacinacao",
            nome="Dados Abertos do Recife, vacinação COVID-19",
            tipo="observada",
            status="atualizada" if linhas else "planejada",
        )
        return RespostaDados(
            dados=dados,
            meta=Meta(
                fontes=[fonte],
                recorte=recorte,
                dados_insuficientes=not linhas,
                amostra=Amostra(n=n, total_fonte=total) if linhas else None,
                avisos=["Amostra parcial da base: não representa o total de vacinados."]
                if linhas and total and n < total
                else [],
            ),
        )
    if indicador == "prioridade":
        # cenário experimental de 72 h por distrito: 0 sem indicação, 1 atenção, 2 alerta, 3 crítico
        escala = {"sem_indicacao": 0, "atencao": 1, "alerta": 2, "critico": 3}
        valores = []
        for c in range(1, 9):
            est = cenarios.emitir(db, f"ds-{c}", 72, agora)["estimativa"]
            valores.append(ValorDistrito(territorio_id=f"ds-{c}", valor=escala.get(est.prioridade)))
        return RespostaDados(
            dados=valores,
            meta=Meta(
                fontes=[
                    servico_fontes.meta(db, f, agora)
                    for f in ("open-meteo-previsao", "open-meteo-mare", "open-meteo-historico")
                ],
                recorte=recorte,
                dados_insuficientes=all(v.valor is None for v in valores),
                avisos=[
                    "Experimental: não validado para uso operacional.",
                    "Prioridade é uma indicação para avaliar, não uma chance de alagar.",
                ],
            ),
        )
    # ocorrências: o conjunto de alagamentos ainda não tem conector (RN-01)
    fonte = servico_fontes.meta(db, "recife-alagamento", agora)
    return RespostaDados(
        dados=[ValorDistrito(territorio_id=f"ds-{c}", valor=None) for c in range(1, 9)],
        meta=Meta(
            fontes=[fonte],
            recorte=recorte,
            dados_insuficientes=True,
            avisos=["Fonte ainda não integrada. Nenhum valor é exibido no lugar."],
        ),
    )


@router.get("/mapa-portatil", summary="Baixar o mapa portátil (HTML offline, porte da Aula 07)")
def mapa(
    _: Contexto = Depends(consultar), cliente=Depends(mongo), config: Configuracao = Depends(configuracao)
) -> Response:
    geo = _geo(cliente, config)
    water = carga.ler_hidrografia(cliente, config.mongo_db_territorio, web=False)
    html = mapa_portatil.gerar(
        geo, water, f"MongoDB Atlas · {config.mongo_db_territorio}.DistritosSanitarios"
    )
    return Response(
        html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="mapa-territorio-recife.html"'},
    )


# ------------------------------------------------------------------ público (landing)
class Bairro(BaseModel):
    id: str
    nome: str
    distrito_id: str | None


@publico.get(
    "/territorios/busca", response_model=list[Bairro], summary="Busca de bairro sem diferenciar acentos"
)
def busca(
    q: str = Query(..., min_length=2, max_length=60), db: Session = Depends(obter_sessao)
) -> list[Bairro]:
    agulha = normalizar_busca(q)
    linhas = db.execute(
        text(
            "select id, nome_exibicao, pai_id from app.territorios where tipo = 'bairro' order by nome_exibicao"
        )
    ).all()
    return [Bairro(id=i, nome=n, distrito_id=p) for i, n, p in linhas if agulha in normalizar_busca(n)][:10]
