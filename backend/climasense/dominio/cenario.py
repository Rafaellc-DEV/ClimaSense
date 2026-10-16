"""Regra de referência dos cenários de alagamento (RF-09). Domínio puro, transparente e EXPERIMENTAL (RN-11).

A regra compara a chuva prevista com a chuva histórica do próprio território, em vez de usar limites
inventados:

1. acumulado previsto nas 24 h mais chuvosas do horizonte ≥ percentil 99 dos dias históricos → Alerta;
   ≥ percentil 95 → Atenção; abaixo disso → Sem indicação;
2. se a maré prevista estiver alta (≥ LIMITE_MARE_ALTA_M acima do nível médio) a até 3 h do pico de chuva,
   a prioridade sobe um nível (Atenção → Alerta → Situação crítica), porque a maré alta dificulta a
   drenagem do Recife;
3. faltando a previsão de chuva, a maré ou o histórico (pelo menos MINIMO_DIAS_HISTORICO) → Dados
   insuficientes (RN-01). Nunca “risco baixo”.

A prioridade é uma indicação para a equipe avaliar, nunca uma probabilidade de alagar (RN-06).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

Prioridade = Literal["sem_indicacao", "atencao", "alerta", "critico", "dados_insuficientes"]
Qualidade = Literal["completa", "parcial", "insuficiente"]

METODO = "regra-referencia-percentis"
VERSAO = "0.1.0"
LIMITE_MARE_ALTA_M = 0.6
MINIMO_DIAS_HISTORICO = 365
HORIZONTES = (24, 48, 72)
_ESCADA: list[Prioridade] = ["sem_indicacao", "atencao", "alerta", "critico"]


@dataclass(frozen=True)
class Insumos:
    chuva_prevista: list[tuple[datetime, float | None]]  # hora UTC → mm na hora
    mare_prevista: list[tuple[datetime, float | None]]  # hora UTC → m acima do nível médio
    chuva_historica_diaria: list[float]  # mm/dia, só dias com dado
    ocorrencias_historicas: int | None  # None = fonte não integrada


@dataclass(frozen=True)
class Janela:
    inicio: datetime
    fim: datetime


@dataclass
class Estimativa:
    prioridade: Prioridade
    qualidade: Qualidade
    janela_atencao: Janela | None
    fatores: list[tuple[str, str]] = field(default_factory=list)  # (nome, descrição)
    limitacoes: list[str] = field(default_factory=list)
    acumulado_previsto_mm: float | None = None
    pico_chuva_em: datetime | None = None
    mare_maxima_m: float | None = None
    mare_maxima_em: datetime | None = None
    p95_mm: float | None = None
    p99_mm: float | None = None
    experimental: bool = True


def percentil(valores: list[float], p: float) -> float:
    """Interpolação linear, como numpy.percentile (método padrão)."""
    v = sorted(valores)
    if not v:
        raise ValueError("percentil de lista vazia")
    k = (len(v) - 1) * p / 100
    baixo = int(k)
    alto = min(baixo + 1, len(v) - 1)
    return v[baixo] + (v[alto] - v[baixo]) * (k - baixo)


def _mm(v: float) -> str:
    return f"{v:.1f}".replace(".", ",") + " mm"


def _maior_24h(chuva: list[tuple[datetime, float]]) -> tuple[float, int]:
    """Maior soma em 24 horas consecutivas e o índice inicial da janela."""
    if len(chuva) <= 24:
        return sum(v for _, v in chuva), 0
    melhor, inicio, soma = -1.0, 0, sum(v for _, v in chuva[:24])
    for i in range(len(chuva) - 23):
        if i > 0:
            soma += chuva[i + 23][1] - chuva[i - 1][1]
        if soma > melhor:
            melhor, inicio = soma, i
    return melhor, inicio


def estimar(insumos: Insumos, horizonte_h: int, emitida_em: datetime) -> Estimativa:
    if horizonte_h not in HORIZONTES:
        raise ValueError("Horizonte deve ser 24, 48 ou 72 horas.")
    limite = emitida_em + timedelta(hours=horizonte_h)
    chuva = [(t, v) for t, v in insumos.chuva_prevista if emitida_em <= t < limite]
    mare = [(t, v) for t, v in insumos.mare_prevista if emitida_em <= t < limite and v is not None]
    faltas = []
    if not chuva or any(v is None for _, v in chuva):
        faltas.append("a previsão de chuva para todo o horizonte")
    if not mare:
        faltas.append("a previsão de maré")
    if len(insumos.chuva_historica_diaria) < MINIMO_DIAS_HISTORICO:
        faltas.append(f"pelo menos {MINIMO_DIAS_HISTORICO} dias de chuva histórica")
    if faltas:
        return Estimativa(
            prioridade="dados_insuficientes",
            qualidade="insuficiente",
            janela_atencao=None,
            limitacoes=[f"Falta {', '.join(faltas)}. Sem esses insumos a regra não estima nada."],
        )

    chuva_ok = [(t, float(v)) for t, v in chuva if v is not None]
    acumulado, i0 = _maior_24h(chuva_ok)
    janela_24 = chuva_ok[i0 : i0 + 24]
    pico_t, pico_v = max(janela_24, key=lambda p: p[1])
    p95 = percentil(insumos.chuva_historica_diaria, 95)
    p99 = percentil(insumos.chuva_historica_diaria, 99)
    mare_t, mare_v = max(mare, key=lambda p: p[1])

    fatores: list[tuple[str, str]] = []
    if acumulado >= p99:
        nivel = 2
        fatores.append(
            (
                "Chuva prevista muito acima do comum",
                f"{_mm(acumulado)} em 24 h; só 1% dos dias do histórico passaram de {_mm(p99)}.",
            )
        )
    elif acumulado >= p95:
        nivel = 1
        fatores.append(
            (
                "Chuva prevista acima do comum",
                f"{_mm(acumulado)} em 24 h; só 5% dos dias do histórico passaram de {_mm(p95)}.",
            )
        )
    else:
        nivel = 0
        fatores.append(
            (
                "Chuva prevista dentro do comum",
                f"{_mm(acumulado)} nas 24 h mais chuvosas; o limite de atenção é {_mm(p95)}.",
            )
        )

    mare_alta_perto = [
        (t, v) for t, v in mare if v >= LIMITE_MARE_ALTA_M and abs((t - pico_t).total_seconds()) <= 3 * 3600
    ]
    if mare_alta_perto:
        texto = f"Nível do mar de {mare_alta_perto[0][1]:.2f} m perto do pico de chuva: a drenagem fica mais lenta.".replace(
            ".", ",", 1
        )
        fatores.append(("Maré alta junto com a chuva", texto))
        if nivel > 0:
            nivel += 1
    else:
        fatores.append(
            (
                "Maré",
                f"Máxima prevista de {mare_v:.2f} m".replace(".", ",") + ", sem coincidir com chuva forte.",
            )
        )

    limitacoes = [
        "Regra de referência, não um modelo validado: compara a previsão com a chuva histórica da reanálise ERA5.",
        f"O limite de maré alta ({LIMITE_MARE_ALTA_M:.1f} m acima do nível médio) é uma referência inicial e ainda não foi calibrado.".replace(
            ".", ",", 1
        ),
        "A previsão é para um ponto representativo do distrito; a chuva varia dentro dele.",
    ]
    qualidade: Qualidade = "completa"
    if insumos.ocorrencias_historicas is None:
        qualidade = "parcial"
        limitacoes.append(
            "Sem histórico de ocorrências de alagamento integrado: a regra não sabe quais áreas costumam alagar."
        )

    janela = None
    if nivel > 0:
        horas_fortes = [t for t, v in janela_24 if v >= 1.0] or [pico_t]
        janela = Janela(inicio=min(horas_fortes), fim=max(horas_fortes) + timedelta(hours=1))
    return Estimativa(
        prioridade=_ESCADA[min(nivel, 3)],
        qualidade=qualidade,
        janela_atencao=janela,
        fatores=fatores,
        limitacoes=limitacoes,
        acumulado_previsto_mm=round(acumulado, 1),
        pico_chuva_em=pico_t,
        mare_maxima_m=round(mare_v, 2),
        mare_maxima_em=mare_t,
        p95_mm=round(p95, 1),
        p99_mm=round(p99, 1),
    )
