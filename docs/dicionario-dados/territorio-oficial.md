# Prefeitura do Recife — distritos, bairros e faixas hídricas

- **Identificador:** `territorio-oficial`
- **Situação:** Implementada
- **Acesso:** Arquivos oficiais em `data/territorio/` (cópia íntegra, `MANIFEST.sha256`) ou `--baixar`
- **Licença:** Dados abertos do Recife
- **Destino:** Atlas `Recife.DistritosSanitarios` e `Recife.FaixasHidricas` + `app.territorios` (103 linhas).

| Variável | Tipo / unidade | Observação |
|---|---|---|
| `cdistscodi` | inteiro | Código do distrito (1–8) |
| `bairros` | lista | 94 bairros, com a correção VII/VIII documentada |
| `area_km2` | número | Calculada em SIRGAS 2000 / UTM 25S |
