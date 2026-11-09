"""Histórico de eventos de chuva (RN-05, RN-13). Domínio puro: tipos, situações e regras de quem pode o quê.

aberto -> encerrado (situação final e pendências) -> aprovado. RN-05: quem abriu ou encerrou não aprova; a
situação final só vale com a segunda pessoa. Eventos antigos entram como retrospectivos (sem linha do tempo
horária). A linha do tempo guarda só número AGREGADO de equipes, nunca nomes de pessoas (RN-13).
"""

from __future__ import annotations

from datetime import date, datetime

from climasense.dominio.estagio import ESCADA
from climasense.dominio.evento import RegistroInvalido
from climasense.dominio.recorte import para_recife

SITUACOES = {"aberto": "Aberto", "encerrado": "Encerrado (aguardando aprovação)", "aprovado": "Aprovado"}
TIPOS_ITEM = {
    "comunicado": "Comunicado recebido",
    "estagio": "Estágio",
    "acao": "Ação",
    "observacao": "Observação",
}
FONTE_PADRAO = "Registro da equipe"
MAX_TEXTO_ITEM = 500
MAX_TEXTO_FINAL = 1000
MAX_FONTE = 160
TOLERANCIA_FUTURO_MIN = 5


def nome_padrao(inicio: datetime) -> str:
    return f"Evento de {para_recife(inicio).strftime('%d/%m/%Y')}"


def _limpo(v: str | None) -> str:
    return " ".join((v or "").split())


def validar_item(
    tipo: str, texto: str | None, fonte: str | None, equipes: int | None, estagio: str | None
) -> dict:
    """Item da linha do tempo. Comunicado exige a fonte (órgão); os demais assumem “Registro da equipe”."""
    if tipo not in TIPOS_ITEM:
        raise RegistroInvalido(422, "Tipo desconhecido. Use: " + ", ".join(TIPOS_ITEM) + ".")
    texto, fonte = _limpo(texto), _limpo(fonte)
    if not texto:
        raise RegistroInvalido(422, "Escreva o texto do registro.")
    if len(texto) > MAX_TEXTO_ITEM:
        raise RegistroInvalido(422, f"O texto passa de {MAX_TEXTO_ITEM} caracteres: resuma.")
    if tipo == "comunicado" and not fonte:
        raise RegistroInvalido(422, "Informe de qual órgão veio o comunicado (fonte).")
    if len(fonte) > MAX_FONTE:
        raise RegistroInvalido(422, f"A fonte passa de {MAX_FONTE} caracteres.")
    if equipes is not None and equipes < 0:
        raise RegistroInvalido(422, "O número de equipes não pode ser negativo.")
    if estagio is not None and estagio not in ESCADA:
        raise RegistroInvalido(422, "Estágio desconhecido. Use: " + ", ".join(ESCADA) + ".")
    if tipo == "estagio" and estagio is None:
        raise RegistroInvalido(422, "Informe o estágio.")
    return {
        "tipo": tipo,
        "texto": texto,
        "fonte": fonte or FONTE_PADRAO,
        "equipes": equipes,
        "estagio": estagio,
    }


def validar_situacao_final(situacao_final: str | None, pendencias: str | None) -> tuple[str, str | None]:
    final, pend = _limpo(situacao_final), _limpo(pendencias)
    if not final:
        raise RegistroInvalido(422, "Escreva a situação final do evento.")
    if len(final) > MAX_TEXTO_FINAL or len(pend) > MAX_TEXTO_FINAL:
        raise RegistroInvalido(422, f"Situação final e pendências têm até {MAX_TEXTO_FINAL} caracteres.")
    return final, pend or None


def validar_periodo(inicio: datetime, fim: datetime | None) -> None:
    if fim is not None and fim < inicio:
        raise RegistroInvalido(422, "O término precisa ser depois do início.")


def validar_aprovador(evento: dict, usuario_id) -> None:
    """RN-05: a situação final exige uma segunda pessoa."""
    if evento["situacao"] == "aprovado":
        raise RegistroInvalido(409, "O evento já foi aprovado.")
    if evento["situacao"] != "encerrado":
        raise RegistroInvalido(409, "Encerre o evento, com a situação final, antes de aprová-lo.")
    if usuario_id in (evento["aberto_por"], evento["encerrado_por"]):
        raise RegistroInvalido(
            403, "Quem abriu ou encerrou o evento não pode aprová-lo. Peça a outra pessoa da equipe."
        )


def duracao_horas(inicio: datetime, fim: datetime | None) -> float | None:
    return None if fim is None else round((fim - inicio).total_seconds() / 3600, 1)


def datas_recife(inicio: datetime, fim: datetime) -> tuple[date, date]:
    return para_recife(inicio).date(), para_recife(fim).date()
