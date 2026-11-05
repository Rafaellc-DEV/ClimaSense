# Mapa interno da API de gestão

> Gerado por `scripts/gerar_mapa_api.py` a partir do OpenAPI da aplicação. Não edite à mão: rode o script.
> Versão da API: 0.1.0. Prefixo: `/api/v1`. Cookies `cs_sessao` e `cs_csrf`; métodos que alteram dados exigem o cabeçalho `X-CSRF-Token`.

Convenções: o envelope `{dados, meta}` traz fontes, recorte, cobertura, amostra, avisos e `dados_insuficientes` (RN-01: sem dado nunca vira zero). Erros seguem `application/problem+json` com `title` e `detail` prontos para a tela. Datas em UTC (ISO 8601). `*` marca parâmetro obrigatório.

## Resumo

| Método | Caminho | Papel mínimo | Telas que usam | Resposta |
|---|---|---|---|---|
| GET | `/api/v1/health` | público | (nenhuma ainda) | objeto direto |
| POST | `/api/v1/auth/entrar` | público | lib | objeto direto |
| POST | `/api/v1/auth/sair` | qualquer conta autenticada | lib | sem corpo |
| GET | `/api/v1/auth/eu` | qualquer conta autenticada | lib | objeto direto |
| POST | `/api/v1/auth/renovar` | qualquer conta autenticada | lib | objeto direto |
| POST | `/api/v1/auth/trocar-senha` | qualquer conta autenticada | features/entrar | sem corpo |
| GET | `/api/v1/admin/usuarios/papeis` | administrador | features/admin | lista direta |
| GET | `/api/v1/admin/usuarios` | administrador | features/admin | lista direta |
| POST | `/api/v1/admin/usuarios` | administrador | features/admin | objeto direto |
| PATCH | `/api/v1/admin/usuarios/{usuario_id}` | administrador | features/admin | objeto direto |
| POST | `/api/v1/admin/usuarios/{usuario_id}/redefinir-senha` | administrador | features/admin | objeto direto |
| GET | `/api/v1/territorios` | analista | app, features/evento | lista direta |
| GET | `/api/v1/territorios/distritos.geojson` | analista | features/territorio | objeto direto |
| GET | `/api/v1/territorios/hidrografia.geojson` | analista | features/territorio | objeto direto |
| GET | `/api/v1/territorios/indicadores` | analista | features/territorio | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/prioridades` | analista | features/cenarios, features/painel, features/territorio | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/mapa-portatil` | analista | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/publico/territorios/busca` | público | features/landing | lista direta |
| GET | `/api/v1/publico/estado` | público | features/landing | objeto direto |
| GET | `/api/v1/publico/avisos` | público | features/landing | lista direta |
| GET | `/api/v1/publico/avisos/{aviso_id}` | público | features/landing | objeto direto |
| GET | `/api/v1/publico/fontes` | público | features/landing | lista direta |
| GET | `/api/v1/publico/abrigos` | público | features/landing | objeto direto |
| GET | `/api/v1/fontes` | analista | features/fontes | lista direta |
| GET | `/api/v1/fontes/{fonte_id}` | analista | features/fontes | objeto direto |
| GET | `/api/v1/fontes/{fonte_id}/execucoes` | analista | features/fontes | lista direta |
| POST | `/api/v1/etl/execucoes` | administrador | features/fontes | sem corpo |
| GET | `/api/v1/etl/execucoes/{execucao_id}` | administrador | features/fontes | objeto direto |
| GET | `/api/v1/series` | analista | features/series | envelope `{dados, meta}` |
| GET | `/api/v1/series/referencia` | analista | features/series | envelope `{dados, meta}` |
| GET | `/api/v1/series/sazonalidade` | analista | features/series | envelope `{dados, meta}` |
| GET | `/api/v1/series/estatisticas` | analista | features/series | envelope `{dados, meta}` |
| GET | `/api/v1/cenarios` | analista | features/cenarios | envelope `{dados, meta}` |
| GET | `/api/v1/avaliacoes` | analista | features/avaliacoes | objeto direto |
| POST | `/api/v1/avaliacoes` | analista | features/avaliacoes | objeto direto |
| GET | `/api/v1/avaliacoes/{avaliacao_id}` | analista | features/avaliacoes | objeto direto |
| PUT | `/api/v1/avaliacoes/{avaliacao_id}` | analista | features/avaliacoes | objeto direto |
| POST | `/api/v1/avaliacoes/{avaliacao_id}/enviar` | analista | features/fluxo | objeto direto |
| POST | `/api/v1/avaliacoes/{avaliacao_id}/aprovar` | revisor | features/fluxo | objeto direto |
| POST | `/api/v1/avaliacoes/{avaliacao_id}/devolver` | revisor | features/fluxo | objeto direto |
| POST | `/api/v1/avaliacoes/{avaliacao_id}/encerrar` | coordenação | features/fluxo | objeto direto |
| GET | `/api/v1/comunicados` | analista | features/comunicados | objeto direto |
| POST | `/api/v1/comunicados` | analista | features/comunicados | objeto direto |
| GET | `/api/v1/comunicados/{comunicado_id}` | analista | features/comunicados | objeto direto |
| PUT | `/api/v1/comunicados/{comunicado_id}` | analista | features/comunicados | objeto direto |
| GET | `/api/v1/comunicados/{comunicado_id}/previa` | analista | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/comunicados/{comunicado_id}/versoes` | analista | (nenhuma ainda) | lista direta |
| GET | `/api/v1/comunicados/{comunicado_id}/versoes/{a}/diferenca/{b}` | analista | features/comunicados | objeto direto |
| POST | `/api/v1/comunicados/{comunicado_id}/enviar` | analista | features/fluxo | objeto direto |
| POST | `/api/v1/comunicados/{comunicado_id}/aprovar` | revisor | features/fluxo | objeto direto |
| POST | `/api/v1/comunicados/{comunicado_id}/devolver` | revisor | features/fluxo | objeto direto |
| POST | `/api/v1/comunicados/{comunicado_id}/publicar` | coordenação | features/fluxo | objeto direto |
| POST | `/api/v1/comunicados/{comunicado_id}/encerrar` | coordenação | features/fluxo | objeto direto |
| GET | `/api/v1/painel/resumo` | analista | app, features/avaliacoes, features/comunicados, features/painel | objeto direto |
| GET | `/api/v1/painel/situacao` | analista | features/boletim, features/painel | envelope `{dados, meta}` |
| GET | `/api/v1/painel/acoes` | analista | features/painel | objeto direto |
| GET | `/api/v1/admin/auditoria` | administrador | features/admin | objeto direto |
| GET | `/api/v1/admin/etl/execucoes` | administrador | features/admin | lista direta |
| PATCH | `/api/v1/admin/fontes/{fonte_id}` | administrador | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/estagios` | analista | features/boletim, features/estagios, features/painel, features/territorio | envelope `{dados, meta}` |
| POST | `/api/v1/estagios` | analista | features/boletim, features/estagios, features/painel, features/territorio | lista direta |
| GET | `/api/v1/estagios/historico` | analista | features/estagios | lista direta |
| GET | `/api/v1/estagios/parametros` | analista | features/estagios, features/evento | objeto direto |
| PUT | `/api/v1/estagios/parametros` | coordenação | features/estagios, features/evento | objeto direto |
| GET | `/api/v1/estagios/parametros/historico` | analista | (nenhuma ainda) | lista direta |
| POST | `/api/v1/estagios/mensagem` | analista | features/estagios, features/painel | objeto direto |
| POST | `/api/v1/estagios/mensagem/uso` | analista | features/evento | sem corpo |
| GET | `/api/v1/abrigos` | analista | features/abrigos, features/boletim, features/painel | objeto direto |
| POST | `/api/v1/abrigos` | analista | features/abrigos, features/boletim, features/painel | objeto direto |
| GET | `/api/v1/abrigos/{abrigo_id}` | analista | features/abrigos | objeto direto |
| PATCH | `/api/v1/abrigos/{abrigo_id}` | analista | features/abrigos | objeto direto |
| GET | `/api/v1/abrigos/{abrigo_id}/historico` | analista | features/abrigos | lista direta |
| GET | `/api/v1/acoes` | analista | features/acoes, features/boletim, features/painel | objeto direto |
| POST | `/api/v1/acoes` | analista | features/acoes, features/boletim, features/painel | objeto direto |
| GET | `/api/v1/acoes/{acao_id}` | analista | features/acoes | objeto direto |
| PATCH | `/api/v1/acoes/{acao_id}` | analista | features/acoes | objeto direto |
| GET | `/api/v1/boletim` | analista | features/abrigos, features/acoes, features/estagios | envelope `{dados, meta}` |
| GET | `/api/v1/boletim/texto` | analista | features/boletim | objeto direto |
| GET | `/api/v1/risco-alagamento` | analista | (nenhuma ainda) | envelope `{dados, meta}` |

## Detalhe por grupo

### Saúde do sistema

#### `GET /api/v1/health`

- **Resumo:** Estado da API e dos bancos
- **Papel mínimo:** público
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "status": "ok",
    "versao": "texto",
    "ambiente": "texto",
    "bancos": {}
  }
  ```

### Autenticação

#### `POST /api/v1/auth/entrar`

- **Resumo:** Entrar com e-mail e senha
- **Papel mínimo:** público
- **Telas que usam:** lib
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "email": "texto",
    "papeis": [
      "texto"
    ],
    "permissoes": [
      "texto"
    ],
    "troca_senha_obrigatoria": true,
    "expira_em": "2026-10-15T20:00:00Z",
    "ambiente": "texto",
    "inatividade_min": 0,
    "mapa_tiles_url": "texto"
  }
  ```

#### `POST /api/v1/auth/sair`

- **Resumo:** Sair
- **Papel mínimo:** qualquer conta autenticada
- **Telas que usam:** lib
- **Resposta:** sem corpo

#### `GET /api/v1/auth/eu`

- **Resumo:** Conta atual e expiração da sessão
- **Papel mínimo:** qualquer conta autenticada
- **Telas que usam:** lib
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "email": "texto",
    "papeis": [
      "texto"
    ],
    "permissoes": [
      "texto"
    ],
    "troca_senha_obrigatoria": true,
    "expira_em": "2026-10-15T20:00:00Z",
    "ambiente": "texto",
    "inatividade_min": 0,
    "mapa_tiles_url": "texto"
  }
  ```

#### `POST /api/v1/auth/renovar`

- **Resumo:** Continuar conectado
- **Papel mínimo:** qualquer conta autenticada
- **Telas que usam:** lib
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "email": "texto",
    "papeis": [
      "texto"
    ],
    "permissoes": [
      "texto"
    ],
    "troca_senha_obrigatoria": true,
    "expira_em": "2026-10-15T20:00:00Z",
    "ambiente": "texto",
    "inatividade_min": 0,
    "mapa_tiles_url": "texto"
  }
  ```

#### `POST /api/v1/auth/trocar-senha`

- **Resumo:** Trocar a senha
- **Papel mínimo:** qualquer conta autenticada
- **Telas que usam:** features/entrar
- **Resposta:** sem corpo

### Administração

#### `GET /api/v1/admin/usuarios/papeis`

- **Resumo:** Papéis disponíveis, em linguagem simples
- **Papel mínimo:** administrador
- **Telas que usam:** features/admin
- **Resposta:** lista direta
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "papel": "texto",
      "descricao": "texto"
    }
  ]
  ```

#### `GET /api/v1/admin/usuarios`

- **Resumo:** Listar contas
- **Papel mínimo:** administrador
- **Telas que usam:** features/admin
- **Resposta:** lista direta
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "nome": "texto",
      "email": "texto",
      "papeis": [
        "texto"
      ],
      "ativo": true,
      "troca_senha_obrigatoria": true,
      "criado_em": "2026-10-15T20:00:00Z"
    }
  ]
  ```

#### `POST /api/v1/admin/usuarios`

- **Resumo:** Criar conta com senha temporária
- **Papel mínimo:** administrador
- **Telas que usam:** features/admin
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "conta": {
      "id": "00000000-0000-0000-0000-000000000000",
      "nome": "texto",
      "email": "texto",
      "papeis": [
        "texto"
      ],
      "ativo": true,
      "troca_senha_obrigatoria": true,
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "senha_temporaria": "texto"
  }
  ```

#### `PATCH /api/v1/admin/usuarios/{usuario_id}`

- **Resumo:** Alterar nome, papéis ou ativar/desativar
- **Papel mínimo:** administrador
- **Telas que usam:** features/admin
- **Resposta:** objeto direto
- **Parâmetros:** `usuario_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "email": "texto",
    "papeis": [
      "texto"
    ],
    "ativo": true,
    "troca_senha_obrigatoria": true,
    "criado_em": "2026-10-15T20:00:00Z"
  }
  ```

#### `POST /api/v1/admin/usuarios/{usuario_id}/redefinir-senha`

- **Resumo:** Redefinir a senha (gera senha temporária)
- **Papel mínimo:** administrador
- **Telas que usam:** features/admin
- **Resposta:** objeto direto
- **Parâmetros:** `usuario_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "senha_temporaria": "texto"
  }
  ```

#### `GET /api/v1/admin/auditoria`

- **Resumo:** Consultar a auditoria (somente leitura)
- **Papel mínimo:** administrador
- **Telas que usam:** features/admin
- **Resposta:** objeto direto
- **Parâmetros:** `usuario_id`, `acao`, `inicio`, `fim`, `pagina`, `por_pagina`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": 0,
        "em": "2026-10-15T20:00:00Z",
        "usuario_id": "00000000-0000-0000-0000-000000000000",
        "usuario_nome": "texto",
        "acao": "texto",
        "alvo_tipo": "texto",
        "alvo_id": "texto",
        "detalhes": {}
      }
    ],
    "acoes": [
      "texto"
    ],
    "pagina": 0,
    "por_pagina": 0
  }
  ```

#### `GET /api/v1/admin/etl/execucoes`

- **Resumo:** Últimas execuções do ETL, de todas as fontes
- **Papel mínimo:** administrador
- **Telas que usam:** features/admin
- **Resposta:** lista direta
- **Parâmetros:** `fonte_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "fonte_id": "texto",
      "fonte_nome": "texto",
      "inicio": "2026-10-15T20:00:00Z",
      "fim": "2026-10-15T20:00:00Z",
      "status": "texto",
      "lidos": 0,
      "gravados": 0,
      "descartados": 0,
      "motivos_descarte": {},
      "erro": "texto",
      "disparado_por_nome": "texto"
    }
  ]
  ```

#### `PATCH /api/v1/admin/fontes/{fonte_id}`

- **Resumo:** Ajustar limites de uma fonte
- **Papel mínimo:** administrador
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Parâmetros:** `fonte_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "texto",
    "limite_desatualizacao_h": 0,
    "min_observacoes": 0
  }
  ```

### Território

#### `GET /api/v1/territorios`

- **Resumo:** Recife, distritos e bairros
- **Papel mínimo:** analista
- **Telas que usam:** app, features/evento
- **Resposta:** lista direta
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "texto",
      "tipo": "texto",
      "nome_exibicao": "texto",
      "pai_id": "texto"
    }
  ]
  ```

#### `GET /api/v1/territorios/distritos.geojson`

- **Resumo:** Os 8 distritos sanitários (GeoJSON)
- **Papel mínimo:** analista
- **Telas que usam:** features/territorio
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  null
  ```

#### `GET /api/v1/territorios/hidrografia.geojson`

- **Resumo:** Faixas marginais dos recursos hídricos (geometria simplificada)
- **Papel mínimo:** analista
- **Telas que usam:** features/territorio
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  null
  ```

#### `GET /api/v1/territorios/indicadores`

- **Resumo:** Valor por distrito para colorir o mapa
- **Papel mínimo:** analista
- **Telas que usam:** features/territorio
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `indicador*`, `inicio`, `fim`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": [
      {
        "territorio_id": "texto",
        "valor": 0.0
      }
    ],
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amostra": {
        "n": 0,
        "total_fonte": 0
      },
      "avisos": [
        "texto"
      ],
      "dados_insuficientes": true
    }
  }
  ```

#### `GET /api/v1/territorios/prioridades`

- **Resumo:** Quais territórios pedem atenção primeiro, por quê e com que confiança
- **Papel mínimo:** analista
- **Telas que usam:** features/cenarios, features/painel, features/territorio
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `nivel`, `horizonte_h`, `distrito_id`, `limite`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "nivel_territorial": "distrito",
      "horizonte_h": 0,
      "gerado_em": "2026-10-15T20:00:00Z",
      "total": 0,
      "resumo": "texto",
      "itens": [
        {
          "posicao": 0,
          "territorio_id": "texto",
          "territorio_nome": "texto",
          "tipo": "distrito",
          "distrito_id": "texto",
          "nivel": "sem_indicacao",
          "rotulo": "texto",
          "nivel_estimador": "sem_indicacao",
          "nivel_equipe": "texto",
          "experimental": true,
          "confianca": "media",
          "motivos": [
            {}
          ],
          "notas_qualidade": [
            "texto"
          ],
          "evidencias": [
            {}
          ],
          "janela_atencao": {
            "inicio": "2026-10-15T20:00:00Z",
            "fim": "2026-10-15T20:00:00Z"
          },
          "acumulado_previsto_mm": 0.0,
          "limite_atencao_mm": 0.0,
          "limite_alerta_mm": 0.0,
          "ocorrencias_historicas": 0
        }
      ]
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amostra": {
        "n": 0,
        "total_fonte": 0
     
    ...(cortado)
  ```

#### `GET /api/v1/territorios/mapa-portatil`

- **Resumo:** Baixar o mapa portátil (HTML offline, porte da Aula 07)
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  null
  ```

### Público

#### `GET /api/v1/publico/territorios/busca`

- **Resumo:** Busca de bairro sem diferenciar acentos
- **Papel mínimo:** público
- **Telas que usam:** features/landing
- **Resposta:** lista direta
- **Parâmetros:** `q*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "texto",
      "nome": "texto",
      "distrito_id": "texto"
    }
  ]
  ```

#### `GET /api/v1/publico/estado`

- **Resumo:** Estado dos avisos para o topo da página inicial
- **Papel mínimo:** público
- **Telas que usam:** features/landing
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "avisos_ativos": 0,
    "distritos_afetados": [
      "texto"
    ],
    "niveis_por_distrito": {},
    "nivel_mais_alto": "texto",
    "principal": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "atualizado_em": "2026-10-15T20:00:00Z"
  }
  ```

#### `GET /api/v1/publico/avisos`

- **Resumo:** Avisos publicados e vigentes, do nível mais alto
- **Papel mínimo:** público
- **Telas que usam:** features/landing
- **Resposta:** lista direta
- **Parâmetros:** `bairro`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    }
  ]
  ```

#### `GET /api/v1/publico/avisos/{aviso_id}`

- **Resumo:** Detalhe de um aviso publicado
- **Papel mínimo:** público
- **Telas que usam:** features/landing
- **Resposta:** objeto direto
- **Parâmetros:** `aviso_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "titulo": "texto",
    "nivel": "texto",
    "territorios": [
      {
        "id": "texto",
        "tipo": "texto",
        "nome_exibicao": "texto"
      }
    ],
    "texto": "texto",
    "orientacoes": [
      "texto"
    ],
    "validade_inicio": "2026-10-15T20:00:00Z",
    "validade_fim": "2026-10-15T20:00:00Z",
    "emitido_por": "texto",
    "publicado_em": "2026-10-15T20:00:00Z",
    "publico": "texto"
  }
  ```

#### `GET /api/v1/publico/fontes`

- **Resumo:** De onde vêm os dados (status das fontes)
- **Papel mínimo:** público
- **Telas que usam:** features/landing
- **Resposta:** lista direta
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "texto",
      "nome": "texto",
      "orgao": "texto",
      "tipo": "texto",
      "status": "texto",
      "ultima_atualizacao": "2026-10-15T20:00:00Z"
    }
  ]
  ```

#### `GET /api/v1/publico/abrigos`

- **Resumo:** Abrigos e pontos de apoio (sem dados pessoais nem ocupação detalhada)
- **Papel mínimo:** público
- **Telas que usam:** features/landing
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "nome": "texto",
        "endereco": "texto",
        "bairro_nome": "texto",
        "distrito_nome": "texto",
        "latitude": 0.0,
        "longitude": 0.0,
        "aberto": true,
        "aberto_fonte": "cop",
        "aberto_lido_em": "2026-10-15T20:00:00Z",
        "atualizado_em": "2026-10-15T20:00:00Z",
        "origem": "texto",
        "fonte_url": "texto",
        "tipo": "texto",
        "capacidade": 0
      }
    ],
    "atualizado_em": "2026-10-15T20:00:00Z",
    "aviso": "texto"
  }
  ```

### Fontes de dados

#### `GET /api/v1/fontes`

- **Resumo:** Fontes com status (atualizada, desatualizada, com falha, planejada)
- **Papel mínimo:** analista
- **Telas que usam:** features/fontes
- **Resposta:** lista direta
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "texto",
      "nome": "texto",
      "orgao": "texto",
      "url": "texto",
      "tipo": "texto",
      "licenca": "texto",
      "status": "texto",
      "ultima_atualizacao": "2026-10-15T20:00:00Z",
      "limite_desatualizacao_h": 0
    }
  ]
  ```

#### `GET /api/v1/fontes/{fonte_id}`

- **Resumo:** Detalhe de uma fonte
- **Papel mínimo:** analista
- **Telas que usam:** features/fontes
- **Resposta:** objeto direto
- **Parâmetros:** `fonte_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "texto",
    "nome": "texto",
    "orgao": "texto",
    "url": "texto",
    "tipo": "texto",
    "licenca": "texto",
    "status": "texto",
    "ultima_atualizacao": "2026-10-15T20:00:00Z",
    "limite_desatualizacao_h": 0
  }
  ```

#### `GET /api/v1/fontes/{fonte_id}/execucoes`

- **Resumo:** Histórico de execuções do ETL
- **Papel mínimo:** analista
- **Telas que usam:** features/fontes
- **Resposta:** lista direta
- **Parâmetros:** `fonte_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "fonte_id": "texto",
      "inicio": "2026-10-15T20:00:00Z",
      "fim": "2026-10-15T20:00:00Z",
      "status": "texto",
      "lidos": 0,
      "gravados": 0,
      "descartados": 0,
      "motivos_descarte": {},
      "erro": "texto"
    }
  ]
  ```

#### `POST /api/v1/etl/execucoes`

- **Resumo:** Atualizar uma fonte agora (administrador)
- **Papel mínimo:** administrador
- **Telas que usam:** features/fontes
- **Resposta:** sem corpo

#### `GET /api/v1/etl/execucoes/{execucao_id}`

- **Resumo:** Status de uma execução
- **Papel mínimo:** administrador
- **Telas que usam:** features/fontes
- **Resposta:** objeto direto
- **Parâmetros:** `execucao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "fonte_id": "texto",
    "inicio": "2026-10-15T20:00:00Z",
    "fim": "2026-10-15T20:00:00Z",
    "status": "texto",
    "lidos": 0,
    "gravados": 0,
    "descartados": 0,
    "motivos_descarte": {},
    "erro": "texto"
  }
  ```

### Séries e sazonalidade

#### `GET /api/v1/series`

- **Resumo:** Série temporal com lacunas explícitas
- **Papel mínimo:** analista
- **Telas que usam:** features/series
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `variavel`, `territorio_id`, `inicio`, `fim`, `frequencia`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "variavel": "texto",
      "unidade": "texto",
      "frequencia": "texto",
      "territorio_id": "texto",
      "territorio_nome": "texto",
      "pontos": [
        {
          "t": "2026-10-15",
          "valor": 0.0,
          "dias": 0,
          "dias_com_dado": 0
        }
      ],
      "referencia": [
        0.0
      ],
      "resumo": "texto",
      "lacunas_dias": 0
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amostra": {
        "n": 0,
        "total_fonte": 0
      },
      "avisos": [
        "texto"
      ],
      "dados_insuficientes": true
    }
  }
  ```

#### `GET /api/v1/series/referencia`

- **Resumo:** Referência histórica por mês
- **Papel mínimo:** analista
- **Telas que usam:** features/series
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "metodo": "texto",
      "meses": [
        {
          "mes": 0,
          "media_mm": 0.0,
          "mediana_mm": 0.0,
          "anos_usados": [
            0
          ],
          "cobertura_pct": 0.0
        }
      ]
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amostra": {
        "n": 0,
        "total_fonte": 0
      },
      "avisos": [
        "texto"
      ],
      "dados_insuficientes": true
    }
  }
  ```

#### `GET /api/v1/series/sazonalidade`

- **Resumo:** Calendário ano × mês
- **Papel mínimo:** analista
- **Telas que usam:** features/series
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "anos": [
        0
      ],
      "celulas": [
        {
          "ano": 0,
          "mes": 0,
          "valor": 0.0,
          "cobertura_pct": 0.0
        }
      ]
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amostra": {
        "n": 0,
        "total_fonte": 0
      },
      "avisos": [
        "texto"
      ],
      "dados_insuficientes": true
    }
  }
  ```

#### `GET /api/v1/series/estatisticas`

- **Resumo:** Estatística descritiva em texto simples
- **Papel mínimo:** analista
- **Telas que usam:** features/series
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id`, `inicio`, `fim`, `frequencia`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "frequencia": "texto",
      "n": 0,
      "minimo_observacoes": 0,
      "serie_curta": true,
      "medidas": [
        {
          "chave": "texto",
          "nome": "texto",
          "valor": 0.0,
          "texto": "texto",
          "explicacao": "texto"
        }
      ]
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amostra": {
        "n": 0,
        "total_fonte": 0
      },
      "avisos": [
        "texto"
      ],
      "dados_insuficientes": true
    }
  }
  ```

### Cenários de alagamento

#### `GET /api/v1/cenarios`

- **Resumo:** Cenário experimental: previsão, maré e prioridade
- **Papel mínimo:** analista
- **Telas que usam:** features/cenarios
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id`, `horizonte_h`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "territorio_id": "texto",
      "territorio_nome": "texto",
      "horizonte_h": 0,
      "previsao_emitida_em": "2026-10-15T20:00:00Z",
      "mare_emitida_em": "2026-10-15T20:00:00Z",
      "emissoes_na_faixa": 0,
      "chuva": [
        {
          "t": "2026-10-15T20:00:00Z",
          "valor": 0.0,
          "min": 0.0,
          "max": 0.0
        }
      ],
      "mare": [
        {
          "t": "2026-10-15T20:00:00Z",
          "valor": 0.0
        }
      ],
      "estimativa": {
        "experimental": true,
        "metodo": "texto",
        "versao_metodo": "texto",
        "emitida_em": "2026-10-15T20:00:00Z",
        "horizonte_h": 0,
        "prioridade": "sem_indicacao",
        "qualidade": "completa",
        "janela_atencao": {
          "inicio": "2026-10-15T20:00:00Z",
          "fim": "2026-10-15T20:00:00Z"
        },
        "fatores": [
          {
            "nome": "texto",
            "descricao": "texto"
          }
        ],
        "limitacoes": [
          "texto"
        ],
        "acumulado_previsto_mm": 0.0,
        "mare_maxima_m": 0.0,
        "mare_maxima_em": "2026-10-15T20:00:00Z",
        "limite_atencao_mm": 0.0,
        "limite_alerta_mm": 0.0
      },
      "registro_id": 0
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
     
    ...(cortado)
  ```

### Avaliações

#### `GET /api/v1/avaliacoes`

- **Resumo:** Avaliações com filtros e contagem por estado
- **Papel mínimo:** analista
- **Telas que usam:** features/avaliacoes
- **Resposta:** objeto direto
- **Parâmetros:** `estado`, `territorio_id`, `inicio`, `fim`, `pagina`, `por_pagina`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "estado": "texto",
        "territorio_id": "texto",
        "territorio_nome": "texto",
        "periodo_inicio": "2026-10-15",
        "periodo_fim": "2026-10-15",
        "prioridade": "texto",
        "versao_atual": 0,
        "autor_id": "00000000-0000-0000-0000-000000000000",
        "autor_nome": "texto",
        "atualizado_em": "2026-10-15T20:00:00Z"
      }
    ],
    "contagens": {},
    "total": 0
  }
  ```

#### `POST /api/v1/avaliacoes`

- **Resumo:** Registrar avaliação (rascunho)
- **Papel mínimo:** analista
- **Telas que usam:** features/avaliacoes
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "periodo_inicio": "2026-10-15",
    "periodo_fim": "2026-10-15",
    "versao_atual": 0,
    "versao": {
      "numero": 0,
      "prioridade": "texto",
      "justificativa": "texto",
      "limitacoes": "texto",
      "evidencias": [
        {}
      ],
      "autor_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ]
  }
  ```

#### `GET /api/v1/avaliacoes/{avaliacao_id}`

- **Resumo:** Detalhe com versão atual e linha do tempo
- **Papel mínimo:** analista
- **Telas que usam:** features/avaliacoes
- **Resposta:** objeto direto
- **Parâmetros:** `avaliacao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "periodo_inicio": "2026-10-15",
    "periodo_fim": "2026-10-15",
    "versao_atual": 0,
    "versao": {
      "numero": 0,
      "prioridade": "texto",
      "justificativa": "texto",
      "limitacoes": "texto",
      "evidencias": [
        {}
      ],
      "autor_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ]
  }
  ```

#### `PUT /api/v1/avaliacoes/{avaliacao_id}`

- **Resumo:** Salvar nova versão
- **Papel mínimo:** analista
- **Telas que usam:** features/avaliacoes
- **Resposta:** objeto direto
- **Parâmetros:** `avaliacao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "periodo_inicio": "2026-10-15",
    "periodo_fim": "2026-10-15",
    "versao_atual": 0,
    "versao": {
      "numero": 0,
      "prioridade": "texto",
      "justificativa": "texto",
      "limitacoes": "texto",
      "evidencias": [
        {}
      ],
      "autor_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ]
  }
  ```

#### `POST /api/v1/avaliacoes/{avaliacao_id}/enviar`

- **Resumo:** Enviar para revisão
- **Papel mínimo:** analista
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `avaliacao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "periodo_inicio": "2026-10-15",
    "periodo_fim": "2026-10-15",
    "versao_atual": 0,
    "versao": {
      "numero": 0,
      "prioridade": "texto",
      "justificativa": "texto",
      "limitacoes": "texto",
      "evidencias": [
        {}
      ],
      "autor_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ]
  }
  ```

#### `POST /api/v1/avaliacoes/{avaliacao_id}/aprovar`

- **Resumo:** Aprovar a versão atual (revisor diferente do autor)
- **Papel mínimo:** revisor
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `avaliacao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "periodo_inicio": "2026-10-15",
    "periodo_fim": "2026-10-15",
    "versao_atual": 0,
    "versao": {
      "numero": 0,
      "prioridade": "texto",
      "justificativa": "texto",
      "limitacoes": "texto",
      "evidencias": [
        {}
      ],
      "autor_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ]
  }
  ```

#### `POST /api/v1/avaliacoes/{avaliacao_id}/devolver`

- **Resumo:** Devolver com justificativa
- **Papel mínimo:** revisor
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `avaliacao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "periodo_inicio": "2026-10-15",
    "periodo_fim": "2026-10-15",
    "versao_atual": 0,
    "versao": {
      "numero": 0,
      "prioridade": "texto",
      "justificativa": "texto",
      "limitacoes": "texto",
      "evidencias": [
        {}
      ],
      "autor_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ]
  }
  ```

#### `POST /api/v1/avaliacoes/{avaliacao_id}/encerrar`

- **Resumo:** Encerrar (coordenação)
- **Papel mínimo:** coordenação
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `avaliacao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "periodo_inicio": "2026-10-15",
    "periodo_fim": "2026-10-15",
    "versao_atual": 0,
    "versao": {
      "numero": 0,
      "prioridade": "texto",
      "justificativa": "texto",
      "limitacoes": "texto",
      "evidencias": [
        {}
      ],
      "autor_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z"
    },
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ]
  }
  ```

### Comunicados

#### `GET /api/v1/comunicados`

- **Resumo:** Comunicados com filtros e contagem por estado
- **Papel mínimo:** analista
- **Telas que usam:** features/comunicados
- **Resposta:** objeto direto
- **Parâmetros:** `estado`, `territorio_id`, `pagina`, `por_pagina`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "estado": "texto",
        "nivel": "texto",
        "titulo": "texto",
        "territorios": [
          "texto"
        ],
        "validade_inicio": "2026-10-15T20:00:00Z",
        "validade_fim": "2026-10-15T20:00:00Z",
        "versao_atual": 0,
        "autor_id": "00000000-0000-0000-0000-000000000000",
        "autor_nome": "texto",
        "atualizado_em": "2026-10-15T20:00:00Z",
        "publicado_em": "2026-10-15T20:00:00Z"
      }
    ],
    "contagens": {},
    "total": 0
  }
  ```

#### `POST /api/v1/comunicados`

- **Resumo:** Criar rascunho de comunicado
- **Papel mínimo:** analista
- **Telas que usam:** features/comunicados
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

#### `GET /api/v1/comunicados/{comunicado_id}`

- **Resumo:** Detalhe com prévia, versões e ações
- **Papel mínimo:** analista
- **Telas que usam:** features/comunicados
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

#### `PUT /api/v1/comunicados/{comunicado_id}`

- **Resumo:** Salvar nova versão
- **Papel mínimo:** analista
- **Telas que usam:** features/comunicados
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

#### `GET /api/v1/comunicados/{comunicado_id}/previa`

- **Resumo:** A versão atual como a landing mostrará
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "titulo": "texto",
    "nivel": "texto",
    "territorios": [
      {
        "id": "texto",
        "tipo": "texto",
        "nome_exibicao": "texto"
      }
    ],
    "texto": "texto",
    "orientacoes": [
      "texto"
    ],
    "validade_inicio": "2026-10-15T20:00:00Z",
    "validade_fim": "2026-10-15T20:00:00Z",
    "emitido_por": "texto",
    "publicado_em": "2026-10-15T20:00:00Z",
    "publico": "texto"
  }
  ```

#### `GET /api/v1/comunicados/{comunicado_id}/versoes`

- **Resumo:** Histórico de versões
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** lista direta
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "numero": 0,
      "criado_em": "2026-10-15T20:00:00Z",
      "hash_conteudo": "texto",
      "titulo": "texto",
      "autor_nome": "texto"
    }
  ]
  ```

#### `GET /api/v1/comunicados/{comunicado_id}/versoes/{a}/diferenca/{b}`

- **Resumo:** O que mudou entre duas versões
- **Papel mínimo:** analista
- **Telas que usam:** features/comunicados
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`, `a*`, `b*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "de": 0,
    "para": 0,
    "campos": {},
    "alterados": [
      "texto"
    ],
    "metadados": {}
  }
  ```

#### `POST /api/v1/comunicados/{comunicado_id}/enviar`

- **Resumo:** Enviar para revisão
- **Papel mínimo:** analista
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

#### `POST /api/v1/comunicados/{comunicado_id}/aprovar`

- **Resumo:** Aprovar a versão atual (revisor diferente do autor)
- **Papel mínimo:** revisor
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

#### `POST /api/v1/comunicados/{comunicado_id}/devolver`

- **Resumo:** Devolver com justificativa
- **Papel mínimo:** revisor
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

#### `POST /api/v1/comunicados/{comunicado_id}/publicar`

- **Resumo:** Publicar na página inicial (só a versão aprovada)
- **Papel mínimo:** coordenação
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

#### `POST /api/v1/comunicados/{comunicado_id}/encerrar`

- **Resumo:** Encerrar: tira o aviso da página inicial
- **Papel mínimo:** coordenação
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `comunicado_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "estado": "texto",
    "versao_atual": 0,
    "versao_aprovada": 0,
    "publicado_em": "2026-10-15T20:00:00Z",
    "avaliacao_id": "00000000-0000-0000-0000-000000000000",
    "autor_id": "00000000-0000-0000-0000-000000000000",
    "autor_nome": "texto",
    "publico": "texto",
    "territorios": [
      "texto"
    ],
    "evidencias": [
      {}
    ],
    "hash_conteudo": "texto",
    "previa": {
      "id": "00000000-0000-0000-0000-000000000000",
      "titulo": "texto",
      "nivel": "texto",
      "territorios": [
        {
          "id": "texto",
          "tipo": "texto",
          "nome_exibicao": "texto"
        }
      ],
      "texto": "texto",
      "orientacoes": [
        "texto"
      ],
      "validade_inicio": "2026-10-15T20:00:00Z",
      "validade_fim": "2026-10-15T20:00:00Z",
      "emitido_por": "texto",
      "publicado_em": "2026-10-15T20:00:00Z",
      "publico": "texto"
    },
    "versoes": [
      {
        "numero": 0,
        "criado_em": "2026-10-15T20:00:00Z",
        "hash_conteudo": "texto",
        "titulo": "texto",
        "autor_nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "tipo": "texto",
        "numero": 0,
        "em": "2026-10-15T20:00:00Z",
        "por": "texto",
        "texto": "texto"
      }
    ],
    "acoes": [
      "texto"
    ],
    "frases_longas": [
      {
        "frase": 0,
        "palavras": 0,
        "inicio": "texto"
      }
    ]
  }
  ```

### Painel

#### `GET /api/v1/painel/resumo`

- **Resumo:** Avisos, revisões pendentes, territórios e fontes
- **Papel mínimo:** analista
- **Telas que usam:** app, features/avaliacoes, features/comunicados, features/painel
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "avisos": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "titulo": "texto",
        "nivel": "texto",
        "territorios": [
          {
            "id": "texto",
            "tipo": "texto",
            "nome_exibicao": "texto"
          }
        ],
        "texto": "texto",
        "orientacoes": [
          "texto"
        ],
        "validade_inicio": "2026-10-15T20:00:00Z",
        "validade_fim": "2026-10-15T20:00:00Z",
        "emitido_por": "texto",
        "publicado_em": "2026-10-15T20:00:00Z",
        "publico": "texto"
      }
    ],
    "abrigos": {
      "abrigos_abertos": 0,
      "pessoas_abrigadas": 0,
      "desabrigados": 0,
      "atualizado_em": "2026-10-15T20:00:00Z"
    },
    "pode_revisar": true,
    "aguardando_revisao": [
      {
        "tipo": "texto",
        "id": "00000000-0000-0000-0000-000000000000",
        "titulo": "texto",
        "autor_nome": "texto",
        "enviado_em": "2026-10-15T20:00:00Z"
      }
    ],
    "territorios_em_atencao": [
      {
        "territorio_id": "texto",
        "territorio_nome": "texto",
        "nivel": "texto",
        "motivo": "texto"
      }
    ],
    "fontes": [
      {
        "id": "texto",
        "nome": "texto",
        "status": "texto",
        "ultima_atualizacao": "2026-10-15T20:00:00Z"
      }
    ],
    "contadores": {
      "avaliacoes": 0,
      "comunicados": 0
    }
  }
  ```

#### `GET /api/v1/painel/situacao`

- **Resumo:** Situação agora: chuva recente, pico previsto, maré, risco e frescor
- **Papel mínimo:** analista
- **Telas que usam:** features/boletim, features/painel
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "territorio_id": "texto",
      "territorio_nome": "texto",
      "gerado_em": "2026-10-15T20:00:00Z",
      "chuva_24h": {
        "janela_h": 0,
        "status": "ok",
        "acumulado_mm": 0.0,
        "horas_com_dado": 0,
        "cobertura_pct": 0.0,
        "referencia_mm": 0.0,
        "razao_referencia_pct": 0.0,
        "comparacao": "texto",
        "ate_em": "2026-10-15T20:00:00Z",
        "fontes_usadas": [
          "texto"
        ],
        "nota": "texto"
      },
      "chuva_72h": {
        "janela_h": 0,
        "status": "ok",
        "acumulado_mm": 0.0,
        "horas_com_dado": 0,
        "cobertura_pct": 0.0,
        "referencia_mm": 0.0,
        "razao_referencia_pct": 0.0,
        "comparacao": "texto",
        "ate_em": "2026-10-15T20:00:00Z",
        "fontes_usadas": [
          "texto"
        ],
        "nota": "texto"
      },
      "pico": {
        "horizonte_h": 0,
        "status": "ok",
        "valor_mm": 0.0,
        "em": "2026-10-15T20:00:00Z",
        "maior_24h_mm": 0.0,
        "limite_atencao_mm": 0.0,
        "limite_alerta_mm": 0.0,
        "emitida_em": "2026-10-15T20:00:00Z",
        "fonte_id": "texto",
        "nota": "texto"
      },
      "mare": {
        "status": "ok",
        "maxima_m": 0.0,
        "maxima_em": "2026-10-15T20:00:00Z",
        "emitida_em": "2026-10-15T20:00:00Z",
        "fonte_id": "texto",
        "nota": "texto"
      },
      "risco": {
        "prioridade": "sem_indicacao",
        "ro
    ...(cortado)
  ```

#### `GET /api/v1/painel/acoes`

- **Resumo:** O que fazer agora: fila curta por urgência (revisões, publicações, avisos, fontes, territórios)
- **Papel mínimo:** analista
- **Telas que usam:** features/painel
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "gerado_em": "2026-10-15T20:00:00Z",
    "itens": [
      {
        "urgencia": "alta",
        "tipo": "texto",
        "titulo": "texto",
        "detalhe": "texto",
        "endereco": "texto"
      }
    ],
    "nota": "texto"
  }
  ```

### Evento de chuva

#### `GET /api/v1/estagios`

- **Resumo:** Estágio sugerido (experimental) e declarado de cada distrito ou bairro
- **Papel mínimo:** analista
- **Telas que usam:** features/boletim, features/estagios, features/painel, features/territorio
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `nivel`, `distrito_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "nivel": "distrito",
      "gerado_em": "2026-10-15T20:00:00Z",
      "parametros_versao": 0,
      "itens": [
        {
          "territorio_id": "texto",
          "territorio_nome": "texto",
          "nivel": "distrito",
          "distrito_id": "texto",
          "herda_chuva_de": "texto",
          "sugerido": {
            "estagio": "sem_dados",
            "rotulo": "texto",
            "motivos": [],
            "faltando": [],
            "insumos": {},
            "calculado_em": "2026-10-15T20:00:00Z",
            "experimental": true
          },
          "declarado": {
            "id": "00000000-0000-0000-0000-000000000000",
            "estagio": "observacao",
            "rotulo": "texto",
            "justificativa": "texto",
            "autor_nome": "texto",
            "declarado_em": "2026-10-15T20:00:00Z",
            "territorio_origem_id": "texto",
            "territorio_origem_nome": "texto",
            "herdado": true
          },
          "alertas_oficiais": [
            {}
          ]
        }
      ]
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amo
    ...(cortado)
  ```

#### `POST /api/v1/estagios`

- **Resumo:** Declarar o estágio de um ou mais territórios (ato humano, auditado, sem revisão)
- **Papel mínimo:** analista
- **Telas que usam:** features/boletim, features/estagios, features/painel, features/territorio
- **Resposta:** lista direta
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "territorio_id": "texto",
      "territorio_nome": "texto",
      "nivel": "texto",
      "estagio": "observacao",
      "rotulo": "texto",
      "justificativa": "texto",
      "sugerido_estagio": "texto",
      "lote_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "declarado_em": "2026-10-15T20:00:00Z"
    }
  ]
  ```

#### `GET /api/v1/estagios/historico`

- **Resumo:** Declarações de estágio, mais recentes primeiro
- **Papel mínimo:** analista
- **Telas que usam:** features/estagios
- **Resposta:** lista direta
- **Parâmetros:** `territorio_id`, `desde`, `ate`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "territorio_id": "texto",
      "territorio_nome": "texto",
      "nivel": "texto",
      "estagio": "observacao",
      "rotulo": "texto",
      "justificativa": "texto",
      "sugerido_estagio": "texto",
      "lote_id": "00000000-0000-0000-0000-000000000000",
      "autor_nome": "texto",
      "declarado_em": "2026-10-15T20:00:00Z"
    }
  ]
  ```

#### `GET /api/v1/estagios/parametros`

- **Resumo:** Limiares atuais do estágio sugerido
- **Papel mínimo:** analista
- **Telas que usam:** features/estagios, features/evento
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "limiares": {
      "chuva_24h_atencao_mm": 0.0,
      "chuva_24h_alerta_mm": 0.0,
      "chuva_24h_critico_mm": 0.0,
      "chuva_prev_24h_atencao_mm": 0.0,
      "chuva_prev_24h_alerta_mm": 0.0,
      "chuva_prev_24h_critico_mm": 0.0,
      "chuva_prev_72h_atencao_mm": 0.0,
      "chuva_prev_72h_alerta_mm": 0.0,
      "chuva_prev_72h_critico_mm": 0.0,
      "mare_alta_m": 0.0,
      "mare_janela_h": 0.0,
      "ocorrencias_bairro_minimo": 0.0
    },
    "versao": 0,
    "padrao": true,
    "justificativa": "texto",
    "atualizado_em": "2026-10-15T20:00:00Z",
    "atualizado_por_nome": "texto"
  }
  ```

#### `PUT /api/v1/estagios/parametros`

- **Resumo:** Alterar os limiares (coordenação e administrador)
- **Papel mínimo:** coordenação
- **Telas que usam:** features/estagios, features/evento
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "limiares": {
      "chuva_24h_atencao_mm": 0.0,
      "chuva_24h_alerta_mm": 0.0,
      "chuva_24h_critico_mm": 0.0,
      "chuva_prev_24h_atencao_mm": 0.0,
      "chuva_prev_24h_alerta_mm": 0.0,
      "chuva_prev_24h_critico_mm": 0.0,
      "chuva_prev_72h_atencao_mm": 0.0,
      "chuva_prev_72h_alerta_mm": 0.0,
      "chuva_prev_72h_critico_mm": 0.0,
      "mare_alta_m": 0.0,
      "mare_janela_h": 0.0,
      "ocorrencias_bairro_minimo": 0.0
    },
    "versao": 0,
    "padrao": true,
    "justificativa": "texto",
    "atualizado_em": "2026-10-15T20:00:00Z",
    "atualizado_por_nome": "texto"
  }
  ```

#### `GET /api/v1/estagios/parametros/historico`

- **Resumo:** Versões anteriores dos limiares
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** lista direta
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "versao": 0,
      "limiares": {
        "chuva_24h_atencao_mm": 0.0,
        "chuva_24h_alerta_mm": 0.0,
        "chuva_24h_critico_mm": 0.0,
        "chuva_prev_24h_atencao_mm": 0.0,
        "chuva_prev_24h_alerta_mm": 0.0,
        "chuva_prev_24h_critico_mm": 0.0,
        "chuva_prev_72h_atencao_mm": 0.0,
        "chuva_prev_72h_alerta_mm": 0.0,
        "chuva_prev_72h_critico_mm": 0.0,
        "mare_alta_m": 0.0,
        "mare_janela_h": 0.0,
        "ocorrencias_bairro_minimo": 0.0
      },
      "justificativa": "texto",
      "atualizado_em": "2026-10-15T20:00:00Z",
      "atualizado_por_nome": "texto"
    }
  ]
  ```

#### `POST /api/v1/estagios/mensagem`

- **Resumo:** Texto padronizado e link wa.me da mudança de estágio (nada é enviado)
- **Papel mínimo:** analista
- **Telas que usam:** features/estagios, features/painel
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "texto": "texto",
    "wa_me_url": "texto"
  }
  ```

#### `POST /api/v1/estagios/mensagem/uso`

- **Resumo:** Registrar na auditoria que a mensagem foi copiada ou aberta no WhatsApp (medição do piloto)
- **Papel mínimo:** analista
- **Telas que usam:** features/evento
- **Resposta:** sem corpo

#### `GET /api/v1/abrigos`

- **Resumo:** Abrigos com os totais de abertos, abrigados e desabrigados
- **Papel mínimo:** analista
- **Telas que usam:** features/abrigos, features/boletim, features/painel
- **Resposta:** objeto direto
- **Parâmetros:** `aberto`, `distrito_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "nome": "texto",
        "bairro_id": "texto",
        "bairro_nome": "texto",
        "distrito_id": "texto",
        "distrito_nome": "texto",
        "endereco": "texto",
        "capacidade": 0,
        "aberto": true,
        "pessoas_abrigadas": 0,
        "desabrigados": 0,
        "observacao": "texto",
        "latitude": 0.0,
        "longitude": 0.0,
        "origem": "manual",
        "criado_em": "2026-10-15T20:00:00Z",
        "atualizado_em": "2026-10-15T20:00:00Z",
        "atualizado_por_nome": "texto"
      }
    ],
    "totais": {
      "abrigos_abertos": 0,
      "abrigos_cadastrados": 0,
      "pessoas_abrigadas": 0,
      "desabrigados": 0,
      "abertos_sem_contagem": 0,
      "atualizado_em": "2026-10-15T20:00:00Z"
    }
  }
  ```

#### `POST /api/v1/abrigos`

- **Resumo:** Cadastrar abrigo
- **Papel mínimo:** analista
- **Telas que usam:** features/abrigos, features/boletim, features/painel
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "bairro_id": "texto",
    "bairro_nome": "texto",
    "distrito_id": "texto",
    "distrito_nome": "texto",
    "endereco": "texto",
    "capacidade": 0,
    "aberto": true,
    "pessoas_abrigadas": 0,
    "desabrigados": 0,
    "observacao": "texto",
    "latitude": 0.0,
    "longitude": 0.0,
    "origem": "manual",
    "criado_em": "2026-10-15T20:00:00Z",
    "atualizado_em": "2026-10-15T20:00:00Z",
    "atualizado_por_nome": "texto"
  }
  ```

#### `GET /api/v1/abrigos/{abrigo_id}`

- **Resumo:** Detalhe do abrigo
- **Papel mínimo:** analista
- **Telas que usam:** features/abrigos
- **Resposta:** objeto direto
- **Parâmetros:** `abrigo_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "bairro_id": "texto",
    "bairro_nome": "texto",
    "distrito_id": "texto",
    "distrito_nome": "texto",
    "endereco": "texto",
    "capacidade": 0,
    "aberto": true,
    "pessoas_abrigadas": 0,
    "desabrigados": 0,
    "observacao": "texto",
    "latitude": 0.0,
    "longitude": 0.0,
    "origem": "manual",
    "criado_em": "2026-10-15T20:00:00Z",
    "atualizado_em": "2026-10-15T20:00:00Z",
    "atualizado_por_nome": "texto"
  }
  ```

#### `PATCH /api/v1/abrigos/{abrigo_id}`

- **Resumo:** Atualizar abrigo (gera histórico)
- **Papel mínimo:** analista
- **Telas que usam:** features/abrigos
- **Resposta:** objeto direto
- **Parâmetros:** `abrigo_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "bairro_id": "texto",
    "bairro_nome": "texto",
    "distrito_id": "texto",
    "distrito_nome": "texto",
    "endereco": "texto",
    "capacidade": 0,
    "aberto": true,
    "pessoas_abrigadas": 0,
    "desabrigados": 0,
    "observacao": "texto",
    "latitude": 0.0,
    "longitude": 0.0,
    "origem": "manual",
    "criado_em": "2026-10-15T20:00:00Z",
    "atualizado_em": "2026-10-15T20:00:00Z",
    "atualizado_por_nome": "texto"
  }
  ```

#### `GET /api/v1/abrigos/{abrigo_id}/historico`

- **Resumo:** Atualizações do abrigo, mais recentes primeiro
- **Papel mínimo:** analista
- **Telas que usam:** features/abrigos
- **Resposta:** lista direta
- **Parâmetros:** `abrigo_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  [
    {
      "id": 0,
      "em": "2026-10-15T20:00:00Z",
      "autor_nome": "texto",
      "aberto": true,
      "capacidade": 0,
      "pessoas_abrigadas": 0,
      "desabrigados": 0,
      "observacao": "texto",
      "alteracoes": {}
    }
  ]
  ```

#### `GET /api/v1/acoes`

- **Resumo:** Linha do tempo das ações por território, situação e período
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes, features/boletim, features/painel
- **Resposta:** objeto direto
- **Parâmetros:** `territorio_id`, `situacao`, `desde`, `ate`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "territorio_id": "texto",
        "territorio_nome": "texto",
        "distrito_id": "texto",
        "tipo": "orientacao",
        "tipo_rotulo": "texto",
        "descricao": "texto",
        "responsavel": "texto",
        "situacao": "planejada",
        "situacao_rotulo": "texto",
        "inicio_em": "2026-10-15T20:00:00Z",
        "fim_em": "2026-10-15T20:00:00Z",
        "licao_aprendida": "texto",
        "criada_em": "2026-10-15T20:00:00Z",
        "atualizada_em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto",
        "atualizado_por_nome": "texto"
      }
    ],
    "contagens": {},
    "total": 0
  }
  ```

#### `POST /api/v1/acoes`

- **Resumo:** Registrar ação de resposta
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes, features/boletim, features/painel
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "distrito_id": "texto",
    "tipo": "orientacao",
    "tipo_rotulo": "texto",
    "descricao": "texto",
    "responsavel": "texto",
    "situacao": "planejada",
    "situacao_rotulo": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "licao_aprendida": "texto",
    "criada_em": "2026-10-15T20:00:00Z",
    "atualizada_em": "2026-10-15T20:00:00Z",
    "autor_nome": "texto",
    "atualizado_por_nome": "texto",
    "linha_do_tempo": [
      {
        "id": 0,
        "em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto",
        "situacao": "planejada",
        "texto": "texto",
        "alteracoes": {}
      }
    ]
  }
  ```

#### `GET /api/v1/acoes/{acao_id}`

- **Resumo:** Detalhe da ação com a linha do tempo
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes
- **Resposta:** objeto direto
- **Parâmetros:** `acao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "distrito_id": "texto",
    "tipo": "orientacao",
    "tipo_rotulo": "texto",
    "descricao": "texto",
    "responsavel": "texto",
    "situacao": "planejada",
    "situacao_rotulo": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "licao_aprendida": "texto",
    "criada_em": "2026-10-15T20:00:00Z",
    "atualizada_em": "2026-10-15T20:00:00Z",
    "autor_nome": "texto",
    "atualizado_por_nome": "texto",
    "linha_do_tempo": [
      {
        "id": 0,
        "em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto",
        "situacao": "planejada",
        "texto": "texto",
        "alteracoes": {}
      }
    ]
  }
  ```

#### `PATCH /api/v1/acoes/{acao_id}`

- **Resumo:** Atualizar situação, descrição ou lição aprendida
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes
- **Resposta:** objeto direto
- **Parâmetros:** `acao_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "distrito_id": "texto",
    "tipo": "orientacao",
    "tipo_rotulo": "texto",
    "descricao": "texto",
    "responsavel": "texto",
    "situacao": "planejada",
    "situacao_rotulo": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "licao_aprendida": "texto",
    "criada_em": "2026-10-15T20:00:00Z",
    "atualizada_em": "2026-10-15T20:00:00Z",
    "autor_nome": "texto",
    "atualizado_por_nome": "texto",
    "linha_do_tempo": [
      {
        "id": 0,
        "em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto",
        "situacao": "planejada",
        "texto": "texto",
        "alteracoes": {}
      }
    ]
  }
  ```

#### `GET /api/v1/boletim`

- **Resumo:** Retrato consolidado do evento para a página do boletim
- **Papel mínimo:** analista
- **Telas que usam:** features/abrigos, features/acoes, features/estagios
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "territorio_id": "texto",
      "territorio_nome": "texto",
      "gerado_em": "2026-10-15T20:00:00Z",
      "estagios": [
        {
          "territorio_id": "texto",
          "territorio_nome": "texto",
          "estagio": "texto",
          "rotulo": "texto",
          "origem": "texto",
          "sugerido": {
            "estagio": "sem_dados",
            "rotulo": "texto",
            "motivos": [],
            "faltando": [],
            "insumos": {},
            "calculado_em": "2026-10-15T20:00:00Z",
            "experimental": true
          },
          "declarado": {
            "id": "00000000-0000-0000-0000-000000000000",
            "estagio": "observacao",
            "rotulo": "texto",
            "justificativa": "texto",
            "autor_nome": "texto",
            "declarado_em": "2026-10-15T20:00:00Z",
            "territorio_origem_id": "texto",
            "territorio_origem_nome": "texto",
            "herdado": true
          }
        }
      ],
      "territorios_em_atencao": [
        {
          "territorio_id": "texto",
          "territorio_nome": "texto",
          "nivel": "texto",
          "distrito_id": "texto",
          "estagio": "texto",
          "rotulo": "texto",
          "origem": "texto",
          "motivo": "texto"
        }
      ],
      "chuva": {
        "chuva_24h_mm": 0.0,
        "chuva_24h_territorio": "texto",
        "chuva_prev_24h_mm": 0.0,
        "chuva_prev_24h_territorio": "texto",
    
    ...(cortado)
  ```

#### `GET /api/v1/boletim/texto`

- **Resumo:** Resumo do boletim em texto para WhatsApp (nada é enviado)
- **Papel mínimo:** analista
- **Telas que usam:** features/boletim
- **Resposta:** objeto direto
- **Parâmetros:** `territorio_id`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "texto": "texto",
    "wa_me_url": "texto"
  }
  ```

### Risco de alagamento (experimental)

#### `GET /api/v1/risco-alagamento`

- **Resumo:** Classe de risco de alagamento por bairro (hoje e amanhã), com fatores; experimental
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `nivel`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "disponivel": true,
      "motivo": "texto",
      "experimental": true,
      "modelo": {
        "versao": "texto",
        "metodo": "texto",
        "treinado_em": "texto",
        "experimental": true,
        "validacao": {}
      },
      "itens": [
        {
          "territorio_id": "texto",
          "classe": "baixo",
          "fatores": [
            "texto"
          ]
        }
      ]
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada"
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct": 0.0,
      "amostra": {
        "n": 0,
        "total_fonte": 0
      },
      "avisos": [
        "texto"
      ],
      "dados_insuficientes": true
    }
  }
  ```
