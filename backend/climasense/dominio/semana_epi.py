"""Semana epidemiológica (SE) do Ministério da Saúde: começa no domingo; a SE 1 é a semana (domingo a sábado) que
tem pelo menos quatro dias no ano novo, ou seja, a que contém o dia 4 de janeiro. É a mesma regra do SINAN e do
InfoDengue (campo `SE` = AAAASS, `data_iniSE` = domingo inicial)."""

from __future__ import annotations

from datetime import date, timedelta


def _inicio_se1(ano: int) -> date:
    quatro = date(ano, 1, 4)
    return quatro - timedelta(days=(quatro.weekday() + 1) % 7)  # weekday(): segunda = 0 … domingo = 6


def inicio_semana(ano: int, semana: int) -> date:
    """Domingo que abre a SE `semana` do ano epidemiológico `ano`."""
    if not 1 <= semana <= 53:
        raise ValueError(f"Semana epidemiológica inválida: {semana}")
    return _inicio_se1(ano) + timedelta(weeks=semana - 1)


def semana_de(dia: date) -> tuple[int, int]:
    """(ano epidemiológico, semana) do dia. Os primeiros dias de janeiro podem cair na última SE do ano anterior."""
    ano = dia.year + 1
    while _inicio_se1(ano) > dia:
        ano -= 1
    return ano, (dia - _inicio_se1(ano)).days // 7 + 1


def de_codigo(codigo: str | int) -> tuple[int, int] | None:
    """'202643' → (2026, 43). Código fora do formato ou semana impossível → None (dado ausente, RN-02)."""
    texto = str(codigo or "").strip().split(".")[0]
    if len(texto) != 6 or not texto.isdigit():
        return None
    ano, semana = int(texto[:4]), int(texto[4:])
    if not 1 <= semana <= 53 or ano < 1990:
        return None
    if semana == 53 and semana_de(inicio_semana(ano, 53))[0] != ano:
        return None  # o ano só tem 52 semanas
    return ano, semana
