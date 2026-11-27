# ADR 0018 — Tipografia compacta: texto base de 16 px

- **Situação:** aceita (decisão do dono do projeto em 26/11/2026)
- **Data:** 26/11/2026
- **Base:** RNF-ACE-02 (`specs/requirements.md`), RF-20, RNF-08; pesquisa em `docs/propostas/inspiracao-frontend.md`

## Contexto

A raiz do site estava em 18 px (`frontend/src/design-system/base.css`) e o token de corpo em 1,125 rem. Na prática, o
texto corrido saía com cerca de 20 px, os números dos indicadores com 45 px e o estágio da cidade com até 81 px. O dono
relatou "muito zoom": telas como Ações e Simulador (cenários) exigiam rolar muito e pareciam ampliadas. A pesquisa de 43
painéis de emergência, saúde e mapas mostrou corpo entre 14 e 16 px em telas de operação.

## Decisão

- Raiz em **16 px**. Corpo (`--t-corpo`) 16 px, apoio (`--t-apoio`) 14 px, títulos de 18 a 32 px
  (`--t-4` a `--t-1`) e estágio da cidade entre 32 e 52 px (`--t-estado`).
- A mesma escala vale para todas as telas, para que o tamanho seja igual entre páginas.
- Alvos de toque continuam com no mínimo 44 px. Campos de formulário no celular continuam com 16 px, para o iOS não
  ampliar a tela ao focar.
- O zoom do navegador continua livre.

## Consequências

- RNF-ACE-02 passa a pedir texto base de 16 px (mínimo 13 px em rótulos).
- Telas com tamanhos próprios em px (Mapa, Dashboards) devem seguir a mesma escala.
- Validar a leitura com as usuárias na próxima rodada; se houver queixa, ajustar os tokens, não cada tela.
