"""Nível dos rios do Capibaribe e vizinhos pela API pública da APAC (sem cadastro), com a ANA como segunda fonte.

- cadastro: `GET /estacoes_rios` (rio, bacia, municípios, coordenadas);
- leituras: `GET /historico_rios?cod_estacao=&periodo=24h|72h` → nível em cm e os limiares OFICIAIS da estação
  (pré-alerta, alerta, enchente), que a própria APAC publica junto de cada leitura;
- segunda fonte (legado, sujeita a descontinuação): ANA `ServiceANA.asmx/DadosHidrometeorologicos` (XML, sem token)
  para a estação 39187800, só nível e vazão; serve de validação cruzada e é mais fresca que a APAC em algumas horas.
  Se a ANA falhar, a execução segue só com a APAC (a falha fica na bronze e em `avisos`).

Nível não é bairro: não existe ligação rio↔território aqui (tabela `silver.rio_referencia_territorio` nasce vazia,
decisão de ADR futuro, com selo Experimental). Ausência de leitura nunca vira nível baixo (RN-01, RN-02).
Hora da leitura em hora local do Recife (UTC−3), gravada em UTC. Leitura com data futura é descartada.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import requests
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.alertas import xml_seguro
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URL_API = "https://api.apac.pe.gov.br/api.php"
URL_ANA = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx"
PERIODOS = ("24h", "72h")
TOLERANCIA_FUTURO = timedelta(minutes=15)  # relógio das PCDs adiantado em poucos minutos não é "futuro"
SUBSTITUICAO = "�"

# Estações iniciais (docs/pesquisa/api-hidrologia.md). Nome, rio e bacia canônicos só entram se o texto da API
# vier com bytes quebrados (U+FFFD não tem conserto); com texto íntegro vale o que a APAC publica.
ESTACOES_INICIAIS: dict[str, dict[str, str]] = {
    "39187800": {
        "nome": "São Lourenço da Mata (ANA/SGB)",
        "rio": "Rio Capibaribe",
        "bacia": "Capibaribe",
        "municipios": "Camaragibe, Recife, São Lourenço da Mata",
    },
    "39150010": {
        "nome": "Paudalho",
        "rio": "Rio Capibaribe",
        "bacia": "Capibaribe",
        "municipios": "Paudalho, São Lourenço da Mata",
    },
    "39145010": {
        "nome": "Limoeiro",
        "rio": "Rio Capibaribe",
        "bacia": "Capibaribe",
        "municipios": "Limoeiro",
    },
    "39130010": {
        "nome": "Toritama",
        "rio": "Rio Capibaribe",
        "bacia": "Capibaribe",
        "municipios": "Toritama",
    },
    "39170000": {
        "nome": "Vitória de Santo Antão",
        "rio": "Rio Tapacurá",
        "bacia": "Capibaribe",
        "municipios": "Vitória de Santo Antão",
    },
    "260790115": {
        "nome": "Jaboatão dos Guararapes (Vila Natal) (Cemaden)",
        "rio": "Rio Jaboatão",
        "bacia": "GL2",
        "municipios": "Jaboatão dos Guararapes",
    },
    "260790119": {
        "nome": "Jaboatão dos Guararapes (Centro) (Cemaden)",
        "rio": "Rio Duas Unas",
        "bacia": "GL2",
        "municipios": "Jaboatão dos Guararapes",
    },
    "39189560": {
        "nome": "Moreno",
        "rio": "Rio Jaboatão",
        "bacia": "GL2",
        "municipios": "Jaboatão dos Guararapes, Moreno",
    },
}
ANA_ESTACOES = ("39187800",)


def corrigir_texto(valor) -> str | None:
    """Texto da APAC com acentos quebrados: conserta o UTF-8 lido como Latin-1/cp1252 ("SÃ£o" → "São").
    Bytes já perdidos (U+FFFD) não voltam: o texto sai como veio e `texto_quebrado` acusa."""
    if valor is None:
        return None
    s = " ".join(str(valor).split())
    if not s:
        return None
    for codec in ("latin-1", "cp1252"):
        try:
            reparado = s.encode(codec).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if reparado != s:
            return reparado
    return s


def texto_quebrado(valor) -> bool:
    return valor is not None and SUBSTITUICAO in str(valor)


def nivel_cm(valor) -> float | None:
    """Nível em cm: ausente, texto e negativo (código de erro do sensor) viram None (RN-02). Zero medido é zero."""
    return comum.numero(valor)


def limiares(pre, alerta, enchente) -> tuple[float, float, float] | None:
    """Limiares oficiais só valem completos, positivos e em ordem crescente; senão a estação fica sem classe."""
    a, b, c = comum.real(pre), comum.real(alerta), comum.real(enchente)
    if a is None or b is None or c is None or not 0 < a < b < c:
        return None
    return a, b, c


def classificar_nivel(nivel, pre, alerta, enchente) -> str:
    """Mesma regra da gold (`gold.RIOS_SITUACAO`): atingiu o limiar = está na classe."""
    lim = limiares(pre, alerta, enchente)
    n = nivel_cm(nivel)
    if n is None or lim is None:
        return "dados_insuficientes"
    if n >= lim[2]:
        return "enchente"
    if n >= lim[1]:
        return "alerta"
    if n >= lim[0]:
        return "pre_alerta"
    return "abaixo_pre_alerta"


def _lista(v) -> list:
    return v if isinstance(v, list) else []


def _texto(v) -> str | None:
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


class ConectorApacRios(Conector):
    id = "apac-rios"
    fonte = FonteInfo(
        "Nível dos rios do Capibaribe e vizinhos (APAC, com ANA como segunda fonte)",
        "APAC — Agência Pernambucana de Águas e Clima / ANA (SGB)",
        URL_API,
        "observada",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}
        self.avisos: dict[str, int] = {}
        self.estacoes: dict[str, dict] = {}
        self.amostra = False

    # ------------------------------------------------------------------ extract
    def _get(self, caminho: str, params: dict):
        r = self.http.get(f"{URL_API}/{caminho}", params=params, timeout=90)
        r.raise_for_status()
        return r.json()

    def _periodo(self, ctx: ExecucaoCtx) -> str:
        periodo = "24h" if ctx.modo in (None, "tempo-real") else ctx.modo
        if periodo not in PERIODOS:
            raise ValueError(f"Modo desconhecido: {ctx.modo}")
        return periodo

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        periodo = self._periodo(ctx)
        cadastro = self._get("estacoes_rios", {})
        if not isinstance(cadastro, list):
            raise FonteSemDados(
                f"APAC sem cadastro de estações de rios: {str(cadastro.get('erro', cadastro))[:200]}"
            )
        codigos = list(ESTACOES_INICIAIS)
        if ctx.limite:  # extração parcial: amostra rotulada (RN-10)
            codigos = codigos[: ctx.limite]
        self.amostra = len(codigos) < len(ESTACOES_INICIAIS)
        marca = {"amostra": True, "n_estacoes": len(codigos)} if self.amostra else {}
        registros = [
            {"_origem": "apac_estacao", **e, **marca}
            for e in cadastro
            if isinstance(e, dict) and str(e.get("cod_estacao")) in codigos
        ]
        falhas = 0
        for cod in codigos:
            doc = {"_origem": "apac_historico", "cod_estacao": cod, "periodo": periodo, **marca}
            try:
                corpo = self._get("historico_rios", {"cod_estacao": cod, "periodo": periodo})
            except (requests.RequestException, ValueError) as e:
                doc |= {"erro": type(e).__name__, "leituras": []}
                falhas += 1
            else:
                if isinstance(corpo, list):
                    doc["leituras"] = corpo
                else:  # {"erro": ...} com HTTP 200
                    doc |= {"erro": str(corpo.get("erro", corpo))[:200], "leituras": []}
                    falhas += 1
            registros.append(doc)
        if falhas == len(codigos):
            raise FonteSemDados("APAC não devolveu o histórico de nenhuma estação de rio.")
        for cod in ANA_ESTACOES:
            if cod in codigos:
                registros.append(self._extrair_ana(cod, ctx, marca))
        if falhas:  # estação sem resposta: extração parcial, rotulada em tudo o que foi lido (RN-10)
            self.amostra = True
            for d in registros:
                d["amostra"] = True
        return registros

    def _extrair_ana(self, cod: str, ctx: ExecucaoCtx, marca: dict) -> dict:
        fim = ctx.agora.astimezone(comum.FUSO_RECIFE).date()
        inicio = fim - timedelta(days=1 if self._periodo(ctx) == "24h" else 3)
        doc = {
            "_origem": "ana_telemetria",
            "cod_estacao": cod,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            **marca,
        }
        try:
            r = self.http.get(
                f"{URL_ANA}/DadosHidrometeorologicos",
                params={
                    "codEstacao": cod,
                    "dataInicio": inicio.strftime("%d/%m/%Y"),
                    "dataFim": fim.strftime("%d/%m/%Y"),
                },
                timeout=90,
            )
            r.raise_for_status()
            doc["leituras"] = parse_ana(r.content)
        except (
            requests.RequestException,
            ValueError,
            KeyError,
        ) as e:  # ValueError inclui XML recusado/inválido
            doc |= {"erro": type(e).__name__, "leituras": []}
        return doc

    # ------------------------------------------------------------------ transform
    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes, self.avisos, self.estacoes = {}, {}, {}
        linhas = []
        docs = bruto.to_dict("records")
        for d in docs:
            if d.get("_origem") == "apac_estacao":
                est = self._estacao(d)
                if est:
                    self.estacoes[est["codigo"]] = est
        limite_futuro = ctx.agora + TOLERANCIA_FUTURO
        for d in docs:
            origem = d.get("_origem")
            if origem not in ("apac_historico", "ana_telemetria"):
                continue
            cod = str(d.get("cod_estacao"))
            fonte = "apac" if origem == "apac_historico" else "ana"
            if cod not in self.estacoes:
                self._contar(self.descartes, "estacao_fora_do_cadastro")
                continue
            if _texto(d.get("erro")):
                self._contar(self.avisos, f"{fonte}_falhou")
            leituras = _lista(d.get("leituras"))
            if not leituras and not _texto(d.get("erro")):
                self._contar(self.avisos, f"{fonte}_sem_leituras_{cod}")
            for r in leituras:
                lida = comum.hora_local(r.get("data_hora") if fonte == "apac" else r.get("DataHora"))
                if lida is None:
                    self._contar(self.descartes, "sem_hora_da_leitura")
                    continue
                if lida > limite_futuro:
                    self._contar(self.descartes, "leitura_no_futuro")
                    continue
                nivel = nivel_cm(r.get("nivel_atual") if fonte == "apac" else r.get("Nivel"))
                if nivel is None:
                    self._contar(self.descartes, "nivel_ausente")
                    continue
                linha = {
                    "estacao_codigo": cod,
                    "fonte": fonte,
                    "lida_em": lida,
                    "nivel_cm": nivel,
                    "pre_alerta_cm": None,
                    "alerta_cm": None,
                    "enchente_cm": None,
                    "alerta_pcd": None,
                    "recente": None,
                    "vazao_m3s": None,
                }
                if fonte == "apac":
                    lim = limiares(
                        r.get("nivel_pre_alerta"), r.get("nivel_alerta"), r.get("nivel_alerta_enchente")
                    )
                    if lim is None:
                        self._contar(self.avisos, "limiares_invalidos")
                    else:
                        linha["pre_alerta_cm"], linha["alerta_cm"], linha["enchente_cm"] = lim
                    pcd = str(r.get("alerta_pcd") or "").strip().upper()
                    linha["alerta_pcd"] = pcd if pcd in ("S", "N") else None
                    rec = comum.real(r.get("recente"))
                    linha["recente"] = int(rec) if rec in (0, 1) else None
                else:
                    linha["vazao_m3s"] = comum.numero(r.get("Vazao"))
                linhas.append(linha)
        if not linhas:
            raise FonteSemDados("Nenhuma estação de rio trouxe leitura de nível no período consultado.")
        return pd.DataFrame(linhas).drop_duplicates(["estacao_codigo", "fonte", "lida_em"], keep="last")

    @staticmethod
    def _contar(dicionario: dict[str, int], chave: str) -> None:
        dicionario[chave] = dicionario.get(chave, 0) + 1

    @staticmethod
    def _estacao(d: dict) -> dict | None:
        cod = str(d.get("cod_estacao") or "").strip()
        canon = ESTACOES_INICIAIS.get(cod)
        lat, lon = comum.real(d.get("latitude")), comum.real(d.get("longitude"))
        if canon is None or lat is None or lon is None:
            return None

        def campo(chave: str, canonico: str) -> str:
            v = corrigir_texto(_texto(d.get(chave)))
            return canonico if v is None or texto_quebrado(v) else v

        codigos = [c for c in str(_texto(d.get("cod_municipio")) or "").split(";") if c.strip()]
        return {
            "codigo": cod,
            "nome": campo("nome_estacao", canon["nome"])[:160],
            "rio": campo("nome_rio", canon["rio"])[:160],
            "bacia": campo("bacia_hidrografica", canon["bacia"])[:80],
            "municipios": campo("municipios", canon["municipios"]),
            "codigos_municipio": [c.strip() for c in codigos],
            "inclui_recife": comum.GEOCODE_RECIFE in [c.strip() for c in codigos],
            "lat": lat,
            "lon": lon,
        }

    # ------------------------------------------------------------------ load (silver) + gold
    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        with ctx.engine.begin() as c:
            if self.estacoes:
                c.execute(
                    text(
                        "insert into silver.rios_estacoes (codigo, nome, rio, bacia, municipios, codigos_municipio, "
                        "inclui_recife, lat, lon, fonte_id, atualizado_em) values (:codigo, :nome, :rio, :bacia, "
                        ":municipios, :codigos_municipio, :inclui_recife, :lat, :lon, :f, :agora) "
                        "on conflict (codigo) do update set nome = excluded.nome, rio = excluded.rio, "
                        "bacia = excluded.bacia, municipios = excluded.municipios, "
                        "codigos_municipio = excluded.codigos_municipio, inclui_recife = excluded.inclui_recife, "
                        "lat = excluded.lat, lon = excluded.lon, atualizado_em = excluded.atualizado_em"
                    ),
                    [{**e, "f": self.id, "agora": ctx.agora} for e in self.estacoes.values()],
                )
            antes = c.execute(text("select count(*) from silver.rios_leituras")).scalar()
            c.execute(
                text(
                    "insert into silver.rios_leituras (estacao_codigo, fonte, lida_em, nivel_cm, pre_alerta_cm, "
                    "alerta_cm, enchente_cm, vazao_m3s, alerta_pcd, recente, coletado_em, visto_em, execucao_id) "
                    "values (:estacao_codigo, :fonte, :lida_em, :nivel_cm, :pre_alerta_cm, :alerta_cm, :enchente_cm, "
                    ":vazao_m3s, :alerta_pcd, :recente, :agora, :agora, :ex) "
                    "on conflict (estacao_codigo, fonte, lida_em) do update set nivel_cm = excluded.nivel_cm, "
                    "pre_alerta_cm = excluded.pre_alerta_cm, alerta_cm = excluded.alerta_cm, "
                    "enchente_cm = excluded.enchente_cm, vazao_m3s = excluded.vazao_m3s, "
                    "alerta_pcd = excluded.alerta_pcd, recente = excluded.recente, visto_em = excluded.visto_em"
                ),
                [
                    {
                        **{
                            k: comum.valor_sql(v, inteiro=(k == "recente"))
                            for k, v in r.items()
                            if k != "lida_em"
                        },
                        "lida_em": r["lida_em"].to_pydatetime(),  # valor_sql reduziria o Timestamp a uma data
                        "agora": ctx.agora,
                        "ex": ctx.execucao_id,
                    }
                    for r in df.to_dict("records")
                ],
            )
            return c.execute(text("select count(*) from silver.rios_leituras")).scalar() - antes

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_RIOS)


def parse_ana(conteudo: bytes | str) -> list[dict]:
    """XML do DataSet da ANA → uma lista de dicts por leitura (valores como texto, como vieram)."""
    raiz = xml_seguro(conteudo)
    saida = []
    for linha in raiz.iter():
        if linha.tag.rsplit("}", 1)[-1] != "DadosHidrometereologicos" or not len(linha):
            continue
        saida.append({f.tag.rsplit("}", 1)[-1]: (f.text or "").strip() for f in linha})
    return saida
