"""Séries e sazonalidade (T6.2, T6.3): chuva por território com lacunas explícitas, referência histórica,
calendário ano × mês e estatística descritiva em linguagem simples."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.dominio import estatistica, series
from climasense.dominio.papeis import Permissao
from climasense.dominio.recorte import RecorteInvalido, dia_no_recife, granularidade
from climasense.infra.postgres import obter_sessao
from climasense.servicos import fontes as servico_fontes
from climasense.servicos import series as servico
from climasense.servicos.territorio import TerritorioUsado, no_maximo_distrito

router = APIRouter(prefix="/series", tags=["Séries e sazonalidade"])
consultar = exige(Permissao.CONSULTAR)

Variavel = Literal["chuva_mm", "mare_m", "temp_c", "nivel_m"]
SEM_HISTORICO = {
    "mare_m": "A maré só tem previsão (Open-Meteo Marine). A série histórica depende da tábua da Marinha, ainda planejada.",
    "temp_c": "Temperatura ainda não tem fonte integrada.",
    "nivel_m": "Nível de rios depende da ANA (telemetria), ainda planejada.",
}
MAXIMO_DIAS = 366 * 6


class PontoSerie(BaseModel):
    t: date
    valor: float | None
    dias: int
    dias_com_dado: int


class SerieTemporal(BaseModel):
    variavel: str
    unidade: str
    frequencia: str
    territorio_id: str
    territorio_nome: str
    pontos: list[PontoSerie]
    referencia: list[float | None]
    resumo: str
    lacunas_dias: int


class MesReferencia(BaseModel):
    mes: int
    media_mm: float | None
    mediana_mm: float | None
    anos_usados: list[int]
    cobertura_pct: float


class Referencia(BaseModel):
    metodo: str
    meses: list[MesReferencia]


class CelulaSazonal(BaseModel):
    ano: int
    mes: int
    valor: float | None
    cobertura_pct: float


class Sazonalidade(BaseModel):
    anos: list[int]
    celulas: list[CelulaSazonal]


class Medida(BaseModel):
    chave: str
    nome: str
    valor: float | None
    texto: str
    explicacao: str


class Estatisticas(BaseModel):
    frequencia: str
    n: int
    minimo_observacoes: int
    serie_curta: bool
    medidas: list[Medida]


def _periodo(inicio: date | None, fim: date | None, agora: datetime) -> tuple[date, date]:
    fim = fim or dia_no_recife(agora)
    inicio = inicio or fim - timedelta(days=364)
    if inicio > fim:
        raise RecorteInvalido("A data de início precisa ser anterior ou igual à data de fim.")
    if (fim - inicio).days > MAXIMO_DIAS:
        raise RecorteInvalido("Escolha um período de até 6 anos.")
    return inicio, fim


def _meta(
    db: Session,
    agora: datetime,
    t: TerritorioUsado,
    inicio: date | None,
    fim: date | None,
    **extra,
) -> Meta:
    return Meta(
        fontes=[servico_fontes.meta(db, servico.FONTE_CHUVA, agora)],
        recorte=RecorteMeta(
            territorio_id=t.usado, inicio=inicio, fim=fim, granularidade=granularidade(t.usado)
        ),
        avisos=t.avisos + extra.pop("avisos", []),
        **extra,
    )


def _sem_historico(variavel: str, db: Session, agora: datetime, t: TerritorioUsado, i, f) -> Meta:
    return _meta(db, agora, t, i, f, avisos=[SEM_HISTORICO[variavel]], dados_insuficientes=True)


def _mm(v: float | None) -> str:
    return "sem dado" if v is None else f"{v:.1f}".replace(".", ",") + " mm"


@router.get("", response_model=RespostaDados[SerieTemporal], summary="Série temporal com lacunas explícitas")
def serie(
    variavel: Variavel = "chuva_mm",
    territorio_id: str = "recife",
    inicio: date | None = None,
    fim: date | None = None,
    frequencia: series.Frequencia = "diaria",
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[SerieTemporal]:
    t = no_maximo_distrito(db, territorio_id)
    inicio, fim = _periodo(inicio, fim, agora)
    vazio = SerieTemporal(
        variavel=variavel,
        unidade="mm",
        frequencia=frequencia,
        territorio_id=t.usado,
        territorio_nome=t.nome,
        pontos=[],
        referencia=[],
        resumo="Não há série histórica para esta variável.",
        lacunas_dias=0,
    )
    if variavel != "chuva_mm":
        return RespostaDados(dados=vazio, meta=_sem_historico(variavel, db, agora, t, inicio, fim))

    diarios = servico.chuva_diaria(db, t.usado, inicio, fim)
    pontos = series.agregar(diarios, inicio, fim, frequencia)
    ref = {r["mes_do_ano"]: (r["media_mm"], r["anos_usados"]) for r in servico.referencia(db, t.usado)}
    lacunas = series.dias_sem_dado(diarios, inicio, fim)
    resumo = series.resumo_em_frase(series.agregar(diarios, inicio, fim, "mensal"), ref, lacunas)
    # referência alinhada aos pontos: só faz sentido para meses inteiros
    referencia = [
        (ref.get(p.inicio.month, (None, []))[0] if frequencia == "mensal" else None) for p in pontos
    ]
    cobertura = series.cobertura_pct(diarios, inicio, fim)
    avisos = []
    if not any(v is not None for v in diarios.values()):
        avisos.append("Nenhum dia com dado neste recorte. Rode a carga do Open-Meteo histórico.")
    if fim > dia_no_recife(agora) - timedelta(days=7):
        avisos.append(
            "A reanálise chega com cerca de 7 dias de atraso: os últimos dias ainda aparecem sem dado."
        )
    dados = vazio.model_copy(
        update={
            "pontos": [
                PontoSerie(t=p.inicio, valor=p.valor, dias=p.dias, dias_com_dado=p.dias_com_dado)
                for p in pontos
            ],
            "referencia": referencia,
            "resumo": resumo,
            "lacunas_dias": lacunas,
        }
    )
    return RespostaDados(
        dados=dados,
        meta=_meta(
            db,
            agora,
            t,
            inicio,
            fim,
            cobertura_pct=cobertura,
            avisos=avisos,
            dados_insuficientes=not any(p.valor is not None for p in pontos),
        ),
    )


@router.get("/referencia", response_model=RespostaDados[Referencia], summary="Referência histórica por mês")
def referencia(
    territorio_id: str = "recife",
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Referencia]:
    t = no_maximo_distrito(db, territorio_id)
    meses = [
        MesReferencia(
            mes=r["mes_do_ano"],
            media_mm=r["media_mm"],
            mediana_mm=r["mediana_mm"],
            anos_usados=r["anos_usados"],
            cobertura_pct=r["cobertura_pct"],
        )
        for r in servico.referencia(db, t.usado)
    ]
    metodo = (
        "Média e mediana do acumulado de cada mês nos anos completos já encerrados, usando só os meses "
        "com pelo menos 80% dos dias com dado."
    )
    return RespostaDados(
        dados=Referencia(metodo=metodo, meses=meses),
        meta=_meta(db, agora, t, None, None, dados_insuficientes=not meses),
    )


@router.get("/sazonalidade", response_model=RespostaDados[Sazonalidade], summary="Calendário ano × mês")
def sazonalidade(
    territorio_id: str = "recife",
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Sazonalidade]:
    t = no_maximo_distrito(db, territorio_id)
    linhas = servico.mensal(db, t.usado)
    celulas = [
        CelulaSazonal(
            ano=r["mes"].year,
            mes=r["mes"].month,
            # mês incompleto é lacuna, como na série (RN-02)
            valor=r["acumulado_mm"] if r["cobertura_pct"] >= 100 else None,
            cobertura_pct=r["cobertura_pct"],
        )
        for r in linhas
    ]
    anos = sorted({c.ano for c in celulas})
    return RespostaDados(
        dados=Sazonalidade(anos=anos, celulas=celulas),
        meta=_meta(
            db,
            agora,
            t,
            date(anos[0], 1, 1) if anos else None,
            date(anos[-1], 12, 31) if anos else None,
            dados_insuficientes=not any(c.valor is not None for c in celulas),
            avisos=["Meses com algum dia sem dado aparecem como lacuna."] if celulas else [],
        ),
    )


@router.get(
    "/estatisticas",
    response_model=RespostaDados[Estatisticas],
    summary="Estatística descritiva em texto simples",
)
def estatisticas(
    territorio_id: str = "recife",
    inicio: date | None = None,
    fim: date | None = None,
    frequencia: series.Frequencia = "diaria",
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[Estatisticas]:
    t = no_maximo_distrito(db, territorio_id)
    inicio, fim = _periodo(inicio, fim, agora)
    pontos = series.agregar(servico.chuva_diaria(db, t.usado, inicio, fim), inicio, fim, frequencia)
    r = estatistica.descrever(p.valor for p in pontos)
    minimo = servico_fontes.minimo_observacoes(db, servico.FONTE_CHUVA)
    if frequencia != "diaria":  # o mínimo da fonte é em dias
        minimo = max(3, minimo // (7 if frequencia == "semanal" else 30))
    curta = series.serie_curta(r.n, minimo)
    unidade = {"diaria": "por dia", "semanal": "por semana", "mensal": "por mês"}[frequencia]

    def m(chave, nome, valor, texto, explicacao):
        return Medida(chave=chave, nome=nome, valor=valor, texto=texto, explicacao=explicacao)

    medidas = [
        m(
            "media",
            "Média",
            r.media,
            _mm(r.media),
            f"Chuva típica {unidade}, somando tudo e dividindo pelo número de períodos.",
        ),
        m(
            "mediana",
            "Mediana",
            r.mediana,
            _mm(r.mediana),
            "Metade dos períodos teve menos chuva que isso, e metade teve mais.",
        ),
        m(
            "moda",
            "Moda",
            r.moda[0] if r.moda else None,
            ", ".join(_mm(v) for v in r.moda[:3]) or "sem dado",
            "O valor que mais se repete. Em chuva diária costuma ser 0 mm (dias secos medidos).",
        ),
        m(
            "desvio_padrao",
            "Desvio padrão",
            r.desvio_padrao,
            _mm(r.desvio_padrao),
            "Quanto os valores costumam se afastar da média.",
        ),
        m(
            "variancia",
            "Variância",
            r.variancia,
            "sem dado" if r.variancia is None else f"{r.variancia:.1f}".replace(".", ",") + " mm²",
            "O desvio padrão ao quadrado; usada em outros cálculos.",
        ),
        m(
            "amplitude",
            "Amplitude",
            r.amplitude,
            "sem dado"
            if r.amplitude is None
            else f"{_mm(r.amplitude)} (de {_mm(r.minimo)} a {_mm(r.maximo)})",
            "A diferença entre o menor e o maior valor do recorte.",
        ),
        m(
            "assimetria",
            "Assimetria",
            r.assimetria,
            "sem dado" if r.assimetria is None else f"{r.assimetria:.2f}".replace(".", ","),
            estatistica.classificar_assimetria(r.assimetria)
            if r.assimetria is not None
            else "Precisa de pelo menos 3 valores.",
        ),
        m(
            "curtose",
            "Curtose",
            r.curtose,
            "sem dado" if r.curtose is None else f"{r.curtose:.2f}".replace(".", ","),
            estatistica.classificar_curtose(r.curtose)
            if r.curtose is not None
            else "Precisa de pelo menos 4 valores.",
        ),
    ]
    avisos = ["Série curta: não use para caracterizar o clima."] if curta else []
    return RespostaDados(
        dados=Estatisticas(
            frequencia=frequencia, n=r.n, minimo_observacoes=minimo, serie_curta=curta, medidas=medidas
        ),
        meta=_meta(db, agora, t, inicio, fim, avisos=avisos, dados_insuficientes=r.n == 0),
    )
