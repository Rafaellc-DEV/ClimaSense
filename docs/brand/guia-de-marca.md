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

## 9. Plataforma de gestão

A área da equipe usa a mesma identidade da landing e do login: azul maré profundo com a malha de pontos e o traço dos rios, amarelo-sol como acento, cartões brancos com sombras suaves em camadas, painéis de 14 px, formas em pílula, títulos em Outfit (800/700), corpo em Atkinson Hyperlegible Next. Isto **atualiza** a regra de §5 para a gestão: os cartões ganham sombra de repouso (`--sombra-cartao`).

### 9.1 Paleta por grupo (tokens em `tokens.css`)

| Grupo | Tokens | Uso |
|---|---|---|
| Marca | `--cs-mare`, `--cs-mare-forte`, `--cs-mare-suave`, `--cs-mangue`, `--cs-sol`, `--cs-espuma` | Maré: títulos, valores, ação principal. Mangue: links. Sol: acento (item ativo, contador); nunca texto. |
| Neutros | `--cs-papel`, `--cs-nevoa`, `--cs-tinta`, `--cs-tinta-2`, `--cs-linha`, `--cs-linha-forte` | Papel: cartões. Névoa: fundo da página. Tinta: texto. Linha: fios. |
| Superfície de marca | `--sup-mare`, `--sup-mare-forte`, `--sup-sobre`, `--sup-sobre-2`, `--sup-linha`, `--sup-hover`, `--sup-ativo`, `--sup-sol` | Menu lateral, gaveta e barra do celular. **Não invertem no tema escuro** (só ficam um tom mais fundos). Texto branco, contraste verificado em `tokens.test.ts`. |
| Níveis | `--n-*` | Só para nível de aviso, sempre com o nome escrito (Pílula ou SeloNivel). Nunca como cor de série. |
| Gráficos | `--g-*`, `--g-seq-*`, `--g-calor-*` | Séries em ordem fixa; referência cinza tracejado. |

Escuro: ligue com `data-tema="escuro"` no `<html>`. Só `--cs-*`, `--n-*-bg`, `--g-*` e as sombras mudam.

### 9.2 Formas

| Token | Valor | Uso |
|---|---|---|
| `--r-campo` | 4 px | Campos de formulário |
| `--r-icone` | 10 px | Balões, blocos de esqueleto, discos de ícone |
| `--r-painel` | 14 px | Cartões, painéis, tabelas, indicadores |
| `--r-pilula` | 999 px | Chips, Pílula, filtro, item de menu, botões (na gestão: `--r-botao`) |
| `--sombra-cartao` | camadas suaves | Cartões em repouso |
| `--sombra-cartao-alta` | camadas maiores | Cartão em foco ou sob o mouse |
| `--sombra-flutuante` | grande | Só o que flutua: diálogos, balões |

### 9.3 Regras da plataforma

1. **Sem texto solto.** Todo dado vive em um componente com rótulo, valor e, quando houver, fonte e hora atrás de um (i).
2. No máximo **uma frase curta** por bloco. Explicação longa vai em `Dica` ou em “Ver detalhes”.
3. As telas existem para **decidir**: qual território pede atenção primeiro, por quê e com que confiança. O mapa é uma lente de apoio (“Territórios”).
4. Falta de dado nunca vira zero: `Indicador` mostra “Sem dado” ou “Dados insuficientes”.
5. A cor nunca fala sozinha: nível, tendência e confiança sempre trazem palavras.

### 9.4 Kit de componentes (`src/design-system/componentes`)

| Componente | Quando usar | Exemplo |
|---|---|---|
| `CabecalhoTela` | Primeira coisa de toda tela. O propósito vai no (i), não em parágrafo. | `<CabecalhoTela titulo="Cenários" proposito="Simule a chuva…" acoes={<Botao>Exportar</Botao>} voltar={<Link to="/app">Voltar ao painel</Link>} />` |
| `Indicador` | Um número que importa. Rótulo, valor, `unidade`, `tendencia`, `nivel`, `explicacao` e `fonte` (ambos no (i)). `carregando`, `insuficiente` e `valor={null}` já tratados. | `<Indicador rotulo="Chuva em 24 h" valor="62,4" unidade="mm" nivel="alerta" tendencia={{sentido:"sobe",texto:"+18 mm",efeito:"ruim"}} fonte={[{nome:"APAC",atualizadoEm}]} />` |
| `Pilula` | Estado ou categoria curta. `nivel` usa as cores do SeloNivel; `tom` para o resto. | `<Pilula nivel="alerta">Alerta</Pilula>`, `<Pilula tom="sucesso">Publicado</Pilula>` |
| `Painel` | Seção com título. `dica` para a explicação, `acoes` à direita, `largo` para ocupar a linha toda. | `<Painel id="x" titulo="Chuva por distrito" dica="…">…</Painel>` |
| `Tabela` | Comparar linhas. `carregando`, `vazio` e `densidade="compacta"`. | `<Tabela legenda="…" colunas linhas chaveLinha vazio="Nenhuma avaliação." />` |
| `Ranking` + `ItemRanking` | Territórios em atenção: posição, nome, nível, até 3 motivos, confiança, clique. | `<Ranking rotulo="Territórios em atenção"><ItemRanking posicao={1} nome="Afogados" nivel="critico" motivos={["chuva 62 mm"]} confianca="alta" para="/app/mapa" /></Ranking>` |
| `Dica` / `DicaFonte` | Qualquer ajuda ou fonte. `lado`, `alinhar` evitam sair da tela. | `<Dica texto="…" rotulo="Sobre o dado" />` |
| `Esqueleto`, `EsqueletoIndicador`, `CarregandoLista` | Carregamento sem salto de layout, no lugar de “Carregando…” solto. | `<CarregandoLista linhas={4} />` |
| `EstadoDados` | Insuficiente, desatualizado ou falha, com `acao` opcional. | `<EstadoDados tipo="falha" acao={<Botao>Tentar de novo</Botao>}>Confira a conexão.</EstadoDados>` |
| `FaixaMare` | A resposta principal da tela, em azul profundo com malha de pontos e rios (“Situação agora”). Dentro: `Pilula sobreMare`, `Botao variante="claro"` e `"contornoClaro"`. | `<FaixaMare titulo="Situação agora" id="f">…</FaixaMare>` |
| `Segmentado` | Escolher uma opção entre poucas (horizonte 24, 48 ou 72 h), em pílulas; rádios nativos. | `<Segmentado rotulo="Horizonte" opcoes={[{valor:24,rotulo:"24 h"}]} valor={24} aoMudar={…} />` |
| `Experimental` | Selo fino em toda estimativa do estimador de referência (RN-06). | `<Experimental />` |
| `Indicador selo` | Selo curto no rodapé do indicador: “Amostra”, “Prevista”. | `<Indicador selo={<Pilula pequena>Amostra</Pilula>} … />` |
| `Ranking compacto`, `ItemRanking selecionado` | Lista mestre-detalhe em coluna estreita: o item escolhido tem `aria-pressed` e realce. `confianca` aceita `"insuficiente"`. | `<Ranking rotulo="Fila" compacto><ItemRanking selecionado aoAbrir={…} /></Ranking>` |

**Faça:** um dado por `Indicador`; motivos em chips de 1 a 3 palavras; `fonte` sempre que o número vier de uma fonte; `Pilula nivel` com o nome do nível.
**Não faça:** parágrafos explicativos soltos; cor de nível sem texto; zero no lugar de “sem dado”; mais de uma frase num bloco; hex solto no CSS (use tokens).

### 9.5 Menu e estrutura

Menu lateral azul profundo (272 px), logo `Marca` branca, três grupos separados por um fio: **decidir** (Painel, Cenários, Séries, Territórios), **acompanhar** (Avaliações, Comunicados) e a **base** (Fontes, Administração, só com permissão). Item ativo: pílula clara com traço sol e ícone em sol; contadores em sol. Embaixo: pessoa (link para Minha conta) e “Sair”. Barra do topo: só o filtro compacto (território e período) e o aviso de demonstração; o nome da seção vive no `<h1>` da página, nunca nos dois. Sem filtro nem aviso, o topo some no computador. Abaixo de 1024 px, o topo vira azul com a logo e o menu abre em gaveta. Vitrine: seção “Plataforma de gestão” em `/_vitrine`, com botão claro/escuro.
