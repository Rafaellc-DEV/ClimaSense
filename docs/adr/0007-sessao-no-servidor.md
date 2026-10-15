# ADR 0007 — Sessão no servidor com cookie HttpOnly e CSRF

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

Requisitos de expiração por inatividade (60 min), revogação no logout e público que não deve lidar com tokens.

## Decisão

Token aleatório de 32 bytes no cookie `cs_sessao` (HttpOnly, SameSite=Lax), só o hash no banco, CSRF por double-submit.

## Consequências

Expirar e revogar é simples e auditável. Não há token acessível ao JavaScript.
