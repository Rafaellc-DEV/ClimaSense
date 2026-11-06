"""Apoio à decisão: situação agora, prioridades entre territórios e fila de ações (painel de gestão).

Reúne dados reais já carregados; o que faltar vira `dados_insuficientes`, nunca zero (RN-01). O estimador é o
`EstimadorReferencia` (experimental) e aqui ele é consultado SEM gravar em silver.previsoes_emitidas: só o
cenário que a pessoa abre na tela de cenários vira registro (RF-09.8).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from urllib.parse import urlencode

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import prioridades as dom
from climasense.servicos import cenarios, series
from climasense.servicos import fontes as servico_fontes

FONTE_HISTORICO = series.FONTE_CHUVA
FONTES_CHAVE = ("open-meteo-previsao", "open-meteo-mare", "open-meteo-historico")
NIVEIS_ALTOS = {"alerta", "critico"}


# ------------------------------------------------------------------ chuva recente
def chuva_horaria_recente(
    db: Session, territorio_id: str, desde: datetime, ate: datetime
) -> tuple[dict[datetime, float | None], dict[datetime, str]]:
    """Hora → mm das últimas horas. Prefere a reanálise (histórico); onde ela ainda não chegou, usa as horas
    já passadas da emissão mais recente da previsão. Devolve também de qual fonte veio cada hora."""
    ts = cenarios._territorios_previsao(territorio_id)
    linhas = db.execute(
        text(
            "select observado_em, fonte_id, emitido_em, avg(valor) as valor, count(valor) as n, count(*) as total "
            "from silver.observacoes where fonte_id in (:h, :p) and territorio_id = any(:ts) "
            "and observado_em >= :d and observado_em < :a group by observado_em, fonte_id, emitido_em"
        ),
        {"h": FONTE_HISTORICO, "p": cenarios.FONTE_PREVISAO, "ts": ts, "d": desde, "a": ate},
    ).all()
    melhor: dict[datetime, tuple[tuple, float | None, str]] = {}
    for hora, fonte, emitido, valor, n, total in linhas:
        if n != total or total < len(ts):  # hora com algum distrito sem dado não entra (RN-02)
            continue
        prioridade = (1 if fonte == FONTE_HISTORICO else 0, emitido.timestamp() if emitido else 0)
        if hora not in melhor or prioridade > melhor[hora][0]:
            melhor[hora] = (prioridade, valor, fonte)
    return {h: v for h, (_, v, _f) in melhor.items()}, {h: f for h, (_, _v, f) in melhor.items()}


# ------------------------------------------------------------------ frescor das fontes
def frescor(db: Session, agora: datetime, ids: tuple[str, ...] = FONTES_CHAVE) -> list[dict]:
    resultado = []
    for f in servico_fontes.linhas(db, agora):
        if f["id"] not in ids:
            continue
        ultimo = f["ultimo_sucesso"]
        resultado.append(
            {
                "fonte_id": f["id"],
                "nome": f["nome"],
                "status": f["status"],
                "ultimo_sucesso": ultimo,
                "idade_h": round((agora - ultimo).total_seconds() / 3600, 1) if ultimo else None,
                "limite_h": f["limite_desatualizacao_h"],
            }
        )
    return sorted(resultado, key=lambda x: ids.index(x["fonte_id"]))


def _problemas(fr: list[dict]) -> int:
    return sum(
        1
        for f in fr
        if f["fonte_id"] in ("open-meteo-previsao", "open-meteo-mare")
        and f["status"] in ("desatualizada", "com_falha")
    )


# ------------------------------------------------------------------ sinais da equipe
def sinais_equipe(db: Session, avisos) -> dict[str, list[tuple[str, str, str]]]:
    """territorio_id → [(nivel, origem, texto)] vindos de avisos vigentes e avaliações em curso."""
    sinais: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for a in avisos:
        nivel = dom.DO_AVISO.get(a.nivel, "sem_indicacao")
        for t in a.territorios:
            sinais[t.id].append((nivel, "aviso", f"Aviso publicado: {a.titulo}"))
    for tid, estado, prioridade in db.execute(
        text(
            "select a.territorio_id, a.estado, v.prioridade from app.avaliacoes a "
            "join app.avaliacao_versoes v on v.avaliacao_id = a.id and v.numero = a.versao_atual "
            "where a.estado in ('em_revisao', 'aprovado')"
        )
    ):
        quando = "aprovada" if estado == "aprovado" else "em revisão"
        sinais[tid].append(
            (
                prioridade,
                "avaliacao",
                f"Avaliação {quando} da equipe indica {dom.ROTULO[prioridade].lower()}.",
            )
        )
    return sinais


def _sinais_de(sinais, ids: list[str]) -> list[tuple[str, str, str]]:
    return [s for i in ids for s in sinais.get(i, [])]


# ------------------------------------------------------------------ prioridades
def prioridades(
    db: Session,
    nivel: str,
    horizonte_h: int,
    agora: datetime,
    avisos,
    distrito_id: str | None = None,
) -> list[dict]:
    distritos = dict(
        db.execute(
            text("select id, nome_exibicao from app.territorios where tipo = 'distrito' order by id")
        ).all()
    )
    fr = frescor(db, agora)
    problemas = _problemas(fr)
    sinais = sinais_equipe(db, avisos)
    por_ds = {ds: cenarios.emitir(db, ds, horizonte_h, agora, registrar=False) for ds in distritos}

    ocorr: dict[str, int] = {}
    if nivel == "bairro":
        if cenarios.ocorrencias(db, "recife") is not None:
            ocorr = dict(
                db.execute(
                    text(
                        "select territorio_id, count(*) from silver.ocorrencias where tipo = 'alagamento' "
                        "group by territorio_id"
                    )
                ).all()
            )
        unidades = [
            (i, n, p)
            for i, n, p in db.execute(
                text(
                    "select id, nome_exibicao, pai_id from app.territorios where tipo = 'bairro' "
                    "order by nome_exibicao"
                )
            )
            if p in distritos and distrito_id in (None, p)
        ]
    else:
        unidades = [(i, n, None) for i, n in distritos.items() if distrito_id in (None, i)]

    candidatos = []
    for uid, nome, pai in unidades:
        ds = pai or uid
        r = por_ds[ds]
        est = r["estimativa"]
        c = dom.Candidato(territorio_id=uid, nivel_estimador=est.prioridade)
        if est.p95_mm:
            c.intensidade = (est.acumulado_previsto_mm or 0) / est.p95_mm
        if pai and ocorr:
            c.ocorrencias = ocorr.get(uid, 0)
        if est.prioridade == "dados_insuficientes":
            c.motivos.append(
                dom.Motivo(
                    "Dados insuficientes",
                    est.limitacoes[0] if est.limitacoes else "Faltam dados.",
                    "qualidade",
                    50,
                )
            )
        else:
            for k, (fator, desc) in enumerate(est.fatores):
                c.motivos.append(dom.Motivo(fator, desc, "estimador", 90 - k * 10))
        if pai:
            c.motivos.append(
                dom.Motivo(
                    "Previsão por distrito",
                    f"A previsão existe só por distrito: este bairro herda a do {distritos[ds]}.",
                    "qualidade",
                    20,
                )
            )
            if c.ocorrencias:
                c.motivos.append(
                    dom.Motivo(
                        "Histórico de ocorrências",
                        f"{c.ocorrencias} ocorrência(s) de alagamento registradas neste bairro.",
                        "ocorrencias",
                        60,
                    )
                )
        equipe = _sinais_de(sinais, [uid, ds, "recife"] if pai else [uid, "recife"])
        for nv, origem, texto in equipe:
            c.motivos.append(dom.Motivo("Sinal da equipe", texto, origem, 80 if dom.PESO.get(nv, 0) else 30))
        niveis = [nv for nv, *_ in equipe if nv in dom.PESO]
        c.nivel_equipe = max(niveis, key=lambda x: dom.PESO[x]) if niveis else None
        notas = [] if est.prioridade == "dados_insuficientes" else list(est.limitacoes)
        if r["emissoes_na_faixa"] < 2 and est.prioridade != "dados_insuficientes":
            notas.append("Só uma emissão da previsão: sem faixa de incerteza.")
        for f in fr:
            if f["fonte_id"] in ("open-meteo-previsao", "open-meteo-mare") and f["status"] in (
                "desatualizada",
                "com_falha",
            ):
                notas.append(
                    f"Fonte {f['nome']}: {'com falha' if f['status'] == 'com_falha' else 'desatualizada'}."
                )
        candidatos.append((c, r, notas, nome, ds, pai))

    itens = []
    for pos, (c, r, notas, nome, ds, pai) in enumerate(
        sorted(candidatos, key=lambda t: dom.chave_ordem(t[0])), 1
    ):
        est = r["estimativa"]
        efetivo = dom.nivel_efetivo(c)
        consulta = urlencode({"territorio": ds})
        itens.append(
            {
                "posicao": pos,
                "territorio_id": c.territorio_id,
                "territorio_nome": nome,
                "tipo": "bairro" if pai else "distrito",
                "distrito_id": ds,
                "nivel": efetivo,
                "rotulo": dom.ROTULO[efetivo],
                "nivel_estimador": c.nivel_estimador,
                "nivel_equipe": c.nivel_equipe,
                "experimental": True,
                "confianca": dom.confianca(est.qualidade, r["emissoes_na_faixa"], problemas),
                "motivos": [
                    {"ordem": k, "fator": m.fator, "descricao": m.descricao, "origem": m.origem}
                    for k, m in enumerate(dom.motivos_ordenados(c), start=1)
                ],
                "notas_qualidade": notas,
                "evidencias": [
                    {
                        "tipo": "cenario",
                        "rotulo": f"Cenário de {horizonte_h} h do {distritos[ds]}",
                        "fonte_id": cenarios.FONTE_PREVISAO,
                        "endereco": f"/app/cenarios?{consulta}",
                        "parametros": {"territorio_id": ds, "horizonte_h": str(horizonte_h)},
                    },
                    {
                        "tipo": "serie",
                        "rotulo": f"Série e referência histórica de chuva do {distritos[ds]}",
                        "fonte_id": series.FONTE_CHUVA,
                        "endereco": f"/app/series?{consulta}",
                        "parametros": {"territorio_id": ds, "variavel": "chuva_mm"},
                    },
                    {
                        "tipo": "mapa",
                        "rotulo": "Mapa dos distritos, indicador de prioridade",
                        "fonte_id": "territorio-oficial",
                        "endereco": f"/app/mapa?{consulta}",
                        "parametros": {"indicador": "prioridade"},
                    },
                ],
                "janela_atencao": {"inicio": est.janela_atencao.inicio, "fim": est.janela_atencao.fim}
                if est.janela_atencao
                else None,
                "acumulado_previsto_mm": est.acumulado_previsto_mm,
                "limite_atencao_mm": est.p95_mm,
                "limite_alerta_mm": est.p99_mm,
                "ocorrencias_historicas": c.ocorrencias,
            }
        )
    return itens
