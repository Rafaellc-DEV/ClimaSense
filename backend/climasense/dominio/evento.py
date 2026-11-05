"""Erro comum dos registros do evento de chuva (estágio, abrigos, ações), com status e mensagem para a tela."""

from __future__ import annotations


class RegistroInvalido(ValueError):
    def __init__(self, status: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem
