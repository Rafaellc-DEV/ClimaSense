"""Boletim situacional (F5): uma página imprimível e o resumo para WhatsApp. specs/foco-chuvas.md §4."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.auditoria_leitura import LEITURA_BOLETIM, auditar_leitura
from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.api.erros import ErroClimaSense
from climasense.api.routers.abrigos import Abrigo, SituacaoEvento, TotaisAbrigos, fontes_abrigos
from climasense.api.routers.acoes import Acao, AndamentoDistrito
from climasense.api.routers.estagios import Declarado, EstagioOficial, Mensagem, Sugerido, _fonte_oficial
from climasense.api.routers.saude_agravos import ResumoAgravo
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
FONTES_SAUDE = ("infodengue", "sinan-leptospirose")


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
    situacao: SituacaoEvento = Field(
        description="Abertos, abrigados e desabrigados na cidade e por distrito; null = sem registro (RN-01)"
    )


class PeriodoBoletim(BaseModel):
    desde: date
    ate: date


class Boletim(BaseModel):
    territorio_id: str
    territorio_nome: str
    gerado_em: datetime
    estagios: list[EstagioDistrito]
    territorios_em_atencao: list[TerritorioEmAtencao]
    chuva: ChuvaBoletim
    mare: MareBoletim
    abrigos: AbrigosBoletim
    acoes_em_andamento: list[Acao] = Field(
        description="Em andamento agora, distritos mais vulneráveis primeiro (RF-22)"
    )
    periodo: PeriodoBoletim = Field(description="Período do relatório executivo (RF-17)")
    estagio_oficial: EstagioOficial | None = Field(
        description="Estágio oficial do COP para a cidade (não há oficial por distrito); null = sem registro"
    )
    acoes_concluidas: list[Acao] = Field(description="Concluídas dentro do período")
    acoes_por_distrito: list[AndamentoDistrito] = Field(
        description="Ações do período por distrito e situação"
    )
    saude: list[ResumoAgravo] = Field(description="Agravos na última semana com dado, no município")


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
    desde: date | None = Query(default=None, description="Início do período (padrão: 7 dias até hoje)"),
    ate: date | None = Query(default=None, description="Fim do período (padrão: hoje, no Recife)"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Boletim]:
    if desde and ate and desde > ate:
        raise ErroClimaSense(422, "A data inicial precisa ser antes da final.")
    t = _recorte(db, territorio_id)
    b = servico.montar(db, _distrito(t), agora, desde, ate)
    avisos = [
        *t.avisos,
        "O estágio sugerido é experimental; o declarado é decisão da equipe. Não substitui a Defesa Civil.",
        "Confira na APAC e no Cemaden.",
        "O estágio oficial do COP é da cidade; não há oficial por distrito.",
    ]
    fontes = [servico_fontes.meta(db, f, agora) for f in (*estagios.FONTES, *FONTES_SAUDE)]
    fontes += [f for f in fontes_abrigos(db, b["abrigos"]["situacao"]["ocupacao_atualizada_em"], agora)]
    fontes.append(_fonte_oficial(b["estagio_oficial"], agora))
    vistas: set[str] = set()
    fontes = [f for f in fontes if not (f.id in vistas or vistas.add(f.id))]
    return RespostaDados(
        dados=Boletim(territorio_id=t.usado, territorio_nome=t.nome, **b),
        meta=Meta(
            fontes=fontes,
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
    desde: date | None = None,
    ate: date | None = None,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> Mensagem:
    if desde and ate and desde > ate:
        raise ErroClimaSense(422, "A data inicial precisa ser antes da final.")
    t = _recorte(db, territorio_id)
    return servico.texto(servico.montar(db, _distrito(t), agora, desde, ate), t.nome)
