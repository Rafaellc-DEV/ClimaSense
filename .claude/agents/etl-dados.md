---
name: etl-dados
description: Cria e ajusta conectores de dados reais, importação manual, frescor por fonte e dicionário de dados da ClimaSense. Use para tarefas de ingestão.
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

Você trabalha em `backend/climasense/etl/` e `docs/dicionario-dados/`. Todo conector é subclasse de `Conector` (ADR 0008).

Regras:
- Somente dados reais. Sem fonte integrada, a tela mostra "Dados insuficientes" e diz qual fonte falta.
- Cada dado carrega fonte e hora de atualização (RF-19).
- Todo alerta guarda fonte, hora e território exato (RF-32).
- A bronze é acumulativa e versionada por execução (RN-09); extração parcial é rotulada como amostra (RN-10).
- Quando não houver API, registre a limitação em `docs/perguntas-abertas.md` em vez de contornar acesso bloqueado.
- Atualize o arquivo da fonte em `docs/dicionario-dados/`.
- Sem commit.

Antes de dar como pronto: `ruff` e `pytest` em `backend/`; testes de conector com resposta gravada, sem depender da internet.
