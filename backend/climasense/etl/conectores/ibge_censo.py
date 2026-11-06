"""Censo 2022 do IBGE: moradores por bairro e faixa de idade → `silver.populacao_bairro` (RF-02, RF-03).

Arquivo `Agregados_por_bairros_demografia_BR.zip` (Agregados por Setores Censitários, por Bairro). Linha = bairro do
IBGE (`CD_BAIRRO` = 7 dígitos do município + 3 do bairro; Recife = 2611606). Só contagens: nada identifica pessoa.

Variáveis usadas (dicionário `dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx`):
- V01006 moradores (total); V01031 0 a 4; V01032 5 a 9; V01033 10 a 14; V01040 60 a 69; V01041 70 anos ou mais.
- Faixas gravadas: "0-4" = V01031; "0-14" = V01031+V01032+V01033; "60+" = V01040+V01041; "70+" = V01041;
  "total" = V01006. **"80+" não existe**: o IBGE agrega por bairro só até "70 anos ou mais"; não é estimado.
- Célula suprimida ("X", em branco ou não numérica) em qualquer parcela → `pessoas` nulo e `suprimido` verdadeiro; nunca 0.

Casamento do bairro do IBGE com os 94 oficiais: nome sem acento e sem caixa (mesmo critério da Defesa Civil), mais um
apelido ("Sítio dos Pintos - São Brás" = Sítio dos Pintos). O que não casar é contado e listado, nunca atribuído a
outro bairro.

Deficiência NÃO existe por bairro nos agregados do Censo 2022: nada é criado (a camada mostra "Dados insuficientes").
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile

import pandas as pd
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores.alagamento import decodificar
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URL_PASTA = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"
    "Agregados_por_Bairro_csv/"
)
URL_ARQUIVO = URL_PASTA + "Agregados_por_bairros_demografia_BR.zip"
ANO = 2022
PREFIXO_RECIFE = comum.GEOCODE_RECIFE
VARIAVEIS = ("V01006", "V01031", "V01032", "V01033", "V01040", "V01041")
FAIXAS: dict[str, tuple[str, ...]] = {
    "0-4": ("V01031",),
    "0-14": ("V01031", "V01032", "V01033"),
    "60+": ("V01040", "V01041"),
    "70+": ("V01041",),
    "total": ("V01006",),
}
APELIDOS_IBGE = {"sitio-dos-pintos-sao-bras": "sitio-dos-pintos"}


def numero_ou_none(v) -> int | None:
    t = str(v if v is not None else "").strip()
    return int(t) if re.fullmatch(r"\d+", t) else None


def somar(linha: dict, variaveis: tuple[str, ...]) -> int | None:
    partes = [numero_ou_none(linha.get(v)) for v in variaveis]
    return None if any(p is None for p in partes) else sum(partes)


class ConectorIbgeCenso2022Bairro(Conector):
    id = "ibge-censo-2022-bairro"
    fonte = FonteInfo(
        "Censo 2022: moradores por bairro e faixa de idade",
        "IBGE",
        URL_PASTA,
        "observada",
        "Dados públicos do IBGE (Censo Demográfico 2022)",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}
        self.nao_casados: list[str] = []

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        resp = self.http.get(URL_ARQUIVO, timeout=300)
        resp.raise_for_status()
        try:
            z = zipfile.ZipFile(io.BytesIO(resp.content))
            nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            texto = decodificar(z.read(nome))
        except (zipfile.BadZipFile, StopIteration) as e:
            raise FonteSemDados("O arquivo de demografia por bairro do IBGE veio sem um CSV legível.") from e
        leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
        falta = [c for c in ("CD_BAIRRO", "NM_BAIRRO", *VARIAVEIS) if c not in (leitor.fieldnames or [])]
        if falta:
            raise FonteSemDados(f"O CSV do IBGE mudou de layout (faltam colunas: {', '.join(falta)}).")
        todas = list(leitor)
        recife = [r for r in todas if str(r["CD_BAIRRO"]).startswith(PREFIXO_RECIFE)]
        if not recife:
            raise FonteSemDados("O arquivo do IBGE não traz nenhum bairro do Recife (2611606).")
        resumo = {
            "registro": "arquivo",
            "url": URL_ARQUIVO,
            "arquivo": nome,
            "sha256": hashlib.sha256(resp.content).hexdigest(),
            "linhas_brasil": len(todas),
            "linhas_recife": len(recife),
            "ano": ANO,
        }
        return [
            resumo,
            *(
                {
                    "registro": "bairro",
                    "cd_bairro": r["CD_BAIRRO"],
                    "nm_bairro": r["NM_BAIRRO"],
                    **{v: r.get(v) for v in VARIAVEIS},
                }
                for r in recife
            ),
        ]

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        from climasense.ml.alagamento.ocorrencias import _slug, mapa_bairros

        mapa = mapa_bairros()
        self.descartes, self.nao_casados = {}, []
        linhas, vistos = [], set()
        for r in bruto[bruto["registro"] == "bairro"].to_dict("records"):
            slug = _slug(r["nm_bairro"])
            slug = APELIDOS_IBGE.get(slug, slug)
            alvo = mapa.get(slug)
            if alvo is None or alvo[0] in vistos:
                self.nao_casados.append(r["nm_bairro"])
                self.descartes["bairro_do_ibge_sem_par_oficial"] = (
                    self.descartes.get("bairro_do_ibge_sem_par_oficial", 0) + 1
                )
                continue
            vistos.add(alvo[0])
            for faixa, variaveis in FAIXAS.items():
                pessoas = somar(r, variaveis)
                linhas.append(
                    {
                        "bairro_id": alvo[0],
                        "ano": ANO,
                        "faixa": faixa,
                        "pessoas": pessoas,
                        "suprimido": pessoas is None,
                    }
                )
        return pd.DataFrame(linhas)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        linhas = [
            {
                "bairro_id": r["bairro_id"],
                "ano": int(r["ano"]),
                "faixa": r["faixa"],
                "pessoas": comum.valor_sql(r["pessoas"], inteiro=True),
                "suprimido": bool(r["suprimido"]),
                "f": self.id,
                "ex": ctx.execucao_id,
            }
            for r in df.to_dict("records")
        ]
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.populacao_bairro where fonte_id = :f"), {"f": self.id})
            c.execute(
                text(
                    "insert into silver.populacao_bairro (bairro_id, ano, faixa, pessoas, suprimido, fonte_id, "
                    "execucao_id) values (:bairro_id, :ano, :faixa, :pessoas, :suprimido, :f, :ex)"
                ),
                linhas,
            )
        bairros = len({r["bairro_id"] for r in linhas})
        print(f"[ibge] {bairros} bairros casados; sem par oficial: {self.nao_casados or 'nenhum'}")
        return len(linhas)
