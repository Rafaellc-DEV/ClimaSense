"""Nome do distrito sanitário para quem lê: "Distrito 5", nunca "Distrito Sanitário V", "DS V" nem romano.

Regra pura, igual à de `frontend/src/lib/distritos.ts`. A base territorial guarda o nome oficial com algarismo
romano e continua guardando; a troca vale só nos textos que a API monta e nos nomes que ela devolve. Os ids
(`ds-5`) nunca mudam.
"""

from __future__ import annotations

import re

ROMANOS = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}

# "Distrito Sanitário VII", "Distrito VII" ou "DS VII" (com ou sem acento), em qualquer ponto do texto. VIII, VII e VI
# vêm antes de V e I na alternância para que o romano maior não seja cortado ("VIII" nunca vira "VII" + "I").
_PADRAO = re.compile(
    r"\b(?:Distrito\s+Sanit[aá]rio|Distrito|DS)\s+(VIII|VII|VI|IV|V|III|II|I)\b", re.IGNORECASE
)


def nome_distrito(texto: str | None) -> str | None:
    """Troca, dentro de qualquer texto, o distrito em romano pelo número. `None` volta `None`."""
    if texto is None:
        return None
    return _PADRAO.sub(lambda m: f"Distrito {ROMANOS[m.group(1).upper()]}", texto)
