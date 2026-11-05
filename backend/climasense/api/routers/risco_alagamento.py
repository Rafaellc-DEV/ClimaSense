"""Risco de alagamento por bairro (F6). EXPERIMENTAL (RN-11); classe de risco, nunca probabilidade (RN-06).

Só lê o modelo salvo em arquivo; nunca treina na requisição. Sem modelo publicado (ocorrências reais
insuficientes ou desempenho abaixo da referência simples) → `disponivel: false` com o motivo e nenhum item
(RF-12.10).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.ml.alagamento import servico
from climasense.servicos import fontes as servico_fontes

router = APIRouter(prefix="/risco-alagamento", tags=["Risco de alagamento (experimental)"])
consultar = exige(Permissao.CONSULTAR)

Classe = Literal["baixo", "moderado", "alto", "sem_dados"]


class ModeloRisco(BaseModel):
    versao: str
    metodo: str
    treinado_em: str
    experimental: Literal[True] = True
    validacao: dict


class ItemRisco(BaseModel):
    territorio_id: str
    classe: Classe
    fatores: list[str]


class RiscoAlagamento(BaseModel):
    disponivel: bool
    motivo: str | None = None
    experimental: Literal[True] = True
    modelo: ModeloRisco | None
    itens: list[ItemRisco]


@router.get(
    "",
    response_model=RespostaDados[RiscoAlagamento],
    summary="Classe de risco de alagamento por bairro (hoje e amanhã), com fatores; experimental",
)
def risco_alagamento(
    nivel: Literal["bairro", "distrito"] = Query(default="bairro"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[RiscoAlagamento]:
    dados = servico.payload(db, agora, nivel)
    avisos = [servico.AVISO_EXPERIMENTAL]
    if nivel == "bairro":
        avisos.append("A chuva é do distrito; cada bairro herda a do seu distrito (RN-07).")
    avisos.append(
        "Rótulo do modelo: atendimentos de alagamento da Defesa Civil (data da vistoria, não do evento); "
        "ausência de registro não prova que não alagou."
    )
    return RespostaDados(
        dados=RiscoAlagamento(**dados),
        meta=Meta(
            fontes=[
                servico_fontes.meta(db, f, agora)
                for f in (servico.FONTE_HISTORICO, servico.FONTE_PREVISAO, servico.FONTE_ROTULO)
            ],
            recorte=RecorteMeta(territorio_id="recife", granularidade=nivel),
            avisos=avisos,
            dados_insuficientes=not dados["disponivel"],
        ),
    )
