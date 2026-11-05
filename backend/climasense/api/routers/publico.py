"""Rotas públicas da landing (T7.6, RF-01). Só mostram comunicados PUBLICADOS e VIGENTES (RN-04, RN-14):
o filtro `validade_fim > agora` vale mesmo que a tarefa de expiração atrase (T7.5).

`/publico/abrigos` lista os locais sem nomes de servidores, autores nem ocupação detalhada."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from climasense.api.autorizacao import relogio
from climasense.api.erros import ErroClimaSense
from climasense.dominio import comunicado as dominio
from climasense.dominio.territorio import normalizar_busca
from climasense.infra.modelos_sql import Comunicado, ComunicadoVersao
from climasense.infra.postgres import obter_sessao
from climasense.servicos import fontes as servico_fontes

router = APIRouter(prefix="/publico", tags=["Público"])
ORDEM_NIVEL = {"critico": 4, "alerta": 3, "atencao": 2, "informativo": 1}


class TerritorioRef(BaseModel):
    id: str
    tipo: str
    nome_exibicao: str


class AvisoPublico(BaseModel):
    id: uuid.UUID
    titulo: str
    nivel: str
    territorios: list[TerritorioRef]
    texto: str
    orientacoes: list[str]
    validade_inicio: datetime
    validade_fim: datetime
    emitido_por: str
    publicado_em: datetime | None
    publico: str


class EstadoPublico(BaseModel):
    avisos_ativos: int
    distritos_afetados: list[str]
    niveis_por_distrito: dict[str, str]
    nivel_mais_alto: str | None
    principal: AvisoPublico | None
    atualizado_em: datetime


def _refs(db: Session, ids: list[str]) -> list[TerritorioRef]:
    linhas = {
        r.id: r
        for r in db.execute(
            text("select id, tipo, nome_exibicao from app.territorios where id = any(:i)"), {"i": ids}
        )
    }
    return [
        TerritorioRef(id=i, tipo=linhas[i].tipo, nome_exibicao=linhas[i].nome_exibicao)
        for i in ids
        if i in linhas
    ]


def aviso_publico(db: Session, c: Comunicado, v: ComunicadoVersao) -> AvisoPublico:
    """O MESMO formato para a landing e para a prévia do editor (RF-11.3): a prévia mostra exatamente a versão."""
    return AvisoPublico(
        id=c.id,
        titulo=v.titulo,
        nivel=v.nivel,
        territorios=_refs(db, v.territorios),
        texto=v.texto,
        orientacoes=v.orientacoes,
        validade_inicio=v.validade_inicio,
        validade_fim=v.validade_fim,
        emitido_por=dominio.EMITIDO_POR,
        publicado_em=c.publicado_em,
        publico=v.publico,
    )


def vigentes(db: Session, agora: datetime) -> list[AvisoPublico]:
    linhas = db.execute(
        select(Comunicado, ComunicadoVersao)
        .join(
            ComunicadoVersao,
            (ComunicadoVersao.comunicado_id == Comunicado.id)
            & (ComunicadoVersao.numero == Comunicado.versao_atual),
        )
        .where(
            Comunicado.estado == "publicado",
            Comunicado.versao_aprovada == Comunicado.versao_atual,
            Comunicado.validade_inicio <= agora,
            Comunicado.validade_fim > agora,
        )
    ).all()
    avisos = [aviso_publico(db, c, v) for c, v in linhas]
    return sorted(
        avisos, key=lambda a: (-ORDEM_NIVEL[a.nivel], -(a.publicado_em.timestamp() if a.publicado_em else 0))
    )


def _distritos(db: Session, territorios: list[TerritorioRef]) -> set[str]:
    resultado = set()
    for t in territorios:
        if t.tipo in ("distrito", "municipio"):
            resultado.add(t.id)
        else:
            pai = db.execute(text("select pai_id from app.territorios where id = :i"), {"i": t.id}).scalar()
            if pai:
                resultado.add(pai)
    return resultado


@router.get(
    "/estado", response_model=EstadoPublico, summary="Estado dos avisos para o topo da página inicial"
)
def estado(db: Session = Depends(obter_sessao), agora: datetime = Depends(relogio)) -> EstadoPublico:
    avisos = vigentes(db, agora)
    niveis: dict[str, str] = {}
    for a in avisos:  # do mais alto para o mais baixo: o distrito fica com o nível mais alto
        for d in _distritos(db, a.territorios):
            niveis.setdefault(d, a.nivel)
    return EstadoPublico(
        avisos_ativos=len(avisos),
        distritos_afetados=sorted(niveis),
        niveis_por_distrito=niveis,
        nivel_mais_alto=avisos[0].nivel if avisos else None,
        principal=avisos[0] if avisos else None,
        atualizado_em=agora,
    )


@router.get(
    "/avisos", response_model=list[AvisoPublico], summary="Avisos publicados e vigentes, do nível mais alto"
)
def avisos(
    bairro: str | None = Query(
        default=None, max_length=60, description="Nome do bairro, sem diferenciar acentos"
    ),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> list[AvisoPublico]:
    lista = vigentes(db, agora)
    if not bairro:
        return lista
    agulha = normalizar_busca(bairro)
    bairros = db.execute(
        text("select id, pai_id, nome_exibicao from app.territorios where tipo = 'bairro'")
    ).all()
    alvos = {b for b, _, n in bairros if agulha in normalizar_busca(n)}
    distritos = {p for b, p, _ in bairros if b in alvos}
    return [
        a for a in lista if any(t.id in alvos or t.id in distritos or t.id == "recife" for t in a.territorios)
    ]


@router.get("/avisos/{aviso_id}", response_model=AvisoPublico, summary="Detalhe de um aviso publicado")
def aviso(
    aviso_id: uuid.UUID, db: Session = Depends(obter_sessao), agora: datetime = Depends(relogio)
) -> AvisoPublico:
    for a in vigentes(db, agora):
        if a.id == aviso_id:
            return a
    raise ErroClimaSense(404, "Este aviso não está mais em vigor ou não existe.")


class FontePublica(BaseModel):
    id: str
    nome: str
    orgao: str
    tipo: str
    status: str
    ultima_atualizacao: datetime | None


@router.get("/fontes", response_model=list[FontePublica], summary="De onde vêm os dados (status das fontes)")
def fontes(db: Session = Depends(obter_sessao), agora: datetime = Depends(relogio)) -> list[FontePublica]:
    return [
        FontePublica(
            **{k: f[k] for k in ("id", "nome", "orgao", "tipo", "status")},
            ultima_atualizacao=f["ultimo_sucesso"],
        )
        for f in servico_fontes.linhas(db, agora)
    ]


# ------------------------------------------------------------------ abrigos (landing)
AVISO_ABRIGOS = (
    "Lista de locais que podem servir de abrigo ou ponto de apoio, montada a partir dos Dados Abertos da "
    "Prefeitura do Recife, do feed de abrigos ativos do COP e dos registros da equipe de Vigilância em Saúde. "
    "“Aberto” só aparece quando o COP ou a equipe informou; sem essa informação, o local não está "
    "necessariamente funcionando. Antes de se deslocar, ligue para a Defesa Civil do Recife: 0800 081 3400 "
    "(gratuito, 24 horas) ou para a Defesa Civil de Pernambuco: 199."
)

SQL_ABRIGOS_PUBLICOS = """
with equipe as (
  select abrigo_id, max(em) as em from app.abrigo_atualizacoes where autor_id is not null group by abrigo_id
), base as (
  select a.id, a.nome, a.endereco, b.nome_exibicao as bairro_nome, d.nome_exibicao as distrito_nome,
         a.latitude, a.longitude, a.aberto, a.origem, a.fonte_url, a.tipo_local,
         coalesce(a.capacidade, a.capacidade_fonte) as capacidade,
         case when e.em is not null and (a.status_lido_em is null or e.em >= a.status_lido_em) then 'equipe'
              when a.status_origem = 'cop' then 'cop'
              when a.origem = 'manual' then 'equipe' end as aberto_fonte,
         a.status_lido_em, e.em as equipe_em, a.atualizado_em
  from app.abrigos a join app.territorios b on b.id = a.bairro_id
  left join app.territorios d on d.id = b.pai_id
  left join equipe e on e.abrigo_id = a.id
)
select id, nome, endereco, bairro_nome, distrito_nome, latitude, longitude,
       case when aberto_fonte is not null then aberto end as aberto,
       aberto_fonte,
       case aberto_fonte when 'cop' then status_lido_em when 'equipe' then coalesce(equipe_em, atualizado_em) end
         as aberto_lido_em,
       origem, fonte_url, tipo_local as tipo, capacidade
from base
order by (case when aberto_fonte is not null then aberto end) desc nulls last, nome
"""


class AbrigoPublico(BaseModel):
    id: uuid.UUID
    nome: str
    endereco: str | None
    bairro_nome: str
    distrito_nome: str | None
    latitude: float | None
    longitude: float | None
    aberto: bool | None
    aberto_fonte: Literal["cop", "equipe"] | None
    aberto_lido_em: datetime | None
    atualizado_em: datetime | None
    origem: str
    fonte_url: str | None
    tipo: str | None
    capacidade: int | None


class ListaAbrigosPublica(BaseModel):
    itens: list[AbrigoPublico]
    atualizado_em: datetime | None
    aviso: str


@router.get(
    "/abrigos",
    response_model=ListaAbrigosPublica,
    summary="Abrigos e pontos de apoio (sem dados pessoais nem ocupação detalhada)",
)
def abrigos_publicos(db: Session = Depends(obter_sessao)) -> ListaAbrigosPublica:
    itens = [
        AbrigoPublico(**dict(r), atualizado_em=r["aberto_lido_em"])
        for r in db.execute(text(SQL_ABRIGOS_PUBLICOS)).mappings()
    ]
    carga = db.execute(
        text(
            "select max(fim) from app.etl_execucoes where fonte_id = 'recife-abrigos' and status = 'sucesso'"
        )
    ).scalar()
    datas = [d for d in [carga, *(i.aberto_lido_em for i in itens)] if d is not None]
    return ListaAbrigosPublica(itens=itens, atualizado_em=max(datas) if datas else None, aviso=AVISO_ABRIGOS)
