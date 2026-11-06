"""Simulador de cenário (PRD §8, RF-23 a RF-25, RF-27, RF-28). EXPERIMENTAL (RN-11).

Reúne os insumos reais (histórico de ocorrências por bairro, malha de territórios, limiares dos estágios), aplica as
regras de `dominio.simulador` aos 94 bairros e 8 distritos e guarda cenários salvos. Os insumos estáticos
(malha e histórico) ficam em cache por `CACHE_ESTATICO_S` segundos; o cálculo em si leva milissegundos.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import simulador as dom
from climasense.dominio.evento import RegistroInvalido
from climasense.infra.modelos_sql import Usuario
from climasense.servicos import cenarios, estagios, fluxo, prioridade_vulnerabilidade

ALVO = "cenario"
FONTE_OCORRENCIAS = prioridade_vulnerabilidade.FONTE
FONTE_APAC = "apac-chuva"
MAX_NOME = 120
CACHE_ESTATICO_S = 300.0
_cache: dict[str, tuple[float, dict]] = {}
_trava = threading.Lock()


def limpar_cache() -> None:
    with _trava:
        _cache.clear()


def _estatico(db: Session) -> dict:
    """Malha e histórico por bairro: mudam no máximo uma vez por dia (carga das ocorrências)."""
    agora_s = time.monotonic()
    if CACHE_ESTATICO_S > 0:
        with _trava:
            guardado = _cache.get("estatico")
        if guardado and agora_s - guardado[0] < CACHE_ESTATICO_S:
            return guardado[1]
    distritos, bairros = estagios._territorios(db)
    carregou = (
        db.execute(
            text("select 1 from app.etl_execucoes where fonte_id = :f and status = 'sucesso' limit 1"),
            {"f": FONTE_OCORRENCIAS},
        ).first()
        is not None
    )
    contagens: dict[tuple[str, str], int] = {}
    desde = None
    if carregou:
        contagens = {
            (t, tipo): n
            for t, tipo, n in db.execute(
                text(
                    "select territorio_id, tipo, count(*)::integer from silver.ocorrencias "
                    "where fonte_id = :f and tipo in ('alagamento', 'deslizamento') group by 1, 2"
                ),
                {"f": FONTE_OCORRENCIAS},
            )
        }
        desde = prioridade_vulnerabilidade._desde(db)
    historico = {
        bid: dom.Historico(
            alagamento=contagens.get((bid, "alagamento"), 0) if carregou else None,
            deslizamento=contagens.get((bid, "deslizamento"), 0) if carregou else None,
            desde=desde,
        )
        for bid, _, _ in bairros
    }
    resultado = {"distritos": distritos, "bairros": bairros, "historico": historico, "carregou": carregou}
    if CACHE_ESTATICO_S > 0:
        with _trava:
            _cache["estatico"] = (agora_s, resultado)
    return resultado


def vulneraveis_por_territorio(db: Session) -> dict[str, dom.Vulneraveis] | None:
    """Gancho da Etapa 6: idosos e crianças (IBGE) e equipamentos de saúde por bairro. `None` = sem fonte."""
    return None


# ------------------------------------------------------------------ simulação
def simular(db: Session, p: dom.Premissas, agora: datetime) -> dict:
    inicio = time.perf_counter()
    par = estagios.parametros_atuais(db)["parametros"]
    est = _estatico(db)
    vul = vulneraveis_por_territorio(db)
    por_bairro: dict[str, dom.Resultado] = {}
    por_distrito: dict[str, list[tuple[str, dom.Resultado]]] = {}
    itens_bairro = []
    for bid, nome, ds in est["bairros"]:
        r = dom.classificar_bairro(p, par, est["historico"][bid])
        por_bairro[bid] = r
        por_distrito.setdefault(ds, []).append((nome, r))
        itens_bairro.append((bid, nome, ds, r))
    itens = []
    for ds, nome in est["distritos"].items():
        r = dom.agregar_distrito(por_distrito.get(ds, []))
        itens.append(_item(ds, nome, "distrito", ds, r, vul))
    itens += [_item(b, n, "bairro", ds, r, vul) for b, n, ds, r in itens_bairro]
    resumo = {
        "por_classe": dom.resumo_por_classe(list(por_bairro.values())),
        "pressao_abrigos": dom.pressao_abrigos(p),
        "impacto_pessoas_aviso": dom.MOTIVO_IMPACTO_PENDENTE if vul is None else None,
    }
    return {
        "itens": itens,
        "resumo": resumo,
        "experimental": True,
        "calculado_em": agora,
        "tempo_calculo_ms": round((time.perf_counter() - inicio) * 1000),
    }


def _item(tid: str, nome: str, nivel: str, ds: str, r: dom.Resultado, vul) -> dict:
    return {
        "territorio_id": tid,
        "nome": nome,
        "nivel": nivel,
        "distrito_id": ds,
        "classe_alagamento": r.classe_alagamento,
        "classe_deslizamento": r.classe_deslizamento,
        "estagio_sugerido": r.estagio_sugerido,
        "confianca": r.confianca,
        "motivos": r.motivos,
        "impacto_pessoas": dom.impacto_pessoas(r.estagio_sugerido, vul.get(tid)) if vul else None,
    }


# ------------------------------------------------------------------ premissas sugeridas pelas fontes
def _chuva_apac_72h(db: Session, agora: datetime) -> float | None:
    """Maior acumulado de 3 dias (hoje e os 2 anteriores, dia local) entre os distritos, pelos pluviômetros da APAC.
    Só vale com os 3 dias medidos em algum distrito; senão `None` (não é zero, RN-02)."""
    hoje = agora.astimezone(ZoneInfo("America/Recife")).date()
    try:
        with db.begin_nested():
            linhas = db.execute(
                text(
                    "select territorio_id, sum(max_mm), count(max_mm) from gold.chuva_apac_diaria "
                    "where nivel = 'distrito' and dia between :a and :b group by territorio_id"
                ),
                {"a": hoje - timedelta(days=2), "b": hoje},
            ).all()
    except Exception:  # noqa: BLE001 — tabela ainda não migrada
        return None
    completos = [float(s) for _, s, n in linhas if n == 3 and s is not None]
    return round(max(completos), 1) if completos else None


def _abrigos(db: Session) -> tuple[int | None, int | None]:
    from climasense.servicos import abrigos

    linhas = abrigos._linhas(db)
    if not linhas:
        return None, None
    abertos = [r for r in linhas if r["aberto"]]
    capacidades = [r["capacidade"] for r in abertos]
    cap = None if any(c is None for c in capacidades) else sum(capacidades)
    return len(abertos), cap


def premissas_atuais(db: Session, agora: datetime) -> dict:
    """Valores sugeridos a partir das fontes reais; `None` quando a fonte falta."""
    par = estagios.parametros_atuais(db)["parametros"]
    inicio = agora.replace(minute=0, second=0, microsecond=0)
    ds = list(estagios._territorios(db)[0])
    insumos = estagios.insumos_distritos(db, ds, agora, par)
    prev = [i.chuva_prev_24h_mm for i, _ in insumos.values() if i.chuva_prev_24h_mm is not None]
    horizonte = 24
    _, mare = cenarios.mare_prevista(db, inicio)
    ate = inicio + timedelta(hours=horizonte)
    niveis = [v for t, v in mare if v is not None and t < ate]
    abertos, cap = _abrigos(db)
    return {
        "chuva_prevista_mm": round(max(prev), 1) if prev else None,
        "duracao_h": 24 if prev else None,
        "chuva_acumulada_mm": _chuva_apac_72h(db, agora),
        "mare_m": round(max(niveis), 2) if niveis else None,
        "horizonte_h": horizonte,
        "abrigos_abertos": abertos,
        "capacidade_abrigos": cap,
    }


# ------------------------------------------------------------------ cenários salvos (RF-27)
def _limpar_nome(nome: str) -> str:
    nome = " ".join((nome or "").split())
    if not nome:
        raise RegistroInvalido(422, "Dê um nome ao cenário.")
    if len(nome) > MAX_NOME:
        raise RegistroInvalido(422, f"O nome passou de {MAX_NOME} caracteres.")
    return nome


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=lambda o: o.isoformat())


def salvar(
    db: Session,
    nome: str,
    p: dom.Premissas,
    premissas: dict,
    fontes: list[dict],
    autor: Usuario,
    ip: str | None,
    agora: datetime,
) -> dict:
    """O servidor recalcula o resultado: o que fica guardado é o que o ClimaSense calculou, não o que veio do cliente."""
    nome = _limpar_nome(nome)
    resultado = simular(db, p, agora)
    resultado["fontes"] = fontes
    try:
        cid = db.execute(
            text(
                "insert into app.cenarios (nome, premissas, resultado, autor_id, criado_em) "
                "values (:n, cast(:p as jsonb), cast(:r as jsonb), :a, :e) returning id"
            ),
            {"n": nome, "p": _json(premissas), "r": _json(resultado), "a": autor.id, "e": agora},
        ).scalar_one()
        fluxo.auditar(db, "cenario_salvo", autor, ALVO, cid, ip, nome=nome)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, cid)


def _resumo(resultado: dict) -> dict:
    r = resultado.get("resumo") or {}
    return {"por_classe": r.get("por_classe"), "pressao_abrigos": r.get("pressao_abrigos")}


_SQL = (
    "select c.id, c.nome, c.premissas, c.resultado, c.criado_em, u.nome as autor_nome "
    "from app.cenarios c join app.usuarios u on u.id = c.autor_id "
)


def listar(db: Session, limite: int = 200) -> list[dict]:
    return [
        {
            "id": r["id"],
            "nome": r["nome"],
            "autor_nome": r["autor_nome"],
            "criado_em": r["criado_em"],
            "resumo": _resumo(r["resultado"]),
        }
        for r in db.execute(text(_SQL + "order by c.criado_em desc limit :n"), {"n": limite}).mappings()
    ]


def obter(db: Session, cenario_id: uuid.UUID) -> dict:
    r = db.execute(text(_SQL + "where c.id = :i"), {"i": cenario_id}).mappings().first()
    if not r:
        raise RegistroInvalido(404, "Cenário não encontrado.")
    return {
        "id": r["id"],
        "nome": r["nome"],
        "autor_nome": r["autor_nome"],
        "criado_em": r["criado_em"],
        "premissas": r["premissas"],
        "resultado": r["resultado"],
        "resumo": _resumo(r["resultado"]),
    }
