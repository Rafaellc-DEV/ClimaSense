"""Pipeline completo em ordem: território → Open-Meteo (histórico, previsão, maré) → APAC (tempo real e
histórico recente) → alertas oficiais → InfoDengue → conjuntos periódicos (alagamento e
deslizamento, SINAN leptospirose, arboviroses por bairro; pulados se já carregados há menos
de `REPETIR_APOS_DIAS`) → verificar-gold.

`etl semanal` roda só a saúde (InfoDengue e SINAN): as duas séries mudam uma vez por semana.

`etl operacional` é o que fica agendado (a cada 15 min): passa por todas as fontes implementadas e só baixa as que
passaram da sua cadência (`INTERVALOS_OPERACIONAIS_MIN`), do tempo real às bases anuais.

Cada passo é registrado em app.etl_execucoes. Um passo que falha não impede os seguintes (são independentes),
mas o código de saída final é diferente de zero (RF-12.6, RF-12.8).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, text

from climasense.config import Configuracao
from climasense.etl import execucao, gold

# O histórico entra em janela móvel (a bronze é acumulativa: não se rebaixa 2021→hoje a cada atualização).
JANELA_HISTORICO_DIAS = 45
JANELA_SOLO_HISTORICO_DIAS = (
    45  # ERA5-Land do solo em janela móvel; a carga completa é `run open-meteo-solo --modo historico`
)
JANELA_APAC_HISTORICO_MESES = (
    2  # mês atual e anterior; a carga completa (desde 2022) é `run apac-chuva --modo historico`
)
ESTATICAS_REPETIR_APOS_DIAS = 7  # conjuntos históricos republicados raramente

# (fonte, modo, limite)
ORDEM_FONTES: tuple[tuple[str, str | None, int | None], ...] = (
    ("open-meteo-historico", None, JANELA_HISTORICO_DIAS),
    ("open-meteo-previsao", None, None),
    ("open-meteo-mare", None, None),
    ("open-meteo-temperatura", None, None),
    ("open-meteo-solo", "previsao", None),
    ("open-meteo-solo", "historico", JANELA_SOLO_HISTORICO_DIAS),
    ("apac-chuva", None, None),
    ("apac-previsao", None, None),
    ("apac-chuva", "historico", JANELA_APAC_HISTORICO_MESES),
    ("apac-rios", None, None),
    ("apac-reservatorios", None, None),
    ("alertas-oficiais", None, None),
    ("infodengue", None, None),
    ("recife-alagamento", None, None),
    ("sinan-leptospirose", None, None),
    ("recife-arboviroses", None, None),
)
# `etl tempo-real` (a cada 10–15 min): só o que muda rápido
ORDEM_TEMPO_REAL: tuple[tuple[str, str | None, int | None], ...] = (
    ("apac-chuva", None, None),
    ("apac-previsao", None, None),
    ("apac-rios", None, None),
    ("alertas-oficiais", None, None),
)
# `etl semanal`: as séries de saúde (o InfoDengue publica uma versão por semana; o DATASUS, a cada 1–3 semanas)
ORDEM_SEMANAL: tuple[tuple[str, str | None, int | None], ...] = (
    ("infodengue", None, None),
    ("sinan-leptospirose", None, None),
)
# --- Perfil `etl operacional`: um único agendamento a cada 15 min para TODAS as fontes (RNF-05, RF-19) ---------
# Cada rodada só baixa o que passou da sua cadência; o resto é pulado sem tocar a rede. A escala segue a fonte:
# a cadência é sempre bem menor que o limite de frescor (`frescor.toml`), para que uma rodada perdida não deixe a
# fonte vencida. O teste `test_cadencia_cabe_no_limite_de_frescor` garante isso. Uma fonte que falhou tenta de novo
# no máximo a cada `RETENTAR_FALHA_MIN`, para não rebaixar um arquivo grande a cada 15 min.
CADENCIA_TEMPO_REAL_MIN = 15
CADENCIA_PREVISAO_MIN = 180  # 3 h: a previsão vence em 6 h; cada rodada grava cerca de 2.100 linhas
CADENCIA_DIARIA_MIN = 24 * 60
CADENCIA_SEMANAL_MIN = 7 * 24 * 60
CADENCIA_MENSAL_MIN = 30 * 24 * 60
RETENTAR_FALHA_MIN = 60  # esbarrar na trava de outra coleta não conta como falha (MSG_OUTRA_COLETA)
INTERVALOS_OPERACIONAIS_MIN = {
    # tempo real
    "apac-chuva": CADENCIA_TEMPO_REAL_MIN,
    "apac-rios": CADENCIA_TEMPO_REAL_MIN,
    "alertas-oficiais": CADENCIA_TEMPO_REAL_MIN,
    "apac-previsao": 60,
    # previsões de modelo
    "open-meteo-previsao": CADENCIA_PREVISAO_MIN,
    "open-meteo-temperatura": CADENCIA_PREVISAO_MIN,
    "open-meteo-solo": CADENCIA_PREVISAO_MIN,
    "open-meteo-mare": 360,
    "apac-reservatorios": 720,
    # diárias
    "open-meteo-historico": CADENCIA_DIARIA_MIN,
    "infodengue": CADENCIA_DIARIA_MIN,
    "sisagua": CADENCIA_DIARIA_MIN,
    "sinan-leptospirose": 3 * CADENCIA_DIARIA_MIN,
    # semanais
    "samu-recife": CADENCIA_SEMANAL_MIN,
    "cnes-equipamentos": CADENCIA_SEMANAL_MIN,
    "recife-alagamento": CADENCIA_SEMANAL_MIN,
    # mensais (bases anuais ou estáticas)
    "recife-arboviroses": CADENCIA_MENSAL_MIN,
    "recife-areas-risco": CADENCIA_MENSAL_MIN,
    "recife-atendimentos-grau-risco": CADENCIA_MENSAL_MIN,
    "recife-alagamento-2026": CADENCIA_MENSAL_MIN,
    "sgb-suscetibilidade-deslizamento": CADENCIA_MENSAL_MIN,
    "atlas-desastres": CADENCIA_MENSAL_MIN,
    "ibge-censo-2022-bairro": CADENCIA_MENSAL_MIN,
}
# Modos secundários de uma fonte que já roda em outro modo: `app.etl_execucoes` não guarda o modo, então a cadência
# por fonte os pularia para sempre. Rodam uma vez por dia, na primeira rodada da hora abaixo (03h no Recife).
HORA_DIARIA_UTC = 6
MODOS_DIARIOS = {("apac-chuva", "historico"), ("open-meteo-solo", "historico")}
# Do mais urgente ao mais pesado: uma carga longa não atrasa a chuva e os alertas.
ORDEM_OPERACIONAL: tuple[tuple[str, str | None, int | None], ...] = (
    *ORDEM_TEMPO_REAL,
    ("open-meteo-previsao", None, None),
    ("open-meteo-temperatura", None, None),
    ("open-meteo-solo", "previsao", None),
    ("open-meteo-mare", None, None),
    ("apac-reservatorios", None, None),
    ("open-meteo-historico", None, JANELA_HISTORICO_DIAS),
    ("open-meteo-solo", "historico", JANELA_SOLO_HISTORICO_DIAS),
    ("apac-chuva", "historico", JANELA_APAC_HISTORICO_MESES),
    ("infodengue", None, None),
    ("sisagua", None, None),
    ("sinan-leptospirose", None, None),
    ("samu-recife", None, None),
    ("cnes-equipamentos", None, None),
    ("recife-alagamento", None, None),
    ("recife-arboviroses", None, None),
    ("recife-areas-risco", None, None),
    ("recife-atendimentos-grau-risco", None, None),
    ("recife-alagamento-2026", None, None),
    ("sgb-suscetibilidade-deslizamento", None, None),
    ("atlas-desastres", None, None),
    ("ibge-censo-2022-bairro", None, None),
)
ESTATICAS = {
    ("recife-alagamento", None),
    ("sinan-leptospirose", None),
    ("recife-arboviroses", None),
}
# Quantos dias até repetir cada conjunto no `atualizar` (o padrão é ESTATICAS_REPETIR_APOS_DIAS)
REPETIR_APOS_DIAS = {"sinan-leptospirose": 6, "recife-arboviroses": 30}


@dataclass
class Passo:
    nome: str
    status: str  # sucesso | falha | pulado
    detalhe: str


# Só pula se o destino da carga estática tem dados (a tabela de execuções não guarda o modo).
DESTINO_ESTATICAS = {
    "recife-alagamento": "select count(*) from silver.ocorrencias",
    "sinan-leptospirose": "select count(*) from silver.leptospirose_semanal",
    "recife-arboviroses": "select count(*) from silver.arboviroses_bairro_ano",
}


def _recente(engine: Engine, fonte: str) -> bool:
    with engine.connect() as c:
        ultima = c.execute(
            text("select max(fim) from app.etl_execucoes where fonte_id = :f and status = 'sucesso'"),
            {"f": fonte},
        ).scalar()
        destino = DESTINO_ESTATICAS.get(fonte)
        if destino and not c.execute(text(destino)).scalar():
            return False
    dias = REPETIR_APOS_DIAS.get(fonte, ESTATICAS_REPETIR_APOS_DIAS)
    return ultima is not None and datetime.now(UTC) - ultima < timedelta(days=dias)


def atualizar(
    engine: Engine,
    mongo,
    config: Configuracao,
    forcar: bool = False,
    carregar_territorio: Callable[[], tuple[int, int]] | None = None,
    executar=execucao.executar,
    ordem=ORDEM_FONTES,
    intervalos_min: dict[str, int] | None = None,
    verificar_gold: bool = True,
    agora: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[Passo]:
    passos: list[Passo] = []
    if carregar_territorio is not None:
        passos.append(_territorio(engine, carregar_territorio))
    for fonte, modo, limite in ordem:
        nome = f"{fonte} ({modo})" if modo else fonte
        if intervalos_min is not None:
            motivo = _dentro_da_cadencia(engine, fonte, modo, intervalos_min, agora())
            if motivo:
                passos.append(Passo(nome, "pulado", motivo))
                continue
        if (fonte, modo) in ESTATICAS and not forcar and _recente(engine, fonte):
            passos.append(
                Passo(
                    nome,
                    "pulado",
                    f"já carregada nos últimos {REPETIR_APOS_DIAS.get(fonte, ESTATICAS_REPETIR_APOS_DIAS)} dias "
                    "(use --forcar)",
                )
            )
            continue
        try:
            eid = execucao.iniciar(engine, fonte)
            r = executar(engine, mongo, config, fonte, eid, limite, modo=modo)
        except Exception as erro:  # noqa: BLE001 — finalização indisponível não impede as outras fontes
            passos.append(Passo(nome, "falha", execucao.mensagem_segura(erro)))
            continue
        detalhe = f"lidos {r['lidos']} · gravados {r['gravados']} · descartados {r['descartados']}"
        passos.append(Passo(nome, r["status"], r["erro"] or detalhe if r["status"] != "sucesso" else detalhe))
    if not verificar_gold:
        return passos
    with engine.connect() as c:
        dif = gold.verificar(c)
    ruins = {t: n for t, n in dif.items() if n}
    passos.append(
        Passo(
            "verificar-gold",
            "falha" if ruins else "sucesso",
            f"{len(ruins)} tabela(s) divergente(s)" if ruins else "gold reproduzível",
        )
    )
    return passos


def _dentro_da_cadencia(
    engine: Engine, fonte: str, modo: str | None, intervalos_min: dict[str, int], agora: datetime
) -> str | None:
    """Motivo para pular o passo nesta rodada, ou None se ele deve rodar."""
    if (fonte, modo) in MODOS_DIARIOS:
        if agora.hour == HORA_DIARIA_UTC and agora.minute < CADENCIA_TEMPO_REAL_MIN:
            return None
        return f"modo diário: roda às {HORA_DIARIA_UTC:02d}h UTC"
    intervalo = intervalos_min.get(fonte)
    if intervalo is None:
        return None
    with engine.connect() as c:
        recente = c.execute(
            text(
                "select exists(select 1 from app.etl_execucoes where fonte_id=:f and ("
                "(status='sucesso' and fim > now() - :min * interval '1 minute') or "
                "(status<>'sucesso' and erro is distinct from :trava "
                "and inicio > now() - :falha * interval '1 minute')))"
            ),
            {
                "f": fonte,
                "min": intervalo,
                "falha": min(intervalo, RETENTAR_FALHA_MIN),
                "trava": execucao.MSG_OUTRA_COLETA,
            },
        ).scalar_one()
    if recente:
        return "coleta recente dentro da cadência operacional"
    return None


def rodada_diaria(agora: datetime) -> bool:
    """A primeira rodada de 15 min da hora diária também confere a gold (cara demais a cada 15 min)."""
    return agora.hour == HORA_DIARIA_UTC and agora.minute < CADENCIA_TEMPO_REAL_MIN


def _territorio(engine: Engine, carregar: Callable[[], tuple[int, int]]) -> Passo:
    eid = execucao.iniciar(engine, execucao.FONTE_TERRITORIO)
    try:
        lidos, gravados = carregar()
    except Exception as e:  # noqa: BLE001 — só o tipo; nunca a string de conexão
        execucao.concluir(engine, eid, erro=f"Carga territorial falhou ({type(e).__name__}).")
        return Passo("territorio-oficial", "falha", f"({type(e).__name__})")
    execucao.concluir(engine, eid, lidos=lidos, gravados=gravados)
    return Passo("territorio-oficial", "sucesso", f"lidos {lidos} · gravados {gravados}")
