# INMET — estação automática A301 (Recife)

- **Identificador:** `inmet`
- **Situação:** Planejada
- **Acesso:** API `apitempo.inmet.gov.br` (token)
- **Licença:** Dados públicos
- **Destino:** —

| Variável | Tipo / unidade | Observação |
|---|---|---|
| `chuva, temperatura, umidade` | vários | Horário UTC |

## Perguntas em aberto

- Verificado em 24/10/2026: `GET /estacoes/T` responde (A301 Recife, operante, lat -8,0189 / lon -34,9442), mas `GET /estacao/{ini}/{fim}/A301` devolve **204 sem conteúdo** para qualquer período (inclusive A001) e a conexão é reiniciada sem `User-Agent`. Sem token não há dado observado: continua planejada.
- Obter o token institucional do INMET.
