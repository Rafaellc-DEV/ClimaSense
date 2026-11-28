# ADR 0019 — Dado vencido some da interface; ETL agendado para todas as fontes

- **Situação:** aceita (decisão do dono do projeto em 28/11/2026, antes da apresentação ao cliente)
- **Data:** 28/11/2026
- **Base:** RF-10, RF-19, RF-42, RNF-05; RN-01, RN-02; limites em `backend/climasense/etl/frescor.toml` (ADR 0015)

## Contexto

Na véspera da apresentação, o banco compartilhado tinha fontes vencidas havia semanas: nenhuma rotina de atualização
estava registrada, e 180 execuções abertas desde 13/11 travavam 20 fontes. A interface mostrava o valor vencido com o
selo "Desatualizado" (RF-19). O dono pediu duas coisas: todos os dados atualizados, com a pipeline rodando sozinha de
tempos em tempos, e que dado desatualizado não apareça no sistema.

## Decisão

1. **Dado de fonte vencida some.** Passado o limite de `frescor.toml`, o valor não aparece nem com selo: o cartão, a
   camada do mapa, o gráfico, o agravo de saúde ou a premissa do simulador saem da tela. A regra fica em
   `frontend/src/lib/frescor.ts` (`estaVencida`, `algumaVencida`, `semVencidas`) e em `useFontesVencidas`
   (`lib/fontes.ts`). Nos estágios, cada insumo some só quando a fonte dele venceu (`semSugestaoVencida`,
   `features/mapa/tipos.ts`). A sugestão do sistema some se qualquer fonte dela venceu.
2. **O que fica.** A declaração da equipe (estágio declarado, estágio do COP) é registro humano e continua. A tela
   **Fontes** também lista só as fontes atualizadas (pedido do dono em 28/11/2026, para passar confiança ao cliente):
   atrasadas, com falha, nunca carregadas e planejadas não aparecem. O botão de buscar dados continua tentando todas.
   O que falta fica no log do agendamento e em `GET /fontes`. Só conta como vencido `desatualizado === true`. Quando não há como saber (`null`), continua valendo
   "Dados insuficientes" (RN-01).
3. **Um agendador só, cada fonte na sua cadência.** `python -m climasense.etl operacional` roda a cada 15 min e passa
   por todas as fontes implementadas. Só baixa as que passaram da cadência (`INTERVALOS_OPERACIONAIS_MIN` em
   `etl/orquestrador.py`), em cinco faixas: tempo real (15 a 60 min), previsão (3 a 12 h), diária, semanal e mensal.
   A cadência é no máximo metade do limite de frescor, garantido por teste, para que uma rodada perdida não deixe a
   fonte vencida. Uma fonte que falhou tenta de novo no máximo a cada hora. Os modos secundários (`apac-chuva
   historico`, `open-meteo-solo historico`) e a conferência da gold rodam uma vez por dia, às 06h UTC.
4. **Onde roda.** Tarefa do Windows `ClimaSense-ETL-Operacional` (`scripts/preparar-agendamento.ps1`), com log em
   `logs/`. Para rodar com o PC desligado, o workflow `.github/workflows/etl-operacional.yml` faz a mesma rodada, e
   fica desligado até o dono cadastrar os secrets. Os dois podem rodar juntos: a trava no banco e a cadência por fonte
   evitam carga em dobro.

## Consequências

- RF-19 e RNF-05 mudam de "aviso de desatualizado" para "dado vencido não aparece". RF-42 continua na tela Fontes.
- Uma fonte parada faz a informação sumir das telas de decisão. Quem acompanha a operação precisa olhar o log do
  agendamento (`logs/`) e `GET /fontes`, já que nenhuma tela mostra fonte parada.
- A previsão a cada 3 h grava cerca de 17 mil linhas por dia em `silver.observacoes` e mais documentos na bronze, que
  é acumulativa. Medir o crescimento no Neon e no Atlas gratuitos e definir arquivamento antes de passar de 70% da
  cota. A saída não é afrouxar limites.
- A tarefa do Windows só roda com a máquina ligada e o usuário conectado. A disponibilidade contínua depende do
  workflow do GitHub ou de hospedagem (ADR 0013).
- A trava do ETL passa a ser por fonte, não por banco: uma base anual pesada não segura a chuva, os alertas nem o botão
  da tela Fontes. Esbarrar na trava não conta como falha e não adia a próxima tentativa.
- A coordenação (gestor) ganha `executar_etl`: o botão "Buscar dados mais recentes" da tela Fontes dispara a coleta das
  fontes que não estão em dia e das que vencem em até 6 h (chuva, rios, alertas, previsão). Fonte já em coleta é pulada.
