"""Pipeline completo em ordem: território → Open-Meteo (histórico, previsão, maré) → APAC (tempo real e
histórico recente) → alertas oficiais → InfoDengue → conjuntos periódicos (alagamento e
deslizamento, SINAN leptospirose, arboviroses por bairro; pulados se já carregados há menos
de `REPETIR_APOS_DIAS`) → verificar-gold.

`etl semanal` roda só a saúde (InfoDengue e SINAN): as duas séries mudam uma vez por semana.

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
# Um único agendamento de 15 min; cada fonte só é baixada na sua cadência.
# Não muda limites de frescor do produto nem cria agendamento na máquina.
INTERVALOS_OPERACIONAIS_MIN = {
    "open-meteo-previsao": 60,
    "open-meteo-mare": 180,
    "apac-chuva": 15,
    "apac-previsao": 60,
    "apac-rios": 15,
    "alertas-oficiais": 15,
    "open-meteo-historico": 1440,
}
ORDEM_OPERACIONAL = (
    ("open-meteo-previsao", None, None),
    ("open-meteo-mare", None, None),
    *ORDEM_TEMPO_REAL,
    ("open-meteo-historico", None, JANELA_HISTORICO_DIAS),
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
) -> list[Passo]:
    passos: list[Passo] = []
    if carregar_territorio is not None:
        passos.append(_territorio(engine, carregar_territorio))
    for fonte, modo, limite in ordem:
        nome = f"{fonte} ({modo})" if modo else fonte
        if intervalos_min and fonte in intervalos_min:
            with engine.connect() as c:
                recente = c.execute(
                    text(
                        "select exists(select 1 from app.etl_execucoes where fonte_id=:f "
                        "and status='sucesso' and fim > now() - :min * interval '1 minute')"
                    ),
                    {"f": fonte, "min": intervalos_min[fonte]},
                ).scalar_one()
            if recente:
                passos.append(Passo(nome, "pulado", "coleta bem-sucedida dentro da cadência operacional"))
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


def _territorio(engine: Engine, carregar: Callable[[], tuple[int, int]]) -> Passo:
    eid = execucao.iniciar(engine, execucao.FONTE_TERRITORIO)
    try:
        lidos, gravados = carregar()
    except Exception as e:  # noqa: BLE001 — só o tipo; nunca a string de conexão
        execucao.concluir(engine, eid, erro=f"Carga territorial falhou ({type(e).__name__}).")
        return Passo("territorio-oficial", "falha", f"({type(e).__name__})")
    execucao.concluir(engine, eid, lidos=lidos, gravados=gravados)
    return Passo("territorio-oficial", "sucesso", f"lidos {lidos} · gravados {gravados}")
