# Guia de marca — ClimaSense

Este guia diz como usar a identidade do ClimaSense. A referência técnica completa está no [`design.md` §8](../../specs/design.md). Os valores de código ficam em [`frontend/src/design-system/tokens.css`](../../frontend/src/design-system/tokens.css).

## 1. A ideia

O Recife é uma cidade de rios e pontes onde a maré decide boa parte dos alagamentos. Nas pontes do Capibaribe há **réguas linimétricas**, que mostram o nível da água. O ClimaSense usa essa régua como o seu elemento central: ela **mostra o nível do aviso**, não enfeita.

Quatro escolhas fazem a identidade:

1. **Régua de maré** como linguagem de nível: na página inicial, nos selos, no editor de comunicados e no ícone.
2. **Cartografia em traço**: rios e distritos desenhados em linha fina, a partir dos arquivos oficiais do Recife.
3. **Tipografia como imagem**: a frase de estado em letra grande ocupa o lugar da foto de destaque.
4. **Um único movimento**: a água sobe até o nível vigente quando a página abre. Nada mais se move sozinho.

## 2. Logo

| Arquivo | Uso |
|---|---|
| `frontend/public/brand/logo.png` · `logo@2x.png` | Principal, sobre fundos claros (papel e névoa) |
| `frontend/public/brand/logo-negativo.png` · `logo-negativo@2x.png` | Sobre o azul maré ou fundos escuros. O nome fica branco e o símbolo mantém as cores |
| `frontend/public/brand/simbolo.svg` | Só o símbolo, em tamanhos pequenos (a partir de 24 px) |
| `frontend/public/brand/icone.svg` e PNGs | Ícone do aplicativo, favicon (16 e 32 px), Apple (180 px), PWA (192 e 512 px) |
| `frontend/public/brand/og-climasense.png` | Imagem de compartilhamento de links (1200 × 630) |
| `docs/brand/climasense-logo.png` | Original enviado pela equipe, preservado |

**Área de proteção:** deixe em volta da logo um espaço livre igual à altura do sol do símbolo.
**Tamanho mínimo:** 120 px de largura para a logo completa; abaixo disso, use o símbolo.

**Não faça:**

- Não aplique a logo principal sobre o azul maré, porque a palavra “Clima” desaparece. Use a versão negativa.
- Não estique, não gire, não troque as cores e não ponha sombra ou contorno.
- Não coloque a logo sobre fotos ou sobre o traço dos rios com opacidade alta.

## 3. Cores

| Nome | Hex | Uso |
|---|---|---|
| Maré | `#0F4C75` | Cor principal: títulos, item ativo do menu, botão principal |
| Mangue | `#0B6F6C` | Links, seleção, ações secundárias |
| Sol | `#EDB105` | Só na marca e na linha d’água. **Nunca como texto** |
| Tinta | `#0E2433` | Texto principal (15,9:1 sobre o papel) |
| Tinta 2 | `#44596A` | Texto secundário (7,2:1) |
| Névoa | `#F2F6F8` | Fundo da página (azul-acinzentado frio) |
| Papel | `#FFFFFF` | Painéis |

**Níveis de aviso** (reservados: nunca use como cor de série de gráfico):

| Nível | Texto exibido | Marcas na régua |
|---|---|---|
| Sem aviso | Nenhum aviso ativo | Água na base |
| Informativo | Fique atento | 1 de 4 |
| Atenção | Atenção | 2 de 4 |
| Alerta | Alerta | 3 de 4 |
| Crítico | Situação crítica | 4 de 4 |
| Dados insuficientes | Dados insuficientes | Régua vazia e tracejada |

A cor **nunca** aparece sozinha: o nome do nível está sempre escrito ao lado. O contraste de todos os pares de texto é verificado automaticamente (`tokens.test.ts`, 31 verificações nos modos claro e escuro).

**Gráficos:** azul rio `#1F6FB2`, laranja barro `#C4612B`, verde mangue `#0A8F63`, violeta `#7A52C7`, oliva `#5D7F1F`, magenta `#B8478F`, sempre nesta ordem, validada para daltonismo. A referência histórica é sempre **cinza tracejado** `#6B7A85`.

## 4. Tipografia

**Atkinson Hyperlegible Next**, criada pelo Braille Institute para leitores com baixa visão. É uma família só, e a hierarquia vem do peso e do tamanho.

| Papel | Tamanho | Peso |
|---|---|---|
| Frase de estado (landing) | até 72 px | 800 |
| Título da página | 44 px | 750 |
| Título da tela | 35 px | 700 |
| Título de seção | 28 px | 700 |
| Título de painel | 22 px | 650 |
| Corpo | **18 px** | 400 |
| Apoio (fontes, ajuda) | 16 px (mínimo) | 400 |

Não use caixa alta em rótulos, itálico ou cor em uma palavra só do título, nem fonte monoespaçada para números (use números tabulares).

## 5. Forma

- Painéis com borda de 1 px e **sem sombra**. A sombra fica só para o que flutua: diálogos, menus e notificações.
- Raios: 4 px em campos e selos, 10 px em painéis, pílula só em chips de filtro, 0 na régua.
- Botões com pelo menos 48 px de altura (56 px no botão principal da página inicial).

## 6. Tom de voz

- Frases curtas, caixa normal e voz ativa. O botão diz o que acontece, e a confirmação repete o verbo: **“Enviar para revisão” → “Enviado para revisão.”**
- Siglas por extenso na primeira vez: “Distrito Sanitário IV (DS IV)”.
- Erros dizem o que aconteceu e o que fazer, sem pedir desculpas.
- Telas vazias convidam a agir: “Nenhuma avaliação ainda. Comece pelo mapa e registre a primeira.”
- Nunca diga “sem risco” ou “tudo seguro”. Sem aviso publicado, diga **“Nenhum aviso ativo publicado pela equipe.”**

## 7. Dados

Tudo o que aparece no produto vem de **fontes reais e identificadas**, com nome e data de atualização. Quando um dado não existe, a tela mostra **“Dados insuficientes”** e nunca inventa valores.

## 8. Onde ver

- Vitrine viva: `http://localhost:5173/_vitrine` (só em desenvolvimento)
- Capturas: [`docs/brand/capturas/`](capturas/)
- Prévia da identidade aprovada na fase de design: [`previa-identidade.html`](previa-identidade.html). Ela contém textos **ilustrativos** de avisos, que não são dados do produto.
