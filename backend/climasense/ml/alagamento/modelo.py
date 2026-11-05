"""Treino e validação TEMPORAL do risco de alagamento por bairro e dia. Único modelo: árvore de decisão.

Método:
1. separa o período mais recente como TESTE (de `ANO_TESTE` em diante); ele só é usado no fim;
2. no treino, compara conjuntos de atributos e hiperparâmetros por validação temporal em janela crescente
   (para cada um dos últimos anos do treino: treina nos anos anteriores e valida nele). A nota é a AUC-PR
   das pontuações fora da amostra de todos os anos de validação juntos (classe rara: AUC-PR, não acurácia);
3. com essas pontuações fora da amostra, fixa os limiares das classes: `moderado` mantém o recall em
   `RECALL_MODERADO` (o cliente prefere alerta falso a evento não avisado) e `alto` em `RECALL_ALTO`;
4. treina no treino inteiro e mede no teste, junto com as referências (limiar de chuva escolhido no treino
   com o mesmo recall-alvo e a regra do `EstimadorReferencia`).

A pontuação da árvore é interna: nunca é exibida e não é probabilidade (RN-06). O produto só vê a classe.
"""

from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from sklearn.tree import DecisionTreeClassifier, export_text

from climasense.ml.alagamento.base import ATRIBUTOS

VERSAO = "0.1.0"
METODO = "arvore-decisao-temporal"
ANO_TESTE = 2024  # 2024 inteiro fica de fora até a avaliação final
N_FOLDS = 5
RECALL_MODERADO = 0.80
RECALL_ALTO = 0.40
CONJUNTOS = {
    "chuva": ["chuva_1d", "chuva_3d", "chuva_7d"],
    "chuva_mare_mes": ["chuva_1d", "chuva_3d", "chuva_7d", "mare_max_m", "mes"],
    "completo": list(ATRIBUTOS),
}
GRADE = {
    "max_depth": [3, 4, 5, 6, 8],
    "min_samples_leaf": [20, 100, 400],
    "class_weight": ["balanced", None],
}
# Critérios para o modelo poder ser exibido no produto (todos precisam valer).
MIN_POSITIVOS_TREINO = 100
MIN_POSITIVOS_TESTE = 30
MIN_GANHO_AUC_PR = 1.10  # AUC-PR do modelo ≥ 110% da melhor referência no teste
MIN_RECALL_TESTE = 0.60


def novo_modelo(**parametros) -> DecisionTreeClassifier:
    """Única fábrica de modelo: sempre DecisionTreeClassifier, sempre random_state=42."""
    return DecisionTreeClassifier(**{**parametros, "random_state": 42})


def pontuar(modelo: DecisionTreeClassifier, X: pd.DataFrame, colunas: list[str]) -> np.ndarray:
    return modelo.predict_proba(X[colunas])[:, 1]


def limiar_para_recall(y, pontuacao, alvo: float) -> float:
    """Maior limiar t tal que marcar `pontuacao >= t` ainda cobre `alvo` dos positivos."""
    positivos = np.sort(np.asarray(pontuacao, dtype=float)[np.asarray(y) == 1])[::-1]
    if len(positivos) == 0:
        return float("inf")
    k = max(int(np.ceil(alvo * len(positivos))), 1)
    return float(positivos[k - 1])


def eventos_avisados(teste: pd.DataFrame, alerta, janela_dias: int) -> dict:
    """Por atendimento real (bairro, dia r): houve aviso para aquele bairro em algum dia de [r - janela, r]?

    É a métrica que o cliente entende ("o evento foi avisado?"), sem a inflação do rótulo com janela.
    """
    if "registro" not in teste:
        return {}
    d = teste[["territorio_id", "data", "registro"]].assign(a=np.asarray(alerta).astype(int))
    d = d.sort_values(["territorio_id", "data"])
    d["avisado"] = d.groupby("territorio_id")["a"].transform(
        lambda s: s.rolling(janela_dias + 1, min_periods=1).max()
    )
    ev = d[d["registro"] == 1]
    dias = ev.groupby("data")["avisado"].max()
    return {
        "eventos": int(len(ev)),
        "eventos_avisados": int(ev["avisado"].sum()),
        "dias_com_atendimento": int(len(dias)),
        "dias_com_atendimento_avisados": int(dias.sum()),
    }


def metricas(y, alerta, pontuacao=None, teste: pd.DataFrame | None = None, janela_dias: int = 0) -> dict:
    y, alerta = np.asarray(y).astype(int), np.asarray(alerta).astype(bool)
    vp = int((alerta & (y == 1)).sum())
    fp = int((alerta & (y == 0)).sum())
    fn = int((~alerta & (y == 1)).sum())
    saida = {
        "recall": vp / (vp + fn) if vp + fn else None,
        "precisao": vp / (vp + fp) if vp + fp else None,
        "auc_pr": float(average_precision_score(y, pontuacao)) if pontuacao is not None and y.any() else None,
        "alertas_pct": float(alerta.mean() * 100) if len(alerta) else None,
        "vp": vp,
        "fp": fp,
        "fn": fn,
    }
    if teste is not None:
        saida.update(eventos_avisados(teste, alerta, janela_dias))
    return saida


@dataclass
class Tentativa:
    numero: int
    conjunto: str
    parametros: dict
    auc_pr_oof: float  # AUC-PR das pontuações fora da amostra (todos os anos de validação juntos)
    auc_pr_folds: list[float]
    auc_pr_desvio: float
    auc_pr_treino: float  # no próprio treino do último fold (lacuna = sobreajuste)


@dataclass
class Resultado:
    tentativas: list[Tentativa]
    escolhida: Tentativa
    referencias_cv: dict[str, float]
    limiares: dict
    limiar_chuva_mm: float
    teste: dict  # nome → métricas
    perfil: dict
    importancias: list[tuple[str, float]]
    regras: str
    modelo: DecisionTreeClassifier = field(repr=False)
    colunas: list[str] = field(default_factory=list)
    publicavel: bool = False
    motivo: str | None = None


def dividir(base: pd.DataFrame, ano_teste: int = ANO_TESTE) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = base.dropna(subset=ATRIBUTOS)
    return base[base["ano"] < ano_teste], base[base["ano"] >= ano_teste]


def folds_temporais(treino: pd.DataFrame, n: int = N_FOLDS) -> list[tuple[pd.Index, pd.Index]]:
    """Janela crescente: para cada um dos `n` últimos anos do treino, treina nos anteriores e valida nele."""
    anos = sorted(treino["ano"].unique())
    return [
        (treino.index[treino["ano"] < a], treino.index[treino["ano"] == a]) for a in anos[-n:] if a > anos[0]
    ]


def _validar(treino, folds, colunas, parametros) -> tuple[pd.Series, list[float], float]:
    fora, aucs, auc_treino = [], [], float("nan")
    for idx_tr, idx_va in folds:
        tr, va = treino.loc[idx_tr], treino.loc[idx_va]
        if not tr["alagou"].any():
            continue
        m = novo_modelo(**parametros).fit(tr[colunas], tr["alagou"])
        s = pd.Series(pontuar(m, va, colunas), index=va.index)
        fora.append(s)
        if va["alagou"].any():
            aucs.append(float(average_precision_score(va["alagou"], s)))
        auc_treino = float(average_precision_score(tr["alagou"], pontuar(m, tr, colunas)))
    return pd.concat(fora), aucs, auc_treino


def buscar(
    treino: pd.DataFrame, grade: dict | None = None, conjuntos: dict | None = None
) -> tuple[list[Tentativa], dict[int, pd.Series]]:
    grade, conjuntos = grade or GRADE, conjuntos or CONJUNTOS
    folds = folds_temporais(treino)
    tentativas, oof = [], {}
    chaves = list(grade)
    combinacoes = itertools.product(conjuntos, itertools.product(*(grade[k] for k in chaves)))
    for i, (nome, valores) in enumerate(combinacoes, start=1):
        p = dict(zip(chaves, valores, strict=True))
        s, aucs, auc_treino = _validar(treino, folds, conjuntos[nome], p)
        oof[i] = s
        nota = float(average_precision_score(treino.loc[s.index, "alagou"], s))
        tentativas.append(Tentativa(i, nome, p, nota, aucs, float(np.std(aucs)) if aucs else 0.0, auc_treino))
    return tentativas, oof


def referencias_cv(treino: pd.DataFrame) -> dict[str, float]:
    """AUC-PR fora da amostra das referências de uma coluna só, nos mesmos anos de validação."""
    idx = pd.Index(np.concatenate([va for _, va in folds_temporais(treino)]))
    y = treino.loc[idx, "alagou"]
    return {c: float(average_precision_score(y, treino.loc[idx, c])) for c in ("chuva_1d", "chuva_3d")}


def escolher(tentativas: list[Tentativa]) -> Tentativa:
    """Maior AUC-PR fora da amostra; empate → menor desvio entre anos → árvore mais rasa."""
    return max(
        tentativas,
        key=lambda t: (
            round(t.auc_pr_oof, 4),
            -round(t.auc_pr_desvio, 4),
            -(t.parametros.get("max_depth") or 99),
        ),
    )


def classificar(pontuacao, limiares: dict) -> np.ndarray:
    pontuacao = np.asarray(pontuacao, dtype=float)
    return np.where(
        pontuacao >= limiares["alto"],
        "alto",
        np.where(pontuacao >= limiares["moderado"], "moderado", "baixo"),
    )


def perfil(base: pd.DataFrame, treino: pd.DataFrame, teste: pd.DataFrame) -> dict:
    def _p(df):
        pos = int(df["alagou"].sum())
        return {
            "linhas": int(len(df)),
            "positivos": pos,
            "taxa_positivos_pct": round(100 * pos / len(df), 4) if len(df) else None,
            "razao_negativos_por_positivo": round((len(df) - pos) / pos, 1) if pos else None,
            "dias_com_ocorrencia": int(df.loc[df["alagou"] == 1, "data"].nunique()),
            "bairros_com_ocorrencia": int(df.loc[df["alagou"] == 1, "territorio_id"].nunique()),
            "periodo": [str(df["data"].min().date()), str(df["data"].max().date())] if len(df) else None,
        }

    return {
        "total": _p(base.dropna(subset=ATRIBUTOS)),
        "treino": _p(treino),
        "teste": _p(teste),
        "linhas_sem_atributo": int(base[ATRIBUTOS].isna().any(axis=1).sum()),
    }


def avaliar_publicacao(perf: dict, teste: dict) -> tuple[bool, str | None]:
    n_tr, n_te = perf["treino"]["positivos"], perf["teste"]["positivos"]
    if n_tr < MIN_POSITIVOS_TREINO or n_te < MIN_POSITIVOS_TESTE:
        return False, (
            f"Ocorrências reais insuficientes (treino {n_tr}, teste {n_te}; mínimo "
            f"{MIN_POSITIVOS_TREINO} e {MIN_POSITIVOS_TESTE})."
        )
    m = teste["modelo"]
    refs = {
        k: v["auc_pr"] for k, v in teste.items() if not k.startswith("modelo") and v.get("auc_pr") is not None
    }
    melhor_nome, melhor = max(refs.items(), key=lambda kv: kv[1]) if refs else ("nenhuma", 0.0)
    if (m["recall"] or 0) < MIN_RECALL_TESTE:
        return False, (
            f"Recall no período de teste ({m['recall']:.2f}) abaixo do mínimo de {MIN_RECALL_TESTE:.2f}: "
            "deixaria eventos sem aviso."
        )
    if (m["auc_pr"] or 0) < MIN_GANHO_AUC_PR * melhor:
        return False, (
            f"O modelo não supera com folga a referência '{melhor_nome}' no período de teste "
            f"(AUC-PR {m['auc_pr']:.3f} contra {melhor:.3f}); a regra simples é preferível."
        )
    return True, None


def treinar(
    base: pd.DataFrame,
    referencia_teste: pd.Series | None = None,
    grade: dict | None = None,
    conjuntos: dict | None = None,
    ano_teste: int = ANO_TESTE,
    janela_dias: int = 0,
) -> Resultado:
    """`referencia_teste`: nível 0..3 do EstimadorReferencia por linha do teste (mesmo índice); nulo = sem dado."""
    conjuntos = conjuntos or CONJUNTOS
    treino, teste = dividir(base, ano_teste)
    perf = perfil(base, treino, teste)
    tentativas, oof = buscar(treino, grade, conjuntos)
    escolhida = escolher(tentativas)
    colunas = conjuntos[escolhida.conjunto]
    s_oof = oof[escolhida.numero]
    y_oof = treino.loc[s_oof.index, "alagou"].to_numpy()
    limiares = {
        "moderado": limiar_para_recall(y_oof, s_oof, RECALL_MODERADO),
        "alto": limiar_para_recall(y_oof, s_oof, RECALL_ALTO),
    }
    limiares["alto"] = max(limiares["alto"], limiares["moderado"])
    modelo = novo_modelo(**escolhida.parametros).fit(treino[colunas], treino["alagou"])

    # ---- único ponto em que o teste é usado ----
    s_teste = pontuar(modelo, teste, colunas)
    classes = classificar(s_teste, limiares)
    y = teste["alagou"].to_numpy()
    limiar_chuva = limiar_para_recall(treino["alagou"], treino["chuva_1d"], RECALL_MODERADO)
    j = janela_dias
    resultados = {
        "modelo": metricas(y, classes != "baixo", s_teste, teste, j),
        "modelo_alto": metricas(y, classes == "alto", None, teste, j),
        "limiar_chuva": metricas(
            y, teste["chuva_1d"].to_numpy() >= limiar_chuva, teste["chuva_1d"], teste, j
        ),
    }
    if referencia_teste is not None:
        ref = referencia_teste.reindex(teste.index)
        resultados["estimador_referencia"] = metricas(
            y, ref.fillna(0).to_numpy() >= 1, ref.fillna(-1), teste, j
        )
        resultados["estimador_referencia"]["sem_dados_pct"] = float(ref.isna().mean() * 100)
    publicavel, motivo = avaliar_publicacao(perf, resultados)
    importancias = sorted(
        zip(colunas, modelo.feature_importances_.round(4).tolist(), strict=True), key=lambda x: -x[1]
    )
    regras = export_text(modelo, feature_names=colunas, max_depth=4, decimals=1, show_weights=True)
    return Resultado(
        tentativas=tentativas,
        escolhida=escolhida,
        referencias_cv=referencias_cv(treino),
        limiares=limiares,
        limiar_chuva_mm=limiar_chuva,
        teste=resultados,
        perfil=perf,
        importancias=importancias,
        regras=regras,
        modelo=modelo,
        colunas=colunas,
        publicavel=publicavel,
        motivo=motivo,
    )


# ----------------------------------------------------------------------------- artefato salvo (joblib)
@dataclass
class Artefato:
    versao: str
    metodo: str
    treinado_em: str
    modelo: DecisionTreeClassifier
    atributos: list[str]
    limiares: dict
    mare_harmonicos: dict
    historico_bairros: dict[str, int]  # territorio_id → dias com atendimento de alagamento (período todo)
    inicio_historico: str
    fim_historico: str
    validacao: dict
    publicavel: bool
    motivo: str | None
    fonte_rotulo: str
    criterio_rotulo: str = "evento"


def montar_artefato(
    r: Resultado, base: pd.DataFrame, harmonicos: dict, fonte_rotulo: str, criterio: str = "evento"
) -> Artefato:
    """O modelo salvo é EXATAMENTE o validado (treinado só no período de treino)."""
    pos = base[base["alagou"] == 1]
    validacao = {
        "tipo": "temporal",
        "treino": r.perfil["treino"]["periodo"],
        "teste": r.perfil["teste"]["periodo"],
        "positivos_treino": r.perfil["treino"]["positivos"],
        "positivos_teste": r.perfil["teste"]["positivos"],
        "taxa_positivos_teste_pct": r.perfil["teste"]["taxa_positivos_pct"],
        "conjunto": r.escolhida.conjunto,
        "parametros": r.escolhida.parametros,
        "metricas_teste": r.teste,
        "recall_alvo_moderado": RECALL_MODERADO,
        "recall_alvo_alto": RECALL_ALTO,
    }
    return Artefato(
        versao=VERSAO,
        metodo=METODO,
        treinado_em=datetime.now(UTC).isoformat(timespec="seconds"),
        modelo=r.modelo,
        atributos=list(r.colunas),
        limiares=r.limiares,
        mare_harmonicos=harmonicos,
        historico_bairros={k: int(v) for k, v in pos.groupby("territorio_id").size().items()},
        inicio_historico=str(base["data"].min().date()),
        fim_historico=str(base["data"].max().date()),
        validacao=validacao,
        publicavel=r.publicavel,
        motivo=r.motivo,
        fonte_rotulo=fonte_rotulo,
        criterio_rotulo=criterio,
    )


def tentativas_dict(tentativas: list[Tentativa]) -> list[dict]:
    return [asdict(t) for t in tentativas]
