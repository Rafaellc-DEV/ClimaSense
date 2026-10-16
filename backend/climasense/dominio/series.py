"""Séries temporais (RF-08). Domínio puro.

Regras:
- um dia sem dado é `None`, nunca 0 (RN-02);
- um período (semana ou mês) só tem valor quando TODOS os seus dias dentro do recorte têm dado; senão é
  lacuna. Somar só os dias disponíveis subestimaria a chuva e esconderia a falta de dado;
- janelas não se sobrepõem: cada dia entra em exatamente um período (RF-08.3).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

Frequencia = Literal["diaria", "semanal", "mensal"]
FREQUENCIAS: tuple[Frequencia, ...] = ("diaria", "semanal", "mensal")

MESES = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


@dataclass(frozen=True)
class Ponto:
    inicio: date  # primeiro dia do período (o dia, a segunda-feira ou o dia 1º)
    valor: float | None
    dias: int  # dias do período dentro do recorte
    dias_com_dado: int


def dias(inicio: date, fim: date) -> list[date]:
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def inicio_do_periodo(dia: date, frequencia: Frequencia) -> date:
    if frequencia == "semanal":
        return dia - timedelta(days=dia.weekday())
    if frequencia == "mensal":
        return dia.replace(day=1)
    return dia


def agregar(
    diarios: Mapping[date, float | None], inicio: date, fim: date, frequencia: Frequencia
) -> list[Ponto]:
    """Acumulado por período, com os dias ausentes do recorte tratados como lacuna."""
    grupos: dict[date, list[float | None]] = {}
    for d in dias(inicio, fim):
        grupos.setdefault(inicio_do_periodo(d, frequencia), []).append(diarios.get(d))
    pontos = []
    for chave, valores in grupos.items():
        com_dado = [v for v in valores if v is not None]
        completo = len(com_dado) == len(valores)
        pontos.append(
            Ponto(
                inicio=chave,
                valor=round(sum(com_dado), 2) if completo else None,
                dias=len(valores),
                dias_com_dado=len(com_dado),
            )
        )
    return pontos


def dias_sem_dado(diarios: Mapping[date, float | None], inicio: date, fim: date) -> int:
    return sum(1 for d in dias(inicio, fim) if diarios.get(d) is None)


def cobertura_pct(diarios: Mapping[date, float | None], inicio: date, fim: date) -> float:
    total = (fim - inicio).days + 1
    return round(100 * (total - dias_sem_dado(diarios, inicio, fim)) / total, 1) if total > 0 else 0.0


def _mm(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",") + " mm"


def _anos(anos: list[int]) -> str:
    if not anos:
        return ""
    return str(anos[0]) if len(anos) == 1 else f"{anos[0]} a {anos[-1]}"


def resumo_em_frase(
    pontos_mensais: list[Ponto],
    referencia: Mapping[int, tuple[float | None, list[int]]],
    lacunas_dias: int,
) -> str:
    """Ex.: “Setembro de 2026 teve 38% menos chuva que a média de 2021 a 2025. Faltam dados em 4 dias.”

    Usa o mês completo mais recente do recorte e a média histórica daquele mês do ano.
    """
    partes: list[str] = []
    completos = [p for p in pontos_mensais if p.valor is not None]
    if not completos:
        partes.append("Não há nenhum mês completo com dados neste recorte.")
    else:
        ultimo = completos[-1]
        nome = f"{MESES[ultimo.inicio.month - 1].capitalize()} de {ultimo.inicio.year}"
        media, anos = referencia.get(ultimo.inicio.month, (None, []))
        if media is None or not anos:
            partes.append(
                f"{nome} acumulou {_mm(ultimo.valor)} de chuva. Ainda não há média histórica para comparar."
            )
        elif media == 0:
            partes.append(f"{nome} acumulou {_mm(ultimo.valor)}; a média de {_anos(anos)} para o mês é 0 mm.")
        else:
            diferenca = round(100 * (ultimo.valor - media) / media)
            if abs(diferenca) < 5:
                comparacao = f"choveu perto da média de {_anos(anos)} ({_mm(media)})"
                partes.append(f"Em {nome.lower()} {comparacao}.")
            else:
                quanto = "mais" if diferenca > 0 else "menos"
                partes.append(
                    f"{nome} teve {abs(diferenca)}% {quanto} chuva que a média de {_anos(anos)} "
                    f"({_mm(ultimo.valor)} contra {_mm(media)})."
                )
    if lacunas_dias == 1:
        partes.append("Falta dado em 1 dia.")
    elif lacunas_dias > 1:
        partes.append(f"Faltam dados em {lacunas_dias} dias.")
    return " ".join(partes)


def serie_curta(n: int, minimo: int) -> bool:
    """RN-08: abaixo do mínimo configurado na fonte, a série não caracteriza o clima."""
    return n < minimo
