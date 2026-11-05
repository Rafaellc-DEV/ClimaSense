"""Dengue e chikungunya por bairro de residência e ano (Dados Abertos do Recife, Secretaria de Saúde, ODbL).

Conjunto CKAN `casos-de-dengue-zika-e-chikungunya`: um CSV por agravo e ano (dengue 2013–2025, chikungunya
2015–2025), no layout do SINAN. Dois formatos convivem: o "curto" do SINAN (`NM_BAIRRO`, `CLASSI_FIN`,
`ID_MN_RESI`; caixa alta ou baixa) e o "longo" de 2013–2020 (`no_bairro_residencia`, `tp_classificacao_final`,
`co_municipio_residencia`). Separador `;` ou `,`, UTF-8.

**Minimização (LGPD):** cada linha do arquivo é um caso com logradouro, CEP, data de nascimento e número da
notificação. Nada disso sai da memória: o CSV é lido e IMEDIATAMENTE agregado por (bairro escrito na fonte,
classificação final). A bronze recebe só essas contagens e o resumo do arquivo (url, sha256, linhas, data);
nenhuma linha individual é gravada em lugar nenhum.

Classificação final (dicionário do SINAN):
- dengue: confirmado = 10 (dengue), 11 (com sinais de alarme), 12 (grave) e, no código antigo (até 2014),
  1 (clássica), 2 (com complicações), 3 (febre hemorrágica), 4 (síndrome do choque); descartado = 5;
- chikungunya: confirmado = 13; descartado = 5;
- o resto (8 inconclusivo, em branco e códigos que não pertencem ao agravo, como 1 e 2 nos arquivos de
  chikungunya de 2015–2016) fica em `outros`, contado no total de notificados mas não como confirmado.

Ano = ano do arquivo publicado (ano epidemiológico da Secretaria). Bairro: o nome escrito na fonte é normalizado e
casado com os 94 bairros oficiais (mesmo critério de `recife-alagamento`); o que não casa (em branco, grafia
truncada) continua na silver com `territorio_id` nulo e aparece no total, nunca no mapa.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter

import pandas as pd
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.alagamento import decodificar
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

CKAN = "https://dados.recife.pe.gov.br/api/3/action/package_show"
CONJUNTO = "casos-de-dengue-zika-e-chikungunya"
_RECURSO = re.compile(r"(dengue|chikungunya).*?(20\d\d)", re.IGNORECASE)
RECIFE_6 = "261160"

COLUNA_BAIRRO = ("nm_bairro", "no_bairro_residencia")
COLUNA_CLASSE = ("classi_fin", "tp_classificacao_final")
COLUNA_RESIDENCIA = ("id_mn_resi", "co_municipio_residencia")
# Colunas que identificam (ou ajudam a identificar) a pessoa: só contadas no resumo, nunca guardadas
SENSIVEIS = re.compile(r"lograd|cep|nasc|notific$|nu_notif|referencia|telefone|nome_|^nm_pacien|ddd", re.I)

CONFIRMADOS = {"dengue": {"10", "11", "12", "1", "2", "3", "4"}, "chikungunya": {"13"}}
DESCARTADO = "5"
SEM_BAIRRO = "(em branco)"


def _codigo(v) -> str:
    """'10.0' → '10'; vazio → ''."""
    t = str(v or "").strip()
    return t[:-2] if t.endswith(".0") else t


def _coluna(cabecalho: dict[str, str], candidatas: tuple[str, ...]) -> str | None:
    return next((cabecalho[c] for c in candidatas if c in cabecalho), None)


def agregar_csv(conteudo: bytes) -> tuple[dict, list[dict]]:
    """(resumo do arquivo, contagens por bairro escrito na fonte × classificação), já sem nenhum campo pessoal."""
    texto = decodificar(conteudo).lstrip("﻿")
    primeira = texto.split("\n", 1)[0]
    sep = ";" if primeira.count(";") >= primeira.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=sep)
    cabecalho = {(c or "").strip().lower(): c for c in leitor.fieldnames or []}
    col_bairro = _coluna(cabecalho, COLUNA_BAIRRO)
    col_classe = _coluna(cabecalho, COLUNA_CLASSE)
    col_resid = _coluna(cabecalho, COLUNA_RESIDENCIA)
    if not (col_bairro and col_classe):
        raise FonteSemDados(
            "Um arquivo de arboviroses do Recife veio sem as colunas de bairro e classificação."
        )
    contagem, motivos, linhas = Counter(), Counter(), 0
    for r in leitor:
        linhas += 1
        classe, bairro = r.get(col_classe), r.get(col_bairro)
        if classe is None and bairro is None:
            motivos["linha_malformada"] += 1
            continue
        if col_resid and _codigo(r.get(col_resid)) not in ("", RECIFE_6):
            motivos["residente_fora_do_recife"] += 1
            continue
        nome = re.sub(r"\s+", " ", (bairro or "").strip().upper()) or SEM_BAIRRO
        contagem[(nome[:120], _codigo(classe))] += 1
    resumo = {
        "linhas": linhas,
        "colunas": len(cabecalho),
        "colunas_sensiveis_descartadas": sorted(c for c in cabecalho if SENSIVEIS.search(c)),
        "motivos": dict(motivos),
    }
    return resumo, [{"bairro_fonte": b, "classificacao": c, "n": n} for (b, c), n in sorted(contagem.items())]


def recursos(http) -> dict[tuple[str, int], dict]:
    """(agravo, ano) → recurso CSV mais recente. Zika e as tabelas auxiliares ficam de fora."""
    r = http.get(CKAN, params={"id": CONJUNTO}, timeout=60)
    r.raise_for_status()
    melhores: dict[tuple[str, int], dict] = {}
    for rec in r.json()["result"]["resources"]:
        nome = (rec.get("name") or "").strip()
        m = _RECURSO.search(nome)
        if not m or "metadado" in nome.lower() or not str(rec.get("url", "")).lower().endswith(".csv"):
            continue
        chave = (m.group(1).lower(), int(m.group(2)))
        quando = rec.get("last_modified") or rec.get("created") or ""
        if chave not in melhores or quando > (melhores[chave].get("last_modified") or ""):
            melhores[chave] = rec
    return dict(sorted(melhores.items()))


class ConectorRecifeArboviroses(Conector):
    id = "recife-arboviroses"
    fonte = FonteInfo(
        "Dengue e chikungunya por bairro e ano (Secretaria de Saúde do Recife)",
        "Prefeitura do Recife (Dados Abertos)",
        f"https://dados.recife.pe.gov.br/dataset/{CONJUNTO}",
        "observada",
        "ODbL",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        achados = recursos(self.http)
        if not achados:
            raise FonteSemDados("O CKAN do Recife não listou nenhum CSV de dengue ou chikungunya.")
        registros = []
        for (agravo, ano), rec in achados.items():
            resp = self.http.get(rec["url"], timeout=300)  # redireciona para o armazenamento (URL assinada)
            resp.raise_for_status()
            resumo, agregados = agregar_csv(resp.content)
            registros.append(
                {
                    "tipo": "arquivo",
                    "agravo": agravo,
                    "ano": ano,
                    "url": rec["url"],
                    "atualizado_em": rec.get("last_modified") or rec.get("created"),
                    "sha256": hashlib.sha256(resp.content).hexdigest(),
                    **resumo,
                }
            )
            registros.extend({"tipo": "agregado", "agravo": agravo, "ano": ano, **g} for g in agregados)
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        from climasense.ml.alagamento import ocorrencias as oc  # mesmo casamento de bairro da Defesa Civil

        mapa = oc.mapa_bairros()
        self.descartes = {}
        for m in bruto.loc[bruto["tipo"] == "arquivo", "motivos"].dropna():
            for k, v in (m or {}).items():
                self.descartes[k] = self.descartes.get(k, 0) + int(v)
        atualizacao = {
            (r["agravo"], int(r["ano"])): r.get("atualizado_em")
            for r in bruto[bruto["tipo"] == "arquivo"].to_dict("records")
        }
        soma: dict[tuple, Counter] = {}
        for r in bruto[bruto["tipo"] == "agregado"].to_dict("records"):
            agravo, ano, nome = r["agravo"], int(r["ano"]), r["bairro_fonte"]
            alvo = None if nome == SEM_BAIRRO else oc.resolver_bairro(nome, mapa)
            c = soma.setdefault((agravo, ano, nome, alvo[0] if alvo else None), Counter())
            n, classe = int(r["n"]), str(r["classificacao"] or "")
            c["notificados"] += n
            if classe in CONFIRMADOS.get(agravo, set()):
                c["confirmados"] += n
            elif classe == DESCARTADO:
                c["descartados"] += n
            else:
                c["outros"] += n
        linhas = []
        for (agravo, ano, nome, territorio), c in soma.items():
            quando = pd.to_datetime(atualizacao.get((agravo, ano)), errors="coerce")
            linhas.append(
                {
                    "agravo": agravo,
                    "ano": ano,
                    "bairro_fonte": nome,
                    "territorio_id": territorio,
                    "notificados": c["notificados"],
                    "confirmados": c["confirmados"],
                    "descartados": c["descartados"],
                    "outros": c["outros"],
                    "fonte_atualizada_em": None if pd.isna(quando) else quando.date(),
                }
            )
            if territorio is None and nome != SEM_BAIRRO:
                self.descartes["bairro_fora_da_base_oficial"] = (
                    self.descartes.get("bairro_fora_da_base_oficial", 0) + c["notificados"]
                )
        return pd.DataFrame(linhas)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.arboviroses_bairro_ano"))
            c.execute(
                text(
                    "insert into silver.arboviroses_bairro_ano (agravo, ano, bairro_fonte, territorio_id, notificados, "
                    "confirmados, descartados, outros, fonte_atualizada_em, execucao_id) values (:agravo, :ano, "
                    ":bairro_fonte, :territorio_id, :notificados, :confirmados, :descartados, :outros, "
                    ":fonte_atualizada_em, :ex)"
                ),
                [
                    {**{k: comum.valor_sql(v) for k, v in r.items()}, "ex": ctx.execucao_id}
                    for r in df.to_dict("records")
                ],
            )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_ARBOVIROSES)
