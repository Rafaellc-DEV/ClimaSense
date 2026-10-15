"""Hash de senhas com Argon2id (RNF-SEG-02). A senha nunca é guardada nem registrada em log."""

from __future__ import annotations

import secrets

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_hash = PasswordHash((Argon2Hasher(),))
# Usado quando o e-mail não existe, para o tempo de resposta não revelar quais contas existem.
_HASH_FICTICIO = _hash.hash(secrets.token_urlsafe(16))

_ALFABETO = "abcdefghjkmnpqrstuvwxyz23456789"  # sem 0/o, 1/l/i: fácil de ditar e digitar


def gerar_hash(senha: str) -> str:
    return _hash.hash(senha)


def conferir(senha: str, hash_salvo: str | None) -> bool:
    if not hash_salvo:
        _hash.verify(senha, _HASH_FICTICIO)
        return False
    try:
        return _hash.verify(senha, hash_salvo)
    except Exception:  # noqa: BLE001 — hash corrompido conta como senha errada
        return False


def senha_temporaria() -> str:
    """Ex.: 'kd7m-x3pa-q9wt' — mostrada uma única vez ao administrador; a troca é obrigatória no 1º acesso."""
    return "-".join("".join(secrets.choice(_ALFABETO) for _ in range(4)) for _ in range(3))
