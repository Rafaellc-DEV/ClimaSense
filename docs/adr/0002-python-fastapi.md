# ADR 0002 — Backend em Python com FastAPI

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

O backend precisa ser em Python (requisito R-02), o mesmo ecossistema do ETL existente (pandas, pymongo).

## Decisão

FastAPI + Pydantic v2, com o OpenAPI gerado automaticamente em `/api/docs`.

## Consequências

O contrato da API fica sempre atualizado e a validação de entrada é tipada. Os tipos do frontend podem ser gerados do OpenAPI.
