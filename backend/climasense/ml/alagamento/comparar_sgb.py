"""Experimento independente: árvore atual versus árvore com suscetibilidade à inundação do SGB.

Apenas arquivos locais em tmp/experimentos. Nenhum artefato operacional é
substituído e os critérios de publicação não são modificados.

IMPORTANTE: 2024 já foi consultado em experimentos anteriores; os números
neste período são exploratórios e NÃO são um novo holdout independente.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline

from climasense.config import RAIZ_REPOSITORIO
from climasense.ml.alagamento import estudo, modelo
from climasense.ml.alagamento.base import ATRIBUTOS
from climasense.ml.alagamento.sgb_inundacao import ATRIBUTOS_SGB, PASTA_RESULTADOS

GRADE = {"max_depth": 4, "min_samples_leaf": 20, "class_weight": "balanced"}
COLUNAS_SGB = list(ATRIBUTOS) + list(ATRIBUTOS_SGB)
DATA_INICIO = pd.Timestamp("2016-01-01")  # carta publicada em 2015


def ler_sgb(caminho: Path) -> pd.DataFrame:
    if not caminho.is_file():
        raise FileNotFoundError(f"Tabela SGB não encontrada: {caminho}. Execute primeiro sgb_inundacao.")
    tabela = pd.read_csv(caminho)
    obrigatorias = {"territorio_id", *ATRIBUTOS_SGB}
    if not obrigatorias.issubset(tabela.columns):
        raise ValueError(f"Colunas ausentes na tabela SGB: {sorted(obrigatorias - set(tabela.columns))}")
    if tabela.territorio_id.isna().any() or tabela.territorio_id.duplicated().any():
        raise ValueError("IDs de bairros ausentes ou duplicados no CSV do SGB.")
    if not tabela["sgb_sem_carta"].isin([0, 1]).all():
        raise ValueError("sgb_sem_carta precisa indicar 0 ou 1.")
    if not (tabela["sgb_sem_carta"] == 0).any():
        raise ValueError("Nenhum bairro possui carta do SGB; comparação não é informativa.")
    # Ausência de carta não pode ser convertida em suscetibilidade baixa (0).
    dados = tabela["sgb_sem_carta"] == 0
    for col in ATRIBUTOS_SGB[:-1]:
        if tabela.loc[dados, col].isna().any():
            raise ValueError(f"Dado ausente em bairro coberto na coluna {col}.")
        if not tabela.loc[dados, col].between(0, 1).all():
            raise ValueError(f"Fração SGB fora de [0, 1] na coluna {col}.")
        if tabela.loc[~dados, col].notna().any():
            raise ValueError(f"Bairro sem carta deve ter NaN, não zero, em {col}.")
    return tabela


def preparar_base(tabela_original: pd.DataFrame, sgb: pd.DataFrame) -> pd.DataFrame:
    """Comparação justa: mesmo conjunto de bairros/dias/positivos para A e B."""
    ids_base = set(tabela_original.territorio_id.unique())
    ids_sgb = set(sgb.territorio_id)
    if ids_base != ids_sgb:
        faltantes = sorted(ids_base - ids_sgb)
        extras = sorted(ids_sgb - ids_base)
        raise ValueError(f"IDs territoriais não coincidem: faltantes={faltantes[:8]}, extras={extras[:8]}")
    b = tabela_original[tabela_original.data >= DATA_INICIO].copy()
    if b.empty:
        raise RuntimeError("A base não possui observações de 2016 em diante.")
    merged = b.merge(sgb[["territorio_id", *ATRIBUTOS_SGB]], on="territorio_id", validate="many_to_one")
    merged.attrs["janela_rotulo_dias"] = tabela_original.attrs.get("janela_rotulo_dias", 0)
    return merged


def _avaliar(configuracao: pd.DataFrame, colunas: list[str], janela: int) -> dict:
    treino, teste = modelo.dividir(configuracao, modelo.ANO_TESTE, janela)
    folds = modelo.folds_temporais(treino)
    pontos: list[pd.Series] = []

    def pipeline():
        # Medianas ajustadas somente no treino de cada fold, evitando vazamento.
        # Indicador sgb_sem_carta conserva a ausência como informação própria.
        return make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            modelo.novo_modelo(**GRADE),
        )

    for idx_t, idx_v in folds:
        tr, va = treino.loc[idx_t], treino.loc[idx_v]
        if tr.empty or va.empty or not tr.alagou.any():
            continue
        estimador = pipeline().fit(tr[colunas], tr.alagou)
        pontos.append(pd.Series(estimador.predict_proba(va[colunas])[:, 1], index=va.index))
    if not pontos:
        raise RuntimeError("Sem folds temporais válidos para o experimento SGB.")
    oof = pd.concat(pontos).sort_index()
    limiares = {
        "moderado": modelo.limiar_para_recall(treino.loc[oof.index, "alagou"], oof, modelo.RECALL_MODERADO),
        "alto": modelo.limiar_para_recall(treino.loc[oof.index, "alagou"], oof, modelo.RECALL_ALTO),
    }
    limiares["alto"] = max(limiares.values())
    est_final = pipeline().fit(treino[colunas], treino.alagou)
    score = est_final.predict_proba(teste[colunas])[:, 1]
    classes = modelo.classificar(score, limiares)
    metrica = modelo.metricas(teste.alagou, classes != "baixo", score, teste, janela)
    arvore = est_final.named_steps["decisiontreeclassifier"]
    importancias = sorted(
        ((nome, round(float(v), 6)) for nome, v in zip(colunas, arvore.feature_importances_, strict=True)),
        key=lambda x: -x[1],
    )
    return {
        "metricas_teste_exploratorio": metrica,
        "auc_pr_oof_treino": float(average_precision_score(treino.loc[oof.index, "alagou"], oof)),
        "linhas_treino": len(treino),
        "linhas_teste": len(teste),
        "positivos_treino": int(treino.alagou.sum()),
        "positivos_teste": int(teste.alagou.sum()),
        "importancias": importancias,
        "limiares_internos": limiares,
    }


def comparar(base: pd.DataFrame, sgb: pd.DataFrame) -> dict:
    total_sgb = len(sgb)
    b = preparar_base(base, sgb)
    _, teste = modelo.dividir(b, modelo.ANO_TESTE, base.attrs.get("janela_rotulo_dias", 0))
    if teste.empty:
        raise RuntimeError("Sem dados de teste temporal disponíveis após 2016.")
    janela = b.attrs.get("janela_rotulo_dias", 0)
    resultado_original = _avaliar(b, list(ATRIBUTOS), janela)
    resultado_sgb = _avaliar(b, COLUNAS_SGB, janela)
    treino, _ = modelo.dividir(b, modelo.ANO_TESTE, janela)
    limite = modelo.limiar_para_recall(
        treino.alagou,
        treino.chuva_1d,
        modelo.RECALL_MODERADO,
    )
    limiar_metrica = modelo.metricas(
        teste.alagou,
        teste.chuva_1d.to_numpy() >= limite,
        teste.chuva_1d.to_numpy(),
        teste,
        janela,
    )
    return {
        "gerado_em": datetime.now(UTC).isoformat(),
        "status": "PESQUISA_LOCAL_NAO_VALIDADA",
        "features_originais": list(ATRIBUTOS),
        "features_novas": list(ATRIBUTOS_SGB),
        "hiperparametros_fixos": GRADE,
        "periodo_minimo": str(DATA_INICIO.date()),
        "periodo_teste_exploratorio": [str(teste.data.min().date()), str(teste.data.max().date())],
        "bairros_total_sgb": total_sgb,
        "bairros_com_carta": int((sgb.sgb_sem_carta == 0).sum()),
        "modelo_original_mesma_amostra": resultado_original,
        "modelo_com_sgb_mesma_amostra": resultado_sgb,
        "referencia_chuva_mesma_amostra": limiar_metrica,
        "observacoes": [
            "A carta é datada de 2015; a análise foi limitada a 2016 em diante.",
            "A ausência de carta é mantida distinta de suscetibilidade baixa.",
            "Imputação ajustada apenas em treino/fold; não utiliza rótulos do teste.",
            "2024 já foi consultado para outros experimentos: não é holdout independente.",
            "Não substitui o modelo 0.2.0, não salva joblib e não altera o gate científico.",
            "Suscetibilidade não é probabilidade, nem risco operacional de alagamento.",
        ],
    }


def executar(*, arquivo_sgb: Path, usar_banco: bool = True) -> dict:
    sgb = ler_sgb(arquivo_sgb)
    # Reutiliza o ETL retrospectivo existente, sem persistir inferências.
    e = estudo.executar(
        usar_banco=usar_banco,
        grade={chave: [valor] for chave, valor in GRADE.items()},
        conjuntos={"completo": list(ATRIBUTOS)},
        diagnosticos=False,
    )
    return comparar(e.base, sgb)


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=PASTA_RESULTADOS / "sgb_inundacao_por_bairro.csv")
    p.add_argument(
        "--sem-banco",
        action="store_true",
        help="Chuva histórica somente via API de arquivo Open-Meteo",
    )
    args = p.parse_args()
    r = executar(arquivo_sgb=args.csv, usar_banco=not args.sem_banco)
    destino = RAIZ_REPOSITORIO / "tmp" / "experimentos" / "comparacao_sgb.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("Relatório experimental:", destino)
    for chave in (
        "modelo_original_mesma_amostra",
        "modelo_com_sgb_mesma_amostra",
        "referencia_chuva_mesma_amostra",
    ):
        obj = r[chave]
        print(chave, "AUC-PR:", obj.get("metricas_teste_exploratorio", obj)["auc_pr"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
