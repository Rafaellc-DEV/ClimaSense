"""Pesquisa isolada: compara 6 features originais e distrito sanitário (8 categorias oficiais).

Não altera o modelo operacional; não persiste no Neon/Atlas. Mesma separação temporal,
mesmo conjunto de teste, mesmo modelo e hiperparâmetros. Distrito é proxy geográfica,
não suscetibilidade hidrológica. Comparação exploratória, sem seleção no teste.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd
from sklearn.metrics import average_precision_score

from climasense.config import RAIZ_REPOSITORIO
from climasense.ml.alagamento import estudo, modelo
from climasense.ml.alagamento.base import ATRIBUTOS

GRADE_FIXA = {"max_depth": [4], "min_samples_leaf": [20], "class_weight": ["balanced"]}


def executar(*, usar_banco: bool = True) -> dict:
    e = estudo.executar(
        usar_banco=usar_banco,
        grade=GRADE_FIXA,
        conjuntos={"completo": list(ATRIBUTOS)},
        diagnosticos=False,
    )
    treino, teste = modelo.dividir(e.base, modelo.ANO_TESTE, e.janela_dias)
    # Codificação só das categorias observadas no TREINO, sem olhar rótulos do teste.
    dummies = pd.get_dummies(treino["distrito_id"], prefix="ds", dtype=int)
    nomes_dummy = list(dummies.columns)
    extra_treino = treino[list(ATRIBUTOS)].join(dummies)
    extra_teste = teste[list(ATRIBUTOS)].join(
        pd.get_dummies(teste["distrito_id"], prefix="ds", dtype=int).reindex(
            columns=nomes_dummy, fill_value=0
        )
    )
    colunas = list(ATRIBUTOS) + nomes_dummy
    oof = []
    for idx_treino, idx_validacao in modelo.folds_temporais(treino):
        f = modelo.novo_modelo(max_depth=4, min_samples_leaf=20, class_weight="balanced")
        f.fit(extra_treino.loc[idx_treino, colunas], treino.loc[idx_treino, "alagou"])
        oof.append(
            pd.Series(f.predict_proba(extra_treino.loc[idx_validacao, colunas])[:, 1], index=idx_validacao)
        )
    if not oof:
        raise RuntimeError("Sem folds temporais suficientes para comparação.")
    pontuacoes_oof = pd.concat(oof)
    limiares = {
        "moderado": modelo.limiar_para_recall(
            treino.loc[pontuacoes_oof.index, "alagou"], pontuacoes_oof, modelo.RECALL_MODERADO
        ),
        "alto": modelo.limiar_para_recall(
            treino.loc[pontuacoes_oof.index, "alagou"], pontuacoes_oof, modelo.RECALL_ALTO
        ),
    }
    limiares["alto"] = max(limiares["alto"], limiares["moderado"])
    f_final = modelo.novo_modelo(max_depth=4, min_samples_leaf=20, class_weight="balanced")
    f_final.fit(extra_treino[colunas], treino["alagou"])
    score_teste = f_final.predict_proba(extra_teste[colunas])[:, 1]
    classes = modelo.classificar(score_teste, limiares)
    resultado_territorial = modelo.metricas(
        teste["alagou"], classes != "baixo", score_teste, teste, e.janela_dias
    )
    anterior = e.resultado.teste
    return {
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "configuracao": GRADE_FIXA,
        "periodo_treino": e.resultado.perfil["treino"]["periodo"],
        "periodo_teste": e.resultado.perfil["teste"]["periodo"],
        "novas_colunas": nomes_dummy,
        "metrica_oof_territorial": float(
            average_precision_score(treino.loc[pontuacoes_oof.index, "alagou"], pontuacoes_oof)
        ),
        "modelo_original": anterior["modelo"],
        "modelo_com_distrito": resultado_territorial,
        "melhor_referencia": max(
            (v for k, v in anterior.items() if not k.startswith("modelo") and v.get("auc_pr") is not None),
            key=lambda v: v["auc_pr"],
        ),
        "observacoes": [
            "Distrito sanitário é variável territorial categórica; não equivale a risco físico ou suscetibilidade.",
            "Resultado exploratório com hiperparâmetros fixados previamente; não altera modelo operacional.",
            "Dados retrospectivos podem não representar a qualidade de uma previsão emitida antes do evento.",
            "Não usar o conjunto de teste para ajustar variáveis ou hiperparâmetros; novos experimentos requerem holdout futuro.",
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sem-banco", action="store_true")
    args = parser.parse_args()
    r = executar(usar_banco=not args.sem_banco)
    destino = RAIZ_REPOSITORIO / "tmp" / "experimentos" / "comparacao-territorial.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("Resultados de pesquisa (sem alterar o modelo operacional):", destino)
    for chave in ("modelo_original", "modelo_com_distrito"):
        print(
            chave,
            "AUC-PR:",
            r[chave]["auc_pr"],
            "recall:",
            r[chave]["recall"],
            "precisao:",
            r[chave]["precisao"],
        )
    print("Referência AUC-PR:", r["melhor_referencia"]["auc_pr"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
