"""Saúde depois da chuva (specs/foco-chuvas.md §9): dengue, chikungunya e leptospirose no Recife, a janela de
vigilância de leptospirose e o histórico de alagamentos e deslizamentos por bairro.

Tudo vem da gold (gerada só por SQL a partir da silver) e dos registros que o ClimaSense já tem (estágios
declarados, ocorrências da Defesa Civil, chuva medida pela APAC). Nada aqui calcula risco nem probabilidade de
doença: são contagens das fontes oficiais e um lembrete de vigilância (RN-06).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import estagio as dom
from climasense.dominio import janela_leptospirose as janela
from climasense.dominio.distritos import nome_distrito
from climasense.dominio.supressao import deve_suprimir, suprimir
from climasense.etl import frescor
from climasense.etl.conectores.comum import FUSO_RECIFE
from climasense.infra import cache
from climasense.infra.postgres import em_paralelo
from climasense.servicos import estagios

AGRAVOS = {
    "dengue": ("Dengue", "infodengue"),
    "chikungunya": ("Chikungunya", "infodengue"),
    "leptospirose": ("Leptospirose", "sinan-leptospirose"),
}
AGRAVOS_BAIRRO = ("dengue", "chikungunya")
TIPOS_OCORRENCIA = ("alagamento", "deslizamento")
FONTE_CHUVA_SEMANAL = "open-meteo-historico"
SEMANAS_PADRAO = 104


def hoje_recife(agora: datetime) -> date:
    return agora.astimezone(FUSO_RECIFE).date()


def domingo(d: date) -> date:
    return d - timedelta(days=(d.weekday() + 1) % 7)


# ------------------------------------------------------------------ séries semanais
_SEMANAS = (
    "select ano, semana, inicio, casos, confirmados, casos_estimados, ic_inf, ic_sup, nivel_alerta, rt, "
    "incompleta from gold.saude_semanal where agravo = :a "
)
_SEMANAS_DESDE = _SEMANAS + "and inicio >= :d order by inicio"
_SEMANAS_RECENTES = _SEMANAS + "order by inicio desc limit :n"


def _semanas(db: Session, agravo: str, desde: date | None = None, limite: int | None = None) -> list[dict]:
    """Com `limite`: as mais recentes primeiro. Com `desde`: em ordem cronológica."""
    sql = _SEMANAS_RECENTES if limite else _SEMANAS_DESDE
    return cache.obter(
        "saude_semanal",
        ("semanas", agravo, desde, limite),
        cache.MEDIO_S,  # a série só muda quando o ETL semanal carrega
        lambda: [
            dict(r)
            for r in db.execute(
                text(sql), {"a": agravo, "d": desde or date(1900, 1, 1), "n": limite}
            ).mappings()
        ],
    )


def variacao_4s_pct(semanas_desc: list[dict], tem_estimativa: bool) -> float | None:
    """Últimas 4 semanas com dado utilizável contra as 4 anteriores, em %.

    Com nowcasting (InfoDengue) vale a estimativa, que já corrige o atraso; sem ela (SINAN), as semanas incompletas
    ficam de fora (o número baixo delas é atraso, não queda). Menos de 8 semanas utilizáveis ou base zero → None."""
    valores: list[float] = []
    for s in semanas_desc:
        if tem_estimativa and s["casos_estimados"] is not None:
            valores.append(float(s["casos_estimados"]))
        elif not s["incompleta"] and s["casos"] is not None:
            valores.append(float(s["casos"]))
        if len(valores) == 8:
            break
    if len(valores) < 8:
        return None
    ultimas, anteriores = sum(valores[:4]), sum(valores[4:])
    return None if anteriores == 0 else round((ultimas - anteriores) / anteriores * 100, 1)


def semana_utilizavel(fonte_id: str, inicio: date | None, agora: datetime) -> bool:
    """A semana (que começa em `inicio`) ainda serve para a equipe? Vale a idade do FIM da semana (sábado) contra o
    limite de frescor da fonte (`etl/frescor.toml`): mais velha que isso é série parada, não dado atual. Sem semana,
    não serve; fonte sem limite definido não reprova por idade."""
    if inicio is None:
        return False
    limite = frescor.limite_frescor_h(fonte_id)
    if limite is None:
        return True
    idade_h = (hoje_recife(agora) - (inicio + timedelta(days=6))).days * 24
    return idade_h <= limite


def _recentes_todos(db: Session) -> dict[str, list[dict]]:
    """16 semanas mais recentes de cada agravo numa só consulta (eram 3), guardadas por `cache.MEDIO_S`: a série
    só muda quando o ETL semanal carrega."""

    def ler() -> dict[str, list[dict]]:
        linhas = db.execute(
            text(
                "select * from (select agravo, ano, semana, inicio, casos, confirmados, casos_estimados, ic_inf, "
                "ic_sup, nivel_alerta, rt, incompleta, row_number() over (partition by agravo order by inicio desc) "
                "as ordem from gold.saude_semanal where agravo = any(:a)) x where ordem <= 16 "
                "order by agravo, inicio desc"
            ),
            {"a": list(AGRAVOS)},
        ).mappings()
        saida: dict[str, list[dict]] = {a: [] for a in AGRAVOS}
        for r in linhas:
            saida[r["agravo"]].append(dict(r))
        return saida

    return cache.obter("saude_semanal", "recentes", cache.MEDIO_S, ler)


def resumo_agravos(db: Session, agora: datetime) -> list[dict]:
    """Um item por agravo com a SEMANA MAIS RECENTE COM DADO (casos não nulos).

    `utilizavel` = essa semana não é mais velha que o limite de frescor da fonte (`semana_utilizavel`). Quando
    não é (ou não há dado), a contagem NÃO é devolvida como se fosse atual: casos, estimados, confirmados, rt,
    variação, nível e `ultima_semana` saem nulos, `ultima_semana_com_dado` diz até quando a série vai e `motivo`
    explica (RN-01: ausência não é zero e série parada não é número atual)."""
    todos = _recentes_todos(db)
    saida = []
    for agravo, (nome, fonte_id) in AGRAVOS.items():
        recentes = todos.get(agravo, [])
        ultima = next((s for s in recentes if s["casos"] is not None), None)
        ref = (
            {"ano": ultima["ano"], "semana": ultima["semana"], "inicio": ultima["inicio"]} if ultima else None
        )
        utilizavel = semana_utilizavel(fonte_id, ultima["inicio"] if ultima else None, agora)
        mostra = ultima if utilizavel else None
        motivo = None
        if not utilizavel:
            limite = frescor.limite_frescor_h(fonte_id)
            motivo = (
                f"Dados insuficientes: a fonte {fonte_id} não tem nenhuma semana com dado."
                if ultima is None
                else f"Dados insuficientes: a última semana com dado da fonte {fonte_id} é a SE "
                f"{ultima['semana']}/{ultima['ano']} (termina em {(ultima['inicio'] + timedelta(days=6)).strftime('%d/%m/%Y')}), "
                f"mais antiga que o limite de {limite / 24:.0f} dias da fonte."
            )
        saida.append(
            {
                "agravo": agravo,
                "nome": nome,
                "fonte_id": fonte_id,
                "utilizavel": utilizavel,
                "ultima_semana_com_dado": ref,
                "motivo": motivo,
                "ultima_semana": ref if utilizavel else None,
                "casos": mostra["casos"] if mostra else None,
                "casos_estimados": mostra["casos_estimados"] if mostra else None,
                "confirmados": mostra["confirmados"] if mostra else None,
                "rt": mostra["rt"] if mostra else None,
                "variacao_4s_pct": variacao_4s_pct(recentes, fonte_id == "infodengue") if mostra else None,
                "nivel_alerta": mostra["nivel_alerta"] if mostra else None,
                "incompleta": bool(mostra["incompleta"]) if mostra else None,
            }
        )
    return saida


def chuva_semanal(db: Session, desde: date) -> list[dict]:
    """Chuva semanal do Recife (soma da diária da reanálise ERA5, média dos distritos), por semana epidemiológica
    (domingo a sábado). Semana sem nenhum dia com dado → chuva_mm nulo, nunca 0 (RN-02). Guardada por
    `cache.MEDIO_S`."""
    return cache.obter(
        "saude_semanal", ("chuva", desde), cache.MEDIO_S, lambda: _ler_chuva_semanal(db, desde)
    )


def _ler_chuva_semanal(db: Session, desde: date) -> list[dict]:
    linhas = db.execute(
        text(
            "select (dia - extract(dow from dia)::integer) as inicio, sum(acumulado_mm) as chuva_mm, "
            "count(acumulado_mm)::integer as dias_com_dado from gold.chuva_diaria "
            "where territorio_id = 'recife' and tipo = 'derivada' and dia >= :d group by 1 order by 1"
        ),
        {"d": domingo(desde)},
    ).mappings()
    return [
        {
            "inicio": r["inicio"],
            "chuva_mm": round(float(r["chuva_mm"]), 1) if r["chuva_mm"] is not None else None,
            "dias_com_dado": r["dias_com_dado"],
        }
        for r in linhas
    ]


def semanal(db: Session, agravo: str, desde: date | None, agora: datetime) -> dict:
    desde = desde or domingo(hoje_recife(agora) - timedelta(weeks=SEMANAS_PADRAO))
    itens = [
        {
            "ano": s["ano"],
            "semana": s["semana"],
            "inicio": s["inicio"],
            "casos": s["casos"],
            "confirmados": s["confirmados"],
            "casos_estimados": s["casos_estimados"],
            "ic_inf": s["ic_inf"],
            "ic_sup": s["ic_sup"],
            "nivel_alerta": s["nivel_alerta"],
            "incompleta": bool(s["incompleta"]),
        }
        for s in _semanas(db, agravo, desde=domingo(desde))
    ]
    return {"agravo": agravo, "desde": domingo(desde), "itens": itens, "chuva": chuva_semanal(db, desde)}


# ------------------------------------------------------------------ arboviroses por bairro
def anos_bairros(db: Session, agravo: str) -> list[int]:
    return list(
        db.execute(
            text(
                "select distinct ano from silver.arboviroses_bairro_ano where agravo = :a order by ano desc"
            ),
            {"a": agravo},
        ).scalars()
    )


def _suprimir_bairros(itens: list[dict], minimo: int) -> tuple[list[dict], bool]:
    """Casos e notificados de 1 a `minimo - 1` saem nulos (`suprimido`). Devolve também se alguma célula de casos
    foi suprimida. A ordem não pode vazar o valor: ≥ mínimo (decrescente), suprimidos (por nome), zeros (por nome)."""
    saida, houve = [], False
    for i in itens:
        casos, s_casos = suprimir(i["casos"], minimo)
        notificados, s_notif = suprimir(i["notificados"], minimo)
        houve = houve or s_casos
        saida.append({**i, "casos": casos, "notificados": notificados, "suprimido": s_casos or s_notif})

    def chave(i: dict):
        if i["suprimido"]:
            return (1, 0, i["bairro_nome"])
        return (
            (0, -(i["casos"] or 0), i["bairro_nome"]) if (i["casos"] or 0) > 0 else (2, 0, i["bairro_nome"])
        )

    return sorted(saida, key=chave), houve


def bairros(db: Session, agravo: str, ano: int | None, supressao_minima: int = 5) -> dict:
    anos = anos_bairros(db, agravo)
    ano = ano if ano is not None else (anos[0] if anos else None)
    if ano is None or ano not in anos:
        return {"agravo": agravo, "ano": ano, "itens": [], "anos_disponiveis": anos, "total_confirmados": None,
                "confirmados_sem_bairro": None, "total_notificados": None}  # fmt: skip
    # o ano está publicado: bairro sem nenhuma notificação no arquivo anual é zero de verdade
    itens = [
        dict(r)
        for r in db.execute(
            text(
                "select t.id as bairro_id, t.nome_exibicao as bairro_nome, t.pai_id as distrito_id, "
                "coalesce(g.casos, 0) as casos, coalesce(g.notificados, 0) as notificados from app.territorios t "
                "left join gold.arboviroses_bairro_ano g on g.bairro_id = t.id and g.agravo = :a and g.ano = :n "
                "where t.tipo = 'bairro' order by casos desc, t.nome_exibicao"
            ),
            {"a": agravo, "n": ano},
        ).mappings()
    ]
    total = (
        db.execute(
            text(
                "select sum(confirmados)::integer as total, "
                "coalesce(sum(confirmados) filter (where territorio_id is null), 0)::integer as sem_bairro, "
                "sum(notificados)::integer as notificados, max(fonte_atualizada_em) as atualizada "
                "from silver.arboviroses_bairro_ano where agravo = :a and ano = :n"
            ),
            {"a": agravo, "n": ano},
        )
        .mappings()
        .one()
    )
    itens, houve_supressao = _suprimir_bairros(itens, supressao_minima)
    # Supressão complementar: com uma célula escondida, total e "sem bairro" publicados juntos a revelariam por
    # diferença; então "sem bairro" sai nulo sempre que algum bairro foi suprimido (ou se ele próprio é pequeno).
    sem_bairro_suprimido = houve_supressao or deve_suprimir(total["sem_bairro"], supressao_minima)
    return {
        "agravo": agravo,
        "ano": ano,
        "itens": itens,
        "anos_disponiveis": anos,
        "total_confirmados": suprimir(total["total"], supressao_minima)[0],
        "confirmados_sem_bairro": None if sem_bairro_suprimido else total["sem_bairro"],
        "sem_bairro_suprimido": sem_bairro_suprimido,
        "total_notificados": suprimir(total["notificados"], supressao_minima)[0],
        "fonte_atualizada_em": total["atualizada"],
    }


# ------------------------------------------------------------------ janela de leptospirose
def _rotulo(d: date) -> str:
    return d.strftime("%d/%m")


def gatilhos_leptospirose(db: Session, agora: datetime) -> list[janela.Gatilho]:
    """Gatilhos dos últimos 60 dias, com a mesma régua dos estágios (limiar de Alerta de chuva em 24 h)."""
    hoje = hoje_recife(agora)
    desde = hoje - timedelta(days=2 * janela.DURACAO_DIAS)
    inicio_utc = datetime.combine(desde, datetime.min.time(), FUSO_RECIFE)
    limiar = estagios.parametros_atuais(db)["parametros"].chuva_24h_alerta_mm
    gatilhos: list[janela.Gatilho] = []

    def lista(sql: str, params: dict):
        return lambda s: [dict(r) for r in s.execute(text(sql), params).mappings()]

    # as três fontes de gatilho são independentes: lidas ao mesmo tempo (banco remoto)
    declaracoes, atendimentos, medidas = em_paralelo(
        db,
        [
            lista(
                _SQL_GATILHO_ESTAGIO,
                {"i": inicio_utc, "agora": agora, "enc": dom.ENCERRADO},
            ),
            lista(_SQL_GATILHO_OCORRENCIA, {"i": inicio_utc, "agora": agora}),
            lista(
                _SQL_GATILHO_CHUVA,
                {"d": desde, "hoje": hoje, "l": limiar, "i": inicio_utc, "agora": agora},
            ),
        ],
    )
    for r in declaracoes:
        gatilhos.append(
            janela.Gatilho(
                r["dia"],
                "estagio",
                r["territorio_id"],
                nome_distrito(r["nome_exibicao"]),
                f"estágio {dom.ROTULO[r['estagio']]} declarado",
            )  # fmt: skip
        )
    for r in atendimentos:
        gatilhos.append(
            janela.Gatilho(
                r["dia"],
                "ocorrencia",
                r["territorio_id"],
                nome_distrito(r["nome_exibicao"]),
                f"{r['n']} atendimento(s) de alagamento da Defesa Civil",
            )  # fmt: skip
        )
    # chuva MEDIDA nos pluviômetros (APAC): dia a dia e a leitura de agora, só do próprio distrito (não herdada)
    for r in medidas:
        gatilhos.append(
            janela.Gatilho(
                r["dia"],
                "chuva",
                r["territorio_id"],
                nome_distrito(r["nome_exibicao"]),
                f"{float(r['max_mm']):.0f} mm em 24 h medidos pela APAC (limiar de Alerta {limiar:.0f} mm)",
            )  # fmt: skip
        )
    return gatilhos


_SQL_GATILHO_ESTAGIO = (
    "select d.territorio_id, t.nome_exibicao, d.estagio, "
    "(d.declarado_em at time zone 'America/Recife')::date as dia from app.estagio_declaracoes d "
    "join app.territorios t on t.id = d.territorio_id "
    "where d.estagio in ('alerta', 'critico') and d.declarado_em >= :i and d.declarado_em <= :agora "
    # só declaração vigente: a equipe pode encerrar o estágio (dele, do distrito ou do Recife) depois
    "and not exists (select 1 from app.estagio_declaracoes e where e.estagio = :enc "
    "and e.declarado_em > d.declarado_em and e.declarado_em <= :agora "
    "and e.territorio_id in (d.territorio_id, t.pai_id, 'recife'))"
)
_SQL_GATILHO_OCORRENCIA = (
    "select o.territorio_id, t.nome_exibicao, (o.registrado_em at time zone 'America/Recife')::date as dia, "
    "count(*) as n from silver.ocorrencias o join app.territorios t on t.id = o.territorio_id "
    "where o.tipo = 'alagamento' and o.registrado_em >= :i and o.registrado_em <= :agora group by 1, 2, 3"
)
_SQL_GATILHO_CHUVA = (
    "select c.territorio_id, t.nome_exibicao, c.dia, c.max_mm from gold.chuva_apac_diaria c "
    "join app.territorios t on t.id = c.territorio_id where c.nivel = 'distrito' and c.herdado_de is null "
    "and c.dia >= :d and c.dia <= :hoje and c.max_mm >= :l "
    "union all "
    "select a.territorio_id, t.nome_exibicao, (a.lida_em at time zone 'America/Recife')::date, "
    "a.chuva_24h_max_mm from gold.chuva_apac_agora a join app.territorios t on t.id = a.territorio_id "
    "where a.nivel = 'distrito' and a.herdado_de is null and a.n_atualizadas > 0 "
    "and a.chuva_24h_max_mm >= :l and a.lida_em >= :i and a.lida_em <= :agora"
)


def janela_leptospirose(db: Session, agora: datetime) -> dict | None:
    """Janela de vigilância só enquanto vale: gatilhos vigentes (declaração encerrada não conta) e o último
    gatilho a no máximo 30 dias. Janela já encerrada (alagamento de referência antigo demais) não é mostrada."""
    jan = janela.calcular(gatilhos_leptospirose(db, agora), hoje_recife(agora), _rotulo)
    return jan if jan and jan["ativa"] else None


# ------------------------------------------------------------------ onde já aconteceu
def ocorrencias_historico(db: Session, tipo: str) -> dict:
    itens = [
        dict(r)
        for r in db.execute(
            text(
                "select o.territorio_id as bairro_id, t.nome_exibicao as bairro_nome, o.distrito_id, o.registros, "
                "o.dias_com_registro, o.primeiro_dia as primeiro_registro, o.ultimo_dia as ultimo_registro "
                "from gold.ocorrencias_bairro o join app.territorios t on t.id = o.territorio_id "
                "where o.tipo = :t order by o.registros desc, t.nome_exibicao"
            ),
            {"t": tipo},
        ).mappings()
    ]
    return {
        "tipo": tipo,
        "itens": itens,
        "total_registros": sum(i["registros"] for i in itens),
        "bairros_com_registro": len(itens),
        "periodo_inicio": min((i["primeiro_registro"] for i in itens), default=None),
        "periodo_fim": max((i["ultimo_registro"] for i in itens), default=None),
    }


def carregada(db: Session, fonte_id: str) -> bool:
    return (
        db.execute(
            text("select 1 from app.etl_execucoes where fonte_id = :f and status = 'sucesso' limit 1"),
            {"f": fonte_id},
        ).first()
        is not None
    )
