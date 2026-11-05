"""Uso do modelo no produto: classe de risco por bairro, com fatores em português. EXPERIMENTAL (RN-11).

- Lê o modelo salvo (joblib); nunca treina na requisição.
- Se não há modelo ou ele não passou nos critérios da validação temporal, nada é publicado (RF-12.10):
  `risco_por_territorio` devolve `{}` e o payload da API traz `disponivel: false` com o motivo.
- Classes: `baixo`, `moderado`, `alto` e `sem_dados` (faltou chuva de algum dia da janela, RN-01).
  Nunca "% de chance" (RN-06): a pontuação interna da árvore não sai daqui.
- A chuva é do distrito (ponto representativo); o bairro herda a do seu distrito (RN-07).
- Dias avaliados: hoje e amanhã (hora do Recife). Vale a maior classe, e o fator diz qual dia pesou.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.ml.alagamento import armazenamento
from climasense.ml.alagamento.base import NOMES
from climasense.ml.alagamento.clima import FUSO_RECIFE, mare_max_diaria
from climasense.ml.alagamento.modelo import Artefato, classificar

FONTE_HISTORICO = "open-meteo-historico"
FONTE_PREVISAO = "open-meteo-previsao"
FONTE_ROTULO = "recife-alagamento"
ORDEM = {"sem_dados": -1, "baixo": 0, "moderado": 1, "alto": 2}
AVISO_EXPERIMENTAL = (
    "Experimental (RN-11): modelo de árvore de decisão validado no passado, não é previsão oficial. "
    "Classe de risco, nunca probabilidade (RN-06). Confira na APAC e no Cemaden."
)
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]  # fmt: skip


def _num(v: float, casas: int = 1) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def hoje_recife(agora: datetime) -> date:
    """Data local do Recife (UTC-3). `agora` sem fuso é tratado como UTC."""
    if agora.tzinfo is not None:
        agora = agora.astimezone(UTC).replace(tzinfo=None)
    return (agora + FUSO_RECIFE).date()


# ----------------------------------------------------------------------------- insumos do banco
def chuva_recente(db: Session, inicio: date, fim: date) -> pd.DataFrame:
    """Chuva horária (hora local) por distrito: reanálise ERA5 quando existe; senão a previsão mais recente
    para aquela hora. Somente leitura."""
    a = datetime.combine(inicio, datetime.min.time()) - FUSO_RECIFE
    b = datetime.combine(fim + timedelta(days=1), datetime.min.time()) - FUSO_RECIFE
    linhas = db.execute(
        text(
            "select distinct on (territorio_id, observado_em, fonte_id) territorio_id, observado_em, valor, "
            "fonte_id from silver.observacoes where fonte_id = any(:fs) and observado_em >= :a "
            "and observado_em < :b and territorio_id like 'ds-%' "
            "order by territorio_id, observado_em, fonte_id, emitido_em desc nulls last"
        ),
        {"fs": [FONTE_HISTORICO, FONTE_PREVISAO], "a": a, "b": b},
    ).all()
    df = pd.DataFrame(linhas, columns=["territorio_id", "observado_em", "mm", "fonte_id"])
    if df.empty:
        return pd.DataFrame(columns=["territorio_id", "hora", "mm", "fonte_id"])
    df["hora"] = pd.to_datetime(df["observado_em"], utc=True).dt.tz_localize(None) + FUSO_RECIFE
    df["prioridade"] = (df["fonte_id"] != FONTE_HISTORICO).astype(int)  # ERA5 vence a previsão
    df = df.dropna(subset=["mm"]).sort_values("prioridade")
    return df.drop_duplicates(["territorio_id", "hora"])[["territorio_id", "hora", "mm", "fonte_id"]]


def bairros(db: Session) -> dict[str, tuple[str, str]]:
    """territorio_id → (nome, distrito_id)."""
    return {
        i: (nome, pai)
        for i, nome, pai in db.execute(
            text("select id, nome_exibicao, pai_id from app.territorios where tipo = 'bairro' order by id")
        )
    }


# ----------------------------------------------------------------------------- atributos e explicação
def chuva_por_dia(horaria: pd.DataFrame) -> dict[str, dict[date, tuple[float, bool]]]:
    """distrito → dia → (mm, usa_previsao). Só dias com as 24 horas."""
    saida: dict[str, dict[date, tuple[float, bool]]] = {}
    if horaria.empty:
        return saida
    h = horaria.assign(dia=horaria["hora"].dt.date, prev=horaria["fonte_id"] == FONTE_PREVISAO)
    g = h.groupby(["territorio_id", "dia"]).agg(mm=("mm", "sum"), n=("mm", "count"), prev=("prev", "any"))
    for (ds, dia), r in g.iterrows():
        if r["n"] >= 24:
            saida.setdefault(ds, {})[dia] = (float(r["mm"]), bool(r["prev"]))
    return saida


def atributos(
    art: Artefato, chuva_ds: dict[date, tuple[float, bool]], territorio_id: str, dia: date
) -> dict | None:
    janela = [dia - timedelta(days=k) for k in range(7)]
    if any(d not in chuva_ds for d in janela):
        return None
    mm = [chuva_ds[d][0] for d in janela]
    inicio = pd.Timestamp(art.inicio_historico)
    anos = max((pd.Timestamp(dia) - inicio).days / 365.25, 1.0)
    return {
        "chuva_1d": mm[0],
        "chuva_3d": sum(mm[:3]),
        "chuva_7d": sum(mm),
        "mare_max_m": float(mare_max_diaria(art.mare_harmonicos, [pd.Timestamp(dia)]).iloc[0]),
        "mes": dia.month,
        "hist_dias_ano": art.historico_bairros.get(territorio_id, 0) / anos,
        "_usa_previsao": any(chuva_ds[d][1] for d in janela[:3]),
    }


def _texto_condicao(atributo: str, minimo: float | None, maximo: float | None) -> str:
    nome = NOMES.get(atributo, atributo)
    if atributo.startswith("chuva"):
        f = lambda v: f"{_num(v)} mm"  # noqa: E731
    elif atributo == "mare_max_m":
        f = lambda v: f"{_num(v, 2)} m"  # noqa: E731
    elif atributo == "hist_dias_ano":
        f = lambda v: f"{_num(v)} dia(s) com atendimento por ano"  # noqa: E731
    elif atributo == "mes":
        de = int(np.floor(minimo)) + 1 if minimo is not None else 1
        ate = int(np.floor(maximo)) if maximo is not None else 12
        return f"Mês entre {MESES[de - 1]} e {MESES[ate - 1]}"
    else:
        f = lambda v: _num(v)  # noqa: E731
    if minimo is not None and maximo is not None:
        return f"{nome.capitalize()} entre {f(minimo)} e {f(maximo)}"
    if minimo is not None:
        return f"{nome.capitalize()} acima de {f(minimo)}"
    return f"{nome.capitalize()} até {f(maximo)}"


def caminho_da_decisao(art: Artefato, x: dict) -> list[str]:
    """As regras da árvore que levaram a esta classe, em português (limites por atributo)."""
    arvore = art.modelo.tree_
    X = pd.DataFrame([{c: x[c] for c in art.atributos}])
    nos = art.modelo.decision_path(X).indices
    limites: dict[str, list[float | None]] = {}
    for no in nos:
        if arvore.children_left[no] == arvore.children_right[no]:
            continue
        atributo = art.atributos[arvore.feature[no]]
        limiar = float(arvore.threshold[no])
        mn, mx = limites.setdefault(atributo, [None, None])
        if X.iloc[0][atributo] <= limiar:
            limites[atributo][1] = limiar if mx is None else min(mx, limiar)
        else:
            limites[atributo][0] = limiar if mn is None else max(mn, limiar)
    return [_texto_condicao(a, mn, mx) for a, (mn, mx) in limites.items()]


def _fatores(art: Artefato, x: dict, dia: date, hoje: date, distrito: str) -> list[str]:
    quando = "hoje" if dia == hoje else "amanhã"
    origem = "inclui previsão" if x["_usa_previsao"] else "reanálise ERA5"
    fatores = [
        f"Dia que pesou: {quando} ({dia.strftime('%d/%m')}).",
        f"Chuva no distrito {distrito} ({origem}): {_num(x['chuva_1d'])} mm no dia, "
        f"{_num(x['chuva_3d'])} mm em 3 dias, {_num(x['chuva_7d'])} mm em 7 dias. O bairro herda a chuva do "
        "distrito.",
    ]
    fatores += [f"Regra do modelo: {c}." for c in caminho_da_decisao(art, x)]
    n = art.historico_bairros.get(x["_territorio_id"], 0)
    fatores.append(
        f"Histórico: {n} dia(s) com atendimento de alagamento da Defesa Civil entre "
        f"{art.inicio_historico[:4]} e {art.fim_historico[:4]}."
    )
    return fatores


# ----------------------------------------------------------------------------- API do módulo
def risco_por_territorio(db: Session, agora: datetime, artefato: Artefato | None = None) -> dict[str, dict]:
    """territorio_id (bairro) → {classe, fatores}. `{}` quando o modelo não está publicado (RF-12.10)."""
    art = artefato if artefato is not None else armazenamento.carregar_em_cache()
    if art is None or not art.publicavel:
        return {}
    hoje = hoje_recife(agora)
    dias = [hoje, hoje + timedelta(days=1)]
    chuva = chuva_por_dia(chuva_recente(db, hoje - timedelta(days=6), hoje + timedelta(days=1)))
    saida: dict[str, dict] = {}
    for territorio_id, (_, distrito) in bairros(db).items():
        candidatos = []
        for dia in dias:
            x = atributos(art, chuva.get(distrito, {}), territorio_id, dia)
            if x is None:
                continue
            x["_territorio_id"] = territorio_id
            score = art.modelo.predict_proba(pd.DataFrame([{c: x[c] for c in art.atributos}]))[:, 1]
            candidatos.append((str(classificar(score, art.limiares)[0]), dia, x))
        if not candidatos:
            saida[territorio_id] = {
                "classe": "sem_dados",
                "fatores": [
                    f"Falta chuva completa (horária) do distrito {distrito} em algum dos últimos 7 dias ou na "
                    "previsão: sem esse insumo o modelo não classifica (dado ausente não é risco baixo)."
                ],
            }
            continue
        classe, dia, x = max(candidatos, key=lambda c: (ORDEM[c[0]], c[1] == hoje))
        saida[territorio_id] = {"classe": classe, "fatores": _fatores(art, x, dia, hoje, distrito)}
    return saida


def descricao_modelo(art: Artefato | None) -> dict | None:
    if art is None:
        return None
    return {
        "versao": art.versao,
        "metodo": art.metodo,
        "treinado_em": art.treinado_em,
        "experimental": True,
        "validacao": art.validacao,
    }


def payload(db: Session, agora: datetime, nivel: str = "bairro") -> dict:
    """Formato do contrato `GET /risco-alagamento` (specs/foco-chuvas.md §4)."""
    art = armazenamento.carregar_em_cache()
    if art is None:
        return {
            "disponivel": False,
            "motivo": "Modelo ainda não treinado neste ambiente (rode `python -m climasense.ml alagamento`).",
            "modelo": None,
            "itens": [],
        }
    if not art.publicavel:
        return {"disponivel": False, "motivo": art.motivo, "modelo": descricao_modelo(art), "itens": []}
    riscos = risco_por_territorio(db, agora, art)
    if nivel == "distrito":
        riscos = por_distrito(riscos, bairros(db))
    itens = [{"territorio_id": t, **r} for t, r in sorted(riscos.items())]
    return {"disponivel": True, "motivo": None, "modelo": descricao_modelo(art), "itens": itens}


def por_distrito(riscos: dict[str, dict], mapa: dict[str, tuple[str, str]]) -> dict[str, dict]:
    """Distrito recebe a maior classe entre os seus bairros e diz quais bairros a puxaram."""
    grupos: dict[str, list[tuple[str, dict]]] = {}
    for t, r in riscos.items():
        nome, ds = mapa.get(t, (t, None))
        if ds:
            grupos.setdefault(ds, []).append((nome, r))
    saida = {}
    for ds, itens in grupos.items():
        maior = max(itens, key=lambda i: ORDEM[i[1]["classe"]])[1]["classe"]
        nomes = sorted(n for n, r in itens if r["classe"] == maior)
        saida[ds] = {
            "classe": maior,
            "fatores": [
                f"Maior classe entre os bairros do distrito: {', '.join(nomes[:8])}"
                + (f" e mais {len(nomes) - 8}" if len(nomes) > 8 else "")
                + "."
            ],
        }
    return saida
