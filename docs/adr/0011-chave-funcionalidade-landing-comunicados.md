# ADR 0011 — Landing pública e comunicados desligados por chave de funcionalidade

- **Situação:** proposta (Gate 0)
- **Data:** 06/11/2026
- **Requisitos:** PRD §5 (fora do escopo), §12 (risco "superfície pública que o cliente não pediu"), RNF-02, RF-20

## Contexto

A landing pública (`frontend/src/features/landing/`, rotas `GET /publico/*`) e o fluxo de comunicados com revisão e
publicação (`frontend/src/features/comunicados/`, rotas `/comunicados/*`, tabelas `app.comunicados*`, `app.revisoes`)
já foram construídos e testados. O PRD v2 os põe fora do escopo do cliente e manda **desligar por chave de
funcionalidade, sem link no menu e sem apagar o código**. As avaliações territoriais (`/avaliacoes/*`) existem só
para alimentar os comunicados.

Hoje o frontend já usa chaves de build (`VITE_VITRINE`, `VITE_AMBIENTE` em `frontend/src/lib/ambiente.ts` e
`frontend/src/app/ambiente.ts`) e o backend lê a configuração de `backend/climasense/config.py` (pydantic-settings).

## Decisão

1. **Uma chave por funcionalidade, desligada por padrão**, no backend e no frontend:

   | Chave (backend, `.env`) | Chave (frontend, build) | O que liga |
   |---|---|---|
   | `FUNC_LANDING_PUBLICA=false` | `VITE_FUNC_LANDING_PUBLICA=0` | Rotas `GET /publico/*`; página `/` e `/avisos/:id` com a landing |
   | `FUNC_COMUNICADOS=false` | `VITE_FUNC_COMUNICADOS=0` | Rotas `/comunicados/*` e `/avaliacoes/*`; telas de comunicados; contador no menu |

2. **Desligada no backend = rota não registrada** (`ROTEADORES` em `backend/climasense/api/main.py` filtra pelos
   valores da configuração). A rota some do OpenAPI exportado e devolve 404, o que reduz a superfície pública
   (RNF-02). Não basta esconder o link.
3. **Desligada no frontend = rota e item de menu ausentes**. Com a landing desligada, `/` leva à tela de entrar
   (`/entrar`) e, com sessão, ao Mapa da equipe.
4. **O código, os testes e as tabelas ficam.** Os testes da landing e dos comunicados rodam com a chave ligada no
   próprio teste, para não apodrecerem. Nenhuma migração apaga tabela.
5. **Ligar exige decisão do dono do produto**, registrada no PRD (o que estiver fora do escopo só volta pelo PRD).
6. A mensagem pronta de WhatsApp **não** é coberta por esta chave: está no escopo (RF-31).

## Alternativas consideradas

- **Apagar o código**: o PRD proíbe; o trabalho pode voltar a ter uso.
- **Só tirar o link do menu**: deixaria as rotas públicas no ar, superfície que o cliente não pediu.
- **Ramo separado no git**: diverge com o tempo e quebra testes; a chave mantém tudo compilando.

## Consequências

- Implementação na Onda 1: `backend-api` (configuração e registro de rotas, testes) e `frontend-equipe` (rotas, menu,
  redirecionamento de `/`).
- `docs/api/openapi.json` passa a refletir só as rotas ligadas no ambiente padrão.
- `RN-03`, `RN-04` e `RN-05` continuam valendo para os comunicados quando ligados; `RN-05` continua valendo para
  as demais revisões.
