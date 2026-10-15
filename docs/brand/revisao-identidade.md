# Revisão da identidade visual (T1.10)

Data: 15/10/2026. Capturas da vitrine (`/_vitrine`) geradas pelo teste `frontend/tests/e2e/vitrine.spec.ts`, que também verifica a acessibilidade (axe, WCAG 2.2 AA) e a ausência de rolagem horizontal.

| Largura | Captura | Rolagem horizontal | Violações sérias ou críticas (axe) |
|---|---|---|---|
| 375 px | [vitrine-375.png](capturas/vitrine-375.png) | Não | 0 |
| 768 px | [vitrine-768.png](capturas/vitrine-768.png) | Não | 0 |
| 1440 px | [vitrine-1440.png](capturas/vitrine-1440.png) | Não | 0 |

## Checklist anti-genérico (design §8.2)

| Item | Situação |
|---|---|
| Sem rótulos em CAIXA ALTA espaçada acima dos títulos | ok |
| Sem meta-textos com “•” ou “·” (frases completas) | ok |
| Sem ondas decorativas; a única água é a régua, que tem valor | ok |
| Sem cards idênticos com sombra; painéis com borda e sem sombra | ok |
| Fonte escolhida pelo público (Atkinson Hyperlegible Next), não a padrão | ok |
| Destaque tipográfico por peso e tamanho, sem cor ou itálico numa palavra só | ok |
| Um único movimento automático (a água da régua) e respeito a `prefers-reduced-motion` | ok |
| Cor nunca sozinha: todo nível tem o nome escrito | ok (21 testes de componente) |
| Contraste de todos os pares de texto (claro e escuro) | ok (31 verificações em `tokens.test.ts`) |
| **Somente dados reais** na vitrine (distritos e bairros oficiais) | ok (`dadosReais.test.ts` compara com o arquivo oficial) |

## Correções feitas durante a revisão

- **Borda dos campos** clareava demais (2,6:1). Escurecida para `#7A8E9C` (3,4:1) no claro e `#6B8494` no escuro.
- **Selo “Situação crítica”** tinha branco a 6,6:1, abaixo da meta de 7:1 dos avisos públicos. O vermelho passou para `#A41F15` (7,5:1).
- **Logo sobre o azul maré**: a palavra “Clima” desaparecia. Criada a versão negativa (nome em branco, símbolo preservado).
- **Halos da logo**: pixels semitransparentes do recorte original removidos.
- **Gráfico**: o ECharts punha um `aria-label` num elemento sem papel (violação do axe). A descrição acessível ficou só no contêiner do gráfico.
- **Cores em telas estreitas**: a grade das amostras de cor passou a ter 2 colunas em 375 px.
- **Dados fictícios removidos**: a vitrine usava uma série inventada de chuva. Agora usa os 8 distritos e os 94 bairros reais.
