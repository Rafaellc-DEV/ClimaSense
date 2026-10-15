# ADR 0003 — Atlas para bronze e território; Postgres (Neon) para silver, gold e aplicação

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

O ETL anterior gravava a bronze no Atlas e a silver no Neon. A aplicação precisa de integridade forte para versões, revisões e auditoria.

## Decisão

Manter o Atlas (bronze e território) e o Postgres/Neon (silver, gold e dados da aplicação). Decisão P2, de 15/10/2026.

## Consequências

O ETL anterior é preservado. Regras críticas (RN-05, auditoria imutável) também são garantidas por constraints e triggers.
