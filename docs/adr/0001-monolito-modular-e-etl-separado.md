# ADR 0001 — Monólito modular em camadas + ETL separado

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

O template de arquitetura da equipe marca camadas, MVC e microsserviços. O MVP é acadêmico, com equipe pequena e prazo de um semestre.

## Decisão

Uma API FastAPI organizada em módulos isolados por camadas (api, auth, servicos, dominio, infra) e um segundo executável para o ETL. Os módulos têm fronteiras claras e podem virar serviços depois.

## Consequências

A parte mais instável (fontes externas) fica isolada da API. Há um só deploy da API. A regra de camadas é verificada por teste (`test_arquitetura.py`).
