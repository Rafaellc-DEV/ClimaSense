"""Textos curtos e padronizados para WhatsApp (F2) e o resumo do boletim (F5). Domínio puro.

Nada é enviado pelo sistema: a pessoa copia o texto ou abre o `wa.me` e escolhe o grupo (RN-18, RF-11.9).
Horários no fuso do Recife, dd/mm/aaaa (RN-16).
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from climasense.dominio.estagio import ROTULO
from climasense.dominio.recorte import para_recife

ASSINATURA = "Fonte: ClimaSense / Vigidesastres. Confira na APAC e no Cemaden."
MAX_TERRITORIOS = 10
MAX_TEXTO = 3500  # folga abaixo do limite prático de uma mensagem e de uma URL do wa.me

ORIENTACOES: dict[str, str] = {
    "observacao": "Manter o acompanhamento da previsão e das ocorrências.",
    "atencao": "Reforçar a vigilância nos pontos de alagamento conhecidos e revisar contatos e abrigos.",
    "alerta": "Preparar abrigos, equipes e insumos; orientar a população das áreas de risco.",
    "critico": "Acionar a resposta: abrigos abertos, equipes em campo e articulação com a Defesa Civil.",
    "sem_dados": "Sem dados suficientes: confirme a situação na APAC e no Cemaden antes de decidir.",
}


def hora_recife(momento: datetime) -> str:
    return para_recife(momento).strftime("%d/%m/%Y %H:%M")


def lista_territorios(nomes: list[str]) -> str:
    if len(nomes) <= MAX_TERRITORIOS:
        return ", ".join(nomes)
    return ", ".join(nomes[:MAX_TERRITORIOS]) + f" e mais {len(nomes) - MAX_TERRITORIOS}"


def mensagem_estagio(
    estagio: str, territorios: list[str], momento: datetime, justificativa: str | None = None
) -> str:
    linhas = [
        "*ClimaSense · Vigidesastres*",
        f"Estágio: *{ROTULO[estagio].upper()}*",
        f"Territórios: {lista_territorios(territorios)}",
    ]
    if justificativa and justificativa.strip():
        linhas.append(f"Motivo: {' '.join(justificativa.split())}")
    linhas += [
        f"O que fazer: {ORIENTACOES[estagio]}",
        f"Hora: {hora_recife(momento)}",
        ASSINATURA,
    ]
    return limitar("\n".join(linhas))


def limitar(texto: str) -> str:
    return texto if len(texto) <= MAX_TEXTO else texto[: MAX_TEXTO - 1].rstrip() + "…"


def wa_me_url(texto: str) -> str:
    """Link do WhatsApp sem destinatário: quem envia escolhe o grupo."""
    return "https://wa.me/?text=" + quote(texto, safe="")


def numero(v: float | None, unidade: str, casas: int = 1) -> str:
    """Valor ausente aparece como “sem dado”, nunca como zero (RN-02)."""
    if v is None:
        return "sem dado"
    return f"{v:.{casas}f}".replace(".", ",") + f" {unidade}"


def texto_boletim(
    territorio_nome: str,
    momento: datetime,
    estagios: list[tuple[str, str, str]],
    chuva: dict,
    mare: tuple[float, datetime] | None,
    abrigos: dict,
    acoes_em_andamento: int,
) -> str:
    """Resumo do boletim (F5) para WhatsApp. `estagios`: (território, estágio, origem: declarado|sugerido)."""
    linhas = [
        "*Boletim ClimaSense · Vigidesastres*",
        f"{territorio_nome} · {hora_recife(momento)}",
        "",
        "*Estágio por distrito*",
    ]
    for nome, estagio, origem in estagios:
        linhas.append(f"- {nome}: {ROTULO[estagio]} ({origem})")
    linhas += ["", "*Chuva*"]
    for chave, rotulo in (
        ("chuva_24h", "Últimas 24 h"),
        ("chuva_prev_24h", "Prevista 24 h"),
        ("chuva_prev_72h", "Prevista 72 h"),
    ):
        valor, onde = chuva.get(chave) or (None, None)
        linhas.append(f"- {rotulo}: {numero(valor, 'mm')}" + (f" (maior: {onde})" if onde else ""))
    linhas.append(
        f"Maré máxima: {numero(mare[0], 'm', 2)} às {para_recife(mare[1]).strftime('%d/%m %H:%M')}"
        if mare
        else "Maré máxima: sem dado"
    )
    # ocupação e desabrigados saíram (sem fonte pública e sem contagem pela equipe): só abertos
    linhas += ["", "*Abrigos*", f"- Abertos: {abrigos.get('abrigos_abertos', 0)}"]
    if abrigos.get("atualizado_em"):
        linhas.append(f"- Atualizado em {hora_recife(abrigos['atualizado_em'])}")
    linhas += ["", f"Ações em andamento: {acoes_em_andamento}", "", ASSINATURA]
    return limitar("\n".join(linhas))
