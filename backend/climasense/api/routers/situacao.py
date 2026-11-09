"""Tela Situação: chuva medida (24 h e 72 h) por distrito, estações sem leitura e a série de chuva prevista com faixa
de incerteza e maré, numa só chamada em cache (RF-19, RN-01, RN-11). Só dados agregados (RN-13)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.api.routers.cenarios import PontoChuva, PontoMare
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos import fontes as servico_fontes
from climasense.servicos import situacao_chuva as servico

router = APIRouter(prefix="/situacao", tags=["Situação"])
consultar = exige(Permissao.CONSULTAR)
FONTES = ("apac-chuva", "open-meteo-previsao", "open-meteo-mare")


class ChuvaDistrito(BaseModel):
    territorio_id: str
    territorio_nome: str
    chuva_24h_mm: float | None = Field(
        description="Maior acumulado de 24 h entre os pluviômetros do distrito (APAC); null sem leitura nas últimas 2 h"
    )
    chuva_72h_mm: float | None = Field(
        description="Soma dos 3 dias locais (hoje e 2 anteriores) do maior valor diário; null sem os 3 dias medidos"
    )
    fonte_chuva: str | None = Field(
        description="Fonte da chuva medida deste distrito ('apac-chuva'); null sem medição"
    )
    lida_em: datetime | None
    estacoes_total: int | None
    estacoes_com_leitura: int | None
    estacoes_sem_leitura: int | None
    medicao_propria: bool = Field(
        description="false = distrito sem pluviômetro próprio: não mostra chuva medida"
    )
    motivo: str | None = Field(description="'Dados insuficientes: ...' quando falta medição; null com dado")


class MaiorChuva(BaseModel):
    territorio_id: str
    territorio_nome: str
    mm: float


class EstacoesResumo(BaseModel):
    total: int | None
    com_leitura: int | None
    sem_leitura: int | None
    lida_em: datetime | None


class PrevisaoSituacao(BaseModel):
    horizonte_h: int
    previsao_emitida_em: datetime | None
    mare_emitida_em: datetime | None
    emissoes_na_faixa: int
    faixa_disponivel: bool = Field(
        description="true com 2 ou mais emissões: `min` e `max` de cada hora valem"
    )
    chuva: list[PontoChuva] = Field(
        description="Chuva prevista por hora (média dos distritos) com faixa min/max"
    )
    mare: list[PontoMare]


class HoraObservada(BaseModel):
    t: datetime = Field(description="Início da hora (UTC)")
    municipio_mm: float = Field(
        description="Maior acumulado de 1 h entre as estações do município nesta hora"
    )
    distritos: dict[str, float] = Field(
        description="Mesmo valor por distrito ('ds-1'...); distrito sem leitura na hora não aparece"
    )


class SerieObservada(BaseModel):
    fonte: str
    janela_h: int
    serie: list[HoraObservada] = Field(
        description="Últimas 72 h, uma barra por hora com leitura (lacuna, não zero)"
    )
    motivo: str | None = Field(description="'Dados insuficientes: ...' com a fonte que falta; null com série")


class SituacaoChuva(BaseModel):
    gerado_em: datetime
    distritos: list[ChuvaDistrito]
    maior_24h: MaiorChuva | None = Field(
        description="Distrito de maior chuva medida em 24 h; null sem medição"
    )
    maior_72h: MaiorChuva | None
    estacoes: EstacoesResumo
    observada: SerieObservada
    previsao: PrevisaoSituacao


@router.get(
    "/chuva",
    response_model=RespostaDados[SituacaoChuva],
    summary="Chuva medida por distrito, estações sem leitura e série prevista de chuva e maré",
)
def chuva(
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[SituacaoChuva]:
    dados = servico.montar(db, agora)
    sem_medicao = all(d["chuva_24h_mm"] is None for d in dados["distritos"])
    avisos = [
        "Previsão experimental (não validada); a faixa vai do menor ao maior valor entre as últimas emissões.",
        "Chuva medida: maior valor entre os pluviômetros da APAC no distrito; distrito sem pluviômetro próprio "
        "não mostra medição.",
    ]
    return RespostaDados(
        dados=SituacaoChuva(**dados),
        meta=Meta(
            fontes=[servico_fontes.meta(db, f, agora) for f in FONTES],
            recorte=RecorteMeta(territorio_id="recife", granularidade="distrito"),
            avisos=avisos,
            dados_insuficientes=sem_medicao and not dados["previsao"]["chuva"],
        ),
    )
