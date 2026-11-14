# Consolidação acadêmica do ClimaSense

Entrega na branch `feat/ml-academico-consolidacao`, criada a partir de
`feat/ml-impacto-territorial`, HEAD inicial `954c69c`. Havia alterações locais
em backend, frontend, ETL, ML, documentação e scripts, além de arquivos novos.
Esse trabalho pertinente foi revisado e incorporado, sem reset ou descarte.

## Inventário e decisões

| Material local examinado | Decisão |
|---|---|
| `climasense_mapa_ml.patch` | Integração já presente: classes, legenda e fatores de ML no Simulador; consolidada sem reaplicar |
| `climasense_previa_ml_e_pesquisa.patch` | Prévia protegida e comparação de distrito já presentes; consolidadas, com testes HTTP e demonstração automática configurável |
| `climasense_sgb_inundacao.patch` | Cruzamento espacial e comparação já presentes; preservados como pesquisa independente |
| `climasense_chuva_intensa.patch` | Picos 1/3/6 h e comparação já presentes; preservados com seus testes e resultados |
| Demonstração automática | Nenhum patch específico adicional encontrado; completada sobre a prévia existente, sem duplicar rota ou modelo |
| `tmp/postgres/postgresql.zip` | Distribuição PostgreSQL/pgAdmin (21.979 entradas); sem patch do ClimaSense; permanece ignorada |
| `tmp/postgres/pgsql/pgAdmin 4/python/python313.zip` | Biblioteca Python compilada do pgAdmin (541 entradas); sem código de entrega; permanece ignorada |

Todos os destinos dos quatro patches já existiam. A inspeção dos módulos e das
alterações confirmou sua integração; verificações reversas não se aplicam
integralmente porque o código evoluiu e foi formatado. Não foram aplicados patches
ou extraídos ZIPs sobre a árvore atual. Os pacotes de dependências locais não
substituem o código do repositório. Patches redundantes e o script pontual
`recuperar_etl_seguro_corrigido.py` foram preservados localmente e ignorados no Git.

O modelo local `0.2.0` foi carregado somente para conferir compatibilidade,
metadados e métricas. Continua `publicavel=false`, com o mesmo SHA-256:
`f5218a20109654c5a8d944d7569b368f51e72da45db384a1ed59a0d0f1536f1b`.
Nenhum treinamento real, ETL, migração, agendamento, push ou merge foi executado.
A migração incremental `0025` e os comandos de persistência existentes fazem
parte do código consolidado; sua execução em banco não foi validada nesta tarefa.

## Correções e preservações

- Preservadas a análise por distrito, a simulação manual e a separação entre
  regras, suscetibilidade física e classes de ML. Modelo reprovado não modifica
  regras, estágio oficial ou persistência operacional.
- Demonstração automática optativa pelo Vite em desenvolvimento; exige sessão
  administrativa e backend de desenvolvimento. Backend exige adicionalmente
  `ML_PREVIA_EXPERIMENTAL_LOCAL=true`. Produção, falta de flag e falta de permissão
  têm testes de bloqueio. O mapa informa uso não operacional.
  Falha ao renovar a prévia remove as classes antigas do mapa, mesmo havendo cache.
- Valores horários negativos, infinitos, nulos ou inválidos não podem ser
  mascarados pela soma diária de chuva no estudo ou na inferência.
- Resposta SGB fora do formato esperado gera erro controlado, sem tentar
  acessar `.get()` em lista/nulo ou reproduzir mensagens arbitrárias do provedor.
- Corrigida compatibilidade de leitura sem tradução de CRLF no Python 3.12 em
  `gravar_no_env`; os testes usam apenas arquivos temporários, sem tocar `.env` real.
- Corrigidos isolamento da dependência de sessão no teste de validação HTTP e
  separação de cabeçalho CSV independente de LF/CRLF. As expectativas originais
  foram mantidas; imports e formatação foram normalizados.
- Contrato OpenAPI exportado com todas as funcionalidades opcionais, sem depender
  das flags locais; geração de tipos usa o JSON versionado. Isso não liga flags
  no servidor real. Teste confere contrato e exportador com flags locais desligadas.
- Relatório 0.1.0 identificado como histórico. Estudo vigente e README documentam
  métricas, amostras, limitações e reprodução. Pequenos JSON científicos foram
  preservados em `docs/ml/resultados/`, sem incluir joblib ou dados temporários.

As melhorias locais já existentes de ETL foram mantidas: cobertura horária,
tratamento de falhas, controle de concorrência, retentativas limitadas para GET,
sanitização de atendimentos e acompanhamento sequencial das fontes na interface.
Seu funcionamento com banco real depende da validação de integração separada.

## Validação desta consolidação

| Verificação | Resultado |
|---|---|
| Backend isolado, incluindo ML e contrato HTTP da prévia | 1.155 testes passaram; 216 testes Atlas/integração excluídos explicitamente |
| Frontend Vitest | 258 testes passaram em 29 arquivos |
| Ruff lint e format no backend | Aprovados |
| ESLint e Prettier do frontend | Aprovados |
| TypeScript e build Vite | Aprovados, inclusive no servidor do Playwright |
| OpenAPI e tipos | Contrato verificado e tipos regenerados offline |
| Documentação e evidências | Links locais, cinco CLIs (`--help`), igualdade dos relatórios JSON e hash do artefato verificados |
| Playwright desktop/celular | 4 testes passaram: cenário territorial e reprodução de captura local dos oito distritos, com verificações de acessibilidade |
| `git diff --check` | Sem erros |

Comandos a partir da raiz:

```powershell
.\.venv\Scripts\python.exe scripts/testar_backend_local.py -q -m "not atlas and not integracao"
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
.\.venv\Scripts\python.exe scripts/exportar_openapi.py --verificar
cd frontend
npm run gerar-tipos
npm test
npm run lint
npm run build
npm run e2e -- --grep "previsão por distrito preserva|apresenta previsão real dos oito"
cd ..
git diff --check
```

O segundo teste de navegador usa `tmp/operacao-local.json` preexistente e é
ignorado se essa captura não existir. Nesta consolidação ela foi apenas lida;
o roteiro que a produz não foi executado. O navegador recebe respostas interceptadas,
sem conexão aos bancos; o teste HTTP da prévia usa autenticação/sessão simuladas
e exerce a dependência real de permissão. Isso não é validação ponta a ponta
com dados vivos nem comprova qualidade do modelo.

O ambiente restrito inicialmente impediu o acesso do Python/esbuild a componentes
instalados fora da pasta. As execuções autorizadas com esse acesso passaram.
Permanecem avisos das bibliotecas (Canvas no jsdom, React Router, adaptador
TestClient/httpx e Node) e aviso de chunks grandes do Vite; não impediram testes
ou build. Não foram adicionadas dependências para silenciar avisos.

Para não gravar em bancos, não foram executados os testes de integração PostgreSQL,
Atlas, migrações, cargas ETL ou persistência real. Também não foram repetidos
treinamentos completos ou consultas a provedores para recalcular métricas. A
conclusão científica permanece: experimentos sem melhoria relevante, 2024
exploratório e necessidade de validação temporal independente antes de operação.
