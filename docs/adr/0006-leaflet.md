# ADR 0006 — Leaflet para o mapa, portando o model.js testado

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

O mapa da Aula 07 já usa Leaflet 1.9.4 e tem lógica testada (escala de 5 classes, busca sem acento, CSV seguro).

## Decisão

Manter o Leaflet e portar o `model.js` para TypeScript com os mesmos testes.

## Consequências

Nenhuma funcionalidade do mapa existente se perde (CA-10).
