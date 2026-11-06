"""Estágio operacional por território (F1) e mensagem para WhatsApp (F2). specs/foco-chuvas.md §4."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.api.erros import ErroClimaSense
from climasense.dominio.estagio import Parametros
from climasense.dominio.evento import RegistroInvalido
from climasense.dominio.fluxo_revisao import TransicaoNegada
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos import estagios as servico
from climasense.servicos import fontes as servico_fontes

router = APIRouter(prefix="/estagios", tags=["Evento de chuva"])
consultar = exige(Permissao.CONSULTAR)
editar = exige(Permissao.EDITAR)
parametrizar = exige(Permissao.PARAMETRIZAR)

Estagio = Literal["sem_dados", "observacao", "atencao", "alerta", "critico"]
Declaravel = Literal["observacao", "atencao", "alerta", "critico"]
# ao declarar também se pode ENCERRAR o estágio (volta a “sem declaração”); no histórico ele aparece como `encerrado`
DeclaravelOuEncerrado = Literal["observacao", "atencao", "alerta", "critico", "encerrado"]


def erro_de_negocio(funcao):
    """Converte os erros do domínio e dos serviços em problem+json com a mensagem pronta."""
    try:
        return funcao()
    except (RegistroInvalido, TransicaoNegada) as e:
        raise ErroClimaSense(e.status, e.mensagem) from None


class RiscoML(BaseModel):
    classe: str
    fatores: list[str]
    experimental: Literal[True] = True


class InsumosEstagio(BaseModel):
    chuva_24h_mm: float | None
    chuva_prev_24h_mm: float | None
    chuva_prev_72h_mm: float | None
    horas_previstas_72h: int | None
    pico_chuva_em: datetime | None
    mare_max_m: float | None
    mare_max_em: datetime | None
    mare_no_pico_m: float | None
    risco_ml: RiscoML | None
    ocorrencias_historicas: int | None
    previsao_emitida_em: datetime | None
    mare_emitida_em: datetime | None
    chuva_24h_fontes: list[str] = Field(
        default_factory=list, description="Fontes da chuva das últimas 24 h (hoje: histórico e previsão)"
    )


class Sugerido(BaseModel):
    estagio: Estagio
    rotulo: str
    motivos: list[str]
    faltando: list[str]
    insumos: InsumosEstagio
    calculado_em: datetime
    experimental: Literal[True] = True


class Declarado(BaseModel):
    id: uuid.UUID
    estagio: Declaravel
    rotulo: str
    justificativa: str
    autor_nome: str
    declarado_em: datetime
    territorio_origem_id: str
    territorio_origem_nome: str
    herdado: bool = Field(
        description="true quando a declaração é do distrito ou do Recife, não do próprio território"
    )


class AlertaOficial(BaseModel):
    """Alerta de órgão oficial (APAC, INMET, Cemaden, Defesa Civil). Reservado para o conector `alertas-oficiais`."""

    origem: str
    nivel: str
    emitido_em: datetime
    expira_em: datetime | None
    url: str | None


class ItemEstagio(BaseModel):
    territorio_id: str
    territorio_nome: str
    nivel: Literal["distrito", "bairro"]
    distrito_id: str
    herda_chuva_de: str | None = Field(
        description="Bairro: id do distrito de onde vem a chuva e a maré (RN-07)"
    )
    sugerido: Sugerido
    declarado: Declarado | None
    alertas_oficiais: list[AlertaOficial] = Field(
        default_factory=list, description="Vazio até o conector de alertas oficiais entrar (próxima onda)"
    )


class ListaEstagios(BaseModel):
    nivel: Literal["distrito", "bairro"]
    gerado_em: datetime
    parametros_versao: int | None
    itens: list[ItemEstagio]


class PedidoDeclaracao(BaseModel):
    territorio_ids: list[str] = Field(min_length=1, max_length=100)
    estagio: DeclaravelOuEncerrado
    justificativa: str = Field(max_length=500)


class Declaracao(BaseModel):
    id: uuid.UUID
    territorio_id: str
    territorio_nome: str
    nivel: str
    estagio: DeclaravelOuEncerrado
    rotulo: str
    justificativa: str
    sugerido_estagio: str | None
    lote_id: uuid.UUID
    autor_nome: str
    declarado_em: datetime


class Limiares(BaseModel):
    chuva_24h_atencao_mm: float
    chuva_24h_alerta_mm: float
    chuva_24h_critico_mm: float
    chuva_prev_24h_atencao_mm: float
    chuva_prev_24h_alerta_mm: float
    chuva_prev_24h_critico_mm: float
    chuva_prev_72h_atencao_mm: float
    chuva_prev_72h_alerta_mm: float
    chuva_prev_72h_critico_mm: float
    mare_alta_m: float
    mare_janela_h: float
    ocorrencias_bairro_minimo: float


class ParametrosEstagio(BaseModel):
    limiares: Limiares
    versao: int | None
    padrao: bool = Field(
        description="true enquanto ninguém alterou: valem os limiares propostos (a validar, P5)"
    )
    justificativa: str | None
    atualizado_em: datetime | None
    atualizado_por_nome: str | None


class PedidoParametros(BaseModel):
    """Aceita os limiares soltos no corpo ou dentro de `limiares`. O que não vier mantém o valor atual."""

    limiares: dict[str, float] | None = None
    justificativa: str | None = Field(default=None, max_length=500)
    chuva_24h_atencao_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_24h_alerta_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_24h_critico_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_prev_24h_atencao_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_prev_24h_alerta_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_prev_24h_critico_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_prev_72h_atencao_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_prev_72h_alerta_mm: float | None = Field(default=None, ge=0, le=2000)
    chuva_prev_72h_critico_mm: float | None = Field(default=None, ge=0, le=2000)
    mare_alta_m: float | None = Field(default=None, ge=0, le=20)
    mare_janela_h: float | None = None
    ocorrencias_bairro_minimo: float | None = None


class VersaoParametros(BaseModel):
    versao: int
    limiares: Limiares
    justificativa: str | None
    atualizado_em: datetime
    atualizado_por_nome: str | None


class PedidoMensagem(BaseModel):
    territorio_ids: list[str] = Field(min_length=1, max_length=100)
    estagio: Estagio
    justificativa: str | None = Field(default=None, max_length=500)


class Mensagem(BaseModel):
    texto: str
    wa_me_url: str


class PedidoUsoMensagem(BaseModel):
    evento: Literal["copiar", "abrir_whatsapp"]
    territorio_ids: list[str] = Field(min_length=1, max_length=100)
    estagio: Estagio | None = None


def _parametros(d: dict) -> ParametrosEstagio:
    return ParametrosEstagio(
        limiares=Limiares(**d["parametros"].como_dict()),
        versao=d["versao"],
        padrao=d["padrao"],
        justificativa=d["justificativa"],
        atualizado_em=d["atualizado_em"],
        atualizado_por_nome=d["atualizado_por_nome"],
    )


@router.get(
    "",
    response_model=RespostaDados[ListaEstagios],
    summary="Estágio sugerido (experimental) e declarado de cada distrito ou bairro",
)
def listar(
    nivel: Literal["distrito", "bairro"] = Query(default="distrito"),
    distrito_id: str | None = Query(
        default=None, pattern=r"^ds-[1-8]$", description="Restringe a um distrito"
    ),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[ListaEstagios]:
    itens = servico.listar(db, nivel, agora, distrito_id)
    versao = servico.parametros_atuais(db)["versao"]
    avisos = [
        "A sugestão é experimental e não muda o estágio sozinha: declarar é decisão da equipe.",
        "Estágio não é chance de alagar (RN-06). Confira na APAC e no Cemaden.",
    ]
    if nivel == "bairro":
        avisos.append("A chuva e a maré existem só por distrito: cada bairro herda as do seu distrito.")
    if versao is None:
        avisos.append("Limiares padrão, ainda não validados com a equipe.")
    sem_dados = sum(1 for i in itens if i["sugerido"]["estagio"] == "sem_dados")
    return RespostaDados(
        dados=ListaEstagios(nivel=nivel, gerado_em=agora, parametros_versao=versao, itens=itens),
        meta=Meta(
            fontes=[servico_fontes.meta(db, f, agora) for f in servico.FONTES],
            recorte=RecorteMeta(territorio_id=distrito_id or "recife", granularidade=nivel),
            avisos=avisos,
            dados_insuficientes=bool(itens) and sem_dados == len(itens),
        ),
    )


@router.post(
    "",
    response_model=list[Declaracao],
    status_code=201,
    summary="Declarar o estágio de um ou mais territórios (ato humano, auditado, sem revisão)",
)
def declarar(
    pedido: PedidoDeclaracao,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> list[Declaracao]:
    return erro_de_negocio(
        lambda: servico.declarar(
            db, pedido.territorio_ids, pedido.estagio, pedido.justificativa, ctx.usuario, ctx.ip, agora
        )
    )


@router.get(
    "/historico", response_model=list[Declaracao], summary="Declarações de estágio, mais recentes primeiro"
)
def historico(
    territorio_id: str | None = Query(default=None, description="Distrito inclui os bairros dele"),
    desde: date | None = Query(default=None, description="Dia inicial (horário do Recife)"),
    ate: date | None = Query(default=None, description="Dia final, inclusive"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
) -> list[Declaracao]:
    if desde and ate and desde > ate:
        raise ErroClimaSense(422, "A data inicial precisa ser antes da final.")
    return servico.historico(db, territorio_id, desde, ate)


@router.get("/parametros", response_model=ParametrosEstagio, summary="Limiares atuais do estágio sugerido")
def parametros(_: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)) -> ParametrosEstagio:
    return _parametros(servico.parametros_atuais(db))


@router.put(
    "/parametros",
    response_model=ParametrosEstagio,
    summary="Alterar os limiares (coordenação e administrador)",
)
def alterar_parametros(
    pedido: PedidoParametros,
    ctx: Contexto = Depends(parametrizar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> ParametrosEstagio:
    soltos = pedido.model_dump(exclude={"limiares", "justificativa"}, exclude_none=True)
    valores: dict[str, Any] = {**(pedido.limiares or {}), **soltos}
    desconhecidos = set(valores) - set(Parametros().como_dict())
    if desconhecidos:
        raise ErroClimaSense(422, "Limiar desconhecido: " + ", ".join(sorted(desconhecidos)) + ".")
    if not valores:
        raise ErroClimaSense(422, "Envie pelo menos um limiar para alterar.")
    return _parametros(
        erro_de_negocio(
            lambda: servico.alterar_parametros(db, valores, pedido.justificativa, ctx.usuario, ctx.ip, agora)
        )
    )


@router.get(
    "/parametros/historico", response_model=list[VersaoParametros], summary="Versões anteriores dos limiares"
)
def historico_parametros(
    _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao)
) -> list[VersaoParametros]:
    return servico.historico_parametros(db)


@router.post(
    "/mensagem",
    response_model=Mensagem,
    summary="Texto padronizado e link wa.me da mudança de estágio (nada é enviado)",
)
def mensagem(
    pedido: PedidoMensagem,
    ctx: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> Mensagem:
    return erro_de_negocio(
        lambda: servico.mensagem(
            db, pedido.territorio_ids, pedido.estagio, pedido.justificativa, ctx.usuario, ctx.ip, agora
        )
    )


@router.post(
    "/mensagem/uso",
    status_code=204,
    response_class=Response,
    summary="Registrar na auditoria que a mensagem foi copiada ou aberta no WhatsApp (medição do piloto)",
)
def uso_mensagem(
    pedido: PedidoUsoMensagem,
    ctx: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
) -> Response:
    erro_de_negocio(
        lambda: servico.registrar_uso(
            db, pedido.evento, pedido.territorio_ids, pedido.estagio, ctx.usuario, ctx.ip
        )
    )
    return Response(status_code=204)
