# Open-Meteo — Forecast

- **Identificador:** `open-meteo-previsao`
- **Situação:** Implementada
- **Acesso:** `api.open-meteo.com/v1/forecast`, sem chave
- **Licença:** CC-BY 4.0
- **Destino:** `silver.observacoes` com `tipo=prevista`.

| Variável | Tipo / unidade | Observação |
|---|---|---|
| `precipitation` | mm/h | Chuva prevista para 72 h e as 7 × 24 h já passadas do modelo (`past_days=7`, fallback da chuva recente enquanto a ERA5 não chega), com `emitido_em` e `horizonte_h` (0 nas horas passadas). Toda emissão é acumulada na silver, nunca sobrescrita |

## Frescor

- Limite: 6 h (configurado em `backend/climasense/etl/frescor.toml`, chave `open-meteo-previsao`; lido por `climasense.etl.frescor`).
- Motivo: o modelo e reprocessado a cada 6 h.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
