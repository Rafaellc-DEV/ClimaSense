# Evidências científicas preservadas

Estes JSON pequenos registram resultados existentes, sem dados pessoais ou modelos
binários. Não são novas execuções nem aprovam operação. O código continua gerando
resultados de novas execuções em `tmp/experimentos/`; as cópias abaixo permitem
conferir a entrega após clonar o repositório.

| Arquivo | Origem |
|---|---|
| `modelo-0.2.0.json` | Metadados extraídos do artefato local compatível treinado em 2026-11-14T02:09:09Z; inclui SHA-256 do joblib, sem regravá-lo |
| `comparacao-territorial.json` | Cópia integral de `tmp/experimentos/comparacao-territorial.json` |
| `comparacao_sgb.json` | Cópia integral de `tmp/experimentos/comparacao_sgb.json` |
| `comparacao_chuva_intensa.json` | Cópia integral de `tmp/experimentos/comparacao_chuva_intensa.json` |
| `sgb_inundacao_qualidade.json` | Cópia integral de `tmp/experimentos/sgb_inundacao_qualidade.json` |

As datas `gerado_em` originais foram mantidas.
Os finais de linha são normalizados para LF pelos hooks do projeto; o conteúdo
JSON foi comparado integralmente às fontes locais, sem alteração dos valores.

O SGB declara ano 2014, com trabalho
de campo entre 2012 e 2014; o experimento usa 2016 em diante por considerar a
publicação da carta em 2015. Há cobertura em 90 de 94 bairros; ausência de carta
nos quatro restantes é desconhecimento, não suscetibilidade baixa.

O arquivo histórico `../risco-alagamento-metricas.json` é da versão 0.1.0 e foi
preservado sem editar números. A interpretação vigente está em
[`../risco-alagamento.md`](../risco-alagamento.md).
