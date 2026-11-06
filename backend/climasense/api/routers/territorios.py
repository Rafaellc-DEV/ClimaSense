"""Território: árvore, GeoJSON dos distritos e da hidrografia, indicadores e mapa portátil (M4)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.deps import configuracao, mongo
from climasense.api.envelope import FonteMeta, Meta, RecorteMeta, RespostaDados
from climasense.api.erros import ErroClimaSense
from climasense.api.esquemas_decisao import Prioridades
from climasense.api.routers.publico import vigentes
from climasense.config import Configuracao
from climasense.dominio.papeis import Permissao
from climasense.dominio.territorio import normalizar_busca
from climasense.infra.postgres import obter_sessao
from climasense.servicos import cenarios, decisao, prioridade_vulnerabilidade
from climasense.servicos import fontes as servico_fontes
from climasense.servicos import territorio as servico_territorio
from climasense.territorio import carga, mapa_portatil

router = APIRouter(prefix="/territorios", tags=["Território"])
publico = APIRouter(prefix="/publico", tags=["Público"])
mapa_portatil_router = APIRouter(prefix="/territorios", tags=["Território"])  # atrás de FUNC_MAPA_PORTATIL
consultar = exige(Permissao.CONSULTAR)

FONTE_TERRITORIO = FonteMeta(
    id="territorio-oficial",
    nome="Dados Abertos do Recife, distritos sanitários",
    tipo="observada",
    status="atualizada",
)
INDICADORES = {"quantidade_bairros", "area_km2", "ocorrencias", "prioridade"}


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


@router.get("/bairros.geojson", summary="Os 94 bairros (GeoJSON simplificado, ids iguais aos de /estagios)")
def bairros_geojson(
    request: Request, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> Response:
    malha = servico_territorio.malha_bairros(db)
    if malha is None:
        raise ErroClimaSense(503, "A malha dos bairros não está disponível neste ambiente.")
    return _geojson(request, malha)


@router.get(
    "/indicadores",
    response_model=RespostaDados[list[ValorDistrito]],
    summary="Valor por distrito para colorir o mapa",
)
def indicadores(
    indicador: str = Query(..., description="quantidade_bairros | area_km2 | ocorrencias | prioridade"),
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
        return RespostaDados(
            dados=dados,
            meta=Meta(fontes=[servico_fontes.com_frescor(FONTE_TERRITORIO, agora)], recorte=recorte),
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


class ItemPrioridade(BaseModel):
    territorio_id: str
    nome: str
    nivel: Literal["distrito", "bairro"]
    posicao: int = Field(description="1 = mais atendimentos; empatados dividem a posição")
    ocorrencias_alagamento: int
    ocorrencias_deslizamento: int
    criterio: str = Field(description="Por que esta ordem, em texto")


class PrioridadeVulnerabilidade(BaseModel):
    itens: list[ItemPrioridade]
    desde: int | None = Field(description="Ano do primeiro atendimento na base")


@router.get(
    "/prioridade",
    response_model=RespostaDados[PrioridadeVulnerabilidade],
    summary="Prioridade por vulnerabilidade: onde já houve mais atendimentos da Defesa Civil (não é probabilidade)",
)
def prioridade_por_vulnerabilidade(
    nivel: Literal["distrito", "bairro"] | None = Query(
        default=None, description="distrito ou bairro; sem o parâmetro vêm os dois, cada um numerado"
    ),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[PrioridadeVulnerabilidade]:
    r = prioridade_vulnerabilidade.listar(db, nivel)
    return RespostaDados(
        dados=PrioridadeVulnerabilidade(itens=r["itens"] if r else [], desde=r["desde"] if r else None),
        meta=Meta(
            fontes=[servico_fontes.meta(db, prioridade_vulnerabilidade.FONTE, agora)],
            recorte=RecorteMeta(territorio_id="recife", granularidade=nivel or "bairro"),
            dados_insuficientes=r is None,
            avisos=[
                "Prioridade é a ordem do histórico de atendimentos, não uma chance de alagar (RN-06).",
                "Ainda não considera idosos e crianças (IBGE).",
            ]
            + (["Fonte sem carga: nenhum território é ordenado."] if r is None else []),
        ),
    )


@router.get(
    "/prioridades",
    response_model=RespostaDados[Prioridades],
    summary="Quais territórios pedem atenção primeiro, por quê e com que confiança",
)
def prioridades(
    nivel: Literal["distrito", "bairro"] = Query(
        default="distrito", description="distrito (padrão) ou bairro"
    ),
    horizonte_h: int = Query(default=72, description="24, 48 ou 72 horas"),
    distrito_id: str | None = Query(default=None, description="Restringe a um distrito (ds-1 a ds-8)"),
    limite: int = Query(default=20, ge=1, le=100, description="Máximo de itens (bairros)"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Prioridades]:
    if horizonte_h not in (24, 48, 72):
        raise ErroClimaSense(422, "Escolha um horizonte de 24, 48 ou 72 horas.")
    if distrito_id is not None and not re.fullmatch(r"ds-[1-8]", distrito_id):
        raise ErroClimaSense(422, "Distrito inválido. Use ds-1 a ds-8.")
    avisos_vigentes = vigentes(db, agora)
    itens = decisao.prioridades(db, nivel, horizonte_h, agora, avisos_vigentes, distrito_id)
    if nivel == "bairro":
        itens = itens[:limite]
    com_indicacao = sum(1 for i in itens if i["nivel"] in ("atencao", "alerta", "critico"))
    insuficientes = sum(1 for i in itens if i["nivel"] == "dados_insuficientes")
    if insuficientes == len(itens) and itens:
        resumo = "Não há dados suficientes para ordenar os territórios. Veja os motivos em cada item."
    elif com_indicacao == 0:
        resumo = "Nenhum território com indicação de atenção no horizonte escolhido."
    else:
        resumo = f"{com_indicacao} território(s) com indicação de atenção; o primeiro da lista pede avaliação antes."
    if insuficientes and insuficientes != len(itens):
        resumo += f" {insuficientes} sem dados suficientes."
    avisos = [
        "Experimental: não validado para uso operacional.",
        "Prioridade é uma indicação para avaliar, não uma chance de alagar.",
    ]
    if nivel == "bairro":
        avisos.append(
            "A previsão existe só por distrito: os bairros herdam a do distrito e se diferenciam pelo histórico."
        )
    return RespostaDados(
        dados=Prioridades(
            nivel_territorial=nivel,
            horizonte_h=horizonte_h,
            gerado_em=agora,
            total=len(itens),
            resumo=resumo,
            itens=itens,
        ),
        meta=Meta(
            fontes=[
                servico_fontes.meta(db, f, agora)
                for f in ("open-meteo-previsao", "open-meteo-mare", "open-meteo-historico")
            ],
            recorte=RecorteMeta(territorio_id=distrito_id or "recife", granularidade=nivel),
            avisos=avisos,
            dados_insuficientes=bool(itens) and insuficientes == len(itens),
        ),
    )


@mapa_portatil_router.get("/mapa-portatil", summary="Baixar o mapa portátil (HTML offline, porte da Aula 07)")
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
