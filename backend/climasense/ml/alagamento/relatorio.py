"""Relatório em markdown do estudo de risco de alagamento (`docs/ml/risco-alagamento.md`)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from climasense.ml.alagamento import modelo
from climasense.ml.alagamento.base import NOMES

PASTA_DOCS = Path(__file__).resolve().parents[4] / "docs" / "ml"
NOMES_LINHA = {
    "modelo": "Árvore: classe moderado ou alto",
    "modelo_alto": "Árvore: só classe alto",
    "limiar_chuva": "Referência: limiar de chuva do dia",
    "estimador_referencia": "Referência: EstimadorReferencia (regra dos cenários)",
}


def _f(v, casas: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{casas}f}"
    return str(v)


def _params(p: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in p.items())


def tabela_teste(teste: dict) -> str:
    linhas = [
        "| Abordagem | Recall | Precisão | AUC-PR | Alertas (% bairro-dias) | VP | FP | FN "
        "| Atendimentos avisados | Dias com atendimento avisados |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for chave, m in teste.items():
        ev = f"{m.get('eventos_avisados', '—')}/{m.get('eventos', '—')}"
        dias = f"{m.get('dias_com_atendimento_avisados', '—')}/{m.get('dias_com_atendimento', '—')}"
        linhas.append(
            f"| {NOMES_LINHA.get(chave, chave)} | {_f(m['recall'])} | {_f(m['precisao'])} | {_f(m['auc_pr'])} "
            f"| {_f(m['alertas_pct'], 1)} | {m['vp']} | {m['fp']} | {m['fn']} | {ev} | {dias} |"
        )
    return "\n".join(linhas) + "\n"


def tabela_tentativas(tentativas: list[modelo.Tentativa], escolhida: modelo.Tentativa, n: int = 15) -> str:
    linhas = [
        "| # | Conjunto | Hiperparâmetros | AUC-PR fora da amostra | Desvio entre anos | AUC-PR no treino |",
        "|--:|---|---|---:|---:|---:|",
    ]
    ordem = sorted(tentativas, key=lambda t: -t.auc_pr_oof)[:n]
    for t in ordem:
        marca = " **(escolhida)**" if t.numero == escolhida.numero else ""
        linhas.append(
            f"| {t.numero} | {t.conjunto}{marca} | {_params(t.parametros)} | {t.auc_pr_oof:.4f} "
            f"| {t.auc_pr_desvio:.4f} | {t.auc_pr_treino:.4f} |"
        )
    return "\n".join(linhas) + "\n"


def _leitura(r: modelo.Resultado, diagnosticos: dict) -> str:
    m, c = r.teste["modelo"], r.teste["limiar_chuva"]
    texto = (
        f"**Leitura.** Com recall {_f(m['recall'], 2)}, a árvore marca {_f(m['alertas_pct'], 1)}% dos bairro-dias; "
        f"o limiar de chuva, com recall {_f(c['recall'], 2)}, marca {_f(c['alertas_pct'], 1)}% (praticamente todo "
        "dia com alguma chuva). A árvore concentra melhor os avisos, mas o critério combinado antes de abrir o "
        "teste é a AUC-PR"
    )
    texto += (
        ", e por ele a árvore " + ("supera" if r.publicavel else "não supera") + " a referência com folga."
    )
    if diagnosticos:
        sim = [k for k, d in diagnosticos.items() if d.publicavel]
        nao = [k for k, d in diagnosticos.items() if not d.publicavel]
        texto += (
            f" Nos diagnósticos, passaria em: {', '.join(sim) or 'nenhum'}; não passaria em: "
            f"{', '.join(nao) or 'nenhum'}. Uma conclusão que muda com o período ou com o rótulo indica sinal "
            "instável; por isso vale a configuração principal, decidida antes de ver o teste."
        )
    return texto


def montar(estudo) -> str:
    r: modelo.Resultado = estudo.resultado
    art: modelo.Artefato = estudo.artefato
    p = r.perfil
    attrs = estudo.rotulos.attrs
    h = estudo.harmonicos
    decisao = (
        "**Publicável como experimental**: passou nos critérios abaixo."
        if r.publicavel
        else f"**Não publicar no produto** (`disponivel: false`). Motivo: {r.motivo}"
    )
    sem_territorio = (
        ", ".join(f"{k} ({v})" for k, v in attrs.get("registros_sem_territorio", {}).items()) or "nenhum"
    )
    diag = []
    for nome, d in estudo.diagnosticos.items():
        diag.append(
            f"### {nome}\n\nTreino {d.perfil['treino']['periodo']} ({d.perfil['treino']['positivos']} positivos), "
            f"teste {d.perfil['teste']['periodo']} ({d.perfil['teste']['positivos']} positivos). "
            f"Escolhida pela validação: `{d.escolhida.conjunto}`, {_params(d.escolhida.parametros)}. "
            f"Publicável: {'sim' if d.publicavel else 'não'}{' (' + d.motivo + ')' if d.motivo else ''}.\n\n"
            + tabela_teste(d.teste)
        )
    por_ano = ", ".join(
        f"{a}: {n}" for a, n in estudo.rotulos.groupby(estudo.rotulos["data"].dt.year).size().items()
    )
    leitura = _leitura(r, estudo.diagnosticos)
    regras = r.regras if len(r.regras) < 6000 else r.regras[:6000] + "\n... (cortado)"
    return (
        f"""# Risco de alagamento por bairro e dia (F6), estudo de ML

> **EXPERIMENTAL (RN-11).** Classe de risco, nunca probabilidade (RN-06). Gerado por
> `python -m climasense.ml alagamento` em {date.today().isoformat()}; modelo `v{art.versao}` treinado em
> {art.treinado_em}. Não edite à mão: rode o comando de novo.

## Decisão

{decisao}

Critérios (todos precisam valer): pelo menos {modelo.MIN_POSITIVOS_TREINO} bairro-dias positivos no treino e
{modelo.MIN_POSITIVOS_TESTE} no teste; recall da classe "alagou" no teste ≥ {modelo.MIN_RECALL_TESTE:.2f}; AUC-PR
no teste ≥ {modelo.MIN_GANHO_AUC_PR:.2f} × a melhor referência simples. Sem isso, a API devolve
`disponivel: false` com o motivo e o gatilho de estágio ignora este insumo; nenhum dado simulado é exibido
(RF-12.10).

## Dados

- **Rótulo** (real): conjunto `registro-de-atendimentos-da-defesa-civil` dos Dados Abertos do Recife (ODbL),
  {attrs.get("fonte")}. O conector `recife-alagamento` do ETL ainda não existe e `silver.ocorrencias` está
  vazia; o estudo baixa os CSVs para `tmp/alagamento/` (fora do Git), sem tocar no ETL nem no banco.
- {attrs.get("registros_lidos", 0):,} registros lidos (2014 em diante); {attrs.get("registros_alagamento", 0):,} são de
  alagamento pelo critério `evento` (ocorrência `Alagamentos`/`Imóveis Alagados`, ou solicitação
  `Vistoria Alagado`/`Vistoria Setor Alagado`/`Monitoramento Setor Alagado`). Registros cujo bairro não
  existe na base oficial (descartados): {sem_territorio}.
- **{len(estudo.rotulos)} bairro-dias com atendimento real**, de {estudo.rotulos["data"].min().date()} a
  {estudo.rotulos["data"].max().date()}, em {estudo.rotulos["data"].nunique()} dias distintos.
- A data da fonte é a da solicitação/vistoria, não a do alagamento. O rótulo do dia D é "houve atendimento
  no bairro entre D e D + {estudo.janela_dias}". Por isso o relatório mede também **atendimentos avisados**
  (houve aviso para o bairro em algum dia da janela antes do atendimento?), que não sofre essa inflação.
- **Chuva**: ERA5 horária por distrito; origem: {estudo.origem_chuva}. Somas diárias em hora do Recife; dia
  sem as 24 horas fica nulo (RN-01). O bairro herda a chuva do seu distrito (RN-07).
- **Maré**: o histórico do Open-Meteo Marine começa no fim de 2022. Ajuste harmônico ({len(h["componentes"])}
  componentes) na série real de {h["periodo"][0][:10]} a {h["periodo"][1][:10]}: R² = {h["r2"]:.3f},
  RMSE = {h["rmse_m"]:.3f} m. A maré de cada dia é a maré astronômica calculada (sem efeito de vento).
- Área e faixa hídrica por bairro **não entram**: a base territorial só tem geometria de distrito.

### Desequilíbrio de classes

| Período | Bairro-dias | Positivos | Taxa | Negativos por positivo | Dias com positivo | Bairros com positivo |
|---|---:|---:|---:|---:|---:|---:|
"""
        + "\n".join(
            f"| {nome} {p[k]['periodo']} | {p[k]['linhas']:,} | {p[k]['positivos']} | {p[k]['taxa_positivos_pct']:.3f}% "
            f"| {p[k]['razao_negativos_por_positivo']} | {p[k]['dias_com_ocorrencia']} | {p[k]['bairros_com_ocorrencia']} |"
            for nome, k in (("Total", "total"), ("Treino", "treino"), ("Teste", "teste"))
        )
        + f"""

Com menos de 1 positivo a cada centenas de linhas, acurácia não diz nada (prever "nunca alaga" acerta
mais de 99%). Usamos **recall** da classe "alagou" (o cliente prefere alerta falso a evento não avisado),
**precisão** e **AUC-PR** (área sob a curva precisão × recall; a de um classificador aleatório é a própria
taxa de positivos).

## Método

1. Atributos por bairro e dia: {", ".join(f"`{a}` ({NOMES[a]})" for a in NOMES)}. O histórico usa só dias
   anteriores ao dia avaliado.
2. **Validação temporal**: treino até {modelo.ANO_TESTE - 1}, teste em {modelo.ANO_TESTE} (nunca visto até o fim).
   Dentro do treino, janela crescente: para cada um dos últimos {modelo.N_FOLDS} anos, treina nos anteriores e
   valida nele. Nota = AUC-PR das pontuações fora da amostra de todos esses anos juntos.
3. Busca: 3 conjuntos de atributos × grade {modelo.GRADE} = {len(r.tentativas)} tentativas.
4. Limiares das classes, fixados nas pontuações fora da amostra do treino: `moderado` mantém recall
   {modelo.RECALL_MODERADO:.0%}, `alto` mantém {modelo.RECALL_ALTO:.0%}. A referência "limiar de chuva" usa o mesmo
   recall-alvo no treino ({r.limiar_chuva_mm:.1f} mm no dia).
5. `EstimadorReferencia` aplicado a cada distrito e dia do teste com a chuva REAL do dia como se fosse a
   previsão (vantagem para a regra), a maré calculada e o histórico de chuva anterior.

### Tentativas (15 melhores pela validação temporal)

{tabela_tentativas(r.tentativas, r.escolhida)}
Referências de uma coluna nos mesmos anos de validação (AUC-PR): {", ".join(f"{k} = {v:.4f}" for k, v in r.referencias_cv.items())}.

## Resultado no período de teste ({p["teste"]["periodo"][0]} a {p["teste"]["periodo"][1]})

Modelo escolhido: conjunto `{r.escolhida.conjunto}`, {_params(r.escolhida.parametros)}.

{tabela_teste(r.teste)}
{leitura}

Importância dos atributos: {", ".join(f"{NOMES.get(n, n)} {v:.2f}" for n, v in r.importancias)}.

### Regras da árvore (até a profundidade 4)

```
{regras}
```

## Diagnósticos (não mudam a escolha; só mostram a robustez da conclusão)

{chr(10).join(diag) if diag else "Não executados."}

## Saída no produto

`GET /api/v1/risco-alagamento?nivel=bairro` e `climasense.ml.alagamento.risco_por_territorio(db, agora)`:
classe `baixo`/`moderado`/`alto` por bairro para hoje e amanhã (vale a maior), ou `sem_dados` quando falta
chuva completa de algum dia da janela de 7 dias. Fatores em português: chuva do distrito, regras da árvore
que levaram à classe e histórico do bairro. Selo experimental sempre. Sem modelo publicado: `disponivel:
false`, motivo e lista vazia.

## Limitações

- O rótulo é um indicador indireto: atendimento da Defesa Civil não é medição de alagamento, e a
  intensidade do registro muda com a gestão e as campanhas (bairro-dias por ano: {por_ano}). Ausência
  de registro não prova que não alagou.
- Chuva de reanálise (ERA5, grade de ~25 km) num ponto por distrito: subestima chuva convectiva local.
- No produto, os últimos dias vêm da previsão quando a reanálise ainda não chegou (atraso de ~7 dias);
  o modelo foi treinado com reanálise.
- O modelo salvo é exatamente o validado (treinado até {modelo.ANO_TESTE - 1}); não foi re-treinado com o teste.

## Pendências

- Conector `recife-alagamento` no ETL (com a regra de critério deste estudo) e carga em `silver.ocorrencias`.
- Pluviômetros APAC/Cemaden (2022+) como atributo de chuva observada; tábua de maré da APAC/Marinha.
- Geometria de bairro para área e faixa hídrica; chamados de drenagem da EMLURB (156) como vulnerabilidade.
- Validar as classes com a equipe do Vigidesastres antes de qualquer uso operacional.
"""
    )


def gravar(estudo, pasta: Path | None = None) -> Path:
    pasta = Path(pasta) if pasta else PASTA_DOCS
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / "risco-alagamento.md"
    destino.write_text(montar(estudo), encoding="utf-8")
    r = estudo.resultado
    metricas = {
        "versao": estudo.artefato.versao,
        "publicavel": r.publicavel,
        "motivo": r.motivo,
        "perfil": r.perfil,
        "escolhida": {"conjunto": r.escolhida.conjunto, "parametros": r.escolhida.parametros},
        "limiares_recall": {"moderado": modelo.RECALL_MODERADO, "alto": modelo.RECALL_ALTO},
        "limiar_chuva_mm": r.limiar_chuva_mm,
        "teste": r.teste,
        "referencias_cv": r.referencias_cv,
        "tentativas": modelo.tentativas_dict(r.tentativas),
        "diagnosticos": {
            k: {"publicavel": d.publicavel, "motivo": d.motivo, "teste": d.teste}
            for k, d in estudo.diagnosticos.items()
        },
    }
    (pasta / "risco-alagamento-metricas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return destino
