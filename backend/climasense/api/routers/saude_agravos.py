"""Saúde depois da chuva (specs/foco-chuvas.md §9): /saude/resumo, /saude/semanal, /saude/bairros e o histórico de
ocorrências da Defesa Civil (/ocorrencias/historico). Área da equipe: exige login (Permissao.CONSULTAR).

O nível de alerta é do InfoDengue (citado como tal), não do ClimaSense; a janela de leptospirose é um lembrete de
vigilância (NT 138/2022), não um risco calculado (RN-06). Nenhuma rota tem recorte por bairro em tempo real: os
casos semanais são do município; o retrato por bairro é anual e histórico (RN-07).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.dominio.papeis import Permissao
from climasense.infra.postgres import obter_sessao
from climasense.servicos import fontes as servico_fontes
from climasense.servicos import saude_agravos as servico

router = APIRouter(prefix="/saude", tags=["Saúde depois da chuva"])
ocorrencias = APIRouter(prefix="/ocorrencias", tags=["Saúde depois da chuva"])
consultar = exige(Permissao.CONSULTAR)

Agravo = Literal["dengue", "chikungunya", "leptospirose"]
AgravoBairro = Literal["dengue", "chikungunya"]
TipoOcorrencia = Literal["alagamento", "deslizamento"]

AVISO_SEMANAS = "Semanas recentes estão incompletas: o número notificado ainda vai subir (atraso de notificação), não é queda."
AVISO_NIVEL = "O nível de alerta (1 verde a 4 vermelho) é do InfoDengue (Fiocruz/FGV), não do ClimaSense."
AVISO_MUNICIPIO = (
    "Casos por semana são do Recife inteiro (município de residência); não há recorte por bairro."
)


class SemanaRef(BaseModel):
    ano: int
    semana: int
    inicio: date


class ResumoAgravo(BaseModel):
    agravo: Agravo
    nome: str
    fonte_id: str
    ultima_semana: SemanaRef | None = Field(description="null enquanto a fonte não tiver carga (RN-01)")
    casos: int | None = Field(description="Casos notificados na última semana da série")
    casos_estimados: float | None = Field(description="Nowcasting do InfoDengue; null na leptospirose")
    confirmados: int | None = Field(default=None, description="Só leptospirose (SINAN)")
    rt: float | None = None
    variacao_4s_pct: float | None = Field(
        description="4 últimas semanas utilizáveis contra as 4 anteriores; null sem base suficiente"
    )
    nivel_alerta: int | None = Field(description="1–4 do InfoDengue; null na leptospirose")
    incompleta: bool | None


class TerritorioJanela(BaseModel):
    id: str
    nome: str


class JanelaLeptospirose(BaseModel):
    ativa: bool
    inicio: date
    fim: date
    dia_da_janela: int | None = Field(description="Dia 1 = data do primeiro gatilho; null se encerrada")
    atencao_maior: bool = Field(description="Entre o 5º e o 14º dia desde o último gatilho (incubação média)")
    motivo: str
    origens: list[Literal["estagio", "ocorrencia", "chuva"]]
    territorios: list[TerritorioJanela]


class ResumoSaude(BaseModel):
    agravos: list[ResumoAgravo]
    janela_leptospirose: JanelaLeptospirose | None
    gerado_em: datetime


class SemanaSaude(BaseModel):
    ano: int
    semana: int
    inicio: date
    casos: int | None
    confirmados: int | None = None
    casos_estimados: float | None
    ic_inf: float | None
    ic_sup: float | None
    nivel_alerta: int | None
    incompleta: bool


class ChuvaSemana(BaseModel):
    inicio: date
    chuva_mm: float | None
    dias_com_dado: int


class SerieSaude(BaseModel):
    agravo: Agravo
    desde: date
    itens: list[SemanaSaude]
    chuva: list[ChuvaSemana]


class BairroAgravo(BaseModel):
    bairro_id: str
    bairro_nome: str
    distrito_id: str | None
    casos: int = Field(description="Casos confirmados de residentes do bairro no ano")
    notificados: int


class BairrosSaude(BaseModel):
    agravo: AgravoBairro
    ano: int | None
    itens: list[BairroAgravo]
    anos_disponiveis: list[int]
    total_confirmados: int | None
    confirmados_sem_bairro: int | None = Field(
        description="Confirmados sem bairro oficial: no total, fora do mapa"
    )
    total_notificados: int | None
    fonte_atualizada_em: date | None = None


class OcorrenciaBairro(BaseModel):
    bairro_id: str
    bairro_nome: str
    distrito_id: str | None
    registros: int
    dias_com_registro: int
    primeiro_registro: date
    ultimo_registro: date


class HistoricoOcorrencias(BaseModel):
    tipo: TipoOcorrencia
    itens: list[OcorrenciaBairro]
    total_registros: int
    bairros_com_registro: int
    periodo_inicio: date | None
    periodo_fim: date | None


def _meta(
    db: Session, fontes: list[str], agora: datetime, granularidade: str, avisos: list[str], vazio: bool
):
    return Meta(
        fontes=[servico_fontes.meta(db, f, agora) for f in fontes],
        recorte=RecorteMeta(territorio_id="recife", granularidade=granularidade),
        avisos=avisos,
        dados_insuficientes=vazio,
    )


@router.get(
    "/resumo",
    response_model=RespostaDados[ResumoSaude],
    summary="Dengue, chikungunya e leptospirose na última semana e a janela de vigilância de leptospirose",
)
def resumo(
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[ResumoSaude]:
    agravos = servico.resumo_agravos(db)
    jan = servico.janela_leptospirose(db, agora)
    avisos = [AVISO_SEMANAS, AVISO_NIVEL, AVISO_MUNICIPIO]
    if jan:
        avisos.append(
            "Janela de leptospirose: lembrete de vigilância por 30 dias após o evento (NT 138/2022), não é risco "
            "calculado. Território sem registro não é território sem risco."
        )
    return RespostaDados(
        dados=ResumoSaude(agravos=agravos, janela_leptospirose=jan, gerado_em=agora),
        meta=_meta(
            db,
            ["infodengue", "sinan-leptospirose", "apac-chuva", "recife-alagamento"],
            agora,
            "municipio",
            avisos,
            all(a["ultima_semana"] is None for a in agravos),
        ),
    )


@router.get(
    "/semanal",
    response_model=RespostaDados[SerieSaude],
    summary="Série semanal de um agravo no Recife com a chuva semanal ao lado",
)
def semanal(
    agravo: Agravo = Query(default="dengue"),
    desde: date | None = Query(default=None, description="AAAA-MM-DD; padrão: 104 semanas atrás"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[SerieSaude]:
    serie = servico.semanal(db, agravo, desde, agora)
    fonte = servico.AGRAVOS[agravo][1]
    avisos = [AVISO_SEMANAS, AVISO_MUNICIPIO]
    avisos.append(
        AVISO_NIVEL if fonte == "infodengue" else "Leptospirose: semana de início dos sintomas (SINAN)."
    )
    avisos.append(
        "Chuva semanal: reanálise ERA5 (Open-Meteo), média dos distritos, domingo a sábado. Ficar lado a lado "
        "no tempo não prova que a chuva causou os casos."
    )
    return RespostaDados(
        dados=SerieSaude(**serie),
        meta=_meta(db, [fonte, servico.FONTE_CHUVA_SEMANAL], agora, "municipio", avisos, not serie["itens"]),
    )


@router.get(
    "/bairros",
    response_model=RespostaDados[BairrosSaude],
    summary="Casos confirmados de dengue ou chikungunya por bairro de residência em um ano (histórico)",
)
def bairros(
    agravo: AgravoBairro = Query(default="dengue"),
    ano: int | None = Query(default=None, ge=2013, le=2100, description="padrão: o último ano publicado"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[BairrosSaude]:
    b = servico.bairros(db, agravo, ano)
    avisos = [
        "Retrato anual e histórico, publicado pela Secretaria de Saúde uma vez por ano; não mostra a situação "
        "atual.",
        "Bairro de residência, não o local da infecção. Em bairro pequeno, poucos casos mudam muito a posição.",
    ]
    if b["ano"] is not None and b["anos_disponiveis"] and b["ano"] not in b["anos_disponiveis"]:
        avisos.append(f"{b['ano']} ainda não foi publicado.")
    return RespostaDados(
        dados=BairrosSaude(**b),
        meta=_meta(db, ["recife-arboviroses"], agora, "bairro", avisos, not b["itens"]),
    )


@ocorrencias.get(
    "/historico",
    response_model=RespostaDados[HistoricoOcorrencias],
    summary="Onde já aconteceu: atendimentos de alagamento ou deslizamento da Defesa Civil por bairro",
)
def historico_ocorrencias(
    tipo: TipoOcorrencia = Query(default="alagamento"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[HistoricoOcorrencias]:
    h = servico.ocorrencias_historico(db, tipo)
    avisos = [
        "Atendimentos registrados pela Defesa Civil (data da vistoria, que pode vir dias depois do evento). "
        "Bairro sem registro não é bairro sem risco.",
    ]
    if tipo == "deslizamento":
        avisos.append(
            "Deslizamento = ocorrências 'Deslizamentos de Barreiras' e desabamento de obras de contenção. "
            "Colocação de lona plástica é prevenção e não entra."
        )
    return RespostaDados(
        dados=HistoricoOcorrencias(**h),
        meta=_meta(db, ["recife-alagamento"], agora, "bairro", avisos, not h["itens"]),
    )
