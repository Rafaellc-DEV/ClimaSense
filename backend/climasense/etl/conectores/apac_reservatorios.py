"""Reservatórios que controlam o Capibaribe a montante do Recife, pela API pública da APAC (sem cadastro).

`GET /reservatorio?bacia_hidrografica=Capibaribe` devolve a leitura mais recente de cada reservatório da bacia
(15 na gravação de 06/11/2026); o conector guarda só os quatro de interesse (Tapacurá, Goitá, Carpina e Matriz da Luz),
casados por `codigo_estacao`, nunca pelo nome (o texto às vezes vem com acentos quebrados). Leitura com data futura é
descartada. Contexto da bacia, não previsão: reservatório cheio não é inundação (RN-06, RN-11).
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.apac_rios import corrigir_texto, texto_quebrado
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URL_API = "https://api.apac.pe.gov.br/api.php"

# codigo_estacao → nome e município canônicos (usados se o texto da API vier com bytes perdidos)
RESERVATORIOS: dict[int, tuple[str, str]] = {
    39175000: ("Tapacurá", "São Lourenço da Mata"),
    39151000: ("Goitá", "Paudalho"),
    39145550: ("Carpina (Lagoa do Carro)", "Lagoa do Carro"),
    39187900: ("Matriz da Luz", "São Lourenço da Mata"),
}


class ConectorApacReservatorios(Conector):
    id = "apac-reservatorios"
    fonte = FonteInfo(
        "Reservatórios do Capibaribe (Tapacurá, Goitá, Carpina e Matriz da Luz)",
        "APAC — Agência Pernambucana de Águas e Clima",
        URL_API,
        "observada",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}
        self.cadastro: dict[int, dict] = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        r = self.http.get(f"{URL_API}/reservatorio", params={"bacia_hidrografica": "Capibaribe"}, timeout=90)
        r.raise_for_status()
        corpo = r.json()
        if not isinstance(corpo, list) or not corpo:
            detalhe = corpo.get("erro", corpo) if isinstance(corpo, dict) else "lista vazia"
            raise FonteSemDados(f"APAC sem dados de reservatórios do Capibaribe: {str(detalhe)[:200]}")
        return [x for x in corpo if isinstance(x, dict)]

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes, self.cadastro = {}, {}
        hoje = ctx.agora.astimezone(comum.FUSO_RECIFE).date()
        linhas = []
        achados = set()
        for r in bruto.to_dict("records"):
            cod = comum.real(r.get("codigo_estacao"))
            cod = int(cod) if cod is not None else None
            if cod not in RESERVATORIOS:
                continue  # os outros reservatórios da bacia ficam só na bronze
            achados.add(cod)
            nome_c, municipio_c = RESERVATORIOS[cod]
            try:
                dia = date.fromisoformat(str(r.get("data_leitura_cota_atual"))[:10])
            except ValueError:
                self.descartes["sem_data_da_leitura"] = self.descartes.get("sem_data_da_leitura", 0) + 1
                continue
            if dia > hoje:
                self.descartes["leitura_no_futuro"] = self.descartes.get("leitura_no_futuro", 0) + 1
                continue
            municipio = corrigir_texto(r.get("municipio"))
            status = corrigir_texto(r.get("status"))
            volume_pct = comum.numero(r.get("volume_percentual"))
            self.cadastro[cod] = {
                "codigo_estacao": cod,
                "nome": nome_c,
                "municipio": municipio_c if municipio is None or texto_quebrado(municipio) else municipio,
                "bacia": "Capibaribe",
                "lat": comum.real(r.get("latitude")),
                "lon": comum.real(r.get("longitude")),
                "capacidade_m3": comum.numero(r.get("capacidade")),
                "uso_principal": corrigir_texto(r.get("uso_principal")),
            }
            linhas.append(
                {
                    "codigo_estacao": cod,
                    "data_leitura": dia,
                    "cota_m": comum.numero(r.get("cota_atual")),
                    "volume_m3": comum.numero(r.get("volume_atual")),
                    "volume_pct": volume_pct,
                    "status": None if status is None or texto_quebrado(status) else status[:60],
                    "cor": corrigir_texto(r.get("cor_status_reservatorio")),
                }
            )
        faltam = set(RESERVATORIOS) - achados
        if faltam:
            self.descartes["reservatorio_ausente_na_resposta"] = len(faltam)
        if not linhas:
            raise FonteSemDados("Nenhum dos reservatórios do Capibaribe de interesse trouxe leitura válida.")
        return pd.DataFrame(linhas).drop_duplicates(["codigo_estacao", "data_leitura"], keep="last")

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        with ctx.engine.begin() as c:
            c.execute(
                text(
                    "insert into silver.reservatorios (codigo_estacao, nome, municipio, bacia, lat, lon, capacidade_m3, "
                    "uso_principal, fonte_id, atualizado_em) values (:codigo_estacao, :nome, :municipio, :bacia, :lat, "
                    ":lon, :capacidade_m3, :uso_principal, :f, :agora) on conflict (codigo_estacao) do update set "
                    "nome = excluded.nome, municipio = excluded.municipio, bacia = excluded.bacia, lat = excluded.lat, "
                    "lon = excluded.lon, capacidade_m3 = excluded.capacidade_m3, "
                    "uso_principal = excluded.uso_principal, atualizado_em = excluded.atualizado_em"
                ),
                [{**e, "f": self.id, "agora": ctx.agora} for e in self.cadastro.values()],
            )
            antes = c.execute(text("select count(*) from silver.reservatorios_leituras")).scalar()
            c.execute(
                text(
                    "insert into silver.reservatorios_leituras (codigo_estacao, data_leitura, cota_m, volume_m3, "
                    "volume_pct, status, cor, coletado_em, visto_em, execucao_id) values (:codigo_estacao, "
                    ":data_leitura, :cota_m, :volume_m3, :volume_pct, :status, :cor, :agora, :agora, :ex) "
                    "on conflict (codigo_estacao, data_leitura) do update set cota_m = excluded.cota_m, "
                    "volume_m3 = excluded.volume_m3, volume_pct = excluded.volume_pct, status = excluded.status, "
                    "cor = excluded.cor, visto_em = excluded.visto_em"
                ),
                [
                    {
                        **{k: comum.valor_sql(v) for k, v in r.items() if k != "data_leitura"},
                        "data_leitura": r["data_leitura"],
                        "agora": ctx.agora,
                        "ex": ctx.execucao_id,
                    }
                    for r in df.to_dict("records")
                ],
            )
            return c.execute(text("select count(*) from silver.reservatorios_leituras")).scalar() - antes

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_RESERVATORIOS)
