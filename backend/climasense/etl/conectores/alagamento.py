"""Atendimentos de ALAGAMENTO e de DESLIZAMENTO da Defesa Civil do Recife (Dados Abertos, ODbL), 2014–2024, por
bairro e dia.

Reaproveita a leitura robusta do estudo de ML (`climasense.ml.alagamento.ocorrencias`): âncoras pelas datas
AAAA-MM-DD (colunas deslocadas em 2020 e 2022), aspas quebradas no endereço, codificação mista, e o critério
`evento` lido SÓ das categorias (Ocorrência "Alagamentos"/"Imóveis Alagados" ou Solicitação de vistoria/
monitoramento de setor alagado) — o endereço nunca é lido para classificar (há ruas "Alagoinha").

Deslizamento (prevenção nos morros): a categoria real da fonte é a Ocorrência "Deslizamentos de Barreiras" (3.157
atendimentos em 2014–2024); entram também "Desabamento Parcial/Total de Obras de Contenção / Drenagem" (muro de
arrimo e contenção de encosta que cedeu, ~130). "Colocação de Lonas Plásticas" é medida PREVENTIVA nas encostas
(acontece também em dias secos) e não conta como ocorrência. Como no alagamento, só as categorias são lidas.

Rótulo fraco: a data é da solicitação/vistoria (pode vir dias depois do alagamento) e a ausência de registro não
prova que não alagou. `silver.ocorrencias.ocorrido_em` fica nulo; `registrado_em` é o dia da vistoria (00:00 do
Recife) e `confirmada` fica nulo.

Bronze: um resumo de cada arquivo anual (url, sha256, linhas, cabeçalho) + os campos sanitizados das linhas que citam
"alag", "desliz" ou "conten" em qualquer campo (superconjunto do critério; o arquivo inteiro tem ~890 mil linhas e 150 MB, e não cabe
no Atlas gratuito a cada carga). Endereço nunca é persistido em novas cargas. A silver é refeita a partir
dos registros lidos de volta do Mongo; lotes antigos continuam legíveis, sem serem regravados.
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

_ALAG = re.compile(r"alag|desliz|conten", re.IGNORECASE)  # superconjunto das categorias, para a bronze
# Categorias de deslizamento lidas SÓ do campo Ocorrência (a fonte tem codificação mista: "Conten��o", "Conteno")
_DESLIZAMENTO = re.compile(r"desliz|desabamento.*obras\s+de\s+conten", re.IGNORECASE)
TIPOS = ("alagamento", "deslizamento")


def tipo_do_atendimento(reg: dict, oc) -> str | None:
    """alagamento | deslizamento | None, lido só das categorias (nunca do endereço)."""
    if _DESLIZAMENTO.search(reg["ocorrencia"] or ""):
        return "deslizamento"
    if oc.e_alagamento(reg, "evento"):
        return "alagamento"
    return None


def _ocorrencias():
    from climasense.ml.alagamento import ocorrencias  # leitura robusta compartilhada com o estudo de ML

    return ocorrencias


def decodificar(conteudo: bytes) -> str:
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("latin-1")


class ConectorRecifeAlagamento(Conector):
    id = "recife-alagamento"
    fonte = FonteInfo(
        "Atendimentos de alagamento e deslizamento da Defesa Civil (por bairro e dia)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/registro-de-atendimentos-da-defesa-civil",
        "observada",
        "ODbL",
    )

    def __init__(self, http=None, recursos: dict[int, str] | None = None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.recursos = recursos
        self.descartes: dict[str, int] = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        recursos = self.recursos or _ocorrencias().recursos_por_ano(self.http)
        registros = []
        for ano, url in sorted(recursos.items()):
            r = self.http.get(url, timeout=300)
            r.raise_for_status()
            linhas = decodificar(r.content).splitlines()
            registros.append(
                {
                    "tipo": "arquivo",
                    "ano": ano,
                    "url": url,
                    "sha256": hashlib.sha256(r.content).hexdigest(),
                    "linhas": max(len(linhas) - 1, 0),
                    "cabecalho": linhas[0] if linhas else "",
                }
            )
            for i, linha in enumerate(linhas[1:], start=2):
                if not _ALAG.search(linha):
                    continue
                reg = next(_ocorrencias().ler_registros(("cabecalho\n" + linha).encode("utf-8")), None)
                # LGPD: a linha original pode conter endereço. Só os campos necessários
                # à classificação e associação territorial chegam à bronze.
                if reg is not None:
                    registros.append(
                        {
                            "tipo": "linha",
                            "ano": ano,
                            "n_linha": i,
                            "registro": {k: reg[k] for k in ("data", "bairro", "ocorrencia", "solicitacao")},
                        }
                    )
        if not any(r["tipo"] == "linha" for r in registros):
            raise FonteSemDados(
                "A Defesa Civil não publicou nenhum atendimento que cite alagamento ou deslizamento."
            )
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        oc = _ocorrencias()
        mapa = oc.mapa_bairros()
        self.descartes, linhas = {}, []

        def conta(m):
            self.descartes[m] = self.descartes.get(m, 0) + 1

        for r in bruto[bruto["tipo"] == "linha"].to_dict("records"):
            reg = r.get("registro")
            if not isinstance(reg, dict):  # leitura compatível de lotes antigos; não cria novas linhas brutas
                reg = next(oc.ler_registros(("cabecalho\n" + r["linha"]).encode("utf-8")), None)
            if reg is None:
                conta("linha_malformada")
                continue
            tipo = tipo_do_atendimento(reg, oc)
            if tipo is None:
                conta(
                    "nao_e_alagamento_nem_deslizamento"
                )  # cita o termo só no endereço ou em rotina planejada
                continue
            alvo = oc.resolver_bairro(reg["bairro"], mapa)
            if alvo is None:
                conta("bairro_fora_da_base_oficial")
                continue
            dia = pd.to_datetime(reg["data"], errors="coerce")
            if pd.isna(dia):
                conta("data_invalida")
                continue
            linhas.append(
                {
                    "codigo_fonte": f"{int(r['ano'])}:{int(r['n_linha'])}",
                    "territorio_id": alvo[0],
                    "registrado_em": dia.to_pydatetime().replace(tzinfo=comum.FUSO_RECIFE),
                    "tipo": tipo,
                    "categoria": (reg["ocorrencia"] or reg["solicitacao"])[:80],
                }
            )
        return pd.DataFrame(linhas)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        """Carga completa (o conjunto é histórico e republicado inteiro): troca as linhas desta fonte numa
        única transação, sem tocar nas de outras fontes."""
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.ocorrencias where fonte_id = :f"), {"f": self.id})
            c.execute(
                text(
                    "insert into silver.ocorrencias (fonte_id, codigo_fonte, territorio_id, ocorrido_em, registrado_em, "
                    "tipo, confirmada, precisao_espacial, execucao_id) values (:f, :codigo_fonte, :territorio_id, null, "
                    ":registrado_em, :tipo, null, 'bairro', :ex)"
                ),
                [{**r, "f": self.id, "ex": ctx.execucao_id} for r in df.to_dict("records")],
            )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, {**gold.TABELAS_ALAGAMENTO, **gold.TABELAS_OCORRENCIAS})
