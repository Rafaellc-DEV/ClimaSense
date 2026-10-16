# Plano visual das telas (M8–M12)

Aplica a skill `frontend-design` (em `.claude/skills/frontend-design/`) sobre a identidade já aprovada no design §8.
Este arquivo registra as escolhas e o que foi revisto, para a próxima pessoa não refazer a mesma discussão.

## Assunto, público e tarefa principal

- **Assunto:** avisos de chuva, maré e alagamento no Recife, revisados pela Vigilância em Saúde.
- **Público:** na landing, moradores, muitos idosos e no celular; na área da equipe, técnicos da saúde, não analistas de dados.
- **Tarefa principal:** na landing, saber em 3 segundos se há aviso e o que fazer. Na equipe, saber o que precisa de mim agora.

## Referências pesquisadas e o que foi aproveitado

| Referência | O que levamos |
|---|---|
| GOV.UK *Check for flooding* (Environment Agency) | Mobile primeiro (mais de 70% dos acessos). A pergunta é “vou alagar?”, então o estado vem antes do mapa. |
| NWS *Hazard Simplification* (EUA) | O cartão de aviso segue **o quê, onde, até quando, o que fazer**, nessa ordem, com títulos em linguagem simples. |
| Government Analysis Function (Reino Unido), Maryland e Mass.gov (EUA): guias de painéis acessíveis | Todo gráfico tem uma frase-resumo, uma tabela com os mesmos valores e exportação CSV. Um gráfico protagonista por bloco. |

## Tokens (já definidos em `design-system/tokens.css`)

| Nome | Hex | Papel |
|---|---|---|
| Maré | `#0F4C75` | Marca, títulos, botão principal, item ativo |
| Mangue | `#0B6F6C` | Links, ações secundárias, barra do item ativo |
| Sol | `#EDB105` | Só a linha d’água da régua e a marca |
| Névoa | `#F2F6F8` | Fundo frio (não creme) |
| Tinta | `#0E2433` | Texto |

Tipografia: **uma família**, Atkinson Hyperlegible Next. A hierarquia vem de peso (400 → 800) e tamanho (escala 1,25 sobre 18 px).

## Layout

```text
Landing (≥1024)                         Área da equipe (≥1024)
┌────────────────────────────────────┐  ┌──────────┬─────────────────────────────┐
│ logo                 links  Entrar │  │ logo     │ Mostrando Recife inteiro,   │
│ ░ rios em traço ░                  │  │ ▌Painel  │ de 1º jul. a 15 out. 2026   │
│ FRASE DE ESTADO 72/800      │régua│ │  │  Mapa    ├─────────────────────────────┤
│ apoio · busca do bairro     │ 1–4 │ │  │  Séries  │ Título (35/700)             │
├────────────────────────────────────┤  │  …       │ frase de propósito          │
│ 199 Defesa Civil │ 193 │ 192       │  │          │ blocos com borda de 1 px    │
├────────────────────────────────────┤  │ conta    │                             │
│ avisos em vigor │ mapa dos distritos│  └──────────┴─────────────────────────────┘
└────────────────────────────────────┘
```

Tudo alinhado à esquerda. Exceções: o formulário de entrar (coluna estreita) e diálogos curtos.

## Revisão contra os padrões genéricos (o que mudou e por quê)

| Encontrado no código anterior | Por que é genérico | Mudança |
|---|---|---|
| Sobretítulo “Avisos de chuva e alagamento · Recife” acima da frase de estado | Rótulo acima do título com meta separada por ponto médio: as duas marcas de template que o design §8.2 proíbe | Removido. A frase de estado é o primeiro texto da página. |
| Links “Ver todas as fontes →” | Seta anexada ao texto do link | O texto do link basta: “Ver todas as fontes”. |
| Rodapé “Projeto acadêmico · Análise… · CESAR School · 2026” | Meta com pontos médios | Frases completas. |
| Menu da equipe azul-escuro com faixa amarela | O design §9.3 pede menu claro, com o item ativo marcado por fundo, barra e peso; menu escuro é o kit de painel SaaS | Menu em papel, item ativo com fundo maré 8%, barra mangue de 4 px e peso 700. |
| Painéis com um número grande como destaque | “Número grande + rótulo pequeno” é o herói padrão de dashboard | Blocos respondem com frases e listas curtas. Número grande só onde ele é a resposta. |

## Princípios

1. **A régua é o único elemento memorável.** Aparece na landing (grande), nos selos, nos botões de nível do editor e da avaliação. Nada mais compete com ela.
2. **Ausência de dado tem uma cara só:** o `EstadoDados`, com hachura. Nunca zero, nunca “baixo”.
3. **Movimento só para responder.** A única animação sozinha é a subida da água na landing (700 ms, desligada com movimento reduzido).
4. **Bordas de 1 px, sem sombra** nos painéis. Sombra só no que flutua (diálogos, menus, aviso de sessão).
