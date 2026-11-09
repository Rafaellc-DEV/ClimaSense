# ADR 0016 — Escopo sem abrigos; foco em chuva, maré, cenário e arboviroses

- **Situação:** proposta (pedido do dono do projeto em 06/11/2026; aguarda a aprovação registrada em D-13 e a
  validação com o cliente)
- **Data:** 06/11/2026
- **Base:** `docs/PRD.md` v3 (RF-02, RF-07, RF-08, RF-09, RF-13, RF-15, RF-16, RF-33, RF-34); RN-01, RN-02, RN-06,
  RN-11, RN-13; ADR 0008

## Contexto

O PRD v2 colocava abrigos no centro da Situação do evento: abrigos abertos e desabrigados (RF-08, RF-09), a camada de
abrigos no mapa (RF-02, RF-07), atendimento nos abrigos na Saúde (RF-13) e a "resposta disponível" (abrigos abertos e
capacidade) como premissa do simulador. Na prática:

- o feed do COP de abrigos ativos estava vazio desde 04/11/2026, e ocupação e desabrigados só existiam por digitação da
  equipe: a tela mostrava "0" ou "Dados insuficientes" na maior parte do tempo (achado P1 do `qa-ux` na Onda 1);
- o dono do projeto revisou com a equipe a dor real: saber **quanto chove, como está a maré, em que cenário as áreas
  são mais afetadas** e, com o aumento das chuvas, **qual distrito sanitário é mais impactado e com quais arboviroses**
  (dengue, chikungunya e zika);
- a equipe pediu também poder **excluir uma ação** registrada por engano, em qualquer situação, e registrar a ação por
  **distrito ou bairro** (ou a cidade toda).

## Decisão

1. **Abrigos saem do produto.** Locais, abertos, ocupação, pessoas abrigadas, desabrigados, capacidade, camada do mapa,
   ETL (`recife-abrigos`, cadastro e feed de ativos do COP), situação de abrigos e pressão nos abrigos do simulador.
   O dado de abrigos deixa de ser coletado e tratado.
   - Código já removido do backend e do frontend; `data/abrigos/` e `docs/dicionario-dados/recife-abrigos.md` apagados.
   - Migração **0019** (`backend/migrations/versions/0019_remove_abrigos_exclusao_acao.py`) apaga `app.abrigos`,
     `app.abrigo_atualizacoes`, a fonte `recife-abrigos` de `app.fontes` e as execuções dela. O `downgrade` recria as
     estruturas **vazias** (os registros não voltam). Testada só no Postgres local (`test_migracao_0019.py`);
     **ainda não aplicada no Neon**, e só o dono aplica (ADR 0014).
   - As coleções bronze `recife_abrigos` e `recife_abrigos_ativos` no Atlas não são apagadas por esta decisão (a bronze
     nunca é apagada pelo ETL); ficam órfãs até o dono decidir (P-31).
2. **Situação do evento** passa a mostrar o estágio oficial da cidade dado pelo COP, a chuva (medida em 24 h e prevista
   em 24 h) e o nível da maré, cada número com fonte e hora (RF-09, RF-10, RF-19).
3. **Arboviroses como contexto do simulador** (RF-33, RF-34). `POST /cenarios/simular` devolve, por distrito, o bloco
   `arboviroses` (`backend/climasense/servicos/arboviroses_cenario.py`):
   - série semanal de dengue e chikungunya **só do município** (InfoDengue), igual em todos os distritos;
   - total anual de confirmados **por distrito** no último ano publicado (Prefeitura do Recife, soma dos bairros; casos
     sem bairro não entram);
   - zika sem série integrada: sempre "Dados insuficientes" com a fonte que falta (RN-01);
   - classe `baixa`, `media` ou `alta` por **terços do total anual entre os distritos com casos**: critério do projeto,
     relativo (compara os distritos entre si), nunca probabilidade nem percentual (RN-06); zero medido é `baixa`, sem
     dado é nulo (RN-02);
   - `ordem_de_atencao_distritos`: pelo estágio sugerido pela chuva simulada e, no empate, pela classe de arboviroses;
   - contagens de 1 a 4 suprimidas (RN-13, ADR 0015);
   - texto fixo: arboviroses são **contexto** (casos recentes notificados), **não previsão causal** da chuva; selo
     "Experimental" (RN-11).
4. **Ações:** `DELETE /acoes/{id}` exclui a ação em qualquer situação (papel analista ou acima). A auditoria grava
   `acao_resposta_excluida` com quem, quando, território, tipo e situação (sem descrição nem responsável). Os eventos
   da linha do tempo (`app.acao_eventos`) continuam guardados: o histórico segue somente-inclusão, e a migração 0019
   retira a chave estrangeira que impedia o DELETE. O território da ação aceita município, distrito ou bairro (RF-15).

## Alternativas consideradas

- **Manter abrigos com registro manual:** rejeitada pelo dono; o dado não chegava e a tela mostrava zeros.
- **Desligar abrigos por chave (como a landing, ADR 0011):** rejeitada; o pedido é tirar do produto, e o dado não deve
  continuar sendo coletado.
- **Arboviroses como previsão de casos:** rejeitada; não há série semanal por distrito nem modelo validado. Seria
  prometer causalidade que o dado não sustenta.
- **Exclusão lógica da ação (marcar como excluída):** não adotada pelo código; a linha some de `app.acoes_resposta` e o
  rastro fica na auditoria e na linha do tempo. A confirmação com o cliente fica em P-30.

## Consequências

- **Saem do escopo:** RF-08 inteiro; a parte de abrigos de RF-02, RF-07 e RF-13; a premissa "resposta disponível" do
  simulador (PRD §8.1); a "pressão nos abrigos" do resultado. P-02 deixa de valer; P-03 fica só com peçonhentos e
  atendimento em eventos de chuva.
- **Entram:** RF-33 e RF-34 (arboviroses por distrito e ordem de atenção no simulador) e a exclusão de ação no RF-15.
- **Dados:** perdem-se no Neon, ao aplicar a 0019, os registros de abrigo e de ocupação feitos pela equipe. Antes de
  aplicar, o dono decide se exporta (P-31).
- **Pendências de tela:** em 06/11/2026 a tela do Simulador ainda não exibe o bloco de arboviroses (só a API devolve).
- **Perguntas novas:** P-27 a P-31 em `docs/perguntas-abertas.md`.

### O que esta decisão substitui ou qualifica em ADRs anteriores

ADRs aceitos não são reescritos; valem com as ressalvas abaixo.

| ADR | Trecho | Como fica |
|---|---|---|
| 0010 | Ocupação de abrigo como registro da equipe; feed de abrigos do COP; `data/abrigos/` entre as pastas permitidas | Abrigos saíram; `data/abrigos/` não existe mais. O resto da política vale. |
| 0011 | Landing com abrigos para a população | A landing segue desligada; sem abrigos mesmo se for religada. |
| 0012 | `servicos/` com casos de uso de abrigos | `servicos/abrigos.py` foi apagado. |
| 0013 | Backup do esquema `app` cita abrigos | O backup cobre ações, estágios declarados e oficiais e cenários. |
| 0014 | `abrigo_atualizacoes` entre as tabelas somente-inclusão | A tabela some na 0019. `acao_eventos` continua somente-inclusão, sem chave estrangeira para `acoes_resposta`. |
| 0015 | Chave `recife-abrigos-ocupacao` no `frescor.toml` | As chaves `recife-abrigos` e `recife-abrigos-ocupacao` saíram do TOML; rodar `sincronizar-frescor` depois da 0019. |
