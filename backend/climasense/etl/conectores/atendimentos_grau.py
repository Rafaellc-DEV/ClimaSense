"""Grau de risco (R1 a R4) dos atendimentos da Defesa Civil do Recife, por bairro e ano (RF-02, RF-04).

Mesmo conjunto do `recife-alagamento` (CKAN `registro-de-atendimentos-da-defesa-civil`, ODbL, um CSV por ano), mas aqui
o interesse é a coluna `Grau_de_Risco` de QUALQUER atendimento (não só alagamento e deslizamento). O indicador é um FATO
("atendimentos com grau R3/R4 de 2014 a 2024"), contagem agregada por bairro e ano. Não é mapeamento de risco: o grau
vem do atendimento, pode refletir o ponto vistoriado, e a fonte não diz o que o grau avalia. Nunca "bairro de risco".

Privacidade (RN-13, RNF-03): o campo `Endereco` (ofuscado pela fonte) NUNCA é lido: o leitor pega só data, bairro e
grau, pelas âncoras de posição (colunas deslocadas em 2020 e 2022, como no conector do alagamento). A bronze guarda o
resumo de cada arquivo (url, sha256, linhas) e as CONTAGENS por (ano, bairro como escrito, grau): um arquivo inteiro
tem ~890 mil linhas no total e não cabe no Atlas gratuito.

O histórico PAROU em 2024: o arquivo de 2025 do portal tem 1 linha e não há 2026. Isso é dito na cobertura (sem 2025,
não se conclui que 2025 foi calmo).
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

import pandas as pd
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores import geo_territorial as geo
from climasense.etl.conectores.alagamento import decodificar
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

GRAUS = ("R1", "R2", "R3", "R4")
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PREFIXO = "atendimentos_grau"


def _ocorrencias():
    from climasense.ml.alagamento import ocorrencias  # recursos do CKAN e mapa de bairros, compartilhados

    return ocorrencias


def contar_graus(conteudo: bytes, ano: int) -> tuple[Counter, dict]:
    """({(ano, bairro_como_escrito, grau): n}, resumo). Lê só bairro e grau (nunca o endereço).

    O ano é o do ARQUIVO (a data de uma ou outra linha vem errada, p. ex. 1900). Uma data AAAA-MM-DD entre os 5
    primeiros campos é a âncora que prova que a linha tem o layout esperado; Bairro e Grau são o 9º e o 7º a partir do fim
    (os 9 últimos campos são fixos: Bairro, Localidade, Grau_de_Risco, Data_da_Acao, Tipo_da_Acao, Quantidade, Altura,
    Largura, Area_m), então valem mesmo quando o endereço quebra em dois campos.
    """
    contagem: Counter = Counter()
    resumo = {"linhas": 0, "sem_ancora": 0, "sem_grau": 0, "grau_invalido": 0}
    linhas = decodificar(conteudo).splitlines()
    for linha in linhas[1:]:
        resumo["linhas"] += 1
        campos = [c.strip().strip('"').strip() for c in linha.split(";")]
        i = next((k for k, c in enumerate(campos[:5]) if _DATA.match(c)), None) if len(campos) >= 14 else None
        if i is None:
            resumo["sem_ancora"] += 1
            continue
        grau = campos[-7].upper()
        if not grau:
            resumo["sem_grau"] += 1
        elif grau not in GRAUS:
            resumo["grau_invalido"] += 1
        else:
            contagem[(ano, campos[-9], grau)] += 1
    return contagem, resumo


class ConectorRecifeAtendimentosGrauRisco(Conector):
    id = "recife-atendimentos-grau-risco"
    fonte = FonteInfo(
        "Atendimentos da Defesa Civil com grau de risco R1 a R4 (por bairro e ano)",
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
        self.cobertura: dict = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        recursos = self.recursos or _ocorrencias().recursos_por_ano(self.http)
        anos = sorted(recursos)
        if ctx.limite is not None:
            anos = anos[: ctx.limite]  # amostra: só os primeiros anos (RN-10)
        arquivos, contagens = [], []
        for ano in anos:
            r = self.http.get(recursos[ano], timeout=300)
            r.raise_for_status()
            contagem, resumo = contar_graus(r.content, ano)
            arquivos.append(
                {
                    "registro": "arquivo",
                    "ano_arquivo": ano,
                    "url": recursos[ano],
                    "sha256": hashlib.sha256(r.content).hexdigest(),
                    **resumo,
                    "amostra": ctx.limite is not None,
                }
            )
            contagens += [
                {"registro": "contagem", "ano": a, "bairro": b, "grau": g, "atendimentos": n}
                for (a, b, g), n in sorted(contagem.items())
            ]
        if not contagens:
            raise FonteSemDados("Nenhum atendimento da Defesa Civil traz grau de risco (R1 a R4).")
        return [*arquivos, *contagens]

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        oc = _ocorrencias()
        mapa = oc.mapa_bairros()
        self.descartes = {}
        soma: Counter = Counter()
        for r in bruto[bruto["registro"] == "contagem"].to_dict("records"):
            alvo = oc.resolver_bairro(r["bairro"], mapa)
            if alvo is None:
                self.descartes["bairro_fora_da_base_oficial"] = self.descartes.get(
                    "bairro_fora_da_base_oficial", 0
                ) + int(r["atendimentos"])
                continue
            soma[(alvo[0], int(r["ano"]), r["grau"])] += int(r["atendimentos"])
        df = pd.DataFrame(
            [
                {"bairro_id": b, "ano": a, "grau": g, "atendimentos": n}
                for (b, a, g), n in sorted(soma.items())
            ]
        )
        arquivos = bruto[bruto["registro"] == "arquivo"]
        if not df.empty:
            com_grau = df.groupby("bairro_id")["atendimentos"].sum()
            r34 = df[df["grau"].isin(("R3", "R4"))].groupby("bairro_id")["atendimentos"].sum()
            self.cobertura = {
                "n_bairros_oficiais": len(mapa_bairros_unicos(mapa)),
                "n_bairros_com_grau": int(com_grau.index.nunique()),
                "n_bairros_com_r3_ou_r4": int((r34 > 0).sum()),
                "ano_inicial": int(df["ano"].min()),
                "ano_final": int(df["ano"].max()),
                "atendimentos_com_grau": int(df["atendimentos"].sum()),
                "por_grau": {g: int(n) for g, n in df.groupby("grau")["atendimentos"].sum().items()},
                "anos_dos_arquivos_sem_grau": sorted(
                    int(a)
                    for a in arquivos["ano_arquivo"]
                    if a not in set(int(x) for x in df["ano"].unique())
                ),
            }
        return df

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        if ctx.limite is not None:
            print(
                "[atendimentos-grau] AMOSTRA (--limite): só a bronze foi gravada; a silver anterior fica intacta."
            )
            return 0
        linhas = [
            {
                "b": r["bairro_id"],
                "a": int(r["ano"]),
                "g": r["grau"],
                "n": int(r["atendimentos"]),
                "f": self.id,
                "ex": ctx.execucao_id,
            }
            for r in df.to_dict("records")
        ]
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.atendimentos_grau_risco where fonte_id = :f"), {"f": self.id})
            c.execute(
                text(
                    "insert into silver.atendimentos_grau_risco (bairro_id, ano, grau, atendimentos, fonte_id, "
                    "execucao_id) values (:b, :a, :g, :n, :f, :ex)"
                ),
                linhas,
            )
        k = self.cobertura
        print(
            f"[atendimentos-grau] {k.get('n_bairros_com_grau')} de {k.get('n_bairros_oficiais')} bairros com "
            f"atendimento com grau; {k.get('n_bairros_com_r3_ou_r4')} com R3 ou R4; "
            f"{k.get('ano_inicial')} a {k.get('ano_final')} (sem dado depois de {k.get('ano_final')}); "
            f"por grau {k.get('por_grau')}; descartes {self.descartes}"
        )
        return len(linhas)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        if ctx.limite is not None:
            return
        with ctx.engine.connect() as c:
            anos = c.execute(
                text("select min(ano), max(ano) from silver.atendimentos_grau_risco where fonte_id = :f"),
                {"f": self.id},
            ).one()
        if anos[0] is None:
            return
        periodo = f"{anos[0]}-{anos[1]}"
        aviso = (
            f"Fato do histórico de atendimentos, não é mapeamento de risco. O histórico publicado para em {anos[1]}: "
            "sem dado depois disso (não indica ausência de ocorrência)."
        )
        base = "select bairro_id, sum(atendimentos)::double precision as valor from silver.atendimentos_grau_risco "
        indicadores = [
            geo.Indicador(
                f"{PREFIXO}_r3_r4",
                f"atendimentos com grau R3/R4 de {anos[0]} a {anos[1]}",
                "atendimentos",
                periodo,
                f"Soma dos atendimentos com grau R3 ou R4 no período. 0 = o bairro tem atendimentos com grau, "
                f"nenhum R3/R4. {aviso}",
                "select bairro_id, coalesce(sum(atendimentos) filter (where grau in ('R3','R4')), 0)::double precision "
                "as valor from silver.atendimentos_grau_risco where fonte_id = :f group by bairro_id",
            ),
            geo.Indicador(
                f"{PREFIXO}_total",
                f"atendimentos com grau de risco (R1 a R4) de {anos[0]} a {anos[1]}",
                "atendimentos",
                periodo,
                f"Soma dos atendimentos com algum grau, R1 a R4. {aviso}",
                base + "where fonte_id = :f group by bairro_id",
            ),
        ]
        with ctx.engine.begin() as c:
            geo.gravar_indicadores(c, self.id, ctx.agora, indicadores)


def mapa_bairros_unicos(mapa: dict) -> set[str]:
    """Os ids de bairro do mapa (várias grafias apontam para o mesmo bairro)."""
    return {v[0] for v in mapa.values()}
