# Open-Meteo — Forecast

- **Identificador:** `open-meteo-previsao`
- **Situação:** Implementada
- **Acesso:** `api.open-meteo.com/v1/forecast`, sem chave
- **Licença:** CC-BY 4.0
- **Destino:** `silver.observacoes` com `tipo=prevista`.

| Variável | Tipo / unidade | Observação |
|---|---|---|
| `precipitation` | mm/h | Chuva prevista para 72 h, com `emitido_em` e `horizonte_h` |
