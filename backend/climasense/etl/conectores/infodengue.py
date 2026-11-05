"""InfoDengue (Fiocruz/FGV): dengue e chikungunya do Recife por semana epidemiológica, desde 2015.

API pública sem chave: `https://info.dengue.mat.br/api/alertcity?geocode=2611606&disease=…&format=json`.
Uma linha por SE com casos notificados (`casos`, revisados retroativamente), a estimativa de *nowcasting*
(`casos_est`, IC 95% em `casos_est_min`/`casos_est_max`), Rt, incidência e o nível de alerta (1 verde … 4 vermelho).

Zika fica de fora: a série do Recife parou em 2024-SE07 (docs/pesquisa/saude-e-chuva.md §1.1); carregar seria
mostrar semanas vazias como se fossem zero.

Semana incompleta: as `SEMANAS_RECENTES_INCOMPLETAS` mais recentes da série, ou qualquer semana em que a estimativa
ainda passa do notificado em mais de 10% (o atraso de notificação ainda não foi absorvido). Nessas semanas o número
notificado baixo NÃO é queda.

Bronze: cada linha da API como veio (só campos agregados municipais; não há dado pessoal na fonte).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import text

from climasense.dominio import semana_epi
from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URL = "https://info.dengue.mat.br/api/alertcity"
AGRAVOS = ("dengue", "chikungunya")
ANO_INICIAL = 2015
SEMANAS_RECENTES_INCOMPLETAS = 4
FOLGA_NOWCAST = 1.10


def _inteiro(v) -> int | None:
    x = comum.real(v)
    return int(round(x)) if x is not None else None


def _nivel(v) -> int | None:
    x = _inteiro(v)
    return x if x in (1, 2, 3, 4) else None


class ConectorInfoDengue(Conector):
    id = "infodengue"
    fonte = FonteInfo(
        "Dengue e chikungunya no Recife por semana (InfoDengue)",
        "InfoDengue — Fiocruz / FGV",
        "https://info.dengue.mat.br/services/api",
        "derivada",
        None,
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        ano_final = ctx.agora.astimezone(comum.FUSO_RECIFE).year
        registros = []
        for agravo in AGRAVOS:
            r = self.http.get(
                URL,
                params={
                    "geocode": comum.GEOCODE_RECIFE,
                    "disease": agravo,
                    "format": "json",
                    "ew_start": 1,
                    "ew_end": 53,
                    "ey_start": ANO_INICIAL,
                    "ey_end": ano_final,
                },
                timeout=120,
            )
            r.raise_for_status()
            corpo = r.json()
            if not isinstance(corpo, list):
                raise FonteSemDados(f"O InfoDengue não devolveu a série de {agravo} (formato inesperado).")
            registros.extend({**linha, "agravo": agravo} for linha in corpo if isinstance(linha, dict))
        if not registros:
            raise FonteSemDados("O InfoDengue não devolveu nenhuma semana para o Recife.")
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {}
        linhas = []
        for r in bruto.to_dict("records"):
            se = semana_epi.de_codigo(r.get("SE"))
            if se is None:
                self.descartes["semana_invalida"] = self.descartes.get("semana_invalida", 0) + 1
                continue
            inicio = semana_epi.inicio_semana(*se)
            ms = comum.real(r.get("data_iniSE"))
            if ms is not None and datetime.fromtimestamp(ms / 1000, UTC).date() != inicio:
                self.descartes["inicio_da_semana_diverge"] = (
                    self.descartes.get("inicio_da_semana_diverge", 0) + 1
                )
                continue
            casos = _inteiro(r.get("casos"))
            linhas.append(
                {
                    "agravo": r["agravo"],
                    "ano": se[0],
                    "semana": se[1],
                    "inicio": inicio,
                    "casos": casos if casos is None or casos >= 0 else None,
                    "casos_est": comum.numero(r.get("casos_est")),
                    "casos_est_min": comum.numero(r.get("casos_est_min")),
                    "casos_est_max": comum.numero(r.get("casos_est_max")),
                    "rt": comum.numero(r.get("Rt")),
                    "p_rt1": comum.numero(r.get("p_rt1")),
                    "p_inc100k": comum.numero(r.get("p_inc100k")),
                    "nivel": _nivel(r.get("nivel")),
                    "nivel_inc": _inteiro(r.get("nivel_inc")),
                    "receptivo": _inteiro(r.get("receptivo")),
                    "transmissao": _inteiro(r.get("transmissao")),
                    "versao_modelo": (str(r.get("versao_modelo") or "")[:20] or None),
                }
            )
        df = pd.DataFrame(linhas)
        if df.empty:
            return df
        df = df.drop_duplicates(subset=["agravo", "ano", "semana"], keep="last")
        df["incompleta"] = False
        for _, grupo in df.groupby("agravo"):
            recentes = grupo.sort_values("inicio").tail(SEMANAS_RECENTES_INCOMPLETAS).index
            df.loc[recentes, "incompleta"] = True
        atraso = (
            df["casos_est"].notna() & df["casos"].notna() & (df["casos_est"] > df["casos"] * FOLGA_NOWCAST)
        )
        df.loc[atraso, "incompleta"] = True
        return df.sort_values(["agravo", "inicio"]).reset_index(drop=True)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        """Upsert por (agravo, ano, semana): o InfoDengue revisa as semanas passadas a cada versão do modelo."""
        colunas = list(df.columns)
        with ctx.engine.begin() as c:
            c.execute(
                text(
                    "insert into silver.infodengue_semanal (agravo, ano, semana, inicio, casos, casos_est, "
                    "casos_est_min, casos_est_max, rt, p_rt1, p_inc100k, nivel, nivel_inc, receptivo, transmissao, "
                    "versao_modelo, incompleta, coletado_em, execucao_id) values (:agravo, :ano, :semana, :inicio, "
                    ":casos, :casos_est, :casos_est_min, :casos_est_max, :rt, :p_rt1, :p_inc100k, :nivel, :nivel_inc, "
                    ":receptivo, :transmissao, :versao_modelo, :incompleta, :coletado_em, :ex) "
                    "on conflict (agravo, ano, semana) do update set inicio = excluded.inicio, casos = excluded.casos, "
                    "casos_est = excluded.casos_est, casos_est_min = excluded.casos_est_min, "
                    "casos_est_max = excluded.casos_est_max, rt = excluded.rt, p_rt1 = excluded.p_rt1, "
                    "p_inc100k = excluded.p_inc100k, nivel = excluded.nivel, nivel_inc = excluded.nivel_inc, "
                    "receptivo = excluded.receptivo, transmissao = excluded.transmissao, "
                    "versao_modelo = excluded.versao_modelo, incompleta = excluded.incompleta, "
                    "coletado_em = excluded.coletado_em, execucao_id = excluded.execucao_id"
                ),
                [
                    {
                        **{k: comum.valor_sql(r[k], k in INTEIRAS) for k in colunas},
                        "coletado_em": ctx.agora,
                        "ex": ctx.execucao_id,
                    }
                    for r in df.to_dict("records")
                ],
            )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_SAUDE)


INTEIRAS = {"ano", "semana", "casos", "nivel", "nivel_inc", "receptivo", "transmissao"}
