"""Política de senha (RF-02). Pensada para pessoas que não são da área técnica: pede comprimento,
não símbolos obrigatórios, e explica o problema em linguagem simples."""

from __future__ import annotations

TAMANHO_MINIMO = 10
COMUNS = {
    "1234567890",
    "12345678910",
    "0123456789",
    "senha12345",
    "senhasenha",
    "recife2026",
    "climasense",
    "qwertyuiop",
    "abcdefghij",
    "1111111111",
    "password123",
    "senha@1234",
}


def problemas_da_senha(senha: str, email: str = "", nome: str = "") -> list[str]:
    erros: list[str] = []
    if len(senha) < TAMANHO_MINIMO:
        erros.append(f"Use pelo menos {TAMANHO_MINIMO} caracteres. Uma frase curta funciona bem.")
    simples = senha.lower().replace(" ", "")
    if simples in COMUNS or len(set(simples)) <= 2:
        erros.append("Essa senha é fácil de adivinhar. Escolha outra.")
    usuario = email.split("@")[0].lower()
    if usuario and len(usuario) >= 4 and usuario in simples:
        erros.append("Não use o seu e-mail na senha.")
    primeiro_nome = nome.split(" ")[0].lower() if nome else ""
    if len(primeiro_nome) >= 4 and primeiro_nome in simples:
        erros.append("Não use o seu nome na senha.")
    return erros
