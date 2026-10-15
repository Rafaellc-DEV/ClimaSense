# ADR 0004 — Frontend em React + TypeScript + Vite

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

Muitas telas e dashboards, filtros compartilhados, identidade própria e acessibilidade para um público idoso e não técnico.

## Decisão

React 18 + TypeScript + Vite, com CSS Modules e tokens (sem framework utilitário), Radix UI para componentes acessíveis e TanStack Query para os dados.

## Consequências

Controle total do visual e da acessibilidade. Streamlit e Dash foram descartados por limitarem a identidade, o login com papéis e o controle de acessibilidade.
