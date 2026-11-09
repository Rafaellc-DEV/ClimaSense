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
| POST | `/api/v1/admin/login/liberar` | administrador | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/territorios` | analista | app, features/evento | lista direta |
| GET | `/api/v1/territorios/distritos.geojson` | analista | features/mapa, features/simulador | objeto direto |
| GET | `/api/v1/territorios/hidrografia.geojson` | analista | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/territorios/bairros.geojson` | analista | features/mapa, features/simulador | objeto direto |
| GET | `/api/v1/territorios/indicadores` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/prioridade` | analista | features/acoes, features/mapa | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/camadas/equipamentos-saude` | analista | features/mapa | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/camadas/vulneraveis` | analista | features/mapa | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/camadas/areas-risco` | analista | features/mapa | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/{territorio_id}/resumo-vulnerabilidade` | analista | features/mapa | envelope `{dados, meta}` |
| GET | `/api/v1/territorios/prioridades` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/fontes` | analista | features/evento, features/fontes, features/situacao | lista direta |
| GET | `/api/v1/fontes/{fonte_id}` | analista | features/fontes | objeto direto |
| GET | `/api/v1/fontes/{fonte_id}/execucoes` | analista | features/fontes | lista direta |
| POST | `/api/v1/etl/execucoes` | administrador | features/fontes | sem corpo |
| GET | `/api/v1/etl/execucoes/{execucao_id}` | administrador | features/fontes | objeto direto |
| GET | `/api/v1/series` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/series/referencia` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/series/sazonalidade` | analista | features/chuva | envelope `{dados, meta}` |
| GET | `/api/v1/cenarios/estimativa` | analista | features/chuva, features/situacao | envelope `{dados, meta}` |
| GET | `/api/v1/cenarios/premissas-atuais` | analista | features/simulador | envelope `{dados, meta}` |
| POST | `/api/v1/cenarios/simular` | analista | features/simulador | envelope `{dados, meta}` |
| GET | `/api/v1/cenarios` | analista | features/simulador | envelope `{dados, meta}` |
| POST | `/api/v1/cenarios` | analista | features/simulador | envelope `{dados, meta}` |
| GET | `/api/v1/cenarios/{cenario_id}` | analista | features/chuva, features/simulador, features/situacao | envelope `{dados, meta}` |
| GET | `/api/v1/painel/resumo` | analista | features/evento | objeto direto |
| GET | `/api/v1/admin/auditoria` | administrador | features/acoes, features/admin | objeto direto |
| GET | `/api/v1/admin/etl/execucoes` | administrador | features/admin | lista direta |
| PATCH | `/api/v1/admin/fontes/{fonte_id}` | administrador | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/estagios` | analista | features/chuva, features/mapa, features/situacao | envelope `{dados, meta}` |
| POST | `/api/v1/estagios` | analista | features/chuva, features/mapa, features/situacao | lista direta |
| GET | `/api/v1/estagios/oficial` | analista | features/mapa, features/situacao | envelope `{dados, meta}` |
| POST | `/api/v1/estagios/oficial` | analista | features/mapa, features/situacao | envelope `{dados, meta}` |
| GET | `/api/v1/estagios/oficial/historico` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/estagios/historico` | analista | (nenhuma ainda) | lista direta |
| GET | `/api/v1/estagios/parametros` | analista | features/chuva, features/evento, features/simulador, features/situacao | objeto direto |
| PUT | `/api/v1/estagios/parametros` | coordenação | features/chuva, features/evento, features/simulador, features/situacao | objeto direto |
| GET | `/api/v1/estagios/parametros/historico` | analista | (nenhuma ainda) | lista direta |
| POST | `/api/v1/estagios/mensagem` | analista | features/situacao | objeto direto |
| POST | `/api/v1/estagios/mensagem/uso` | analista | features/evento | sem corpo |
| GET | `/api/v1/acoes` | analista | features/acoes | objeto direto |
| POST | `/api/v1/acoes` | analista | features/acoes | objeto direto |
| GET | `/api/v1/acoes/{acao_id}` | analista | features/acoes | objeto direto |
| PATCH | `/api/v1/acoes/{acao_id}` | analista | features/acoes | objeto direto |
| DELETE | `/api/v1/acoes/{acao_id}` | analista | features/acoes | sem corpo |
| GET | `/api/v1/eventos` | analista | (nenhuma ainda) | objeto direto |
| POST | `/api/v1/eventos` | analista | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/eventos/{evento_id}` | analista | (nenhuma ainda) | objeto direto |
| POST | `/api/v1/eventos/{evento_id}/itens` | analista | (nenhuma ainda) | objeto direto |
| POST | `/api/v1/eventos/{evento_id}/encerrar` | analista | features/fluxo | objeto direto |
| POST | `/api/v1/eventos/{evento_id}/aprovar` | analista | features/fluxo | objeto direto |
| GET | `/api/v1/eventos/{evento_id}/relatorio` | analista | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/boletim` | analista | features/acoes, features/boletim, features/situacao | envelope `{dados, meta}` |
| GET | `/api/v1/boletim/texto` | analista | (nenhuma ainda) | objeto direto |
| GET | `/api/v1/risco-alagamento` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/saude/resumo` | analista | features/boletim, features/saude | envelope `{dados, meta}` |
| GET | `/api/v1/saude/semanal` | analista | features/saude | envelope `{dados, meta}` |
| GET | `/api/v1/saude/bairros` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/situacao/chuva` | analista | (nenhuma ainda) | envelope `{dados, meta}` |
| GET | `/api/v1/ocorrencias/historico` | analista | (nenhuma ainda) | envelope `{dados, meta}` |

## Detalhe por grupo

### Saúde do sistema

#### `GET /api/v1/health`

- **Resumo:** Estado da API e dos bancos (em produção, só ok ou falha)
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

#### `POST /api/v1/admin/login/liberar`

- **Resumo:** Liberar um e-mail e/ou IP bloqueados no login (auditado)
- **Papel mínimo:** administrador
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "email": "texto",
    "ip": "texto"
  }
  ```

#### `GET /api/v1/admin/auditoria`

- **Resumo:** Consultar a auditoria (somente leitura)
- **Papel mínimo:** administrador
- **Telas que usam:** features/acoes, features/admin
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
- **Telas que usam:** features/mapa, features/simulador
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  null
  ```

#### `GET /api/v1/territorios/hidrografia.geojson`

- **Resumo:** Faixas marginais dos recursos hídricos (geometria simplificada)
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  null
  ```

#### `GET /api/v1/territorios/bairros.geojson`

- **Resumo:** Os 94 bairros (GeoJSON simplificado, ids iguais aos de /estagios)
- **Papel mínimo:** analista
- **Telas que usam:** features/mapa, features/simulador
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  null
  ```

#### `GET /api/v1/territorios/indicadores`

- **Resumo:** Valor por distrito para colorir o mapa
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/territorios/prioridade`

- **Resumo:** Prioridade por vulnerabilidade: onde já houve mais atendimentos da Defesa Civil (não é probabilidade)
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes, features/mapa
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `nivel`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "itens": [
        {
          "territorio_id": "texto",
          "nome": "texto",
          "nivel": "distrito",
          "posicao": 0,
          "ocorrencias_alagamento": 0,
          "ocorrencias_deslizamento": 0,
          "criterio": "texto",
          "idosos_60_mais": 0,
          "criancas_0_14": 0
        }
      ],
      "desde": 0
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/territorios/camadas/equipamentos-saude`

- **Resumo:** Equipamentos de saúde (CNES) como pontos no mapa
- **Papel mínimo:** analista
- **Telas que usam:** features/mapa
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {},
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/territorios/camadas/vulneraveis`

- **Resumo:** Idosos e crianças por bairro (Censo 2022), com supressão de células pequenas
- **Papel mínimo:** analista
- **Telas que usam:** features/mapa
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "itens": [
        {
          "bairro_id": "texto",
          "nome": "texto",
          "distrito_id": "texto",
          "criancas_0_4": 0,
          "criancas_0_14": 0,
          "idosos_60_mais": 0,
          "idosos_70_mais": 0,
          "total": 0,
          "suprimido": {},
          "deficiencia": null
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/territorios/camadas/areas-risco`

- **Resumo:** Áreas de risco mapeadas pela Prefeitura (com a cobertura, que pode ser parcial)
- **Papel mínimo:** analista
- **Telas que usam:** features/mapa
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {},
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/territorios/{territorio_id}/resumo-vulnerabilidade`

- **Resumo:** Cruzamento do território: idosos, crianças, equipamentos e áreas de risco (RF-04, RF-07)
- **Papel mínimo:** analista
- **Telas que usam:** features/mapa
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "idosos_60_mais": 0,
      "criancas_0_14": 0,
      "equipamentos": [
        {
          "cnes": "texto",
          "nome": "texto",
          "tipo": "texto"
        }
      ],
      "equipamentos_em_area_de_risco": 0,
      "areas_risco": 0,
      "cobertura_risco_parcial": true
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/territorios/prioridades`

- **Resumo:** Quais territórios pedem atenção primeiro, por quê e com que confiança
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": "municipio"
      },
      "cobertura_pct"
    ...(cortado)
  ```

### Fontes de dados

#### `GET /api/v1/fontes`

- **Resumo:** Fontes com status (atualizada, desatualizada, com falha, planejada)
- **Papel mínimo:** analista
- **Telas que usam:** features/evento, features/fontes, features/situacao
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
      "limite_desatualizacao_h": 0,
      "limite_frescor_h": 0.0,
      "desatualizado": true
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
    "limite_desatualizacao_h": 0,
    "limite_frescor_h": 0.0,
    "desatualizado": true
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
- **Telas que usam:** nenhuma ainda
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/series/referencia`

- **Resumo:** Referência histórica por mês
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/series/sazonalidade`

- **Resumo:** Calendário ano × mês
- **Papel mínimo:** analista
- **Telas que usam:** features/chuva
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

### Cenários de alagamento

#### `GET /api/v1/cenarios/estimativa`

- **Resumo:** Estimativa experimental por distrito: previsão, maré e prioridade (antiga GET /cenarios)
- **Papel mínimo:** analista
- **Telas que usam:** features/chuva, features/situacao
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
   
    ...(cortado)
  ```

#### `GET /api/v1/cenarios/premissas-atuais`

- **Resumo:** Premissas sugeridas pelas fontes reais (previsão, maré e chuva medida)
- **Papel mínimo:** analista
- **Telas que usam:** features/simulador
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "chuva_prevista_mm": 0.0,
      "duracao_h": 0.0,
      "chuva_acumulada_mm": 0.0,
      "mare_m": 0.0,
      "horizonte_h": 0
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `POST /api/v1/cenarios/simular`

- **Resumo:** Simular um cenário por regras: classe de alagamento e deslizamento por bairro e distrito
- **Papel mínimo:** analista
- **Telas que usam:** features/simulador
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "itens": [
        {
          "territorio_id": "texto",
          "nome": "texto",
          "nivel": "bairro",
          "distrito_id": "texto",
          "classe_alagamento": "sem_dados",
          "classe_deslizamento": "sem_dados",
          "estagio_sugerido": "sem_dados",
          "confianca": "alta",
          "motivos": [
            "texto"
          ],
          "impacto_pessoas": {
            "idosos_60_mais": 0,
            "criancas_0_14": 0,
            "equipamentos_saude": 0,
            "deficiencia": null,
            "total_pessoas": 0,
            "criterio": "texto"
          },
          "arboviroses": {
            "agravos": [],
            "classe_impacto": "baixa",
            "agravos_em_destaque": []
          }
        }
      ],
      "resumo": {
        "por_classe": {},
        "impacto_pessoas_aviso": "texto",
        "arboviroses": {
          "experimental": true,
          "contexto": true,
          "aviso": "texto",
          "granularidade_semanal": "municipio",
          "granularidade_anual": "distrito",
          "fontes": [
            {}
          ]
        },
        "ordem_de_atencao_distritos": [
          {
            "distrito_id": "texto",
            "nome": "texto",
            "estagio_sugerido": "sem_dados",
            "classe_arboviroses": "baixa",
            "agravos_em_destaque": []
          }
        ],
        "pessoas_vulneraveis_em_alerta": {
          "bairros_em_alerta": 0,
          "idosos_
    ...(cortado)
  ```

#### `GET /api/v1/cenarios`

- **Resumo:** Cenários salvos, mais recente primeiro
- **Papel mínimo:** analista
- **Telas que usam:** features/simulador
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "nome": "texto",
        "autor_nome": "texto",
        "criado_em": "2026-10-15T20:00:00Z",
        "resumo": {
          "por_classe": {}
        }
      }
    ],
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `POST /api/v1/cenarios`

- **Resumo:** Salvar o cenário (analista ou acima; auditado; o servidor recalcula o resultado)
- **Papel mínimo:** analista
- **Telas que usam:** features/simulador
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "id": "00000000-0000-0000-0000-000000000000",
      "nome": "texto",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z",
      "resumo": {
        "por_classe": {}
      },
      "premissas": {
        "chuva_prevista_mm": 0.0,
        "duracao_h": 0.0,
        "chuva_acumulada_mm": 0.0,
        "mare_m": 0.0,
        "horizonte_h": 0
      },
      "resultado": {
        "itens": [
          {
            "territorio_id": "texto",
            "nome": "texto",
            "nivel": "bairro",
            "distrito_id": "texto",
            "classe_alagamento": "sem_dados",
            "classe_deslizamento": "sem_dados",
            "estagio_sugerido": "sem_dados",
            "confianca": "alta",
            "motivos": [],
            "impacto_pessoas": {},
            "arboviroses": {}
          }
        ],
        "resumo": {
          "por_classe": {},
          "impacto_pessoas_aviso": "texto",
          "arboviroses": {
            "experimental": true,
            "contexto": true,
            "aviso": "texto",
            "granularidade_semanal": "municipio",
            "granularidade_anual": "distrito",
            "fontes": []
          },
          "ordem_de_atencao_distritos": [
            {}
          ],
          "pessoas_vulneraveis_em_alerta": {
            "bairros_em_alerta": 0,
            "idosos_60_mais": 0,
            "criancas_0_14": 0,
            "parcial": true,
            "criterio": "texto"
          }
       
    ...(cortado)
  ```

#### `GET /api/v1/cenarios/{cenario_id}`

- **Resumo:** Abrir um cenário salvo
- **Papel mínimo:** analista
- **Telas que usam:** features/chuva, features/simulador, features/situacao
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `cenario_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "id": "00000000-0000-0000-0000-000000000000",
      "nome": "texto",
      "autor_nome": "texto",
      "criado_em": "2026-10-15T20:00:00Z",
      "resumo": {
        "por_classe": {}
      },
      "premissas": {
        "chuva_prevista_mm": 0.0,
        "duracao_h": 0.0,
        "chuva_acumulada_mm": 0.0,
        "mare_m": 0.0,
        "horizonte_h": 0
      },
      "resultado": {
        "itens": [
          {
            "territorio_id": "texto",
            "nome": "texto",
            "nivel": "bairro",
            "distrito_id": "texto",
            "classe_alagamento": "sem_dados",
            "classe_deslizamento": "sem_dados",
            "estagio_sugerido": "sem_dados",
            "confianca": "alta",
            "motivos": [],
            "impacto_pessoas": {},
            "arboviroses": {}
          }
        ],
        "resumo": {
          "por_classe": {},
          "impacto_pessoas_aviso": "texto",
          "arboviroses": {
            "experimental": true,
            "contexto": true,
            "aviso": "texto",
            "granularidade_semanal": "municipio",
            "granularidade_anual": "distrito",
            "fontes": []
          },
          "ordem_de_atencao_distritos": [
            {}
          ],
          "pessoas_vulneraveis_em_alerta": {
            "bairros_em_alerta": 0,
            "idosos_60_mais": 0,
            "criancas_0_14": 0,
            "parcial": true,
            "criterio": "texto"
          }
       
    ...(cortado)
  ```

### Painel

#### `GET /api/v1/painel/resumo`

- **Resumo:** Avisos, revisões pendentes, territórios e fontes
- **Papel mínimo:** analista
- **Telas que usam:** features/evento
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
        "ultima_atualizacao": "2026-10-15T20:00:00Z",
        "limite_frescor_h": 0.0,
        "desatualizado": true
      }
    ],
    "contadores": {
      "avaliacoes": 0,
      "comunicados": 0
    }
  }
  ```

### Evento de chuva

#### `GET /api/v1/estagios`

- **Resumo:** Estágio sugerido (experimental) e declarado de cada distrito ou bairro, com o oficial do COP
- **Papel mínimo:** analista
- **Telas que usam:** features/chuva, features/mapa, features/situacao
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granu
    ...(cortado)
  ```

#### `POST /api/v1/estagios`

- **Resumo:** Declarar o estágio de um ou mais territórios (ato humano, auditado, sem revisão)
- **Papel mínimo:** analista
- **Telas que usam:** features/chuva, features/mapa, features/situacao
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

#### `GET /api/v1/estagios/oficial`

- **Resumo:** Estágio oficial da cidade dado pelo COP (registro da equipe); null sem registro
- **Papel mínimo:** analista
- **Telas que usam:** features/mapa, features/situacao
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "estagio": "observacao",
      "informado_em": "2026-10-15T20:00:00Z",
      "registrado_em": "2026-10-15T20:00:00Z",
      "autor_nome": "texto",
      "observacao": "texto",
      "fonte": "texto"
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `POST /api/v1/estagios/oficial`

- **Resumo:** Registrar o estágio oficial informado pelo COP (analista ou acima; auditado; só inclusão)
- **Papel mínimo:** analista
- **Telas que usam:** features/mapa, features/situacao
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "estagio": "observacao",
      "informado_em": "2026-10-15T20:00:00Z",
      "registrado_em": "2026-10-15T20:00:00Z",
      "autor_nome": "texto",
      "observacao": "texto",
      "fonte": "texto"
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/estagios/oficial/historico`

- **Resumo:** Histórico do estágio oficial, mais recente primeiro
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": [
      {
        "estagio": "observacao",
        "informado_em": "2026-10-15T20:00:00Z",
        "registrado_em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto",
        "observacao": "texto",
        "fonte": "texto"
      }
    ],
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/estagios/historico`

- **Resumo:** Declarações de estágio, mais recentes primeiro
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
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
- **Telas que usam:** features/chuva, features/evento, features/simulador, features/situacao
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
- **Telas que usam:** features/chuva, features/evento, features/simulador, features/situacao
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
- **Telas que usam:** features/situacao
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

#### `GET /api/v1/acoes`

- **Resumo:** Linha do tempo das ações por território, situação e período
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes
- **Resposta:** objeto direto
- **Parâmetros:** `territorio_id`, `situacao`, `desde`, `ate`, `ordem`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "territorio_id": "texto",
        "territorio_nome": "texto",
        "territorio_nivel": "municipio",
        "distrito_id": "texto",
        "distrito_nome": "texto",
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
    "total": 0,
    "por_distrito": [
      {
        "distrito_id": "texto",
        "distrito_nome": "texto",
        "contagens": {}
      }
    ],
    "ordenado_por_prioridade": true
  }
  ```

#### `POST /api/v1/acoes`

- **Resumo:** Registrar ação de resposta
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "territorio_id": "texto",
    "territorio_nome": "texto",
    "territorio_nivel": "municipio",
    "distrito_id": "texto",
    "distrito_nome": "texto",
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
    "territorio_nivel": "municipio",
    "distrito_id": "texto",
    "distrito_nome": "texto",
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
    "territorio_nivel": "municipio",
    "distrito_id": "texto",
    "distrito_nome": "texto",
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

#### `DELETE /api/v1/acoes/{acao_id}`

- **Resumo:** Excluir ação em qualquer situação (auditado: quem, quando e o que foi excluído)
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes
- **Resposta:** sem corpo
- **Parâmetros:** `acao_id*`

#### `GET /api/v1/boletim`

- **Resumo:** Retrato consolidado do evento para a página do boletim
- **Papel mínimo:** analista
- **Telas que usam:** features/acoes, features/boletim, features/situacao
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `territorio_id`, `desde`, `ate`
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
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Parâmetros:** `territorio_id`, `desde`, `ate`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "texto": "texto",
    "wa_me_url": "texto"
  }
  ```

### Histórico de eventos

#### `GET /api/v1/eventos`

- **Resumo:** Listar eventos de chuva registrados
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Parâmetros:** `situacao`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "itens": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "nome": "texto",
        "inicio_em": "2026-10-15T20:00:00Z",
        "fim_em": "2026-10-15T20:00:00Z",
        "situacao": "aberto",
        "situacao_rotulo": "texto",
        "retrospectivo": true,
        "distritos_afetados": [
          "texto"
        ],
        "situacao_final": "texto",
        "pendencias": "texto",
        "duracao_horas": 0.0,
        "aguarda_aprovacao": true,
        "aberto_por_nome": "texto",
        "aberto_em": "2026-10-15T20:00:00Z",
        "encerrado_por_nome": "texto",
        "encerrado_em": "2026-10-15T20:00:00Z",
        "aprovado_por_nome": "texto",
        "aprovado_em": "2026-10-15T20:00:00Z"
      }
    ],
    "contagens": {},
    "total": 0
  }
  ```

#### `POST /api/v1/eventos`

- **Resumo:** Abrir evento de chuva
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "situacao": "aberto",
    "situacao_rotulo": "texto",
    "retrospectivo": true,
    "distritos_afetados": [
      "texto"
    ],
    "situacao_final": "texto",
    "pendencias": "texto",
    "duracao_horas": 0.0,
    "aguarda_aprovacao": true,
    "aberto_por_nome": "texto",
    "aberto_em": "2026-10-15T20:00:00Z",
    "encerrado_por_nome": "texto",
    "encerrado_em": "2026-10-15T20:00:00Z",
    "aprovado_por_nome": "texto",
    "aprovado_em": "2026-10-15T20:00:00Z",
    "distritos": [
      {
        "id": "texto",
        "nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "id": 0,
        "tipo": "comunicado",
        "tipo_rotulo": "texto",
        "texto": "texto",
        "fonte": "texto",
        "estagio": "observacao",
        "equipes_mobilizadas": 0,
        "ocorrido_em": "2026-10-15T20:00:00Z",
        "registrado_em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto"
      }
    ]
  }
  ```

#### `GET /api/v1/eventos/{evento_id}`

- **Resumo:** Abrir um evento com a linha do tempo
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Parâmetros:** `evento_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "situacao": "aberto",
    "situacao_rotulo": "texto",
    "retrospectivo": true,
    "distritos_afetados": [
      "texto"
    ],
    "situacao_final": "texto",
    "pendencias": "texto",
    "duracao_horas": 0.0,
    "aguarda_aprovacao": true,
    "aberto_por_nome": "texto",
    "aberto_em": "2026-10-15T20:00:00Z",
    "encerrado_por_nome": "texto",
    "encerrado_em": "2026-10-15T20:00:00Z",
    "aprovado_por_nome": "texto",
    "aprovado_em": "2026-10-15T20:00:00Z",
    "distritos": [
      {
        "id": "texto",
        "nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "id": 0,
        "tipo": "comunicado",
        "tipo_rotulo": "texto",
        "texto": "texto",
        "fonte": "texto",
        "estagio": "observacao",
        "equipes_mobilizadas": 0,
        "ocorrido_em": "2026-10-15T20:00:00Z",
        "registrado_em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto"
      }
    ]
  }
  ```

#### `POST /api/v1/eventos/{evento_id}/itens`

- **Resumo:** Registrar item na linha do tempo (comunicado, estágio, ação ou observação)
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Parâmetros:** `evento_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "situacao": "aberto",
    "situacao_rotulo": "texto",
    "retrospectivo": true,
    "distritos_afetados": [
      "texto"
    ],
    "situacao_final": "texto",
    "pendencias": "texto",
    "duracao_horas": 0.0,
    "aguarda_aprovacao": true,
    "aberto_por_nome": "texto",
    "aberto_em": "2026-10-15T20:00:00Z",
    "encerrado_por_nome": "texto",
    "encerrado_em": "2026-10-15T20:00:00Z",
    "aprovado_por_nome": "texto",
    "aprovado_em": "2026-10-15T20:00:00Z",
    "distritos": [
      {
        "id": "texto",
        "nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "id": 0,
        "tipo": "comunicado",
        "tipo_rotulo": "texto",
        "texto": "texto",
        "fonte": "texto",
        "estagio": "observacao",
        "equipes_mobilizadas": 0,
        "ocorrido_em": "2026-10-15T20:00:00Z",
        "registrado_em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto"
      }
    ]
  }
  ```

#### `POST /api/v1/eventos/{evento_id}/encerrar`

- **Resumo:** Encerrar o evento com situação final e pendências (falta a aprovação de outra pessoa)
- **Papel mínimo:** analista
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `evento_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "situacao": "aberto",
    "situacao_rotulo": "texto",
    "retrospectivo": true,
    "distritos_afetados": [
      "texto"
    ],
    "situacao_final": "texto",
    "pendencias": "texto",
    "duracao_horas": 0.0,
    "aguarda_aprovacao": true,
    "aberto_por_nome": "texto",
    "aberto_em": "2026-10-15T20:00:00Z",
    "encerrado_por_nome": "texto",
    "encerrado_em": "2026-10-15T20:00:00Z",
    "aprovado_por_nome": "texto",
    "aprovado_em": "2026-10-15T20:00:00Z",
    "distritos": [
      {
        "id": "texto",
        "nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "id": 0,
        "tipo": "comunicado",
        "tipo_rotulo": "texto",
        "texto": "texto",
        "fonte": "texto",
        "estagio": "observacao",
        "equipes_mobilizadas": 0,
        "ocorrido_em": "2026-10-15T20:00:00Z",
        "registrado_em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto"
      }
    ]
  }
  ```

#### `POST /api/v1/eventos/{evento_id}/aprovar`

- **Resumo:** Aprovar a situação final (RN-05: outra pessoa, que não abriu nem encerrou o evento)
- **Papel mínimo:** analista
- **Telas que usam:** features/fluxo
- **Resposta:** objeto direto
- **Parâmetros:** `evento_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "nome": "texto",
    "inicio_em": "2026-10-15T20:00:00Z",
    "fim_em": "2026-10-15T20:00:00Z",
    "situacao": "aberto",
    "situacao_rotulo": "texto",
    "retrospectivo": true,
    "distritos_afetados": [
      "texto"
    ],
    "situacao_final": "texto",
    "pendencias": "texto",
    "duracao_horas": 0.0,
    "aguarda_aprovacao": true,
    "aberto_por_nome": "texto",
    "aberto_em": "2026-10-15T20:00:00Z",
    "encerrado_por_nome": "texto",
    "encerrado_em": "2026-10-15T20:00:00Z",
    "aprovado_por_nome": "texto",
    "aprovado_em": "2026-10-15T20:00:00Z",
    "distritos": [
      {
        "id": "texto",
        "nome": "texto"
      }
    ],
    "linha_do_tempo": [
      {
        "id": 0,
        "tipo": "comunicado",
        "tipo_rotulo": "texto",
        "texto": "texto",
        "fonte": "texto",
        "estagio": "observacao",
        "equipes_mobilizadas": 0,
        "ocorrido_em": "2026-10-15T20:00:00Z",
        "registrado_em": "2026-10-15T20:00:00Z",
        "autor_nome": "texto"
      }
    ]
  }
  ```

#### `GET /api/v1/eventos/{evento_id}/relatorio`

- **Resumo:** Relatório executivo do evento, só com dados reais; cada bloco com fonte e hora
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** objeto direto
- **Parâmetros:** `evento_id*`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "gerado_em": "2026-10-15T20:00:00Z",
    "periodo": {
      "inicio_em": "2026-10-15T20:00:00Z",
      "fim_em": "2026-10-15T20:00:00Z",
      "desde": "2026-10-15",
      "ate": "2026-10-15",
      "em_andamento": true
    },
    "aviso": "texto",
    "evento": {
      "fonte": "texto",
      "atualizado_em": "2026-10-15T20:00:00Z",
      "suficiente": true,
      "motivo": "texto",
      "id": "00000000-0000-0000-0000-000000000000",
      "nome": "texto",
      "situacao": "aberto",
      "situacao_rotulo": "texto",
      "retrospectivo": true,
      "inicio_em": "2026-10-15T20:00:00Z",
      "fim_em": "2026-10-15T20:00:00Z",
      "duracao_horas": 0.0,
      "aberto_por_nome": "texto",
      "aberto_em": "2026-10-15T20:00:00Z",
      "encerrado_por_nome": "texto",
      "encerrado_em": "2026-10-15T20:00:00Z",
      "aprovado_por_nome": "texto",
      "aprovado_em": "2026-10-15T20:00:00Z",
      "aprovado": true
    },
    "comunicados": {
      "fonte": "texto",
      "atualizado_em": "2026-10-15T20:00:00Z",
      "suficiente": true,
      "motivo": "texto",
      "itens": [
        {}
      ]
    },
    "equipes_mobilizadas": {
      "fonte": "texto",
      "atualizado_em": "2026-10-15T20:00:00Z",
      "suficiente": true,
      "motivo": "texto",
      "maior_numero": 0,
      "registros": [
        {}
      ]
    },
    "distritos_afetados": {
      "fonte": "texto",
      "atualizado_em": "2026-10-15T20:00:00Z",
      "suficiente": true,
      "motivo": "texto",
      "com
    ...(cortado)
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
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

### Saúde depois da chuva

#### `GET /api/v1/saude/resumo`

- **Resumo:** Dengue, chikungunya e leptospirose na última semana e a janela de vigilância de leptospirose
- **Papel mínimo:** analista
- **Telas que usam:** features/boletim, features/saude
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "agravos": [
        {
          "agravo": "dengue",
          "nome": "texto",
          "fonte_id": "texto",
          "utilizavel": true,
          "ultima_semana_com_dado": {
            "ano": 0,
            "semana": 0,
            "inicio": "2026-10-15"
          },
          "motivo": "texto",
          "ultima_semana": {
            "ano": 0,
            "semana": 0,
            "inicio": "2026-10-15"
          },
          "casos": 0,
          "casos_estimados": 0.0,
          "confirmados": 0,
          "rt": 0.0,
          "variacao_4s_pct": 0.0,
          "nivel_alerta": 0,
          "incompleta": true
        }
      ],
      "janela_leptospirose": {
        "ativa": true,
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "dia_da_janela": 0,
        "atencao_maior": true,
        "motivo": "texto",
        "origens": [
          "estagio"
        ],
        "territorios": [
          {
            "id": "texto",
            "nome": "texto"
          }
        ]
      },
      "gerado_em": "2026-10-15T20:00:00Z"
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
        }
      ],
      "recorte": {
        "territorio_id": "texto",
        "inicio": "2026-10-15",
        "fim": "2026-10-15",
        "granularidade": 
    ...(cortado)
  ```

#### `GET /api/v1/saude/semanal`

- **Resumo:** Série semanal de um agravo no Recife com a chuva semanal ao lado
- **Papel mínimo:** analista
- **Telas que usam:** features/saude
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `agravo`, `desde`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "agravo": "dengue",
      "desde": "2026-10-15",
      "itens": [
        {
          "ano": 0,
          "semana": 0,
          "inicio": "2026-10-15",
          "casos": 0,
          "confirmados": 0,
          "casos_estimados": 0.0,
          "ic_inf": 0.0,
          "ic_sup": 0.0,
          "nivel_alerta": 0,
          "incompleta": true
        }
      ],
      "chuva": [
        {
          "inicio": "2026-10-15",
          "chuva_mm": 0.0,
          "dias_com_dado": 0
        }
      ],
      "motivo": "texto"
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/saude/bairros`

- **Resumo:** Casos confirmados de dengue ou chikungunya por bairro de residência em um ano (histórico)
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `agravo`, `ano`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "agravo": "dengue",
      "ano": 0,
      "itens": [
        {
          "bairro_id": "texto",
          "bairro_nome": "texto",
          "distrito_id": "texto",
          "casos": 0,
          "notificados": 0,
          "suprimido": true
        }
      ],
      "anos_disponiveis": [
        0
      ],
      "total_confirmados": 0,
      "confirmados_sem_bairro": 0,
      "sem_bairro_suprimido": true,
      "total_notificados": 0,
      "fonte_atualizada_em": "2026-10-15"
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

#### `GET /api/v1/ocorrencias/historico`

- **Resumo:** Onde já aconteceu: atendimentos de alagamento ou deslizamento da Defesa Civil por bairro
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** envelope `{dados, meta}`
- **Parâmetros:** `tipo`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "tipo": "alagamento",
      "itens": [
        {
          "bairro_id": "texto",
          "bairro_nome": "texto",
          "distrito_id": "texto",
          "registros": 0,
          "dias_com_registro": 0,
          "primeiro_registro": "2026-10-15",
          "ultimo_registro": "2026-10-15"
        }
      ],
      "total_registros": 0,
      "bairros_com_registro": 0,
      "periodo_inicio": "2026-10-15",
      "periodo_fim": "2026-10-15"
    },
    "meta": {
      "fontes": [
        {
          "id": "texto",
          "nome": "texto",
          "tipo": "observada",
          "atualizado_em": "2026-10-15T20:00:00Z",
          "status": "atualizada",
          "limite_frescor_h": 0.0,
          "desatualizado": true
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
      "fonte_por_premissa": {},
      "dados_insuficientes": true,
      "supressao_minima": 0,
      "ano": 0,
      "deficiencia": "texto",
      "cobertura": {}
    }
  }
  ```

### Situação

#### `GET /api/v1/situacao/chuva`

- **Resumo:** Chuva medida por distrito, estações sem leitura e série prevista de chuva e maré
- **Papel mínimo:** analista
- **Telas que usam:** nenhuma ainda
- **Resposta:** envelope `{dados, meta}`
- **Exemplo (gerado do esquema, valores ilustrativos):**

  ```json
  {
    "dados": {
      "gerado_em": "2026-10-15T20:00:00Z",
      "distritos": [
        {
          "territorio_id": "texto",
          "territorio_nome": "texto",
          "chuva_24h_mm": 0.0,
          "chuva_72h_mm": 0.0,
          "fonte_chuva": "texto",
          "lida_em": "2026-10-15T20:00:00Z",
          "estacoes_total": 0,
          "estacoes_com_leitura": 0,
          "estacoes_sem_leitura": 0,
          "medicao_propria": true,
          "motivo": "texto"
        }
      ],
      "maior_24h": {
        "territorio_id": "texto",
        "territorio_nome": "texto",
        "mm": 0.0
      },
      "maior_72h": {
        "territorio_id": "texto",
        "territorio_nome": "texto",
        "mm": 0.0
      },
      "estacoes": {
        "total": 0,
        "com_leitura": 0,
        "sem_leitura": 0,
        "lida_em": "2026-10-15T20:00:00Z"
      },
      "observada": {
        "fonte": "texto",
        "janela_h": 0,
        "serie": [
          {
            "t": "2026-10-15T20:00:00Z",
            "municipio_mm": 0.0,
            "distritos": {}
          }
        ],
        "motivo": "texto"
      },
      "previsao": {
        "horizonte_h": 0,
        "previsao_emitida_em": "2026-10-15T20:00:00Z",
        "mare_emitida_em": "2026-10-15T20:00:00Z",
        "emissoes_na_faixa": 0,
        "faixa_disponivel": true,
        "chuva": [
          {
            "t": "2026-10-15T20:00:00Z",
            "valor": 0.0,
            "min": 0.0,
            "max": 0.0
          }
        ],
    ...(cortado)
  ```
