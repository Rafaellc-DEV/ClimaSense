"""Simulador de cenário (PRD §8, RF-23 a RF-28) e estimativa de alagamento por distrito (T6.4).

Tudo aqui é EXPERIMENTAL (RN-11). A classe de risco é ordinal, nunca probabilidade nem percentual (RN-06).
A antiga `GET /cenarios` passou para `GET /cenarios/estimativa`, para dar a raiz à lista de cenários salvos.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import FonteMeta, Meta, RecorteMeta, RespostaDados
from climasense.api.erros import ErroClimaSense
from climasense.dominio import cenario
from climasense.dominio import simulador as dom_sim
from climasense.dominio.evento import RegistroInvalido
from climasense.dominio.papeis import Permissao
from climasense.dominio.recorte import granularidade
from climasense.infra.postgres import obter_sessao
from climasense.servicos import cenarios as servico
from climasense.servicos import fontes as servico_fontes
from climasense.servicos import simulador as sim
from climasense.servicos.series import FONTE_CHUVA
from climasense.servicos.territorio import no_maximo_distrito

router = APIRouter(prefix="/cenarios", tags=["Cenários de alagamento"])
consultar = exige(Permissao.CONSULTAR)
editar = exige(Permissao.EDITAR)


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
    "/estimativa",
    response_model=RespostaDados[Cenario],
    summary="Estimativa experimental por distrito: previsão, maré e prioridade (antiga GET /cenarios)",
)
def estimativa(
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


# ------------------------------------------------------------------ simulador (PRD §8)
Classe = Literal["sem_dados", "observacao", "atencao", "alerta", "critico"]


def erro_de_negocio(funcao):
    try:
        return funcao()
    except RegistroInvalido as e:
        raise ErroClimaSense(e.status, e.mensagem) from None


class PremissasAtuais(BaseModel):
    """Valores sugeridos a partir das fontes reais; `null` = a fonte falta (Dados insuficientes)."""

    chuva_prevista_mm: float | None = Field(
        description="Maior chuva prevista em 24 h entre os distritos (Open-Meteo)"
    )
    duracao_h: float | None
    chuva_acumulada_mm: float | None = Field(
        description="Chuva medida nas últimas 72 h (APAC), maior entre os distritos"
    )
    mare_m: float | None = Field(description="Maré máxima prevista no horizonte (Open-Meteo)")
    horizonte_h: int
    abrigos_abertos: int | None
    capacidade_abrigos: int | None


class PedidoSimulacao(BaseModel):
    chuva_prevista_mm: float = Field(ge=0, le=600, description="Volume previsto, em mm, durante a duração")
    duracao_h: float = Field(gt=0, le=72, description="Duração da chuva prevista, em horas (até 72)")
    chuva_acumulada_mm: float | None = Field(
        ge=0, le=800, description="Chuva dos 3 dias anteriores, em mm; null = desconhecida (RN-01)"
    )
    mare_m: float | None = Field(
        ge=-3, le=5, description="Nível previsto da maré junto do pico, em m; null = desconhecido"
    )
    horizonte_h: int = Field(ge=1, le=72, description="Próximas horas do cenário")
    abrigos_abertos: int | None = Field(default=None, ge=0, le=500)
    capacidade_abrigos: int | None = Field(default=None, ge=0, le=200000)

    def premissas(self) -> dom_sim.Premissas:
        if self.duracao_h > self.horizonte_h:
            raise RegistroInvalido(422, "A duração da chuva não pode passar do horizonte do cenário.")
        return dom_sim.Premissas(**self.model_dump())


class ImpactoPessoas(BaseModel):
    idosos: int | None
    criancas: int | None
    equipamentos_saude: int | None
    total_pessoas: int | None
    criterio: str


class ItemSimulacao(BaseModel):
    territorio_id: str
    nome: str
    nivel: Literal["bairro", "distrito"]
    distrito_id: str
    classe_alagamento: Classe
    classe_deslizamento: Classe
    estagio_sugerido: Classe = Field(description="Apoio à decisão; não é o estágio oficial nem o declarado")
    confianca: Literal["alta", "media", "baixa", "insuficiente"]
    motivos: list[str] = Field(description="De 1 a 3 frases curtas")
    impacto_pessoas: ImpactoPessoas | None = Field(
        description="null até a população vulnerável ser integrada (Etapa 6)"
    )


class ResumoSimulacao(BaseModel):
    por_classe: dict[str, dict[str, int]] = Field(
        description="Contagem de bairros por classe: alagamento, deslizamento e estagio_sugerido"
    )
    pressao_abrigos: str | None
    impacto_pessoas_aviso: str | None


class Simulacao(BaseModel):
    itens: list[ItemSimulacao]
    resumo: ResumoSimulacao
    experimental: Literal[True] = True
    calculado_em: datetime
    tempo_calculo_ms: int


def _fontes_simulacao(db: Session, agora: datetime) -> list[FonteMeta]:
    return [servico_fontes.meta(db, sim.FONTE_OCORRENCIAS, agora)]


FONTE_POR_PREMISSA = {
    "chuva_prevista_mm": servico.FONTE_PREVISAO,
    "duracao_h": servico.FONTE_PREVISAO,
    "chuva_acumulada_mm": sim.FONTE_APAC,
    "mare_m": servico.FONTE_MARE,
    "abrigos_abertos": "recife-abrigos",
    "capacidade_abrigos": "recife-abrigos",
}

AVISOS_SIMULACAO = [
    "Experimental: regras sobre os limiares dos estágios, ainda sem validação temporal. "
    "A classe é uma ordem de atenção, não uma probabilidade."
]


@router.get(
    "/premissas-atuais",
    response_model=RespostaDados[PremissasAtuais],
    summary="Premissas sugeridas pelas fontes reais (previsão, maré, chuva medida e abrigos)",
)
def premissas_atuais(
    _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao), agora: datetime = Depends(relogio)
) -> RespostaDados[PremissasAtuais]:
    dados = sim.premissas_atuais(db, agora)
    faltam = [k for k, v in dados.items() if v is None]
    return RespostaDados(
        dados=PremissasAtuais(**dados),
        meta=Meta(
            fontes=[
                servico_fontes.meta(db, f, agora)
                for f in (servico.FONTE_PREVISAO, servico.FONTE_MARE, sim.FONTE_APAC, "recife-abrigos")
            ],
            recorte=RecorteMeta(territorio_id="recife", granularidade="municipio"),
            fonte_por_premissa=FONTE_POR_PREMISSA,
            avisos=[f"Dados insuficientes para: {', '.join(faltam)}. Preencha à mão."] if faltam else [],
            dados_insuficientes=bool(faltam),
        ),
    )


@router.post(
    "/simular",
    response_model=RespostaDados[Simulacao],
    summary="Simular um cenário por regras: classe de alagamento e deslizamento por bairro e distrito",
)
def simular(
    pedido: PedidoSimulacao,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Simulacao]:
    p = erro_de_negocio(pedido.premissas)
    dados = sim.simular(db, p, agora)
    return RespostaDados(
        dados=Simulacao(**dados),
        meta=Meta(
            fontes=_fontes_simulacao(db, agora),
            recorte=RecorteMeta(territorio_id="recife", granularidade="bairro"),
            avisos=AVISOS_SIMULACAO,
            fonte_por_premissa=FONTE_POR_PREMISSA,
        ),
    )


class PedidoSalvar(BaseModel):
    nome: str = Field(min_length=1, max_length=120, description="Nome curto; não escreva dado de pessoas")
    premissas: PedidoSimulacao
    resultado: dict | None = Field(
        default=None, description="Ignorado: o servidor recalcula e guarda o próprio resultado"
    )


class ResumoSalvo(BaseModel):
    por_classe: dict[str, dict[str, int]] | None
    pressao_abrigos: str | None


class CenarioListado(BaseModel):
    id: uuid.UUID
    nome: str
    autor_nome: str
    criado_em: datetime
    resumo: ResumoSalvo


class ResultadoSalvo(Simulacao):
    fontes: list[dict] = Field(
        default_factory=list, description="Fontes e horas de atualização no momento de salvar"
    )


class CenarioSalvo(CenarioListado):
    premissas: PedidoSimulacao
    resultado: ResultadoSalvo


def _salvo(db: Session, r: dict, agora: datetime) -> RespostaDados[CenarioSalvo]:
    fontes = [FonteMeta(**f) for f in r["resultado"].get("fontes", [])] or _fontes_simulacao(db, agora)
    return RespostaDados(
        dados=CenarioSalvo(**r),
        meta=Meta(
            fontes=fontes,
            recorte=RecorteMeta(territorio_id="recife", granularidade="bairro"),
            avisos=[
                f"Resultado calculado em {r['resultado']['calculado_em']} com os dados daquele momento.",
                *AVISOS_SIMULACAO,
            ],
            fonte_por_premissa=FONTE_POR_PREMISSA,
        ),
    )


@router.post(
    "",
    response_model=RespostaDados[CenarioSalvo],
    status_code=201,
    summary="Salvar o cenário (analista ou acima; auditado; o servidor recalcula o resultado)",
)
def salvar(
    pedido: PedidoSalvar,
    ctx: Contexto = Depends(editar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[CenarioSalvo]:
    p = erro_de_negocio(pedido.premissas.premissas)
    fontes = [f.model_dump(mode="json") for f in _fontes_simulacao(db, agora)]
    r = erro_de_negocio(
        lambda: sim.salvar(
            db, pedido.nome, p, pedido.premissas.model_dump(), fontes, ctx.usuario, ctx.ip, agora
        )
    )
    return _salvo(db, r, agora)


@router.get(
    "", response_model=RespostaDados[list[CenarioListado]], summary="Cenários salvos, mais recente primeiro"
)
def listar(
    _: Contexto = Depends(consultar), db: Session = Depends(obter_sessao), agora: datetime = Depends(relogio)
) -> RespostaDados[list[CenarioListado]]:
    return RespostaDados(
        dados=sim.listar(db),
        meta=Meta(
            fontes=_fontes_simulacao(db, agora),
            recorte=RecorteMeta(territorio_id="recife", granularidade="bairro"),
            avisos=AVISOS_SIMULACAO,
        ),
    )


@router.get("/{cenario_id}", response_model=RespostaDados[CenarioSalvo], summary="Abrir um cenário salvo")
def abrir(
    cenario_id: uuid.UUID,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[CenarioSalvo]:
    return _salvo(db, erro_de_negocio(lambda: sim.obter(db, cenario_id)), agora)
