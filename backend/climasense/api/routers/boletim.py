"""Boletim situacional (F5): uma página imprimível e o resumo para WhatsApp. specs/foco-chuvas.md §4."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from climasense.api.auditoria_leitura import LEITURA_BOLETIM, auditar_leitura
from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.api.routers.abrigos import Abrigo, TotaisAbrigos
from climasense.api.routers.acoes import Acao
from climasense.api.routers.estagios import Declarado, Mensagem, Sugerido
from climasense.dominio.papeis import Permissao
from climasense.dominio.recorte import granularidade
from climasense.infra.postgres import obter_sessao
from climasense.servicos import boletim as servico
from climasense.servicos import estagios
from climasense.servicos import fontes as servico_fontes
from climasense.servicos.territorio import TerritorioUsado, no_maximo_distrito

router = APIRouter(
    prefix="/boletim",
    tags=["Evento de chuva"],
    dependencies=[Depends(auditar_leitura(LEITURA_BOLETIM))],  # RNF-01: quem leu qual rota
)
consultar = exige(Permissao.CONSULTAR)


class EstagioDistrito(BaseModel):
    territorio_id: str
    territorio_nome: str
    estagio: str
    rotulo: str
    origem: str  # declarado | sugerido
    sugerido: Sugerido
    declarado: Declarado | None


class TerritorioEmAtencao(BaseModel):
    territorio_id: str
    territorio_nome: str
    nivel: str
    distrito_id: str
    estagio: str
    rotulo: str
    origem: str
    motivo: str


class ChuvaBoletim(BaseModel):
    chuva_24h_mm: float | None
    chuva_24h_territorio: str | None
    chuva_prev_24h_mm: float | None
    chuva_prev_24h_territorio: str | None
    chuva_prev_72h_mm: float | None
    chuva_prev_72h_territorio: str | None
    previsao_emitida_em: datetime | None


class MareBoletim(BaseModel):
    maxima_m: float | None
    maxima_em: datetime | None
    emitida_em: datetime | None


class AbrigosBoletim(BaseModel):
    totais: TotaisAbrigos
    abertos: list[Abrigo]


class Boletim(BaseModel):
    territorio_id: str
    territorio_nome: str
    gerado_em: datetime
    estagios: list[EstagioDistrito]
    territorios_em_atencao: list[TerritorioEmAtencao]
    chuva: ChuvaBoletim
    mare: MareBoletim
    abrigos: AbrigosBoletim
    acoes_em_andamento: list[Acao]


def _recorte(db: Session, territorio_id: str) -> TerritorioUsado:
    return no_maximo_distrito(db, territorio_id)


def _distrito(t: TerritorioUsado) -> str | None:
    return None if t.usado == "recife" else t.usado


@router.get(
    "",
    response_model=RespostaDados[Boletim],
    summary="Retrato consolidado do evento para a página do boletim",
)
def boletim(
    territorio_id: str = Query(
        default="recife", description="recife ou ds-1 a ds-8 (bairro vira o distrito)"
    ),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Boletim]:
    t = _recorte(db, territorio_id)
    b = servico.montar(db, _distrito(t), agora)
    avisos = [
        *t.avisos,
        "O estágio sugerido é experimental; o declarado é decisão da equipe. Não substitui a Defesa Civil.",
        "Confira na APAC e no Cemaden.",
    ]
    return RespostaDados(
        dados=Boletim(territorio_id=t.usado, territorio_nome=t.nome, **b),
        meta=Meta(
            fontes=[servico_fontes.meta(db, f, agora) for f in estagios.FONTES],
            recorte=RecorteMeta(territorio_id=t.usado, granularidade=granularidade(t.usado)),
            avisos=avisos,
            dados_insuficientes=bool(b["estagios"])
            and all(e["sugerido"]["estagio"] == "sem_dados" for e in b["estagios"]),
        ),
    )


@router.get(
    "/texto", response_model=Mensagem, summary="Resumo do boletim em texto para WhatsApp (nada é enviado)"
)
def texto(
    territorio_id: str = Query(default="recife"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> Mensagem:
    t = _recorte(db, territorio_id)
    return servico.texto(servico.montar(db, _distrito(t), agora), t.nome)
