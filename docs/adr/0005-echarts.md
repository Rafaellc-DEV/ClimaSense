# ADR 0005 — Apache ECharts para gráficos

- **Situação:** aceita
- **Data:** 15/10/2026

## Contexto

Os gráficos previstos incluem faixa de incerteza, calendário-heatmap, séries longas e barras, e precisam funcionar para pessoas com daltonismo.

## Decisão

ECharts 5 com um tema derivado dos tokens e o componente `QuadroGrafico` (resumo em frase + tabela alternativa).

## Consequências

As texturas (`decal`) atendem o daltonismo. A paleta categórica foi validada com o verificador de CVD.
