"""Arboviroses como CONTEXTO do simulador de cenário (RF-23 a RF-28, RN-01, RN-02, RN-06, RN-11, RN-13).

Dengue, chikungunya e zika por distrito: casos recentes notificados, nunca previsão causal da chuva. O que existe:
- semanal: só do município (InfoDengue, série única do Recife), igual em todos os distritos do bloco;
- anual: confirmados no último ano publicado por distrito (Prefeitura do Recife, soma dos bairros; casos sem bairro
  identificado não entram);
- zika: não integrado (a série do InfoDengue para o Recife parou em 2024-SE07), sempre "Dados insuficientes".
A classe de impacto é relativa entre os distritos com casos (terços do total anual confirmado): ordem de atenção, nunca
probabilidade nem percentual. Contagens de 1 a 4 saem nulas e marcadas como suprimidas (RN-13).
"""

from __future__ import annotations

from datetime import datetime
from math import ceil

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio.supressao import suprimir
from climasense.servicos import fontes as servico_fontes
from climasense.servicos import saude_agravos as saude

FONTE_SEMANAL = "infodengue"
FONTE_ANUAL = "recife-arboviroses"
SEMANAS_SERIE = 8
MINIMO = 5
AGRAVOS = (("dengue", "Dengue"), ("chikungunya", "Chikungunya"), ("zika", "Zika"))
RANK = {"baixa": 1, "media": 2, "alta": 3}

AVISO = (
    "Experimental. Arboviroses são CONTEXTO: casos recentes notificados, não previsão causal da chuva; o "
    "simulador não estima casos futuros. A série semanal é do município (InfoDengue); o total por distrito é o "
    "de confirmados no último ano publicado (Prefeitura do Recife), sem os casos sem bairro identificado. "
    "A classe compara os distritos entre si e não é probabilidade."
)
MOTIVO_ZIKA = (
    "Dados insuficientes: zika não está integrado (fonte infodengue: a série do Recife parou em 2024-SE07)."
)


def _classes(totais: dict[str, int]) -> dict[str, str]:
    """Terços do total anual entre os distritos com casos. Zero medido é sempre `baixa`."""
    if not totais:
        return {}
    valores = sorted((v for v in totais.values() if v > 0), reverse=True)
    n = len(valores)
    alto = valores[ceil(n / 3) - 1] if n else 0
    medio = valores[ceil(2 * n / 3) - 1] if n else 0
    return {
        d: "alta" if v > 0 and v >= alto else "media" if v > 0 and v >= medio else "baixa"
        for d, v in totais.items()
    }


def _anual(db: Session, agravo: str) -> tuple[int | None, dict[str, int]]:
    anos = saude.anos_bairros(db, agravo)
    if not anos:
        return None, {}
    linhas = db.execute(
        text(
            "select d.id, coalesce(sum(g.casos), 0)::integer from app.territorios d "
            "left join app.territorios b on b.pai_id = d.id and b.tipo = 'bairro' "
            "left join gold.arboviroses_bairro_ano g on g.bairro_id = b.id and g.agravo = :a and g.ano = :n "
            "where d.tipo = 'distrito' group by d.id"
        ),
        {"a": agravo, "n": anos[0]},
    ).all()
    return anos[0], {d: int(n) for d, n in linhas}


def _semanal(db: Session, agravo: str, agora: datetime) -> tuple[dict | None, list[dict], bool]:
    """(semana recente, série, há dado utilizável). Série parada (última semana com dado mais velha que o limite da
    fonte) não vira número atual: sem semana recente e sem dado utilizável (RN-01)."""
    desc = saude._semanas(db, agravo, limite=SEMANAS_SERIE)
    serie = []
    for s in reversed(desc):
        casos, sup = suprimir(s["casos"], MINIMO)
        serie.append(
            {
                "ano": s["ano"],
                "semana": s["semana"],
                "inicio": s["inicio"],
                "casos": casos,
                "suprimido": sup,
                "incompleta": bool(s["incompleta"]),
                "nivel_alerta": s["nivel_alerta"],
            }
        )
    # semana mais recente COM dado: casos nulos (ainda não publicados) não valem como zero
    recente = next((e for e, s in zip(reversed(serie), desc, strict=True) if s["casos"] is not None), None)
    if recente is not None and not saude.semana_utilizavel(FONTE_SEMANAL, recente["inicio"], agora):
        return None, [], False
    return recente, serie, bool(desc)


def _sem_dado(agravo: str, nome: str) -> dict:
    return {
        "agravo": agravo,
        "nome": nome,
        "semana_recente": None,
        "serie_semanal": [],
        "ano_distrito": None,
        "casos_ano_distrito": None,
        "casos_ano_suprimido": False,
        "classe_impacto": None,
        "dados_insuficientes": True,
        "motivo": MOTIVO_ZIKA,
        "fonte_semanal": FONTE_SEMANAL,
        "fonte_anual": FONTE_ANUAL,
    }


def montar(db: Session, distritos: dict[str, str], agora: datetime) -> dict:
    """Bloco por distrito (`por_distrito`) e o resumo do contexto. `distritos`: id → nome."""
    fontes = {f: servico_fontes.meta(db, f, agora) for f in (FONTE_SEMANAL, FONTE_ANUAL)}
    semanais = {a: _semanal(db, a, agora) for a, _ in AGRAVOS if a != "zika"}
    anuais = {a: _anual(db, a) for a, _ in AGRAVOS if a != "zika"}
    classes = {a: _classes(anuais[a][1]) for a in anuais}
    por_distrito: dict[str, dict] = {}
    for ds in distritos:
        lista, classes_ds = [], []
        for agravo, nome in AGRAVOS:
            if agravo == "zika":
                lista.append(_sem_dado(agravo, nome))
                continue
            recente, serie, tem_semanal = semanais[agravo]
            ano, totais = anuais[agravo]
            tem_anual = ano is not None
            casos_ano, sup_ano = suprimir(totais.get(ds), MINIMO) if tem_anual else (None, False)
            classe = classes[agravo].get(ds) if tem_anual else None
            faltas = [
                f"falta a fonte {f}"
                for f, ok in ((FONTE_SEMANAL, tem_semanal), (FONTE_ANUAL, tem_anual))
                if not ok
            ]
            if classe:
                classes_ds.append(classe)
            lista.append(
                {
                    "agravo": agravo,
                    "nome": nome,
                    "semana_recente": recente,
                    "serie_semanal": serie,
                    "ano_distrito": ano,
                    "casos_ano_distrito": casos_ano,
                    "casos_ano_suprimido": sup_ano,
                    "classe_impacto": classe,
                    "dados_insuficientes": bool(faltas),
                    "motivo": ("Dados insuficientes: " + "; ".join(faltas) + ".") if faltas else None,
                    "fonte_semanal": FONTE_SEMANAL,
                    "fonte_anual": FONTE_ANUAL,
                }
            )
        por_distrito[ds] = {
            "agravos": lista,
            "classe_impacto": max(classes_ds, key=RANK.get) if classes_ds else None,
            "agravos_em_destaque": [a["agravo"] for a in lista if a["classe_impacto"] == "alta"],
        }
    return {
        "por_distrito": por_distrito,
        "resumo": {
            "experimental": True,
            "contexto": True,
            "aviso": AVISO,
            "granularidade_semanal": "municipio",
            "granularidade_anual": "distrito",
            "fontes": [
                {"id": f, "nome": m.nome, "atualizado_em": m.atualizado_em, "status": m.status}
                for f, m in fontes.items()
            ],
        },
    }
