"""Ações de resposta em campo (F4). Domínio puro: tipos, situações e transições.

planejada → em_andamento → concluida; qualquer uma não final → cancelada. Concluída e cancelada são finais:
depois delas só a “lição aprendida” pode ser escrita, para a reunião pós-evento.
"""

from __future__ import annotations

from datetime import datetime

from climasense.dominio.evento import RegistroInvalido as AcaoInvalida

TIPOS = {
    "orientacao": "Orientação",
    "visita": "Visita",
    "distribuicao_insumos": "Distribuição de insumos",
    "vigilancia_agravo": "Vigilância de agravo",
    "articulacao": "Articulação",
    "outro": "Outro",
}
SITUACOES = {
    "planejada": "Planejada",
    "em_andamento": "Em andamento",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}
FINAIS = {"concluida", "cancelada"}
TRANSICOES = {
    "planejada": {"em_andamento", "concluida", "cancelada"},
    "em_andamento": {"concluida", "cancelada"},
    "concluida": set(),
    "cancelada": set(),
}


def validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS:
        raise AcaoInvalida(422, "Tipo de ação desconhecido. Use: " + ", ".join(TIPOS) + ".")


def validar_situacao(situacao: str) -> None:
    if situacao not in SITUACOES:
        raise AcaoInvalida(422, "Situação desconhecida. Use: " + ", ".join(SITUACOES) + ".")


def validar_transicao(atual: str, nova: str) -> None:
    validar_situacao(nova)
    if nova != atual and nova not in TRANSICOES[atual]:
        raise AcaoInvalida(
            409, f"A ação está {SITUACOES[atual].lower()}: não pode passar para {SITUACOES[nova].lower()}."
        )


def horarios(
    situacao: str, inicio_em: datetime | None, fim_em: datetime | None, agora: datetime
) -> tuple[datetime | None, datetime | None]:
    """Começar marca o início; concluir ou cancelar marca o fim, quando a pessoa não informou."""
    if situacao in ("em_andamento", "concluida") and inicio_em is None:
        inicio_em = agora
    if situacao in FINAIS and fim_em is None:
        fim_em = agora
    if inicio_em and fim_em and fim_em < inicio_em:
        raise AcaoInvalida(422, "O fim da ação precisa ser depois do início.")
    return inicio_em, fim_em


def validar_licao(situacao: str, licao: str | None) -> None:
    if licao and licao.strip() and situacao not in FINAIS:
        raise AcaoInvalida(422, "A lição aprendida é registrada ao concluir ou cancelar a ação.")
