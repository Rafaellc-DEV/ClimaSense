"""Demanda de urgência do SAMU do Recife por semana epidemiológica e bairro (Dados Abertos do Recife, ODbL).

Conjunto CKAN `servico-de-atendimento-movel-de-urgencia-samu-<ano>` (um por ano; a partir de 2016 o CSV
"Solicitações de Atendimento <ano>" traz `data;hora_minuto;municipio;bairro;endereco;origem_chamado;tipo;subtipo;
sexo;idade;motivo_finalizacao;motivo_desfecho`, UTF-8, separador `;`). A central regula o Recife e outros 17
municípios; o conector fica só com `municipio = RECIFE`.

O que isto É: chamados de urgência, por bairro do chamado (não da residência). O que NÃO é: caso de doença nem
diagnóstico. Toda tela e toda API devem rotular como "demanda de urgência (SAMU)".

**Minimização (LGPD, RN-13, RNF-03):** cada linha do arquivo é um atendimento a uma pessoa, com endereço, sexo e idade.
O CSV é lido em memória, por POSIÇÃO de coluna, e só `data`, `municipio`, `bairro`, `tipo` e `subtipo` são
consultados. `endereco`, `sexo`, `idade`, `hora_minuto`, `origem_chamado` e os motivos de finalização nunca são
lidos para um dicionário, nunca viram variável e jamais chegam à bronze. A bronze recebe só contagens por
(semana, bairro escrito na fonte, grupo) e o resumo do arquivo (url, sha256, datas, nomes das colunas descartadas).

Grupos (pelo `subtipo`, sem acento): diarreia, infecção gastrointestinal, vômitos, desidratação, febre, mialgia e
síndrome viral, mais `total` (todos os chamados do Recife). Um chamado entra em `total` e, se for de um grupo, nele; a
soma dos grupos não é o total. Linha ausente em semana coberta pelo arquivo = 0 chamados (zero medido, RN-02); semana
depois do último dia do arquivo = sem dado (RN-01).

Semana epidemiológica começa no domingo e pode cruzar dois arquivos anuais (a SE 53 de 2025 vai de 28/12 a 03/01):
por isso a série é agregada pelo domingo inicial e os arquivos são somados na transformação.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from collections import Counter
from datetime import date

import pandas as pd
from sqlalchemy import text

from climasense.dominio import semana_epi
from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.alagamento import decodificar
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

CKAN = "https://dados.recife.pe.gov.br/api/3/action/package_show"
PACOTE = "servico-de-atendimento-movel-de-urgencia-samu-{ano}"
ANO_MINIMO = 2016  # antes disso o layout é outro (sem tipo e subtipo)
ANOS_RECENTES = (
    5  # ano corrente e os 4 anteriores: linha de base sazonal de 2 a 5 anos (pesquisa de 06/11/2026)
)
MUNICIPIO = "RECIFE"
SEM_BAIRRO = "(em branco)"

# Colunas que identificam a pessoa ou o atendimento: só os NOMES vão ao resumo, nunca os valores
INDIVIDUAIS = (
    "hora_minuto",
    "endereco",
    "origem_chamado",
    "sexo",
    "idade",
    "motivo_finalizacao",
    "motivo_desfecho",
)
USADAS = ("data", "municipio", "bairro", "tipo", "subtipo")

GRUPOS = {
    "DIARREIA": "diarreia",
    "INFECCAO GASTROINTESTINAL": "infeccao_gastrointestinal",
    "VOMITOS": "vomitos",
    "DESIDRATACAO": "desidratacao",
    "FEBRE": "febre",
    "MIALGIA": "mialgia",
    "SINDROME VIRAL": "sindrome_viral",
}
TOTAL = "total"
ROTULO = "demanda de urgência (SAMU)"


def sem_acento(valor: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", valor or "") if not unicodedata.combining(c))


def chave(valor: str) -> str:
    """'Febre ' → 'FEBRE'; espaços repetidos e acentos saem."""
    return re.sub(r"\s+", " ", sem_acento(valor).strip().upper())


def grupo_do_subtipo(subtipo: str) -> str | None:
    return GRUPOS.get(chave(subtipo))


def _dia(texto: str) -> date | None:
    t = (texto or "").strip()
    try:
        if re.fullmatch(r"\d{4}-\d\d-\d\d.*", t):
            return date.fromisoformat(t[:10])
        if re.fullmatch(r"\d\d/\d\d/\d{4}.*", t):
            return date(int(t[6:10]), int(t[3:5]), int(t[:2]))
    except ValueError:
        return None
    return None


def agregar_csv(conteudo: bytes, ano: int) -> tuple[dict, list[dict]]:
    """(resumo do arquivo, contagens por domingo da semana × bairro escrito na fonte × grupo), sem campo individual."""
    texto = decodificar(conteudo).lstrip("﻿")
    leitor = csv.reader(io.StringIO(texto, newline=""), delimiter=";")
    cabecalho = [(c or "").strip().lower() for c in next(leitor, [])]
    faltam = [c for c in USADAS if c not in cabecalho]
    if faltam:
        raise FonteSemDados(f"O CSV do SAMU de {ano} veio sem as colunas {', '.join(faltam)}.")
    i_data, i_mun, i_bairro, i_tipo, i_sub = (cabecalho.index(c) for c in USADAS)
    ultima_posicao = max(i_data, i_mun, i_bairro, i_tipo, i_sub)
    contagem: Counter = Counter()
    motivos: Counter = Counter()
    linhas = recife = 0
    primeiro = ultimo = None
    inicios: dict[date, date] = {}
    for linha in leitor:
        linhas += 1
        if len(linha) <= ultima_posicao:
            motivos["linha_malformada"] += 1
            continue
        dia = _dia(linha[i_data])
        if dia is None:
            motivos["data_invalida"] += 1
            continue
        if dia.year != ano:
            motivos["data_fora_do_ano_do_arquivo"] += 1
            continue
        primeiro = dia if primeiro is None or dia < primeiro else primeiro
        ultimo = dia if ultimo is None or dia > ultimo else ultimo
        if chave(linha[i_mun]) != MUNICIPIO:
            motivos["outro_municipio_da_regulacao"] += 1
            continue
        recife += 1
        if dia not in inicios:
            inicios[dia] = semana_epi.inicio_semana(*semana_epi.semana_de(dia))
        bairro = re.sub(r"\s+", " ", linha[i_bairro].strip().upper())[:120] or SEM_BAIRRO
        contagem[(inicios[dia], bairro, TOTAL)] += 1
        grupo = grupo_do_subtipo(linha[i_sub])
        if grupo:
            contagem[(inicios[dia], bairro, grupo)] += 1
    resumo = {
        "linhas": linhas,
        "chamados_recife": recife,
        "primeiro_dia": primeiro.isoformat() if primeiro else None,
        "ultimo_dia": ultimo.isoformat() if ultimo else None,
        "colunas": len(cabecalho),
        "colunas_individuais_descartadas": sorted(c for c in cabecalho if c in INDIVIDUAIS),
        "motivos": dict(motivos),
    }
    agregados = [
        {"inicio": i.isoformat(), "bairro_fonte": b, "grupo": g, "n": n}
        for (i, b, g), n in sorted(contagem.items())
    ]
    return resumo, agregados


def recurso_solicitacoes(pacote: dict) -> dict | None:
    """O CSV de solicitações do pacote (mais recente por `last_modified`); remoções, hospitais etc. ficam de fora."""
    melhor = None
    for rec in pacote.get("resources", []):
        if not str(rec.get("url", "")).lower().endswith(".csv"):
            continue
        if "SOLICIT" not in chave(rec.get("name") or ""):
            continue
        quando = rec.get("last_modified") or rec.get("created") or ""
        if melhor is None or quando > (melhor.get("last_modified") or melhor.get("created") or ""):
            melhor = rec
    return melhor


class ConectorSamuRecife(Conector):
    id = "samu-recife"
    fonte = FonteInfo(
        "Demanda de urgência (SAMU Recife): chamados por semana e bairro",
        "Prefeitura do Recife (Dados Abertos), Secretaria de Saúde",
        "https://dados.recife.pe.gov.br/dataset/servico-de-atendimento-movel-de-urgencia-samu-2026",
        "observada",
        "ODbL",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}

    def anos(self, ctx: ExecucaoCtx) -> list[int]:
        fim = ctx.agora.year
        return list(range(max(ANO_MINIMO, fim - ANOS_RECENTES + 1), fim + 1))

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        registros: list[dict] = []
        for ano in self.anos(ctx):
            r = self.http.get(CKAN, params={"id": PACOTE.format(ano=ano)}, timeout=60)
            if getattr(r, "status_code", 200) == 404:
                continue  # ano ainda sem conjunto publicado (janeiro): sem dado, não zero
            r.raise_for_status()
            rec = recurso_solicitacoes(r.json()["result"])
            if rec is None:
                continue
            resp = self.http.get(rec["url"], timeout=300)  # redireciona para o armazenamento do portal
            resp.raise_for_status()
            resumo, agregados = agregar_csv(resp.content, ano)
            registros.append(
                {
                    "tipo": "arquivo",
                    "ano": ano,
                    "url": rec["url"],
                    "atualizado_em": rec.get("last_modified") or rec.get("created"),
                    "sha256": hashlib.sha256(resp.content).hexdigest(),
                    **resumo,
                }
            )
            registros.extend({"tipo": "agregado", "ano": ano, **g} for g in agregados)
        if not registros:
            raise FonteSemDados(
                "O CKAN do Recife não listou nenhum CSV de solicitações do SAMU para os anos pedidos."
            )
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        from climasense.ml.alagamento import ocorrencias as oc  # mesmo casamento de bairro da Defesa Civil

        mapa = oc.mapa_bairros()
        self.descartes = {}
        arquivos = bruto[bruto["tipo"] == "arquivo"]
        for m in arquivos["motivos"].dropna():
            for k, v in (m or {}).items():
                self.descartes[k] = self.descartes.get(k, 0) + int(v)
        primeiro = min(date.fromisoformat(d) for d in arquivos["primeiro_dia"].dropna())
        ultimo = max(date.fromisoformat(d) for d in arquivos["ultimo_dia"].dropna())
        atualizacoes = [
            d.date() for d in pd.to_datetime(arquivos["atualizado_em"], errors="coerce").dropna()
        ]  # data da última publicação no portal
        atualizada = max(atualizacoes) if atualizacoes else None
        soma: Counter = Counter()
        for r in bruto[bruto["tipo"] == "agregado"].to_dict("records"):
            soma[(date.fromisoformat(r["inicio"]), r["bairro_fonte"], r["grupo"])] += int(r["n"])
        resolvido: dict[str, str | None] = {}
        linhas = []
        for (inicio, bairro, grupo), n in sorted(soma.items()):
            if bairro not in resolvido:
                alvo = None if bairro == SEM_BAIRRO else oc.resolver_bairro(bairro, mapa)
                resolvido[bairro] = alvo[0] if alvo else None
            fim_semana = inicio.toordinal() + 6
            linhas.append(
                {
                    "inicio": inicio,
                    "bairro_fonte": bairro,
                    "territorio_id": resolvido[bairro],
                    "grupo": grupo,
                    "chamados": n,
                    # a semana não está inteira no que o portal publicou (começo da série ou fim do último mês)
                    "incompleta": inicio < primeiro or fim_semana > ultimo.toordinal(),
                    "primeiro_dia_dado": primeiro,
                    "ultimo_dia_dado": ultimo,
                    "fonte_atualizada_em": atualizada,
                }
            )
            if grupo == TOTAL and resolvido[bairro] is None and bairro != SEM_BAIRRO:
                self.descartes["bairro_fora_da_base_oficial"] = (
                    self.descartes.get("bairro_fora_da_base_oficial", 0) + n
                )  # fica na silver e no total do município; não vai para bairro nem distrito
        return pd.DataFrame(linhas)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        """Os arquivos anuais são republicados inteiros: troca a série numa única transação."""
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.samu_demanda_semana"))
            c.execute(
                text(
                    "insert into silver.samu_demanda_semana (inicio, bairro_fonte, territorio_id, grupo, chamados, "
                    "incompleta, primeiro_dia_dado, ultimo_dia_dado, fonte_atualizada_em, coletado_em, execucao_id) "
                    "values (:inicio, :bairro_fonte, :territorio_id, :grupo, :chamados, :incompleta, "
                    ":primeiro_dia_dado, :ultimo_dia_dado, :fonte_atualizada_em, :coletado_em, :ex)"
                ),
                [
                    {
                        **{k: comum.valor_sql(v) for k, v in r.items()},
                        "coletado_em": ctx.agora,
                        "ex": ctx.execucao_id,
                    }
                    for r in df.to_dict("records")
                ],
            )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_SAMU)
