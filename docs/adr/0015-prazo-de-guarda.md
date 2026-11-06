# ADR 0015 — Prazo de guarda e limites de frescor

- **Situação:** aceita
- **Data:** 06/11/2026
- **Base:** RNF-03, RNF-01, RF-19; ADR 0014 (papel do dono para manutenção)

## Decisão

1. **Prazo de guarda** (dados de acesso, que contêm e-mail e IP):

   | Dado | Guarda | Apagado quando |
   |---|---|---|
   | `app.tentativas_login` | 90 dias | `em` anterior a 90 dias |
   | `app.sessoes` | 30 dias após expirar | `expira_em` anterior a 30 dias |
   | `app.auditoria` | sem prazo definido aqui | a aplicação não apaga (gatilhos e GRANT); fica para decisão do cliente |

   Variáveis: `RETENCAO_TENTATIVAS_LOGIN_DIAS` (90) e `RETENCAO_SESSOES_DIAS` (30).
2. **Comando:** `python -m climasense.admin limpar-retencao`. Idempotente. Usa a URL do dono (`DATABASE_URL_MIGRACOES`):
   o papel `climasense_app` não apaga auditoria e a limpeza não deve depender dele. Grava em `app.auditoria` a ação
   `limpeza_retencao` só com as quantidades (nenhum e-mail ou IP). Deve rodar por agendamento (diário); enquanto não
   houver agendador, o dono roda à mão.
3. **Frescor das fontes (RF-19):** a fonte única do limite é `backend/climasense/etl/frescor.toml`
   (`etl/frescor.py`). `meta.fontes[].limite_frescor_h` e `desatualizado` vêm dele (`null` = sem dado ou sem limite,
   nunca "em dia" por falta de dado). `python -m climasense.admin sincronizar-frescor` faz
   `app.fontes.limite_desatualizacao_h` seguir o TOML (arredonda para cima, idempotente, auditado), para a tela de
   Fontes e a API não divergirem. Rodar depois de alterar o TOML. A chave `recife-abrigos-ocupacao` vale para a
   ocupação lançada à mão (não é conector, não existe em `app.fontes`).
4. **Supressão (RNF-03, RN-13):** contagem de agravo por bairro entre 1 e `supressao_minima - 1` (padrão 5) sai
   `null` com `suprimido: true`; zero continua zero. Supressão complementar: se algum bairro foi suprimido, ou se o
   "sem bairro" é pequeno, `confirmados_sem_bairro` sai `null` (`sem_bairro_suprimido: true`); totais menores que o
   mínimo também. Itens suprimidos são ordenados por nome, depois dos de valor ≥ mínimo, para a ordem não vazar o valor.
   Séries semanais do município (sem recorte territorial) não são suprimidas.
5. **Leitura auditada:** toda leitura de `/saude/*` e `/boletim*` grava uma linha (`leitura_dados_saude`,
   `leitura_boletim`) com usuário, IP, rota, método e filtros; nunca o corpo.

## Consequências

- O campo admin `limite_desatualizacao_h` (PATCH de fonte) deixa de definir o `desatualizado` da API; vale o TOML.
