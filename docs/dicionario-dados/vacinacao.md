# Dados Abertos do Recife — perfil das pessoas vacinadas (COVID-19)

- **Identificador:** `vacinacao`
- **Situação:** Implementada
- **Acesso:** API CKAN `datastore_search` (paginação de 500)
- **Licença:** Licença aberta do portal (ODbL / CC-BY, conforme o conjunto)
- **Destino:** Bronze `mongo_db_bronze_vacinacao.bronze_vacinados` → `silver.vacinados` → `gold.vacinacao_distrito_mes` (supressão abaixo de `SUPRESSAO_MINIMA`).

| Variável | Tipo / unidade | Observação |
|---|---|---|
| `faixa_etaria` | texto | Faixa etária, maiúsculas |
| `idade` | inteiro | Idade em anos; inválida → registro descartado |
| `sexo` | texto |  |
| `raca_cor` | texto |  |
| `grupo / categoria` | texto | Grupo prioritário |
| `vacina` | texto | Derivada de `vacina_fabricante` (parte após “ - ”) |
| `dose` | inteiro | Derivada de `descricao_dose` |
| `distrito_sanitario` | texto | Derivado do `cnes` (ex.: “DS 4”) |
| `unidade_saude` | texto | Derivada do `cnes` |
| `data_vacinacao` | data | Inválida → registro descartado |
