# ClimaSense

Painel de gestão do Vigidesastres (Secretaria de Saúde do Recife) para antecipar o impacto de chuvas por bairro e acompanhar a resposta. Projeto acadêmico do Grupo 3 (AVD 2026.2, CESAR School) que atende a um cliente real.

## Fonte da verdade
- O PRD está em `docs/PRD.md`. Em conflito com `specs/requirements.md` ou `specs/foco-chuvas.md`, vale o PRD.
- Todo trabalho cita um ID do PRD (`RF-xx`, `RNF-xx`) e, quando couber, uma regra `RN-xx` de `specs/requirements.md`.
- Se algo não está no PRD, não construa. Registre como pergunta em `docs/perguntas-abertas.md`.
- Decisões de arquitetura ficam em `docs/adr/` (próximo número: 0014).

## Regras que valem para todo código
1. Somente dados reais (ADR 0008, RF-12.10). Sem dado simulado no produto. Dados de exemplo só em testes automatizados.
2. Ausência de dado não é risco baixo (RN-01). Sem dado: "Dados insuficientes" e a fonte que falta. Zero medido é diferente de ausente (RN-02).
3. Prioridade não é probabilidade (RN-06). Risco aparece como classe, nunca como percentual.
4. Experimental até validar (RN-11): previsão de alagamento leva o selo até haver validação temporal documentada.
5. Decisão humana por último: o sistema sugere, a equipe declara o estágio e publica avisos. Ninguém aprova o próprio conteúdo (RN-05).
6. Todo indicador mostra fonte e hora da última atualização (RF-19).
7. Telas intuitivas e simples de usar; só o que o cliente pediu (RF-20, RNF-08).
8. Só dados agregados; nada que identifique pessoa (RN-13, RNF-03).
9. Segurança primeiro: sem segredos no código, gitleaks e pre-commit sempre ativos.

## Estrutura
- `backend/climasense/api/` rotas; `dominio/` regras de negócio; `auth/` autenticação; `infra/` banco
- `backend/climasense/etl/` conectores e pipeline (bronze, silver, gold)
- `backend/climasense/ml/` estudos e modelos
- `backend/tests/` testes do backend; `frontend/tests/e2e/` testes de ponta a ponta
- `frontend/src/features/` telas por funcionalidade; `design-system/`, `map/`, `charts/`, `lib/`
- `specs/` requisitos, design e tarefas; `docs/` PRD, ADRs, dicionário de dados, ML

## Como trabalhar
- Cada agente edita só as suas pastas.
- Não faça commit. Deixe as mudanças na árvore de trabalho para o usuário revisar e commitar.
- Antes de dar uma tarefa como pronta, rode os checks da sua área:
  - backend: `ruff check . && ruff format --check .` e `pytest` (dentro de `backend/`)
  - frontend: `npm run lint`, `npm test` e `npm run build` (dentro de `frontend/`)
- Textos da interface e documentação em português do Brasil.
