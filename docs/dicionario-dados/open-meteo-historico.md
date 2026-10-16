# Open-Meteo — Historical Weather (ERA5)

- **Identificador:** `open-meteo-historico`
- **Situação:** Implementada
- **Acesso:** `archive-api.open-meteo.com/v1/archive`, sem chave
- **Licença:** CC-BY 4.0 (atribuir “Weather data by Open-Meteo.com”)
- **Destino:** Um ponto representativo por distrito (8) desde 2021-01-01 até 7 dias atrás → `silver.observacoes` → `gold.chuva_diaria`, `chuva_mensal`, `referencia_mensal`.

| Variável | Tipo / unidade | Observação |
|---|---|---|
| `precipitation` | mm/h | Chuva horária, `tipo=derivada` (reanálise, não pluviômetro). Nulo continua nulo. |
