"""Estatística descritiva das séries (RF-08.6), porte das Atividades 3 e 4. Domínio puro.

As fórmulas reproduzem as do pandas usadas nos exercícios (variância e desvio amostrais, assimetria
ajustada de Fisher-Pearson e excesso de curtose sem viés). A diferença deliberada: o valor ausente é
ignorado — nunca convertido em 0, como o `'...' → 0` dos exercícios fazia (RN-02).
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

Serie = Iterable[float | None]


def validos(x: Serie) -> list[float]:
    return [float(v) for v in x if v is not None and not math.isnan(v)]


def media(x: Serie) -> float | None:
    v = validos(x)
    return sum(v) / len(v) if v else None


def mediana(x: Serie) -> float | None:
    v = sorted(validos(x))
    if not v:
        return None
    meio = len(v) // 2
    return v[meio] if len(v) % 2 else (v[meio - 1] + v[meio]) / 2


def moda(x: Serie) -> list[float]:
    """Todos os valores mais frequentes, em ordem crescente (como `Series.mode()`)."""
    contagem = Counter(validos(x))
    if not contagem:
        return []
    maximo = max(contagem.values())
    return sorted(v for v, n in contagem.items() if n == maximo)


def variancia(x: Serie) -> float | None:
    v = validos(x)
    if len(v) < 2:
        return None
    m = sum(v) / len(v)
    return sum((a - m) ** 2 for a in v) / (len(v) - 1)


def desvio_padrao(x: Serie) -> float | None:
    s2 = variancia(x)
    return math.sqrt(s2) if s2 is not None else None


def amplitude(x: Serie) -> tuple[float, float, float] | None:
    """(mínimo, máximo, máximo − mínimo)."""
    v = validos(x)
    return (min(v), max(v), max(v) - min(v)) if v else None


def assimetria(x: Serie) -> float | None:
    v = validos(x)
    n = len(v)
    s = desvio_padrao(v)
    if n < 3 or not s:
        return None
    m = sum(v) / n
    return n / ((n - 1) * (n - 2)) * sum(((a - m) / s) ** 3 for a in v)


def curtose(x: Serie) -> float | None:
    """Excesso de curtose (0 = normal), como `Series.kurtosis()`."""
    v = validos(x)
    n = len(v)
    s = desvio_padrao(v)
    if n < 4 or not s:
        return None
    m = sum(v) / n
    soma = sum(((a - m) / s) ** 4 for a in v)
    return n * (n + 1) / ((n - 1) * (n - 2) * (n - 3)) * soma - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))


def classificar_curtose(valor: float) -> str:
    if abs(valor) < 0.2:
        return "Mesocúrtica: formato parecido com o da distribuição normal."
    if valor < 0:
        return "Platicúrtica: valores espalhados, sem um pico concentrado nem extremos frequentes."
    return "Leptocúrtica: a maior parte dos valores fica perto do centro, com alguns extremos raros."


def classificar_assimetria(valor: float) -> str:
    if abs(valor) < 0.1:
        return "Praticamente simétrica."
    lado = (
        "à direita: há alguns valores bem acima do comum"
        if valor > 0
        else "à esquerda: há alguns valores bem abaixo do comum"
    )
    forca = "leve" if abs(valor) < 0.5 else "moderada" if abs(valor) < 1 else "forte"
    return f"Assimetria {forca} {lado}."


@dataclass(frozen=True)
class Resumo:
    n: int
    media: float | None
    mediana: float | None
    moda: list[float]
    variancia: float | None
    desvio_padrao: float | None
    minimo: float | None
    maximo: float | None
    amplitude: float | None
    assimetria: float | None
    curtose: float | None


def descrever(x: Serie) -> Resumo:
    v = validos(x)
    amp = amplitude(v)
    return Resumo(
        n=len(v),
        media=media(v),
        mediana=mediana(v),
        moda=moda(v),
        variancia=variancia(v),
        desvio_padrao=desvio_padrao(v),
        minimo=amp[0] if amp else None,
        maximo=amp[1] if amp else None,
        amplitude=amp[2] if amp else None,
        assimetria=assimetria(v),
        curtose=curtose(v),
    )
