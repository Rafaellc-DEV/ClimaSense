"""Histórico de eventos de chuva e relatório executivo (RN-05, RF-19, RN-13). Escrita exige `editar`, como as ações."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.deps import configuracao
from climasense.api.routers.estagios import erro_de_negocio
from climasense.config import Configuracao
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos import eventos_chuva as servico
from climasense.servicos import relatorio_evento

router = APIRouter(prefix="/eventos", tags=["Histórico de eventos"])
consultar = exige(Permissao.CONSULTAR)
editar = exige(Permissao.EDITAR)

Situacao = Literal["aberto", "encerrado", "aprovado"]
TipoItem = Literal["comunicado", "estagio", "acao", "observacao"]
Estagio = Literal["observacao", "atencao", "alerta", "critico"]


class Distrito(BaseModel):
    id: str
    nome: str


class ItemLinhaDoTempo(BaseModel):
    id: int
    tipo: TipoItem
    tipo_rotulo: str
    texto: str
    fonte: str = Field(description="Origem do registro (RF-19); “Registro da equipe” quando não é informada")
    estagio: Estagio | None
    equipes_mobilizadas: int | None = Field(description="Número agregado de equipes; nunca nomes (RN-13)")
    ocorrido_em: datetime
    registrado_em: datetime
    autor_nome: str


class Evento(BaseModel):
    id: uuid.UUID
    nome: str
    inicio_em: datetime
    fim_em: datetime | None
    situacao: Situacao
    situacao_rotulo: str
    retrospectivo: bool
    distritos_afetados: list[str] = Field(description="Ids dos distritos marcados pela equipe (ds-1 a ds-8)")
    situacao_final: str | None
    pendencias: str | None
    duracao_horas: float | None
    aguarda_aprovacao: bool = Field(description="true = encerrado, falta a aprovação de OUTRA pessoa (RN-05)")
    aberto_por_nome: str
    aberto_em: datetime
    encerrado_por_nome: str | None
    encerrado_em: datetime | None
    aprovado_por_nome: str | None
    aprovado_em: datetime | None


class DetalheEvento(Evento):
    distritos: list[Distrito]
    linha_do_tempo: list[ItemLinhaDoTempo]


class ListaEventos(BaseModel):
    itens: list[Evento]
    contagens: dict[str, int]
    total: int


class PedidoEvento(BaseModel):
    nome: str | None = Field(default=None, max_length=160, description="Vazio = “Evento de dd/mm/aaaa”")
    inicio_em: datetime | None = Field(default=None, description="Vazio = agora")
    fim_em: datetime | None = Field(default=None, description="Só em evento retrospectivo")
    retrospectivo: bool = Field(
        default=False,
        description="Evento antigo: exige início, término e situação final; sem linha do tempo horária",
    )
    distritos_afetados: list[str] = Field(default_factory=list, max_length=8)
    situacao_final: str | None = Field(default=None, max_length=1000, description="Só retrospectivo")
    pendencias: str | None = Field(default=None, max_length=1000, description="Só retrospectivo")


class PedidoItem(BaseModel):
    tipo: TipoItem
    texto: str = Field(max_length=500)
    fonte: str | None = Field(default=None, max_length=160, description="Obrigatória em comunicado (órgão)")
    estagio: Estagio | None = Field(default=None, description="Obrigatório em tipo=estagio")
    equipes_mobilizadas: int | None = Field(default=None, ge=0, le=1000, description="Número agregado")
    ocorrido_em: datetime | None = Field(default=None, description="Vazio = agora")


class PedidoEncerramento(BaseModel):
    situacao_final: str = Field(max_length=1000)
    pendencias: str | None = Field(default=None, max_length=1000)
    fim_em: datetime | None = Field(default=None, description="Vazio = agora")


class Periodo(BaseModel):
    inicio_em: datetime
    fim_em: datetime | None
    desde: date = Field(description="Primeiro dia (Recife)")
    ate: date = Field(description="Último dia (Recife); hoje se o evento estiver em andamento")
    em_andamento: bool


class Bloco(BaseModel):
    """Todo bloco do relatório: fonte e hora (RF-19). `suficiente = false`: `motivo` traz “Dados insuficientes”."""

    fonte: str
    atualizado_em: datetime | None
    suficiente: bool
    motivo: str | None


class BlocoEvento(Bloco):
    id: uuid.UUID
    nome: str
    situacao: Situacao
    situacao_rotulo: str
    retrospectivo: bool
    inicio_em: datetime
    fim_em: datetime | None
    duracao_horas: float | None
    aberto_por_nome: str
    aberto_em: datetime
    encerrado_por_nome: str | None
    encerrado_em: datetime | None
    aprovado_por_nome: str | None
    aprovado_em: datetime | None
    aprovado: bool


class BlocoComunicados(Bloco):
    itens: list[dict[str, Any]] = Field(description="ocorrido_em, texto, fonte, autor_nome")


class BlocoEquipes(Bloco):
    maior_numero: int | None
    registros: list[dict[str, Any]] = Field(description="ocorrido_em, equipes_mobilizadas, fonte")


class BlocoDistritos(Bloco):
    com_estagio_declarado: list[dict[str, Any]] = Field(
        description="distrito_id, distrito_nome, maior_estagio, maior_estagio_rotulo, n_declaracoes, ultima_em"
    )
    registrados: list[dict[str, Any]] = Field(description="distrito_id, distrito_nome (marcados pela equipe)")


class BlocoChuva(Bloco):
    pico_diario_mm: float | None
    pico_dia: date | None = None
    pico_distrito_nome: str | None = None
    dias: list[dict[str, Any]] = Field(
        description="dia, maximo_mm (nulo = sem dado), distrito_nome, distritos_com_dado"
    )


class BlocoMare(Bloco):
    maximo_m: float | None
    dias: list[dict[str, Any]] = Field(description="dia, maximo_m, minimo_m, horas_com_dado")


class AgravoJanela(Bloco):
    agravo: str
    nome: str
    semanas: list[dict[str, Any]] = Field(
        description="ano, semana, inicio, casos, confirmados, casos_estimados, ic_inf, ic_sup, nivel_alerta, "
        "incompleta, suprimido (casos nulos com suprimido = contagem pequena escondida, RN-13)"
    )
    total_casos: int | None
    suprimido: bool


class BlocoSaude(BaseModel):
    supressao_minima: int
    suficiente: bool
    itens: list[AgravoJanela]


class BlocoAcoes(Bloco):
    contagens: dict[str, int]
    itens: list[dict[str, Any]]


class BlocoLinhaDoTempo(Bloco):
    itens: list[dict[str, Any]] = Field(description="em, tipo, texto, fonte, em ordem de hora")


class BlocoSituacaoFinal(Bloco):
    situacao_final: str | None
    pendencias: str | None
    encerrado_por_nome: str | None = None
    aprovada: bool = False
    aprovado_por_nome: str | None = None
    aprovado_em: datetime | None = None


class RelatorioEvento(BaseModel):
    gerado_em: datetime
    periodo: Periodo
    aviso: str | None = Field(description="Rascunho enquanto a situação final não foi aprovada (RN-05)")
    evento: BlocoEvento
    comunicados: BlocoComunicados
    equipes_mobilizadas: BlocoEquipes
    distritos_afetados: BlocoDistritos
    chuva: BlocoChuva
    mare: BlocoMare
    saude: BlocoSaude
    acoes: BlocoAcoes
    linha_do_tempo: BlocoLinhaDoTempo
    situacao_final: BlocoSituacaoFinal


@router.get("", response_model=ListaEventos, summary="Listar eventos de chuva registrados")
def listar(
    situacao: Situacao | None = None,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
) -> ListaEventos:
    return erro_de_negocio(lambda: servico.listar(db, situacao))


@router.post("", response_model=DetalheEvento, status_code=201, summary="Abrir evento de chuva")
def abrir(
    pedido: PedidoEvento,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheEvento:
    return erro_de_negocio(lambda: servico.abrir(db, pedido.model_dump(), ctx.usuario, ctx.ip, agora))


@router.get("/{evento_id}", response_model=DetalheEvento, summary="Abrir um evento com a linha do tempo")
def detalhe(
    evento_id: uuid.UUID, _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> DetalheEvento:
    return erro_de_negocio(lambda: servico.obter(db, evento_id))


@router.post(
    "/{evento_id}/itens",
    response_model=DetalheEvento,
    status_code=201,
    summary="Registrar item na linha do tempo (comunicado, estágio, ação ou observação)",
)
def registrar_item(
    evento_id: uuid.UUID,
    pedido: PedidoItem,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheEvento:
    return erro_de_negocio(
        lambda: servico.registrar_item(db, evento_id, pedido.model_dump(), ctx.usuario, ctx.ip, agora)
    )


@router.post(
    "/{evento_id}/encerrar",
    response_model=DetalheEvento,
    summary="Encerrar o evento com situação final e pendências (falta a aprovação de outra pessoa)",
)
def encerrar(
    evento_id: uuid.UUID,
    pedido: PedidoEncerramento,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheEvento:
    return erro_de_negocio(
        lambda: servico.encerrar(db, evento_id, pedido.model_dump(), ctx.usuario, ctx.ip, agora)
    )


@router.post(
    "/{evento_id}/aprovar",
    response_model=DetalheEvento,
    summary="Aprovar a situação final (RN-05: outra pessoa, que não abriu nem encerrou o evento)",
)
def aprovar(
    evento_id: uuid.UUID,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> DetalheEvento:
    return erro_de_negocio(lambda: servico.aprovar(db, evento_id, ctx.usuario, ctx.ip, agora))


@router.get(
    "/{evento_id}/relatorio",
    response_model=RelatorioEvento,
    summary="Relatório executivo do evento, só com dados reais; cada bloco com fonte e hora",
)
def relatorio(
    evento_id: uuid.UUID,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
    config: Configuracao = Depends(configuracao),
) -> RelatorioEvento:
    return erro_de_negocio(lambda: relatorio_evento.montar(db, evento_id, agora, config.supressao_minima))
