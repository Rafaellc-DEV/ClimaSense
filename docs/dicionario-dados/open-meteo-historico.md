# Open-Meteo — Historical Weather (ERA5)

- **Identificador:** `open-meteo-historico`
- **Situação:** Implementada
- **Acesso:** `archive-api.open-meteo.com/v1/archive`, sem chave
- **Licença:** CC-BY 4.0 (atribuir “Weather data by Open-Meteo.com”)
- **Destino:** Um ponto representativo por distrito (8) desde 2021-01-01 até 7 dias atrás → `silver.observacoes` → `gold.chuva_diaria`, `chuva_mensal`, `referencia_mensal`.

| Variável | Tipo / unidade | Observação |
|---|---|---|
| `precipitation` | mm/h | Chuva horária, `tipo=derivada` (reanálise, não pluviômetro). Nulo continua nulo. |

## Frescor

- Limite: 192 h (8 dias) (configurado em `backend/climasense/etl/frescor.toml`, chave `open-meteo-historico`; lido por `climasense.etl.frescor`).
- Motivo: a reanalise ERA5 chega com cerca de 7 dias de atraso, mais um dia de folga.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
