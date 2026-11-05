"""Janela de vigilância de leptospirose depois de um evento de chuva (regra pura, sem banco).

Referência: Nota Técnica nº 138/2022-CGZV/DEIDT/SVS/MS (enfrentamento da leptospirose em inundações): incubação de
1 a 30 dias (média de 5 a 14), orientar os expostos a procurar atendimento com sintomas **em até 30 dias** e manter
vigilância ativa nesse período.

Gatilhos (o que o ClimaSense já registra): estágio declarado Alerta ou Crítico, atendimento de alagamento da Defesa
Civil, ou chuva MEDIDA em 24 h acima do limiar de Alerta dos estágios (`Parametros.chuva_24h_alerta_mm`).

A janela é um LEMBRETE de vigilância baseado na incubação, não um risco calculado: não diz que haverá casos nem
quantos. Território sem gatilho não é "sem risco" (pode ter alagado sem registro).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DURACAO_DIAS = 30
ATENCAO_MAIOR_DIAS = (5, 14)  # média de incubação (NT 138/2022)
ORIGENS = ("estagio", "ocorrencia", "chuva")


@dataclass(frozen=True)
class Gatilho:
    dia: date
    origem: str  # estagio | ocorrencia | chuva
    territorio_id: str
    territorio_nome: str
    descricao: str  # ex.: "estágio Crítico declarado", "72 mm em 24 h (APAC)"


def calcular(gatilhos: list[Gatilho], hoje: date, rotulo_dia=lambda d: d.strftime("%d/%m")) -> dict | None:
    """Janela a partir dos gatilhos dos últimos 60 dias.

    - ativa: o gatilho mais recente foi há no máximo 30 dias; `inicio` é o primeiro gatilho da sequência que ainda
      se sobrepõe (gatilhos encadeados estendem a janela) e `fim` = último gatilho + 30 dias;
    - encerrada há pouco (30 a 60 dias): devolve `ativa: false` com as datas, para a equipe ver que já passou;
    - sem gatilho em 60 dias: None.
    """
    recentes = sorted(
        (g for g in gatilhos if timedelta(0) <= hoje - g.dia <= timedelta(days=2 * DURACAO_DIAS)),
        key=lambda g: g.dia,
    )
    if not recentes:
        return None
    # cadeia: volta do mais recente enquanto o anterior ainda estava dentro da janela do seguinte
    fim_cadeia = recentes[-1].dia
    inicio = fim_cadeia
    for g in reversed(recentes):
        if (inicio - g.dia).days <= DURACAO_DIAS:
            inicio = min(inicio, g.dia)
        else:
            break
    usados = [g for g in recentes if g.dia >= inicio]
    fim = fim_cadeia + timedelta(days=DURACAO_DIAS)
    ativa = hoje <= fim
    territorios: dict[str, str] = {}
    for g in usados:
        territorios.setdefault(g.territorio_id, g.territorio_nome)
    partes: list[str] = []
    for g in usados:
        texto = f"{g.descricao} em {rotulo_dia(g.dia)} ({g.territorio_nome})"
        if texto not in partes:
            partes.append(texto)
    excedente = len(partes) - 4
    motivo = "; ".join(partes[:4]) + (f"; e mais {excedente} registro(s)" if excedente > 0 else "")
    dia_da_janela = (hoje - inicio).days + 1 if ativa else None
    return {
        "ativa": ativa,
        "inicio": inicio,
        "fim": fim,
        "dia_da_janela": dia_da_janela,
        "atencao_maior": ativa
        and dia_da_janela is not None
        and ATENCAO_MAIOR_DIAS[0] <= (hoje - fim_cadeia).days + 1 <= ATENCAO_MAIOR_DIAS[1],
        "motivo": motivo,
        "origens": sorted({g.origem for g in usados}),
        "territorios": [{"id": i, "nome": n} for i, n in territorios.items()],
    }
