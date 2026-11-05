"""Leptospirose no Recife por semana epidemiológica de início dos sintomas (SINAN, DATASUS).

Arquivos públicos de microdados: `ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/FINAIS/LEPTBRAA.dbc`
(anos encerrados) e `…/PRELIM/LEPTBRAA.dbc` (anos em curso, preliminares). Um arquivo por ANO DE NOTIFICAÇÃO,
Brasil inteiro. Filtro: município de residência `ID_MN_RESI = 261160` (Recife, IBGE de 6 dígitos).

Minimização (LGPD): o .dbc é lido só nas colunas `COLUNAS` (nenhuma identifica pessoa: não há nome, endereço, data
de nascimento nem unidade) e a bronze guarda apenas CONTAGENS por arquivo × semana de sintomas × classificação ×
evolução × exposição a enchente, mais o resumo de cada arquivo (tamanho, sha256, data). Nenhuma linha individual
sai deste módulo.

Semana incompleta: começou há menos de `SEMANAS_INCOMPLETAS` semanas antes da última notificação do arquivo mais
recente (atraso sintomas → notificação de ~5 dias e notificação → encerramento de ~18 dias, medido em 2026) — nelas
o número baixo NÃO é queda. Semanas depois da última notificação não existem na série (sem dado ≠ zero, RN-01).
"""

from __future__ import annotations

import ftplib
import hashlib
import io
import re
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import text

from climasense.dominio import semana_epi
from climasense.etl import gold
from climasense.etl.conectores import dbc
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

SERVIDOR = "ftp.datasus.gov.br"
PASTAS = {
    "FINAIS": "/dissemin/publicos/SINAN/DADOS/FINAIS",
    "PRELIM": "/dissemin/publicos/SINAN/DADOS/PRELIM",
}
_ARQUIVO = re.compile(r"^LEPTBR(\d\d)\.dbc$", re.IGNORECASE)
RECIFE_6 = "261160"
ANO_INICIAL = 2015
SEMANAS_INCOMPLETAS = 6
COLUNAS = ("ID_MN_RESI", "SEM_PRI", "CLASSI_FIN", "EVOLUCAO", "ANT_CB_LAM", "DT_NOTIFIC")
CONFIRMADO, DESCARTADO = "1", "2"
OBITO_PELO_AGRAVO = "2"
EXPOSTO_SIM = "1"


def _data(texto: str) -> date | None:
    t = (texto or "").strip()
    try:
        return date(int(t[:4]), int(t[4:6]), int(t[6:8])) if len(t) == 8 else None
    except ValueError:
        return None


class FtpDatasus:
    """Acesso mínimo ao FTP público do DATASUS (anônimo). Substituível nos testes."""

    def __init__(self, fabrica: Callable[[], ftplib.FTP] | None = None) -> None:
        # o DATASUS só publica por FTP anônimo (sem TLS); o conteúdo é público e conferido pelo sha256 na bronze
        self.fabrica = fabrica or (lambda: ftplib.FTP(SERVIDOR, timeout=120))  # noqa: S321

    def arquivos(self) -> list[dict]:
        ftp = self.fabrica()
        try:
            ftp.login()
            achados = []
            for pasta, caminho in PASTAS.items():
                ftp.cwd(caminho)
                for nome in ftp.nlst():
                    m = _ARQUIVO.match(nome)
                    if not m:
                        continue
                    mdtm = ftp.sendcmd(f"MDTM {nome}").split()[-1]
                    achados.append(
                        {
                            "pasta": pasta,
                            "arquivo": nome,
                            "ano": 2000 + int(m.group(1)),
                            "atualizado_em": datetime.strptime(mdtm[:14], "%Y%m%d%H%M%S").isoformat() + "Z",
                        }
                    )
            return achados
        finally:
            ftp.close()

    def baixar(self, pasta: str, arquivo: str) -> bytes:
        ftp = self.fabrica()
        try:
            ftp.login()
            ftp.cwd(PASTAS[pasta])
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {arquivo}", buf.write)
            return buf.getvalue()
        finally:
            ftp.close()


def agregar(conteudo: bytes) -> tuple[dict, list[dict]]:
    """Resumo do arquivo + contagens do Recife (sem nenhuma linha individual)."""
    _, registros = dbc.ler(conteudo, COLUNAS)
    total, ultima, cont = 0, None, Counter()
    for r in registros:
        total += 1
        d = _data(r["DT_NOTIFIC"])
        if d and (ultima is None or d > ultima):
            ultima = d
        if r["ID_MN_RESI"] != RECIFE_6:
            continue
        cont[(r["SEM_PRI"], r["CLASSI_FIN"], r["EVOLUCAO"], r["ANT_CB_LAM"])] += 1
    resumo = {
        "registros_brasil": total,
        "registros_recife": sum(cont.values()),
        "ultima_notificacao": ultima.isoformat() if ultima else None,
    }
    agregados = [
        {"sem_pri": s, "classi_fin": c, "evolucao": e, "ant_cb_lam": a, "n": n}
        for (s, c, e, a), n in sorted(cont.items())
    ]
    return resumo, agregados


class ConectorSinanLeptospirose(Conector):
    id = "sinan-leptospirose"
    fonte = FonteInfo(
        "Leptospirose no Recife por semana de sintomas (SINAN)",
        "Ministério da Saúde — DATASUS / SINAN",
        "https://datasus.saude.gov.br/transferencia-de-arquivos/",
        "observada",
        None,
    )

    def __init__(self, ftp: FtpDatasus | None = None, **kw) -> None:
        super().__init__(**kw)
        self.ftp = ftp or FtpDatasus()
        self.descartes: dict[str, int] = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        por_ano: dict[int, dict] = {}
        for a in self.ftp.arquivos():
            if a["ano"] < ANO_INICIAL:
                continue
            atual = por_ano.get(a["ano"])
            if atual is None or (a["pasta"] == "FINAIS" and atual["pasta"] == "PRELIM"):
                por_ano[a["ano"]] = a  # ano já encerrado: vale o arquivo final
        if not por_ano:
            raise FonteSemDados("O FTP do DATASUS não listou nenhum arquivo LEPTBR de 2015 em diante.")
        registros: list[dict] = []
        for ano, a in sorted(por_ano.items()):
            conteudo = self.ftp.baixar(a["pasta"], a["arquivo"])
            resumo, agregados = agregar(conteudo)
            registros.append(
                {
                    "tipo": "arquivo",
                    **a,
                    "tamanho": len(conteudo),
                    "sha256": hashlib.sha256(conteudo).hexdigest(),
                    **resumo,
                }
            )
            registros.extend(
                {"tipo": "agregado", "arquivo": a["arquivo"], "ano_arquivo": ano, **g} for g in agregados
            )
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {}
        arquivos = bruto[bruto["tipo"] == "arquivo"]
        ultimas = [
            d for d in (_data(str(u).replace("-", "")) for u in arquivos["ultima_notificacao"].dropna()) if d
        ]
        if not ultimas:
            raise FonteSemDados("Os arquivos do SINAN não trazem nenhuma data de notificação.")
        ultima = max(ultimas)
        preliminares = set(arquivos.loc[arquivos["pasta"] == "PRELIM", "ano"].astype(int))
        ano_preliminar = min(preliminares) if preliminares else None
        versao = "; ".join(  # ex.: "FINAIS LEPTBR15–LEPTBR24 (2026-07-15); PRELIM LEPTBR25–LEPTBR26 (2026-11-03)"
            f"{pasta} {min(g['arquivo'])[:8]}–{max(g['arquivo'])[:8]} ({str(g['atualizado_em'].max())[:10]})"
            for pasta, g in arquivos.groupby("pasta")
        )
        inicio_serie = semana_epi.inicio_semana(ANO_INICIAL, 1)
        fim_serie = semana_epi.inicio_semana(*semana_epi.semana_de(ultima))
        corte_incompleta = fim_serie - timedelta(weeks=SEMANAS_INCOMPLETAS - 1)

        semanas: dict[date, Counter] = {}
        for r in bruto[bruto["tipo"] == "agregado"].to_dict("records"):
            n = int(r["n"])
            se = semana_epi.de_codigo(r["sem_pri"])
            if se is None:
                self.descartes["semana_de_sintomas_invalida"] = (
                    self.descartes.get("semana_de_sintomas_invalida", 0) + n
                )
                continue
            inicio = semana_epi.inicio_semana(*se)
            if inicio < inicio_serie:
                self.descartes["sintomas_antes_de_2015"] = self.descartes.get("sintomas_antes_de_2015", 0) + n
                continue
            if inicio > fim_serie:
                self.descartes["sintomas_depois_da_ultima_notificacao"] = (
                    self.descartes.get("sintomas_depois_da_ultima_notificacao", 0) + n
                )
                continue
            c = semanas.setdefault(inicio, Counter())
            c["notificados"] += n
            classe = str(r["classi_fin"] or "")
            if classe == CONFIRMADO:
                c["confirmados"] += n
                if str(r["evolucao"] or "") == OBITO_PELO_AGRAVO:
                    c["obitos"] += n
                if str(r["ant_cb_lam"] or "") == EXPOSTO_SIM:
                    c["expostos_enchente"] += n
            elif classe == DESCARTADO:
                c["descartados"] += n
            else:
                c["em_investigacao"] += n  # sem encerramento (ou inconclusivo)
        linhas = []
        inicio = inicio_serie
        while inicio <= fim_serie:  # semana sem notificação no período coberto pelo arquivo = 0 notificado
            c = semanas.get(inicio, Counter())
            ano, sem = semana_epi.semana_de(inicio)
            linhas.append(
                {
                    "ano": ano,
                    "semana": sem,
                    "inicio": inicio,
                    "notificados": c["notificados"],
                    "confirmados": c["confirmados"],
                    "descartados": c["descartados"],
                    "em_investigacao": c["em_investigacao"],
                    "obitos": c["obitos"],
                    "expostos_enchente": c["expostos_enchente"],
                    "incompleta": inicio >= corte_incompleta,
                    "preliminar": ano_preliminar is not None and ano >= ano_preliminar,
                    "ultima_notificacao": ultima,
                    "versao_fonte": versao[:300],
                }
            )
            inicio += timedelta(weeks=1)
        return pd.DataFrame(linhas)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        """Carga completa (os arquivos são republicados inteiros): troca a série numa única transação."""
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.leptospirose_semanal"))
            c.execute(
                text(
                    "insert into silver.leptospirose_semanal (ano, semana, inicio, notificados, confirmados, "
                    "descartados, em_investigacao, obitos, expostos_enchente, incompleta, preliminar, "
                    "ultima_notificacao, versao_fonte, coletado_em, execucao_id) values (:ano, :semana, :inicio, "
                    ":notificados, :confirmados, :descartados, :em_investigacao, :obitos, :expostos_enchente, "
                    ":incompleta, :preliminar, :ultima_notificacao, :versao_fonte, :coletado_em, :ex)"
                ),
                [{**r, "coletado_em": ctx.agora, "ex": ctx.execucao_id} for r in df.to_dict("records")],
            )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_SAUDE)
