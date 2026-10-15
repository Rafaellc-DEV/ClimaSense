# ADR 0008 — Somente dados reais; ETL em POO

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

Revisão de 15/10/2026: o produto não deve conter dados simulados ou inventados, e o ETL deve seguir POO como ensinado na disciplina.

## Decisão

Fontes climáticas reais sem cadastro no MVP (Open-Meteo: histórico, previsão e maré; Dados Abertos do Recife: alagamentos). Os conectores são subclasses de `Conector`, que compõe `Extract`, `Transform` e `Load`. Na falta de dado, a tela mostra “Dados insuficientes”.

## Consequências

Dados de modelos (reanálise, previsão) aparecem como “derivada” ou “prevista”, nunca como “observada”. ANA, APAC, INMET, Cemaden e a Marinha entram quando houver acesso.
