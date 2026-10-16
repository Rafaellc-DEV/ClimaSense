"""Cenários de alagamento (T6.4). Tudo aqui é EXPERIMENTAL (RN-11) e a prioridade nunca é probabilidade (RN-06)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.api.erros import ErroClimaSense
from climasense.dominio import cenario
from climasense.dominio.papeis import Permissao
from climasense.dominio.recorte import granularidade
from climasense.infra.postgres import obter_sessao
from climasense.servicos import cenarios as servico
from climasense.servicos import fontes as servico_fontes
from climasense.servicos.series import FONTE_CHUVA
from climasense.servicos.territorio import no_maximo_distrito

router = APIRouter(prefix="/cenarios", tags=["Cenários de alagamento"])
consultar = exige(Permissao.CONSULTAR)


class PontoChuva(BaseModel):
    t: datetime
    valor: float | None
    min: float | None
    max: float | None


class PontoMare(BaseModel):
    t: datetime
    valor: float | None


class Fator(BaseModel):
    nome: str
    descricao: str


class JanelaAtencao(BaseModel):
    inicio: datetime
    fim: datetime


class EstimativaSaida(BaseModel):
    experimental: Literal[True] = True
    metodo: str
    versao_metodo: str
    emitida_em: datetime
    horizonte_h: int
    prioridade: cenario.Prioridade
    qualidade: cenario.Qualidade
    janela_atencao: JanelaAtencao | None
    fatores: list[Fator]
    limitacoes: list[str]
    acumulado_previsto_mm: float | None
    mare_maxima_m: float | None
    mare_maxima_em: datetime | None
    limite_atencao_mm: float | None
    limite_alerta_mm: float | None


class Cenario(BaseModel):
    territorio_id: str
    territorio_nome: str
    horizonte_h: int
    previsao_emitida_em: datetime | None
    mare_emitida_em: datetime | None
    emissoes_na_faixa: int
    chuva: list[PontoChuva]
    mare: list[PontoMare]
    estimativa: EstimativaSaida
    registro_id: int


@router.get(
    "", response_model=RespostaDados[Cenario], summary="Cenário experimental: previsão, maré e prioridade"
)
def cenarios(
    territorio_id: str = "recife",
    horizonte_h: int = Query(default=72, description="24, 48 ou 72 horas"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Cenario]:
    if horizonte_h not in cenario.HORIZONTES:
        raise ErroClimaSense(422, "Escolha um horizonte de 24, 48 ou 72 horas.")
    t = no_maximo_distrito(db, territorio_id)
    r = servico.emitir(db, t.usado, horizonte_h, agora)
    est: cenario.Estimativa = r["estimativa"]
    estimativa = EstimativaSaida(
        metodo=cenario.METODO,
        versao_metodo=cenario.VERSAO,
        emitida_em=agora,
        horizonte_h=horizonte_h,
        prioridade=est.prioridade,
        qualidade=est.qualidade,
        janela_atencao=JanelaAtencao(inicio=est.janela_atencao.inicio, fim=est.janela_atencao.fim)
        if est.janela_atencao
        else None,
        fatores=[Fator(nome=n, descricao=d) for n, d in est.fatores],
        limitacoes=est.limitacoes,
        acumulado_previsto_mm=est.acumulado_previsto_mm,
        mare_maxima_m=est.mare_maxima_m,
        mare_maxima_em=est.mare_maxima_em,
        limite_atencao_mm=est.p95_mm,
        limite_alerta_mm=est.p99_mm,
    )
    dados = Cenario(
        territorio_id=t.usado,
        territorio_nome=t.nome,
        horizonte_h=horizonte_h,
        previsao_emitida_em=r["previsao_emitida_em"],
        mare_emitida_em=r["mare_emitida_em"],
        emissoes_na_faixa=r["emissoes_na_faixa"],
        chuva=[PontoChuva(**p) for p in r["chuva"]],
        mare=[PontoMare(**p) for p in r["mare"]],
        estimativa=estimativa,
        registro_id=r["registro_id"],
    )
    avisos = ["Experimental: não validado para uso operacional."] + t.avisos
    if r["emissoes_na_faixa"] < 2:
        avisos.append(
            "Só há uma emissão da previsão: a faixa de incerteza aparece depois da próxima atualização."
        )
    return RespostaDados(
        dados=dados,
        meta=Meta(
            fontes=[
                servico_fontes.meta(db, f, agora)
                for f in (servico.FONTE_PREVISAO, servico.FONTE_MARE, FONTE_CHUVA)
            ],
            recorte=RecorteMeta(territorio_id=t.usado, granularidade=granularidade(t.usado)),
            avisos=avisos,
            dados_insuficientes=est.prioridade == "dados_insuficientes",
        ),
    )
