# Prévia local NÃO VALIDADA e pesquisa de atributos territoriais

A prévia é uma ferramenta **de demonstração acadêmica no ambiente local**. NÃO é
uma funcionalidade operacional, nem altera o estágio COP ou o resultado por regras.
As métricas atuais do modelo ficam abaixo da referência de chuva simples.

## Preparação (Windows, PowerShell, raiz do repositório)

1. Verificar que `.env` contém `AMBIENTE=desenvolvimento` e adicionar
   `ML_PREVIA_EXPERIMENTAL_LOCAL=true` **somente no computador de desenvolvimento**.
   Em produção, a rota sempre devolve 404. Somente usuários com permissão
   `administrar` podem consultá-la.
2. Executar uma vez, sem gravar dados nos bancos:

   ```powershell
   cd backend
   ..\.venv\Scripts\python.exe -m climasense.ml alagamento-previa-local
   cd ..
   ```

   O comando utiliza dados históricos reais e pode levar algum tempo (mas **somente
   uma configuração fixa e até cinco folds**, sem diagnósticos adicionais). Ele salva
   o `.joblib` local em `tmp/modelos/`; não altera o status `publicavel=false`,
   não reescreve os relatórios científicos e não grava em Neon/Atlas.
3. Para abrir automaticamente, copiar `frontend/.env.example` para
   `frontend/.env.local` e definir `VITE_ML_DEMO_ACADEMICA=true`.
   Reiniciar `dev.ps1`, autenticar-se como administrador e abrir **Simulador**.
   Com a chave desligada, abrir **Previsão por distrito** e clicar em
   **Ver prévia de pesquisa do ML**. Em ambos os casos a camada informa uso não validado.
   Na visualização **ML de alagamento**, aparecem classes apenas se existir
   chuva horária completa (sete dias) por distrito, artefato compatível e
   outros insumos requeridos. Ausência de dado fica hachurada, não baixo risco.

O contrato normal `/api/v1/cenarios/impacto-previsto` permanece bloqueado para
modelos não publicáveis. A prévia é consumida separadamente de
`/api/v1/risco-alagamento/previa-local`. Não persistir o resultado da prévia
na Gold operacional ou apresentar como alerta oficial.

## Comparar informação territorial conhecida antes de 2024

```powershell
cd backend
..\.venv\Scripts\python.exe -m climasense.ml.alagamento.comparar_territorio
```

O resultado fica em `tmp/experimentos/comparacao-territorial.json`. A pesquisa
compara a mesma árvore de decisão, hiperparâmetros fixos, cinco folds temporais
e mesmo teste de 2024 usando (a) seis atributos originais, (b) os seis mais
`distrito_id` codificado como categoria. Não incorpora a variável ao produto
nem treina uma árvore durante requisições. Só se considerará uma variável de
suscetibilidade física após verificar fonte, data de referência anterior ao
teste, cobertura e justificativa para **alagamento** (não confundir com carta
de *deslizamento* SGB). Uma melhoria num único holdout de 2024 não basta
para alegar desempenho operacional: será necessário outro período independente.

**Segurança:** não colocar `.env` ou arquivos `.joblib` no Git; não usar flags
em produção; não alterar o gate de publicação ou as regras existentes.

## Resultado preservado

O [relatório existente](resultados/comparacao-territorial.json) registra
treino de 01/01/2014 a 28/12/2023 e teste de 01/01 a 28/12/2024.
AUC-PR original **0,045971**, com distrito **0,045255**; AUC-PR fora da
amostra da variante territorial **0,048270**. Ambas tiveram recall 80,06%,
precisão 3,38% e 7.696 falsos positivos. A referência simples alcançou
**0,049624**. A categoria administrativa não trouxe melhoria relevante.
O teste de 2024 já consultado é exploratório, não uma nova validação independente.
