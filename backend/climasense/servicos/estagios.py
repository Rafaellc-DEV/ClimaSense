"""Estágio operacional por território (F1) e mensagem para WhatsApp (F2).

Reúne os insumos reais por distrito (chuva recente, previsão, maré, ocorrências e, quando houver, o risco do
modelo de ML), aplica a regra pura de `dominio.estagio` e junta a última declaração humana. Bairro herda a chuva
e a maré do distrito (RN-07). Declarar é ato de uma pessoa, auditado, sem fluxo de revisão; a sugestão nunca
muda o estágio sozinha.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import estagio as dom
from climasense.dominio import situacao as sit
from climasense.dominio.distritos import nome_distrito
from climasense.dominio.evento import RegistroInvalido
from climasense.dominio.mensagem import mensagem_estagio, wa_me_url
from climasense.dominio.recorte import inicio_do_dia_utc
from climasense.infra import cache
from climasense.infra.modelos_sql import Usuario
from climasense.infra.postgres import em_paralelo
from climasense.servicos import cenarios, decisao, fluxo

log = logging.getLogger("climasense.estagios")
ALVO = "estagio"
FONTES = (
    "apac-chuva",
    "open-meteo-previsao",
    "open-meteo-mare",
    "open-meteo-historico",
    "recife-alagamento",
    "alertas-oficiais",
)
MAX_JUSTIFICATIVA = 500


# ------------------------------------------------------------------ parâmetros (limiares com histórico)
def parametros_atuais(db: Session) -> dict:
    """Limiares vigentes. Guardados por `cache.VIVO_S`; `alterar_parametros` esquece o cache na hora."""
    return cache.obter("estagio_parametros", "vigentes", cache.VIVO_S, lambda: _ler_parametros(db))


def _ler_parametros(db: Session) -> dict:
    linha = (
        db.execute(
            text(
                "select p.versao, p.limiares, p.justificativa, p.criado_em, u.nome from app.estagio_parametros p "
                "left join app.usuarios u on u.id = p.autor_id order by p.versao desc limit 1"
            )
        )
        .mappings()
        .first()
    )
    if not linha:
        return {
            "parametros": dom.Parametros(),
            "versao": None,
            "padrao": True,
            "justificativa": None,
            "atualizado_em": None,
            "atualizado_por_nome": None,
        }
    return {
        "parametros": dom.Parametros.de_dict(linha["limiares"]),
        "versao": linha["versao"],
        "padrao": False,
        "justificativa": linha["justificativa"],
        "atualizado_em": linha["criado_em"],
        "atualizado_por_nome": linha["nome"],
    }


def historico_parametros(db: Session, limite: int = 50) -> list[dict]:
    return [
        {
            "versao": r["versao"],
            "limiares": dom.Parametros.de_dict(r["limiares"]).como_dict(),
            "justificativa": r["justificativa"],
            "atualizado_em": r["criado_em"],
            "atualizado_por_nome": r["nome"],
        }
        for r in db.execute(
            text(
                "select p.versao, p.limiares, p.justificativa, p.criado_em, u.nome from app.estagio_parametros p "
                "left join app.usuarios u on u.id = p.autor_id order by p.versao desc limit :n"
            ),
            {"n": limite},
        ).mappings()
    ]


def alterar_parametros(
    db: Session, valores: dict, justificativa: str | None, autor: Usuario, ip: str | None, agora: datetime
) -> dict:
    """Grava uma nova versão dos limiares (as anteriores ficam no histórico). Campos ausentes mantêm o valor."""
    try:
        atual = parametros_atuais(db)["parametros"]
        novo = dom.Parametros.de_dict({**atual.como_dict(), **valores})
        erros = dom.problemas_parametros(novo)
        if erros:
            raise RegistroInvalido(422, " ".join(erros))
        versao = db.execute(
            text(
                "insert into app.estagio_parametros (limiares, justificativa, autor_id, criado_em) "
                "values (cast(:l as jsonb), :j, :a, :e) returning versao"
            ),
            {
                "l": json.dumps(novo.como_dict()),
                "j": (justificativa or "").strip() or None,
                "a": autor.id,
                "e": agora,
            },
        ).scalar_one()
        mudou = {
            k: {"de": v, "para": novo.como_dict()[k]}
            for k, v in atual.como_dict().items()
            if novo.como_dict()[k] != v
        }
        fluxo.auditar(db, "estagio_parametros_alterados", autor, ALVO, versao, ip, alteracoes=mudou)
        db.commit()
    except Exception:
        db.rollback()
        raise
    cache.limpar("estagio_parametros")
    return parametros_atuais(db)


# ------------------------------------------------------------------ insumos reais
def _risco_ml(db: Session, agora: datetime) -> dict[str, dict]:
    """Classe de risco por bairro do modelo F6, quando o agente de ML a publicar. Import tolerante: sem o
    módulo, sem modelo publicado ou com erro, o insumo fica de fora (None) e não entra no cálculo."""
    try:
        from climasense.ml import risco_alagamento as ml  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — módulo ainda não existe ou falhou ao carregar
        return {}
    funcao = getattr(ml, "risco_por_bairro", None)
    if funcao is None:
        return {}
    try:
        r = funcao(db, agora)
    except Exception as erro:  # noqa: BLE001 — o modelo é experimental: falha nunca derruba o estágio
        log.warning("Risco de alagamento (ML) indisponível (%s)", type(erro).__name__)
        return {}
    r = r if isinstance(r, dict) else getattr(r, "__dict__", {})
    if not r.get("disponivel"):
        return {}
    saida = {}
    for item in r.get("itens") or []:
        item = item if isinstance(item, dict) else getattr(item, "__dict__", {})
        if item.get("territorio_id") and item.get("classe"):
            saida[item["territorio_id"]] = {
                "classe": str(item["classe"]),
                "fatores": [str(f) for f in item.get("fatores") or []],
                "experimental": True,
            }
    return saida


def _ocorrencias_por_bairro(db: Session) -> dict[str, int] | None:
    """None enquanto o conector de ocorrências não tiver carga bem-sucedida (ausência ≠ zero, RN-02)."""

    def ler() -> dict[str, int] | None:
        if cenarios.ocorrencias(db, "recife") is None:
            return None
        return dict(
            db.execute(
                text(
                    "select territorio_id, count(*) from silver.ocorrencias where tipo = 'alagamento' "
                    "group by territorio_id"
                )
            ).all()
        )

    return cache.obter("ocorrencias", "por_bairro", cache.MEDIO_S, ler)


APAC_DESATUALIZADA_MIN = 120  # leitura mais velha que isso não vale como "agora" (é desatualizada, não zero)


def _chuva_apac_todos(db: Session, inicio: datetime) -> dict[str, float]:
    """Maior acumulado de 24 h entre as estações atualizadas de cada território (gold do `apac-chuva`), numa só
    consulta. O máximo, não a média: alerta não confirmado é melhor que evento não avisado
    (specs/foco-chuvas.md §1). Território sem leitura válida (ausente ou com mais de 120 min) fica de fora."""
    try:
        with db.begin_nested():
            linhas = db.execute(
                text(
                    "select territorio_id, chuva_24h_max_mm, lida_em from gold.chuva_apac_agora "
                    "where n_atualizadas > 0"
                )
            ).all()
    except Exception:  # noqa: BLE001 — tabela ainda não migrada: segue a lógica anterior
        return {}
    return {
        t: round(float(mm), 1)
        for t, mm, lida in linhas
        if mm is not None and lida is not None and inicio - lida <= timedelta(minutes=APAC_DESATUALIZADA_MIN)
    }


def _chuva_apac(db: Session, territorio_id: str, inicio: datetime) -> float | None:
    return _chuva_apac_todos(db, inicio).get(territorio_id)


def chuva_24h(
    db: Session,
    territorio_id: str,
    inicio: datetime,
    apac: dict[str, float] | None = None,
    horaria: dict | None = None,
) -> tuple[float | None, list[str]]:
    """Chuva das últimas 24 h do distrito e as fontes usadas. Prefere os pluviômetros observados da APAC
    (`apac-chuva`, estações atualizadas há até 120 min); sem eles, a reanálise e as horas já passadas da
    previsão (decisao.py). `apac` é a leitura de todos os territórios e `horaria` a da reanálise/previsão de todos os
    distritos (`decisao.chuva_horaria_recente_distritos`), quando quem chama já as tem."""
    apac_mm = apac.get(territorio_id) if apac is not None else _chuva_apac(db, territorio_id, inicio)
    if apac_mm is not None:
        return apac_mm, ["apac-chuva"]
    if horaria is not None and territorio_id in horaria:
        por_hora, fontes_hora = horaria[territorio_id]
    else:
        por_hora, fontes_hora = decisao.chuva_horaria_recente(
            db, territorio_id, inicio - timedelta(hours=24), inicio
        )
    usadas = sorted({f for h, f in fontes_hora.items() if inicio - timedelta(hours=24) <= h < inicio})
    return sit.acumulado_recente(por_hora, inicio, 24).acumulado_mm, usadas


# Os insumos de tempo (chuva e maré) mudam a cada 10 a 15 min, mas custam dezenas de consultas ao banco: guardá-los
# por 60 s deixa o painel e a lista de estágios rápidos sem atrasar nada. Declarações e alertas NÃO passam por aqui.
CACHE_INSUMOS_S = 60.0


def limpar_cache_insumos() -> None:
    cache.limpar("insumos")


def insumos_distritos(db: Session, distritos: list[str], agora: datetime, p: dom.Parametros) -> dict:
    """ds → (Insumos do domínio, dict extra com as emissões usadas). Guardado por `CACHE_INSUMOS_S` segundos."""
    chave = (
        tuple(distritos),
        agora.replace(minute=0, second=0, microsecond=0),
        tuple(sorted(p.como_dict().items())),
    )
    return cache.obter(
        "insumos", chave, CACHE_INSUMOS_S, lambda: _calcular_insumos_distritos(db, distritos, agora, p)
    )


def _calcular_insumos_distritos(
    db: Session, distritos: list[str], agora: datetime, p: dom.Parametros
) -> dict:
    inicio = agora.replace(minute=0, second=0, microsecond=0)
    # quatro leituras independentes (maré, APAC, previsão e chuva horária dos distritos) ao mesmo tempo
    (emitido_mare, mare), apac, previsoes, horaria = em_paralelo(
        db,
        [
            lambda s: cenarios.mare_prevista(s, inicio),
            lambda s: _chuva_apac_todos(s, inicio),
            lambda s: cenarios.previsao_por_emissao_distritos(s, distritos, inicio),
            lambda s: decisao.chuva_horaria_recente_distritos(
                s, distritos, inicio - timedelta(hours=24), inicio
            ),
        ],
    )
    mare = [(t, v) for t, v in mare if t < inicio + timedelta(hours=72)]
    validas = [(t, v) for t, v in mare if v is not None]
    mare_em, mare_max = max(validas, key=lambda x: x[1]) if validas else (None, None)
    mare_max = round(mare_max, 2) if mare_max is not None else None
    resultado = {}
    for ds in distritos:
        por_emissao = previsoes.get(ds, {})
        ultima = max(por_emissao) if por_emissao else None
        chuva = por_emissao.get(ultima, []) if ultima else []
        prev24, _ = dom.acumulado_previsto(chuva, inicio, 24)
        prev72, horas72 = dom.acumulado_previsto(chuva, inicio, 72)
        pico_em = dom.pico(chuva, inicio, 72)
        recente_mm, recente_fontes = chuva_24h(db, ds, inicio, apac, horaria)
        no_pico = dom.mare_perto_do_pico(mare, pico_em, p.mare_janela_h)
        resultado[ds] = (
            dom.Insumos(
                chuva_24h_mm=recente_mm,
                chuva_prev_24h_mm=prev24,
                chuva_prev_72h_mm=prev72,
                horas_previstas_72h=horas72 if chuva else None,
                pico_chuva_em=pico_em,
                mare_max_m=mare_max,
                mare_max_em=mare_em,
                mare_no_pico_m=round(no_pico, 2) if no_pico is not None else None,
            ),
            {
                "previsao_emitida_em": ultima,
                "mare_emitida_em": emitido_mare,
                "chuva_24h_fontes": recente_fontes,
            },
        )
    return resultado


def _alertas_vigentes(db: Session | None, agora: datetime | None) -> list[dict]:
    """Avisos oficiais vigentes que atingem o Recife (silver do `alertas-oficiais`: APAC, INMET, Cemaden, IDAP),
    do nível mais alto. Os filtros geográficos são municipais (geocode IBGE, polígono ou mesorregião), então o
    resultado é o mesmo para todo território do Recife e uma consulta basta por requisição."""
    if db is None or agora is None:
        return []
    return cache.obter("alertas", "vigentes", cache.VIVO_S, lambda: _ler_alertas(db, agora))


def _ler_alertas(db: Session, agora: datetime) -> list[dict]:
    from climasense.etl.conectores.alertas import CEMADEN_SEM_VALIDADE_H, vigentes_sql

    try:
        with db.begin_nested():
            linhas = (
                db.execute(text(vigentes_sql()), {"agora": agora, "sem_validade_h": CEMADEN_SEM_VALIDADE_H})
                .mappings()
                .all()
            )
    except Exception:  # noqa: BLE001 — tabela ainda não migrada
        return []
    return [{k: v for k, v in r.items() if k != "nivel_original"} for r in linhas]


def alertas_oficiais(
    territorio_id: str,
    db: Session | None = None,
    agora: datetime | None = None,
    vigentes: list[dict] | None = None,
) -> list[dict]:
    """Avisos oficiais vigentes do território: [{origem, evento, nivel, emitido_em, inicio_em, expira_em, url,
    area, criterio_geo, territorio_id}]. `vigentes` evita repetir a consulta quando quem chama já a fez. Sem
    carga, vazio: nunca é preenchido com dado inventado."""
    if vigentes is None:
        vigentes = _alertas_vigentes(db, agora)
    return [r | {"territorio_id": territorio_id} for r in vigentes]


def _sugerido(ins: dom.Insumos, extra: dict, risco: dict | None, p: dom.Parametros, agora: datetime) -> dict:
    s = dom.sugerir(ins, p)
    insumos = ins.como_dict()
    insumos.pop("herdado_de")
    insumos.update(extra)
    insumos["risco_ml"] = risco
    return {
        "estagio": s.estagio,
        "rotulo": dom.ROTULO[s.estagio],
        "motivos": s.motivos,
        "faltando": s.faltando,
        "insumos": insumos,
        "calculado_em": agora,
        "experimental": True,
    }


# ------------------------------------------------------------------ declarações
def _ultimas_declaracoes(db: Session) -> dict[str, dict]:
    return {
        r["territorio_id"]: {**r, "territorio_nome": nome_distrito(r["territorio_nome"])}
        for r in db.execute(
            text(
                "select distinct on (d.territorio_id) d.id, d.territorio_id, t.nome_exibicao as territorio_nome, "
                "d.estagio, d.justificativa, d.declarado_em, u.nome as autor_nome "
                "from app.estagio_declaracoes d join app.usuarios u on u.id = d.autor_id "
                "join app.territorios t on t.id = d.territorio_id "
                "order by d.territorio_id, d.declarado_em desc"
            )
        ).mappings()
    }


def _declarado(ultimas: dict[str, dict], cadeia: list[str]) -> dict | None:
    """A declaração mais recente entre o próprio território, o distrito e o Recife (o COP declara para a
    cidade; a equipe, por distrito ou bairro). Diz de onde ela veio."""
    candidatas = [ultimas[t] for t in cadeia if t in ultimas]
    if not candidatas:
        return None
    d = max(candidatas, key=lambda x: x["declarado_em"])
    if d["estagio"] == dom.ENCERRADO:  # a equipe encerrou: vale como “sem declaração”, não herda uma anterior
        return None
    return {
        "id": d["id"],
        "estagio": d["estagio"],
        "rotulo": dom.ROTULO[d["estagio"]],
        "justificativa": d["justificativa"],
        "autor_nome": d["autor_nome"],
        "declarado_em": d["declarado_em"],
        "territorio_origem_id": d["territorio_id"],
        "territorio_origem_nome": d["territorio_nome"],
        "herdado": d["territorio_id"] != cadeia[0],
    }


def _territorios(db: Session) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    """Distritos e bairros do cadastro (só mudam quando a base territorial é recarregada)."""
    return cache.obter("territorios", "distritos_bairros", cache.CARGA_S, lambda: _ler_territorios(db))


def _ler_territorios(db: Session) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    distritos = {
        i: nome_distrito(n)  # "Distrito 5": o nome guardado no banco não muda, só o que a API devolve
        for i, n in db.execute(
            text("select id, nome_exibicao from app.territorios where tipo = 'distrito' order by id")
        ).all()
    }
    bairros = [
        (i, n, pai)
        for i, n, pai in db.execute(
            text(
                "select id, nome_exibicao, pai_id from app.territorios where tipo = 'bairro' order by nome_exibicao"
            )
        )
        if pai in distritos
    ]
    return distritos, bairros


def listar(db: Session, nivel: str, agora: datetime, distrito_id: str | None = None) -> list[dict]:
    """`nivel`: distrito, bairro ou todos (distritos e depois bairros, com uma só leitura dos insumos)."""
    p = parametros_atuais(db)["parametros"]
    distritos, bairros = _territorios(db)
    alvo_ds = [d for d in distritos if distrito_id in (None, d)]
    insumos = insumos_distritos(db, alvo_ds, agora, p)
    ultimas = _ultimas_declaracoes(db)
    vigentes = _alertas_vigentes(db, agora)
    itens = []
    if nivel in ("distrito", "todos"):
        for ds in alvo_ds:
            base, extra = insumos[ds]
            itens.append(
                {
                    "territorio_id": ds,
                    "territorio_nome": distritos[ds],
                    "nivel": "distrito",
                    "distrito_id": ds,
                    "herda_chuva_de": None,
                    "sugerido": _sugerido(base, extra, None, p, agora),
                    "declarado": _declarado(ultimas, [ds, "recife"]),
                    "alertas_oficiais": alertas_oficiais(ds, vigentes=vigentes),
                }
            )
    if nivel in ("bairro", "todos"):
        ocorr = _ocorrencias_por_bairro(db)
        risco = _risco_ml(db, agora)
        for bid, nome, ds in bairros:
            if ds not in insumos:
                continue
            base, extra = insumos[ds]
            ins = dom.Insumos(
                **{
                    **base.como_dict(),
                    "ocorrencias_historicas": None if ocorr is None else ocorr.get(bid, 0),
                    "risco_ml": (risco.get(bid) or {}).get("classe"),
                    "herdado_de": distritos[ds],
                }
            )
            itens.append(
                {
                    "territorio_id": bid,
                    "territorio_nome": nome,
                    "nivel": "bairro",
                    "distrito_id": ds,
                    "herda_chuva_de": ds,
                    "sugerido": _sugerido(ins, extra, risco.get(bid), p, agora),
                    "declarado": _declarado(ultimas, [bid, ds, "recife"]),
                    "alertas_oficiais": alertas_oficiais(bid, vigentes=vigentes),
                }
            )
    return itens


def declarar(
    db: Session,
    territorio_ids: list[str],
    estagio: str,
    justificativa: str,
    autor: Usuario,
    ip: str | None,
    agora: datetime,
) -> list[dict]:
    """Uma declaração por território, no mesmo lote, com a sugestão daquele momento guardada junto."""
    ids = list(dict.fromkeys(territorio_ids))
    if not ids:
        raise RegistroInvalido(422, "Escolha pelo menos um território.")
    encerrando = estagio == dom.ENCERRADO
    if estagio not in dom.DECLARAVEIS and not encerrando:
        raise RegistroInvalido(422, "Escolha o estágio: observação, atenção, alerta ou crítico.")
    justificativa = " ".join((justificativa or "").split())
    if not justificativa:
        raise RegistroInvalido(
            422,
            "Escreva uma justificativa curta: por que encerrar o estágio."
            if encerrando
            else "Escreva uma justificativa curta: por que este estágio agora.",
        )
    if len(justificativa) > MAX_JUSTIFICATIVA:
        raise RegistroInvalido(422, f"A justificativa passou de {MAX_JUSTIFICATIVA} caracteres.")
    fluxo.validar_territorios(db, ids)
    sugestoes = {}
    try:
        nivel = "todos" if any(i.startswith("bairro-") for i in ids) else "distrito"
        sugestoes = {it["territorio_id"]: it["sugerido"] for it in listar(db, nivel, agora)}
    except Exception as erro:  # noqa: BLE001 — sem a sugestão, a declaração humana ainda vale
        log.warning("Sugestão indisponível ao declarar (%s)", type(erro).__name__)
    lote = uuid.uuid4()
    try:
        criadas = []
        for tid in ids:
            sug = sugestoes.get(tid)
            foto = {"estagio": sug["estagio"], "motivos": sug["motivos"]} if sug else {}
            did = db.execute(
                text(
                    "insert into app.estagio_declaracoes (territorio_id, estagio, justificativa, sugerido, lote_id, "
                    "autor_id, declarado_em) values (:t, :e, :j, cast(:s as jsonb), :l, :a, :em) returning id"
                ),
                {
                    "t": tid,
                    "e": estagio,
                    "j": justificativa,
                    "s": json.dumps(foto, ensure_ascii=False),
                    "l": lote,
                    "a": autor.id,
                    "em": agora,
                },
            ).scalar_one()
            criadas.append(did)
            fluxo.auditar(
                db,
                "estagio_encerrado" if encerrando else "estagio_declarado",
                autor,
                ALVO,
                did,
                ip,
                territorio_id=tid,
                estagio=estagio,
                sugerido=foto.get("estagio"),
                lote_id=str(lote),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return historico(db, ids_declaracoes=criadas)


def historico(
    db: Session,
    territorio_id: str | None = None,
    desde: date | None = None,
    ate: date | None = None,
    ids_declaracoes: list | None = None,
    limite: int = 500,
) -> list[dict]:
    """Declarações em ordem decrescente; `territorio_id` de distrito inclui os bairros dele."""
    linhas = db.execute(
        text(
            "select d.id, d.territorio_id, t.nome_exibicao as territorio_nome, t.tipo as nivel, d.estagio, "
            "d.justificativa, d.sugerido, d.lote_id, d.declarado_em, u.nome as autor_nome "
            "from app.estagio_declaracoes d join app.territorios t on t.id = d.territorio_id "
            "join app.usuarios u on u.id = d.autor_id "
            "where (cast(:t as varchar) is null or d.territorio_id = :t or t.pai_id = :t) "
            "and (cast(:d as timestamptz) is null or d.declarado_em >= :d) "
            "and (cast(:a as timestamptz) is null or d.declarado_em < :a) "
            "and (cast(:ids as uuid[]) is null or d.id = any(:ids)) "
            "order by d.declarado_em desc, t.nome_exibicao limit :n"
        ),
        {
            "t": territorio_id,
            "d": inicio_do_dia_utc(desde) if desde else None,
            "a": inicio_do_dia_utc(ate + timedelta(days=1)) if ate else None,
            "ids": ids_declaracoes,
            "n": limite,
        },
    ).mappings()
    return [
        {
            **dict(r),
            "territorio_nome": nome_distrito(r["territorio_nome"]),
            "rotulo": dom.ROTULO[r["estagio"]],
            "sugerido_estagio": (r["sugerido"] or {}).get("estagio"),
        }
        for r in linhas
    ]


# ------------------------------------------------------------------ mensagem (F2)
def mensagem(
    db: Session,
    territorio_ids: list[str],
    estagio: str,
    justificativa: str | None,
    autor: Usuario,
    ip: str | None,
    agora: datetime,
) -> dict:
    """Texto padronizado e link `wa.me`. Nada é enviado; a geração fica na auditoria para medir o piloto."""
    ids = list(dict.fromkeys(territorio_ids))
    if not ids:
        raise RegistroInvalido(422, "Escolha pelo menos um território.")
    if estagio not in dom.ROTULO or estagio == dom.ENCERRADO:
        raise RegistroInvalido(422, "Estágio desconhecido.")
    fluxo.validar_territorios(db, ids)
    nomes = dict(
        db.execute(text("select id, nome_exibicao from app.territorios where id = any(:i)"), {"i": ids}).all()
    )
    texto = mensagem_estagio(estagio, [nomes[i] for i in ids], agora, justificativa)
    fluxo.auditar(db, "estagio_mensagem_gerada", autor, ALVO, ids[0], ip, territorio_ids=ids, estagio=estagio)
    db.commit()
    return {"texto": texto, "wa_me_url": wa_me_url(texto)}


EVENTOS_USO = {"copiar": "estagio_mensagem_copiada", "abrir_whatsapp": "estagio_mensagem_aberta_whatsapp"}


def registrar_uso(
    db: Session, evento: str, territorio_ids: list[str], estagio: str | None, autor: Usuario, ip: str | None
) -> None:
    if evento not in EVENTOS_USO:
        raise RegistroInvalido(422, "Evento desconhecido. Use “copiar” ou “abrir_whatsapp”.")
    ids = list(dict.fromkeys(territorio_ids))[:100]
    if not ids:
        raise RegistroInvalido(422, "Informe os territórios da mensagem.")
    fluxo.auditar(db, EVENTOS_USO[evento], autor, ALVO, ids[0], ip, territorio_ids=ids, estagio=estagio)
    db.commit()
