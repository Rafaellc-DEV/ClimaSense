"""Proteção contra força bruta (RF-02.3, RNF-01). Domínio puro: recebe as tentativas e o relógio, devolve até
quando está bloqueado ou em espera.

Duas escalas, para ninguém conseguir manter uma conta travada de fora:
- por e-mail E IP (o par): 5 falhas em 15 min bloqueiam aquele par por 15 min. Falhas vindas de outro IP não
  contam para o par, então um IP atacante só trava a si mesmo e a coordenação segue entrando do seu IP;
- por IP (todas as contas): 20 falhas em 15 min bloqueiam o IP por 15 min (barra a tentativa de adivinhar
  senha de muitas contas). Um login com sucesso zera a contagem.

Além do bloqueio há um atraso progressivo: passadas as falhas "livres", cada nova falha obriga a esperar
2^k segundos (k = falhas acima das livres), com teto. O administrador pode liberar e-mail e/ou IP
(servicos.autenticacao.liberar_login)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

LIMITE_FALHAS = 5
LIMITE_FALHAS_IP = 20
FALHAS_LIVRES = 2  # par e-mail+IP: a 3ª falha já obriga a esperar 2 s
FALHAS_LIVRES_IP = 5
TETO_ESPERA_S = 30
TETO_ESPERA_IP_S = 30
JANELA = timedelta(minutes=15)
DURACAO_BLOQUEIO = timedelta(minutes=15)


@dataclass(frozen=True)
class Tentativa:
    em: datetime
    sucesso: bool


def bloqueado_ate(
    tentativas: Iterable[Tentativa], agora: datetime, limite: int = LIMITE_FALHAS
) -> datetime | None:
    """Conta as falhas desde o último sucesso; se a falha de número `limite` caiu numa janela de 15 min,
    bloqueia por 15 min."""
    falhas: list[datetime] = []
    for t in sorted(tentativas, key=lambda t: t.em):
        if t.sucesso:
            falhas.clear()
        else:
            falhas.append(t.em)
            falhas = [f for f in falhas if t.em - f < JANELA]
            if len(falhas) >= limite:
                fim = t.em + DURACAO_BLOQUEIO
                if fim > agora:
                    return fim
                falhas.clear()
    return None


def espera_ate(tentativas: Iterable[Tentativa], agora: datetime, livres: int, teto_s: int) -> datetime | None:
    """Atraso progressivo: com `k` falhas na janela (desde o último sucesso) acima das `livres`, a próxima
    tentativa só vale 2^k segundos depois da última falha, no máximo `teto_s`. None = pode tentar."""
    falhas: list[datetime] = []
    for t in sorted(tentativas, key=lambda t: t.em):
        if t.sucesso:
            falhas.clear()
        else:
            falhas.append(t.em)
    falhas = [f for f in falhas if agora - f < JANELA]
    excesso = len(falhas) - livres
    if excesso <= 0:
        return None
    fim = falhas[-1] + timedelta(seconds=min(2**excesso, teto_s))
    return fim if fim > agora else None
