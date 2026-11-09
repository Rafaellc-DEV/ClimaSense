"""Previsão horária, tendência de chuva e radar da APAC (contexto de aviso; NÃO é chuva medida).

Três rotas públicas da API da APAC, cada uma tolerada isoladamente (uma falha não derruba as outras):

- `GET /previsao_municipio?municipio=Recife`: previsão horária de 5 dias (temperatura, umidade, chuva prevista).
  A API devolve `codigo_municipio` 2612000 para o Recife (o IBGE é 2611606) e, pelo código IBGE, devolve outro
  município (Pombos). Por isso o lote só é gravado se o nome for Recife, o código for um dos dois conhecidos e o
  ponto cair na caixa do Recife; qualquer outro lote é descartado inteiro. O código recebido fica guardado.
- `GET /tendencia_precipitacao`: categoria diária por mesorregião; só a Metropolitana (onde fica o Recife).
- `GET /radar_meteorologico`: lista de imagens do radar. Guarda só as URLs (https, domínio da APAC) e a hora; a
  imagem NUNCA é baixada.

Horas locais do Recife (UTC−3) viram UTC. Valor ausente fica nulo, nunca 0 (RN-02).
"""

from __future__ import annotations

import unicodedata
from urllib.parse import urlparse

import pandas as pd
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores.apac import URL_API, corrigir_texto, json_utf8
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

CODIGOS_RECIFE = {2611606, 2612000}  # IBGE e o código que a APAC devolve para o Recife
CAIXA_RECIFE = {"lat": (-8.20, -7.90), "lon": (-35.10, -34.80)}
MESORREGIAO = "metropolitana"
ROTAS = {
    "previsao": "previsao_municipio",
    "tendencia": "tendencia_precipitacao",
    "radar": "radar_meteorologico",
}
DOMINIO_RADAR = ".apac.pe.gov.br"


def _simples(t) -> str:
    base = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return base.strip().lower()


def previsao_valida(r: dict) -> bool:
    """O registro é mesmo do Recife? (nome, código conhecido e coordenadas)."""
    lat, lon = comum.real(r.get("latitude")), comum.real(r.get("longitude"))
    codigo = comum.real(r.get("codigo_municipio"))
    return bool(
        _simples(r.get("municipio")) == "recife"
        and codigo is not None
        and int(codigo) in CODIGOS_RECIFE
        and lat is not None
        and lon is not None
        and CAIXA_RECIFE["lat"][0] <= lat <= CAIXA_RECIFE["lat"][1]
        and CAIXA_RECIFE["lon"][0] <= lon <= CAIXA_RECIFE["lon"][1]
    )


def url_radar_valida(u) -> str | None:
    if not isinstance(u, str):
        return None
    p = urlparse(u.strip())
    ok = p.scheme == "https" and (p.hostname or "").endswith(DOMINIO_RADAR)
    return u.strip() if ok else None


def _py(chave: str, v):
    """Valor do DataFrame pronto para o driver (NaN/NaT → None; Timestamp → datetime com fuso, não date)."""
    if v is None or v is pd.NaT or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if chave == "codigo_recebido":
        return int(v)
    return v.item() if hasattr(v, "item") else v


class ConectorApacPrevisao(Conector):
    id = "apac-previsao"
    fonte = FonteInfo(
        "Previsão horária do Recife, tendência de chuva e radar (APAC)",
        "APAC — Agência Pernambucana de Águas e Clima",
        URL_API,
        "prevista",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}
        self._falhas: list[str] = []

    def _get(self, rota: str, params: dict | None = None):
        r = self.http.get(f"{URL_API}/{rota}", params=params or {}, timeout=90)
        r.raise_for_status()
        return json_utf8(r)

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        registros, self._falhas = [], []
        for alvo, rota in ROTAS.items():
            try:
                corpo = self._get(rota, {"municipio": "Recife"} if alvo == "previsao" else None)
            except Exception:  # noqa: BLE001 — a rota fora do ar não pode derrubar as outras
                corpo = None
            if not isinstance(corpo, list) or not corpo:
                self._falhas.append(alvo)
                continue
            registros.extend({**r, "_endpoint": alvo} for r in corpo if isinstance(r, dict))
        if not registros:
            raise FonteSemDados("APAC sem previsão, tendência nem radar nesta coleta.")
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {f"rota_indisponivel:{a}": 1 for a in self._falhas}
        linhas: list[dict] = []
        for r in bruto.to_dict("records"):
            alvo = r.get("_endpoint")
            if alvo == "previsao":
                linhas.extend(self._previsao(r))
            elif alvo == "tendencia":
                linhas.extend(self._tendencia(r))
            elif alvo == "radar":
                linhas.extend(self._radar(r))
        return pd.DataFrame(linhas)

    def _descartar(self, motivo: str) -> list[dict]:
        self.descartes[motivo] = self.descartes.get(motivo, 0) + 1
        return []

    def _previsao(self, r: dict) -> list[dict]:
        if not previsao_valida(r):
            return self._descartar("previsao_de_outro_municipio_ou_codigo_invalido")
        hora = comum.hora_local(r.get("data"))
        if hora is None:
            return self._descartar("previsao_sem_hora")
        umidade = comum.real(r.get("umidade_relativa"))
        return [
            {
                "alvo": "previsao",
                "hora_prevista": hora,
                "temperatura_c": comum.real(r.get("temperatura")),
                "umidade_pct": umidade if umidade is not None and 0 <= umidade <= 100 else None,
                "precipitacao_mm": comum.numero(r.get("precipitacao")),
                "codigo_recebido": int(comum.real(r.get("codigo_municipio"))),
            }
        ]

    def _tendencia(self, r: dict) -> list[dict]:
        if _simples(r.get("mesoregiao")) != MESORREGIAO:
            return []  # outras mesorregiões não valem para o Recife (não é descarte de erro)
        try:
            dia = pd.Timestamp(str(r.get("data"))).date()
        except (ValueError, TypeError):
            return self._descartar("tendencia_sem_data")
        categoria = corrigir_texto(r.get("categoria"))
        if not categoria:
            return self._descartar("tendencia_sem_categoria")
        return [
            {
                "alvo": "tendencia",
                "mesorregiao": "Metropolitana",
                "dia": dia,
                "categoria": categoria[:60],
                "faixa_mm": corrigir_texto(r.get("categoria_valores"))[:40] or None,
                "atualizado_em": comum.hora_local(r.get("data_atualizacao")),
            }
        ]

    def _radar(self, r: dict) -> list[dict]:
        hora = comum.hora_local(r.get("data_referencia"))
        lat, lon = comum.real(r.get("latitude")), comum.real(r.get("longitude"))
        if hora is None or lat is None or lon is None:
            return self._descartar("radar_sem_hora_ou_posicao")
        urls = {k: url_radar_valida(r.get(k)) for k in ("acumulado_1h", "acumulado_24h", "cappi_1km")}
        if not any(urls.values()):
            return self._descartar("radar_sem_url_valida")
        return [
            {
                "alvo": "radar",
                "data_referencia": hora,
                "lat": lat,
                "lon": lon,
                "url_acumulado_1h": urls["acumulado_1h"],
                "url_acumulado_24h": urls["acumulado_24h"],
                "url_cappi_1km": urls["cappi_1km"],
            }
        ]

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        extra = {"agora": ctx.agora, "ex": ctx.execucao_id}
        sql = {
            "previsao": (
                "insert into silver.apac_previsao_horaria (hora_prevista, temperatura_c, umidade_pct, "
                "precipitacao_mm, codigo_recebido, coletado_em, execucao_id) values (:hora_prevista, "
                ":temperatura_c, :umidade_pct, :precipitacao_mm, :codigo_recebido, :agora, :ex) "
                "on conflict (hora_prevista) do update set temperatura_c = excluded.temperatura_c, "
                "umidade_pct = excluded.umidade_pct, precipitacao_mm = excluded.precipitacao_mm, "
                "codigo_recebido = excluded.codigo_recebido, coletado_em = excluded.coletado_em, "
                "execucao_id = excluded.execucao_id"
            ),
            "tendencia": (
                "insert into silver.apac_tendencia_chuva (mesorregiao, dia, categoria, faixa_mm, atualizado_em, "
                "coletado_em, execucao_id) values (:mesorregiao, :dia, :categoria, :faixa_mm, :atualizado_em, "
                ":agora, :ex) on conflict (mesorregiao, dia) do update set categoria = excluded.categoria, "
                "faixa_mm = excluded.faixa_mm, atualizado_em = excluded.atualizado_em, "
                "coletado_em = excluded.coletado_em, execucao_id = excluded.execucao_id"
            ),
            "radar": (
                "insert into silver.apac_radar (data_referencia, lat, lon, url_acumulado_1h, url_acumulado_24h, "
                "url_cappi_1km, coletado_em, execucao_id) values (:data_referencia, :lat, :lon, :url_acumulado_1h, "
                ":url_acumulado_24h, :url_cappi_1km, :agora, :ex) on conflict (data_referencia) do update set "
                "lat = excluded.lat, lon = excluded.lon, url_acumulado_1h = excluded.url_acumulado_1h, "
                "url_acumulado_24h = excluded.url_acumulado_24h, url_cappi_1km = excluded.url_cappi_1km, "
                "coletado_em = excluded.coletado_em, execucao_id = excluded.execucao_id"
            ),
        }
        gravados = 0
        with ctx.engine.begin() as c:
            for alvo, comando in sql.items():
                parte = df[df["alvo"] == alvo]
                if parte.empty:
                    continue
                linhas = [
                    {k: _py(k, v) for k, v in r.items() if k != "alvo"} | extra
                    for r in parte.to_dict("records")
                ]
                c.execute(text(comando), linhas)
                gravados += len(linhas)
        return gravados
