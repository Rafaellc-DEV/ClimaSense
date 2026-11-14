"""Pesquisa local: picos de chuva em 1h, 3h e 6h versus as seis features originais.

Um pico de 3h/6h e a MAIOR soma de horas consecutivas em uma janela que
termina no dia D. A janela pode atravessar meia-noite, mas nunca utiliza
horas posteriores a D 23:00 (fuso America/Recife).

Este é um diagnóstico retrospectivo no fim do dia D, NÃO uma previsão
operacional emitida antes da chuva: o rótulo original abrange [D, D+3].
Não escreve em Neon/Atlas, não salva modelo e não altera o gate científico.
2024 já foi consultado: o teste de 2024 NÃO é um holdout independente.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from climasense.config import RAIZ_REPOSITORIO
from climasense.ml.alagamento import clima, estudo, modelo
from climasense.ml.alagamento.base import ATRIBUTOS

NOVAS_FEATURES = ("chuva_pico_1h", "chuva_pico_3h", "chuva_pico_6h")
GRADE_FIXA = {"max_depth": 4, "min_samples_leaf": 20, "class_weight": "balanced"}
DESTINO = RAIZ_REPOSITORIO / "tmp" / "experimentos" / "comparacao_chuva_intensa.json"


def picos_por_distrito_dia(horaria: pd.DataFrame) -> pd.DataFrame:
    """Máximo diário dos acumulados móveis, em mm, com 29 horas consecutivas completas.

    Exige D 00:00..23:00 e D-1 19:00..23:00 para não preencher lacunas com zero.
    Usar máximo de janela móvel (e NÃO soma de todos os valores do dia).
    A chuva horária deve estar no fuso local do Recife, com timestamps ingênuos.
    """
    colunas = ["territorio_id", "data", *NOVAS_FEATURES]
    if horaria.empty:
        return pd.DataFrame(columns=colunas)
    obrigatorias = {"territorio_id", "hora", "mm"}
    if not obrigatorias.issubset(horaria.columns):
        raise ValueError(f"Colunas horárias ausentes: {sorted(obrigatorias - set(horaria.columns))}")
    dados = horaria[["territorio_id", "hora", "mm"]].copy()
    dados["hora"] = pd.to_datetime(dados["hora"], errors="coerce")
    if dados["hora"].isna().any():
        raise ValueError("Há horários inválidos no histórico da chuva.")
    if dados["hora"].dt.tz is not None:
        raise ValueError("Horas devem estar no fuso local de Recife, sem tzinfo; normalizar antes de chamar.")
    if not (dados["hora"] == dados["hora"].dt.floor("h")).all():
        raise ValueError("Esperadas observações horárias exatas, sem minutos ou segundos.")
    dados["mm"] = pd.to_numeric(dados["mm"], errors="coerce")
    dados.loc[~np.isfinite(dados["mm"]) | (dados["mm"] < 0), "mm"] = np.nan
    dados = dados.drop_duplicates(["territorio_id", "hora"], keep="last")
    partes = []
    for distrito, grupo in dados.groupby("territorio_id", sort=True):
        # asfreq cria NaNs para buracos; janelas incompletas NÃO recebem zero artificial.
        s = grupo.sort_values("hora").set_index("hora")["mm"].asfreq("h")
        picos = pd.DataFrame(
            {
                NOVAS_FEATURES[0]: s,
                NOVAS_FEATURES[1]: s.rolling(3, min_periods=3).sum(),
                NOVAS_FEATURES[2]: s.rolling(6, min_periods=6).sum(),
            }
        )
        diarios = picos.resample("D").max()
        # Exige TODAS as 29 horas (5 anteriores + 24 de D) para comparar
        # dias com os mesmos critérios de disponibilidade de dados.
        ultimas_29 = s.notna().astype(int).rolling(29, min_periods=29).sum().eq(29)
        completo = (
            ultimas_29[ultimas_29.index.hour == 23]
            .resample("D")
            .last()
            .reindex(diarios.index, fill_value=False)
            .fillna(False)
            .astype(bool)
        )
        diarios.loc[~completo, list(NOVAS_FEATURES)] = np.nan
        diarios = diarios.rename_axis("data").reset_index()
        diarios.insert(0, "territorio_id", distrito)
        partes.append(diarios[colunas])
    return pd.concat(partes, ignore_index=True)


def preparar_mesma_amostra(base: pd.DataFrame, picos: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Cruza distrito+dia e elimina linhas incompletas para AMBOS os modelos.

    Evita o erro de atribuir ganho de AUC-PR a diferenças de amostragem.
    """
    obrigatorias = {"territorio_id", "data", "distrito_id", "alagou", *ATRIBUTOS}
    if not obrigatorias.issubset(base.columns):
        raise ValueError(f"Colunas de treino ausentes: {sorted(obrigatorias - set(base.columns))}")
    if picos.duplicated(["territorio_id", "data"]).any():
        raise ValueError("Picos contêm distritos/datas duplicados.")
    b = base.merge(
        picos.rename(columns={"territorio_id": "distrito_id"}),
        on=["distrito_id", "data"],
        how="left",
        validate="many_to_one",
    )
    original = int(b[ATRIBUTOS].notna().all(axis=1).sum())
    junto = b.dropna(subset=[*ATRIBUTOS, *NOVAS_FEATURES]).copy()
    junto.attrs["janela_rotulo_dias"] = base.attrs.get("janela_rotulo_dias", 0)
    if junto.empty:
        raise RuntimeError("Nenhuma linha completa com chuva horária e atributos originais.")
    qualidade = {
        "linhas_base": int(len(base)),
        "linhas_originais_completas": original,
        "linhas_comuns_completas": int(len(junto)),
        "linhas_removidas_por_picos_ausentes": original - int(len(junto)),
        "cobertura_pct_dentre_originais": round(100 * len(junto) / original, 3) if original else 0,
        "distritos_com_picos": int(
            picos.loc[picos[list(NOVAS_FEATURES)].notna().all(axis=1), "territorio_id"].nunique()
        ),
        "dias_com_picos": int(picos.loc[picos[list(NOVAS_FEATURES)].notna().all(axis=1), "data"].nunique()),
    }
    return junto, qualidade


def _avaliar(b: pd.DataFrame, colunas: list[str], janela: int) -> dict:
    treino, teste = modelo.dividir(b, modelo.ANO_TESTE, janela)
    if treino.empty or teste.empty or not treino.alagou.any() or not teste.alagou.any():
        raise RuntimeError("Treino ou teste temporal está vazio ou sem positivos.")
    fora = []
    folds_utilizados = []
    for idx_t, idx_v in modelo.folds_temporais(treino):
        tr, va = treino.loc[idx_t], treino.loc[idx_v]
        if tr.empty or va.empty or not tr.alagou.any():
            continue
        m = modelo.novo_modelo(**GRADE_FIXA).fit(tr[colunas], tr.alagou)
        fora.append(pd.Series(m.predict_proba(va[colunas])[:, 1], index=va.index))
        folds_utilizados.append(int(va.ano.iloc[0]))
    if not fora:
        raise RuntimeError("Não há folds temporais válidos para avaliação.")
    scores_oof = pd.concat(fora).sort_index()
    y_oof = treino.loc[scores_oof.index, "alagou"]
    limiares = {
        "moderado": modelo.limiar_para_recall(y_oof, scores_oof, modelo.RECALL_MODERADO),
        "alto": modelo.limiar_para_recall(y_oof, scores_oof, modelo.RECALL_ALTO),
    }
    limiares["alto"] = max(limiares["alto"], limiares["moderado"])
    final = modelo.novo_modelo(**GRADE_FIXA).fit(treino[colunas], treino.alagou)
    scores = final.predict_proba(teste[colunas])[:, 1]
    alertas = modelo.classificar(scores, limiares) != "baixo"
    metrics = modelo.metricas(teste.alagou, alertas, scores, teste, janela)
    imp = sorted(
        ((nome, round(float(v), 6)) for nome, v in zip(colunas, final.feature_importances_, strict=True)),
        key=lambda item: -item[1],
    )
    # Diagnóstico de ranking, NÃO outra métrica para aprovar o modelo.
    topk = {}
    for k in (10, 20):
        s = teste[["data", "alagou"]].copy()
        s["score"] = scores
        s["selecionado"] = s.groupby("data")["score"].rank(method="first", ascending=False) <= k
        p = int((s.selecionado & (s.alagou == 1)).sum())
        total = int(s.alagou.sum())
        topk[str(k)] = {
            "positivos_bairro_dia_capturados": p,
            "positivos_bairro_dia_total": total,
            "cobertura_pct": round(p / total * 100, 2) if total else None,
        }
    return {
        "auc_pr_oof_treino": float(average_precision_score(y_oof, scores_oof)),
        "metricas_teste_exploratorio": metrics,
        "importancias": imp,
        "limiares_internos": limiares,
        "folds_validacao": folds_utilizados,
        "linhas_treino": int(len(treino)),
        "linhas_teste": int(len(teste)),
        "positivos_treino": int(treino.alagou.sum()),
        "positivos_teste": int(teste.alagou.sum()),
        "topk_exploratorio": topk,
    }


def comparar(base: pd.DataFrame, horaria: pd.DataFrame) -> dict:
    picos = picos_por_distrito_dia(horaria)
    b, qualidade = preparar_mesma_amostra(base, picos)
    janela = b.attrs["janela_rotulo_dias"]
    original = _avaliar(b, list(ATRIBUTOS), janela)
    intensos = _avaliar(b, [*ATRIBUTOS, *NOVAS_FEATURES], janela)
    treino, teste = modelo.dividir(b, modelo.ANO_TESTE, janela)
    # Mesma amostra e referência diária, com limiar definido apenas no treino.
    limiar_chuva = modelo.limiar_para_recall(treino.alagou, treino.chuva_1d, modelo.RECALL_MODERADO)
    refer = modelo.metricas(
        teste.alagou,
        teste.chuva_1d.to_numpy() >= limiar_chuva,
        teste.chuva_1d.to_numpy(),
        teste,
        janela,
    )
    return {
        "gerado_em": datetime.now(UTC).isoformat(),
        "status": "PESQUISA_LOCAL_NAO_VALIDADA",
        "features_originais": list(ATRIBUTOS),
        "features_novas": list(NOVAS_FEATURES),
        "configuracao_fixa": GRADE_FIXA,
        "definicao_feature": "máximo dos totais móveis de 1, 3 e 6h, janelas encerradas em D; mm",
        "janela_rotulo_dias": janela,
        "periodo_teste_exploratorio": [str(teste.data.min().date()), str(teste.data.max().date())],
        "qualidade_dados": qualidade,
        "modelo_original_mesma_amostra": original,
        "modelo_com_picos_mesma_amostra": intensos,
        "referencia_chuva_1d_mesma_amostra": refer,
        "observacoes": [
            "Chuva horária é reanálise/observação retrospectiva; não representa a previsão que existia na véspera.",
            "Atributos de D exigem dia D completo; rótulo atual inclui atendimentos em D..D+3: NÃO é previsão prospectiva.",
            "Ausência de horas nunca é preenchida com 0; dias com menos de 29h consecutivas não são comparados.",
            "Ambos os classificadores foram avaliados na MESMA amostra, com mesmo modelo e hiperparâmetros.",
            "2024 foi consultado em experimentos anteriores: não é holdout independente; não aprovar produção.",
            "Não grava bancos, não troca artefato joblib, não altera mapas nem gate científico.",
        ],
    }


def executar(*, usar_banco: bool = True) -> dict:
    # Reutiliza o estudo existente. Acesso ao Postgres é exclusivamente leitura.
    engine = estudo._engine_ou_nada() if usar_banco else None
    e = estudo.executar(
        engine=engine,
        usar_banco=usar_banco,
        grade={chave: [valor] for chave, valor in GRADE_FIXA.items()},
        conjuntos={"completo": list(ATRIBUTOS)},
        diagnosticos=False,
    )
    inicio = estudo.INICIO - timedelta(days=8)
    fim = e.base.data.max().date()
    horaria = clima.chuva_horaria(inicio, fim, engine=engine)
    return comparar(e.base, horaria)


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--sem-banco", action="store_true", help="Usar somente o cache e a API histórica Open-Meteo"
    )
    args = p.parse_args()
    r = executar(usar_banco=not args.sem_banco)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("Relatório experimental:", DESTINO)
    print("Cobertura da amostra original: ", r["qualidade_dados"]["cobertura_pct_dentre_originais"], "%")
    for chave in ("modelo_original_mesma_amostra", "modelo_com_picos_mesma_amostra"):
        m = r[chave]["metricas_teste_exploratorio"]
        print(
            chave, "AUC-PR:", m["auc_pr"], "recall:", m["recall"], "precisao:", m["precisao"], "FP:", m["fp"]
        )
    print("referencia_chuva_1d_mesma_amostra AUC-PR:", r["referencia_chuva_1d_mesma_amostra"]["auc_pr"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
