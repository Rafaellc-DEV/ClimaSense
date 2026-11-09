"""Pluviômetros do Recife pela API pública da APAC (sem cadastro): estações da APAC e do Cemaden.

- tempo real (padrão): `GET /precipitacao_acumulada?municipio=Recife` → acumulados de 1 h a 120 h de cada
  estação no instante da última leitura (hora local do Recife, UTC−3). "-"/null = ausente, nunca 0 (RN-02).
  Leitura com mais de 120 min em relação à coleta mais recente fica `desatualizada` (não entra na chuva do
  território, que herda do distrito ou cai para a reanálise).
- histórico (`--modo historico`): `GET /historico_pluviometrico_mensal?tipo=diario` mês a mês desde 2022.
  Mês de uma estação com total muito abaixo das vizinhas (falha de equipamento) vira ausente (`falha`).

Além das leituras acumuladas, o tempo real guarda `ultima_medicao` de cada leitura única (`silver.apac_chuva_passos`):
a gold soma por hora e distrito o que chega a cada 10-15 min, só a partir da coleta (nunca preenche o passado) e
sem transformar lacuna em zero. O cadastro `GET /estacoes?municipio=Recife` (`status_dados`, `tempo_min`) marca
as estações sem leitura; se falhar, a chuva segue sem ele.

Estação → bairro por ponto-em-polígono na malha oficial de bairros; sem malha, distrito (RN-07).
"""

from __future__ import annotations

import contextlib
import json
import statistics
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URL_API = "https://api.apac.pe.gov.br/api.php"
JANELAS = (1, 3, 6, 12, 24, 48, 72, 96, 120)
INICIO_HISTORICO = date(2022, 1, 1)
LIMITE_DESATUALIZADA_MIN = 120
# Na checagem de 06/11/2026 a API entregou os acentos certos (UTF-8 com `charset` no cabeçalho ou escape \uXXXX): o
# "Torre?o" da pesquisa era do console do Windows. Mesmo assim o texto é decodificado como UTF-8 e reparado se chegar
# com U+FFFD ou com UTF-8 lido como Latin-1 ("Ã£"), para a estação não aparecer com nome quebrado.
REPAROS_NOME = {
    "Torre�o": "Torreão",
    "concei��o": "Conceição",
    "V�rzea": "Várzea",
    "Irm�os": "Irmãos",
    "Esperan�a": "Esperança",
    "C�u": "Céu",
    "C�rrego": "Córrego",
    "Caxang�": "Caxangá",
    "manuten��o": "manutenção",
    "observa��o": "observação",
}


def corrigir_texto(texto) -> str:
    """Texto sem acento quebrado: desfaz UTF-8 lido como Latin-1, repara palavras conhecidas com U+FFFD e troca o
    que sobrar por '?' (nunca um caractere inválido)."""
    t = str(texto or "").strip()
    if "Ã" in t or "Â" in t:
        with contextlib.suppress(UnicodeEncodeError, UnicodeDecodeError):
            t = t.encode("latin-1").decode("utf-8")
    for quebrado, certo in REPAROS_NOME.items():
        t = t.replace(quebrado, certo)
    return t.replace("�", "?")


def json_utf8(resposta):
    """Corpo JSON decodificado como UTF-8 (não pela adivinhação de charset da biblioteca)."""
    bruto = getattr(resposta, "content", None)
    if isinstance(bruto, (bytes, bytearray)):
        try:
            return json.loads(bytes(bruto).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            pass
    return resposta.json()


def _hora_ou_none(texto):
    return comum.hora_local(texto) if texto and str(texto).strip() not in ("", "-") else None


# Falha de estação no histórico: total do mês < 10% da mediana das vizinhas, quando elas somam ≥ 30 mm.
FALHA_FRACAO, FALHA_MEDIANA_MIN_MM, FALHA_VIZINHAS_MIN = 0.10, 30.0, 2
PICO_MIN_MM, PICO_FATOR, PICO_VIZINHAS_MIN = 80.0, 20.0, 3


def _meses(inicio: date, fim: date) -> list[tuple[date, date]]:
    meses, d = [], inicio.replace(day=1)
    while d <= fim:
        prox = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
        meses.append((d, min(prox - timedelta(days=1), fim)))
        d = prox
    return meses


class ConectorApacChuva(Conector):
    id = "apac-chuva"
    fonte = FonteInfo(
        "Chuva observada nos pluviômetros do Recife (APAC + Cemaden)",
        "APAC — Agência Pernambucana de Águas e Clima",
        URL_API,
        "observada",
    )

    def __init__(self, http=None, localizador=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self._localizador = localizador
        self.descartes: dict[str, int] = {}
        self.cadastro_indisponivel = False
        self.passos: list[dict] = []
        self.cadastro: list[dict] = []

    @property
    def localizador(self):
        return self._localizador or comum.localizador()

    def colecao_bronze(self, ctx: ExecucaoCtx):
        nome = "apac_chuva_historico" if ctx.modo == "historico" else "apac_chuva"
        return ctx.mongo[self.banco_bronze][nome]

    # ------------------------------------------------------------------ extract
    def _get(self, caminho: str, params: dict):
        r = self.http.get(f"{URL_API}/{caminho}", params=params, timeout=90)
        r.raise_for_status()
        return json_utf8(r)

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        if ctx.modo == "historico":
            return self._extrair_historico(ctx)
        if ctx.modo not in (None, "tempo-real"):
            raise ValueError(f"Modo desconhecido: {ctx.modo}")
        corpo = self._get("precipitacao_acumulada", {"municipio": "Recife"})
        if not isinstance(corpo, list):
            raise FonteSemDados(f"APAC sem dados de chuva acumulada: {str(corpo.get('erro', corpo))[:200]}")
        try:  # o cadastro só marca a saúde das estações: a chuva não depende dele
            cadastro = self._get("estacoes", {"municipio": "Recife"})
        except Exception:  # noqa: BLE001
            cadastro = None
        if isinstance(cadastro, list):
            corpo = corpo + [{**c, "_endpoint": "estacoes"} for c in cadastro if isinstance(c, dict)]
        else:
            self.cadastro_indisponivel = True  # só a marcação de saúde das estações fica sem dado
        return corpo

    def _extrair_historico(self, ctx: ExecucaoCtx) -> list[dict]:
        hoje = ctx.agora.astimezone(comum.FUSO_RECIFE).date()
        inicio = INICIO_HISTORICO
        if ctx.limite:  # janela móvel em meses (o mês atual conta como 1)
            inicio = max(
                INICIO_HISTORICO, (hoje.replace(day=1) - timedelta(days=31 * (ctx.limite - 1))).replace(day=1)
            )
        registros, erros = [], 0
        for a, b in _meses(inicio, hoje):
            corpo = self._get(
                "historico_pluviometrico_mensal",
                {
                    "dataInicial": a.isoformat(),
                    "dataFinal": b.isoformat(),
                    "tipo": "diario",
                    "municipio": "Recife",
                },
            )
            if not isinstance(corpo, list):
                erros += 1
                continue
            registros.extend(
                {**r, "_consulta": {"inicio": a.isoformat(), "fim": b.isoformat()}} for r in corpo
            )
        if not registros:
            raise FonteSemDados(
                f"APAC sem histórico diário entre {inicio} e {hoje} ({erros} mês(es) com erro)."
            )
        return registros

    # ------------------------------------------------------------------ transform
    def _estacao(self, codigo, nome, lat, lon) -> dict | None:
        lat, lon = comum.real(lat), comum.real(lon)
        if not codigo or lat is None or lon is None:
            return None
        bairro, distrito = self.localizador.localizar(lon, lat)
        if not (bairro or distrito):
            return None
        return {
            "id": f"apac-{codigo}",
            "codigo": str(codigo),
            "nome": corrigir_texto(nome or codigo)[:160],
            "lat": lat,
            "lon": lon,
            "territorio_id": bairro or distrito,
        }

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {}
        if ctx.modo == "historico":
            return self._transformar_historico(bruto, ctx)
        linhas, self.estacoes, self.passos = [], {}, []
        self.cadastro = self._cadastro(bruto)
        if "_endpoint" in bruto.columns:
            bruto = bruto[bruto["_endpoint"].isna()]
        for r in bruto.to_dict("records"):
            est = self._estacao(
                r.get("codigo_estacao"), r.get("estacao"), r.get("latitude"), r.get("longitude")
            )
            lida = comum.hora_local(r.get("data_hora_ultima_leitura"))
            motivo = (
                "estacao_fora_do_recife" if est is None else "sem_hora_da_leitura" if lida is None else None
            )
            if motivo:
                self.descartes[motivo] = self.descartes.get(motivo, 0) + 1
                continue
            self.estacoes[est["id"]] = est
            self.passos.append(
                {"estacao_id": est["id"], "lida_em": lida, "valor_mm": comum.numero(r.get("ultima_medicao"))}
            )
            for j in JANELAS:
                linhas.append(
                    {
                        "estacao_id": est["id"],
                        "lida_em": lida,
                        "janela_h": j,
                        "valor_mm": comum.numero(r.get(f"{j}_hora" if j == 1 else f"{j}_horas")),
                    }
                )
        return pd.DataFrame(linhas)

    def _cadastro(self, bruto: pd.DataFrame) -> list[dict]:
        """Estado atual por código de estação a partir de /estacoes. Código repetido: fica o cadastro com hora de
        leitura (o outro é um registro vazio da mesma estação)."""
        if "_endpoint" not in bruto.columns:
            return []
        melhor: dict[str, dict] = {}
        for r in bruto[bruto["_endpoint"] == "estacoes"].to_dict("records"):
            codigo = str(r.get("codigo_gmmc") or "").strip()
            if not codigo:
                continue
            item = {
                "codigo_fonte": codigo,
                "nome": corrigir_texto(r.get("estacao"))[:160],
                "status_dados": corrigir_texto(r.get("status_dados"))[:40] or None,
                "tempo_min": _inteiro(r.get("tempo_min")),
                "ultima_leitura_em": _hora_ou_none(r.get("data_hora_leitura")),
            }
            atual = melhor.get(codigo)
            if atual is None or (
                atual["ultima_leitura_em"] is None and item["ultima_leitura_em"] is not None
            ):
                melhor[codigo] = item
        return list(melhor.values())

    def _transformar_historico(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        hoje = ctx.agora.astimezone(comum.FUSO_RECIFE).date()
        linhas, self.estacoes = [], {}
        for r in bruto.to_dict("records"):
            est = self._estacao(r.get("codigo_gmmc"), r.get("estacao"), r.get("latitude"), r.get("longitude"))
            if est is None:
                self.descartes["estacao_fora_do_recife"] = self.descartes.get("estacao_fora_do_recife", 0) + 1
                continue
            self.estacoes[est["id"]] = est
            for mes in r.get("dados") or []:
                for dia, valor in (mes.get("chuva_diaria") or {}).items():
                    try:
                        d = date.fromisoformat(dia)
                    except ValueError:
                        continue
                    if d > hoje:
                        continue
                    v = comum.numero(valor)
                    linhas.append({"estacao_id": est["id"], "dia": d, "valor_bruto_mm": v, "valor_mm": v})
        if not linhas:
            return pd.DataFrame()
        df = pd.DataFrame(linhas).drop_duplicates(["estacao_id", "dia"], keep="last")
        df["qualidade"] = df["valor_mm"].isna().map({True: "ausente", False: "ok"})
        df["mes"] = pd.to_datetime(df["dia"]).dt.to_period("M")
        totais = df.groupby(["mes", "estacao_id"])["valor_mm"].agg(["sum", "count"]).reset_index()
        falhas = set()
        for mes, grupo in totais.groupby("mes"):
            for _, linha in grupo.iterrows():
                outras = grupo[(grupo["estacao_id"] != linha["estacao_id"]) & (grupo["count"] >= 20)]["sum"]
                if len(outras) < FALHA_VIZINHAS_MIN:
                    continue
                mediana = statistics.median(outras)
                if mediana >= FALHA_MEDIANA_MIN_MM and linha["sum"] < FALHA_FRACAO * mediana:
                    falhas.add((mes, linha["estacao_id"]))
        if falhas:
            marca = [(m, e) in falhas for m, e in zip(df["mes"], df["estacao_id"], strict=True)]
            df.loc[marca, "valor_mm"] = None
            df.loc[marca, "qualidade"] = "falha"
            self.descartes["dias_em_mes_com_falha_de_estacao"] = int(sum(marca))
        # Pico isolado: uma estação com ≥ 80 mm no dia enquanto as vizinhas (≥ 3) quase não registram
        # (> 20 × (mediana + 1 mm)) é defeito de sensor provável → suspeito, fora da gold (valor bruto guardado).
        validos = df[df["valor_mm"].notna()]
        suspeitos = []
        for _, grupo in validos.groupby("dia"):
            if len(grupo) < PICO_VIZINHAS_MIN + 1:
                continue
            for idx, v in grupo["valor_mm"].items():
                outras = grupo["valor_mm"].drop(idx)
                if v >= PICO_MIN_MM and v > PICO_FATOR * (outras.median() + 1):
                    suspeitos.append(idx)
        if suspeitos:
            df.loc[suspeitos, "valor_mm"] = None
            df.loc[suspeitos, "qualidade"] = "suspeito"
            self.descartes["pico_isolado_suspeito"] = len(suspeitos)
        return df.drop(columns=["mes"])

    # ------------------------------------------------------------------ load (silver) + gold
    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        with ctx.engine.begin() as c:
            comum.gravar_estacoes(c, self.id, list(self.estacoes.values()))
            if ctx.modo == "historico":
                return self._gravar_diaria(c, df, ctx)
            antes = c.execute(text("select count(*) from silver.apac_chuva_leituras")).scalar()
            c.execute(
                text(
                    "insert into silver.apac_chuva_leituras (estacao_id, lida_em, janela_h, valor_mm, coletado_em, "
                    "visto_em, execucao_id) values (:estacao_id, :lida_em, :janela_h, :valor_mm, :agora, :agora, :ex) "
                    "on conflict (estacao_id, lida_em, janela_h) do update set visto_em = excluded.visto_em"
                ),
                [
                    {**r, "valor_mm": _nulo(r["valor_mm"]), "agora": ctx.agora, "ex": ctx.execucao_id}
                    for r in df.to_dict("records")
                ],
            )
            novas = c.execute(text("select count(*) from silver.apac_chuva_leituras")).scalar() - antes
            self._gravar_passos_e_cadastro(c, ctx)
            return novas

    def _gravar_passos_e_cadastro(self, c, ctx: ExecucaoCtx) -> None:
        if self.passos:
            c.execute(
                text(
                    "insert into silver.apac_chuva_passos (estacao_id, lida_em, valor_mm, coletado_em, visto_em, "
                    "execucao_id) values (:estacao_id, :lida_em, :valor_mm, :agora, :agora, :ex) "
                    "on conflict (estacao_id, lida_em) do update set visto_em = excluded.visto_em"
                ),
                [
                    {**p, "valor_mm": _nulo(p["valor_mm"]), "agora": ctx.agora, "ex": ctx.execucao_id}
                    for p in self.passos
                ],
            )
        if self.cadastro:
            c.execute(
                text(
                    "insert into silver.apac_estacoes_cadastro (codigo_fonte, nome, status_dados, tempo_min, "
                    "ultima_leitura_em, visto_em, execucao_id) values (:codigo_fonte, :nome, :status_dados, "
                    ":tempo_min, :ultima_leitura_em, :agora, :ex) on conflict (codigo_fonte) do update set "
                    "nome = excluded.nome, status_dados = excluded.status_dados, tempo_min = excluded.tempo_min, "
                    "ultima_leitura_em = excluded.ultima_leitura_em, visto_em = excluded.visto_em, "
                    "execucao_id = excluded.execucao_id"
                ),
                [{**d, "agora": ctx.agora, "ex": ctx.execucao_id} for d in self.cadastro],
            )

    def _gravar_diaria(self, c, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        c.execute(
            text(
                "insert into silver.apac_chuva_diaria (estacao_id, dia, valor_mm, valor_bruto_mm, qualidade, "
                "coletado_em, execucao_id) values (:estacao_id, :dia, :valor_mm, :valor_bruto_mm, :qualidade, :agora, "
                ":ex) on conflict (estacao_id, dia) do update set valor_mm = excluded.valor_mm, "
                "valor_bruto_mm = excluded.valor_bruto_mm, qualidade = excluded.qualidade, "
                "coletado_em = excluded.coletado_em, execucao_id = excluded.execucao_id"
            ),
            [
                {
                    **r,
                    "valor_mm": _nulo(r["valor_mm"]),
                    "valor_bruto_mm": _nulo(r["valor_bruto_mm"]),
                    "agora": ctx.agora,
                    "ex": ctx.execucao_id,
                }
                for r in df.to_dict("records")
            ],
        )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            if ctx.modo == "historico":
                gold.recalcular(c, gold.TABELAS_APAC_DIARIA)
            else:
                gold.recalcular(c, {**gold.TABELAS_APAC_AGORA, **gold.TABELAS_CHUVA_OBS})


def _nulo(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else float(v)


def _inteiro(v):
    n = comum.real(v)
    return None if n is None or n < 0 else int(n)
