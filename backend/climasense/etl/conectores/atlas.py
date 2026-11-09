"""Histórico de desastres do Recife: Atlas Digital de Desastres no Brasil (Sedec/MIDR e Ceped/UFSC).

Não há API. A página `https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml` publica o consolidado nacional
1991–<ano> em CSV (`;`, latin-1, ~74 MB, 70 colunas, ~70 mil registros) com nome que muda a cada consolidação
(`/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv`). O conector descobre o link na página, baixa o
CSV em fluxo (nunca inteiro na memória), mantém só as linhas com `Cod_IBGE_Mun = 2611606` (Recife) e só as colunas
úteis. A bronze recebe os registros do Recife (cerca de 16) e o resumo do arquivo (url, versão, sha256, tamanho,
linhas lidas); as outras ~70 mil linhas morrem no fluxo.

Os registros vêm do S2iD, informados pelo município: só entram eventos que viraram registro ou decreto, e a
subnotificação é possível. Datas de dia e município; sem bairro e sem horário. O evento de abril–maio de 2026 NÃO
está aqui (a consolidação vai até 2025).

Colunas lidas (todas administrativas, nenhuma identifica pessoa): `Protocolo_S2iD`, `Data_Evento`, `Data_Registro`,
`Cod_Cobrade`, `descricao_tipologia`, `Status` (Registro ou Reconhecido), `DH_MORTOS`, `DH_FERIDOS`,
`DH_DESABRIGADOS`, `DH_DESALOJADOS`, `DH_OUTROS AFETADOS`, `DH_total_danos_humanos_diretos`,
`DM_total_danos_materiais`, `PEPL_total_publico`, `PEPR_total_privado`. Os campos de texto livre (`DH_Descricao`,
`DM_Descricao`, `DA_Descricao`, `PEPL_Descricao`, `PEPR_Descricao`) ficam de fora.

Zero no Atlas NÃO é "zero medido": o município pode não ter preenchido o campo e o CSV grava 0. Campo vazio vira
ausente (nulo); 0 é guardado como 0 e a tela precisa dizer que a fonte não distingue.

`chuva_relacionada` é classificação do ClimaSense pela tipologia Cobrade, não do Atlas: hidrológicos (12xxx:
inundação, enxurrada, alagamento), movimento de massa (113xx) e chuvas intensas (13214).

Licença: não declarada na página. Atribuição obrigatória: "Sedec/MIDR, Atlas Digital de Desastres no Brasil".
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Iterable, Iterator
from datetime import date

import pandas as pd
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

BASE = "https://atlasdigital.mdr.gov.br"
PAGINA_DOWNLOADS = f"{BASE}/paginas/downloads.xhtml"
_LINK = re.compile(r'href="(/arquivos/\d{4}/BD_Atlas_[^"]*Consolidado\.csv)"', re.IGNORECASE)
_CONSOLIDADO = re.compile(r"(\d{4})\.(\d\d)\.(\d\d)_Consolidado", re.IGNORECASE)
IBGE_RECIFE = "2611606"
BLOCO = 1 << 20

# coluna do CSV → campo guardado
COLUNAS = {
    "Protocolo_S2iD": "protocolo",
    "Data_Evento": "data_evento",
    "Data_Registro": "data_registro",
    "Cod_Cobrade": "cobrade",
    "descricao_tipologia": "tipologia",
    "Status": "status",
    "DH_MORTOS": "mortos",
    "DH_FERIDOS": "feridos",
    "DH_DESABRIGADOS": "desabrigados",
    "DH_DESALOJADOS": "desalojados",
    "DH_OUTROS AFETADOS": "outros_afetados",
    "DH_total_danos_humanos_diretos": "danos_humanos_total",
    "DM_total_danos_materiais": "danos_materiais_rs",
    "PEPL_total_publico": "prejuizo_publico_rs",
    "PEPR_total_privado": "prejuizo_privado_rs",
}
CAMPOS_INTEIROS = (
    "mortos",
    "feridos",
    "desabrigados",
    "desalojados",
    "outros_afetados",
    "danos_humanos_total",
)
CAMPOS_REAIS = ("danos_materiais_rs", "prejuizo_publico_rs", "prejuizo_privado_rs")


def link_do_csv(html: str) -> str:
    """URL do consolidado mais novo listado na página de downloads (o nome muda a cada consolidação)."""
    achados = sorted(set(_LINK.findall(html)), key=lambda c: (_consolidado(c) or date.min, c))
    if not achados:
        raise FonteSemDados(
            "A página de downloads do Atlas Digital não lista mais o CSV consolidado: o endereço mudou."
        )
    return BASE + achados[-1]


def _consolidado(url: str) -> date | None:
    m = _CONSOLIDADO.search(url)
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except ValueError:
        return None


def _data(texto: str) -> date | None:
    t = (texto or "").strip()
    try:
        return date(int(t[6:10]), int(t[3:5]), int(t[:2])) if re.fullmatch(r"\d\d/\d\d/\d{4}", t) else None
    except ValueError:
        return None


def chuva_relacionada(cobrade: str) -> bool:
    c = (cobrade or "").strip()
    return c.startswith(("12", "113")) or c == "13214"


def linhas_latin1(blocos: Iterable[bytes], controle: dict) -> Iterator[str]:
    """Blocos de bytes → linhas decodificadas (latin-1), atualizando o sha256 e o tamanho em `controle`."""
    resto = b""
    for bloco in blocos:
        controle["sha"].update(bloco)
        controle["bytes"] += len(bloco)
        resto += bloco
        *completas, resto = resto.split(b"\n")
        for linha in completas:
            yield linha.decode("latin-1") + "\n"
    if resto:
        yield resto.decode("latin-1")


def filtrar_recife(linhas: Iterable[str]) -> tuple[dict, list[dict]]:
    """(resumo da leitura, registros do Recife já reduzidos às colunas úteis)."""
    leitor = csv.reader(linhas, delimiter=";")
    cabecalho = next(leitor, [])
    nomes = [c.strip() for c in cabecalho]
    faltam = [c for c in ("Cod_IBGE_Mun", *COLUNAS) if c not in nomes]
    if faltam:
        raise FonteSemDados(f"O CSV do Atlas veio sem as colunas {', '.join(faltam)}.")
    i_ibge = nomes.index("Cod_IBGE_Mun")
    posicoes = {campo: nomes.index(col) for col, campo in COLUNAS.items()}
    ultima = max([i_ibge, *posicoes.values()])
    lidas = 0
    registros: list[dict] = []
    for linha in leitor:
        lidas += 1
        if len(linha) <= ultima or linha[i_ibge].strip() != IBGE_RECIFE:
            continue
        registros.append({campo: linha[i].strip() for campo, i in posicoes.items()})
    return {"linhas_brasil": lidas, "colunas": len(nomes)}, registros


def _inteiro(valor: str) -> int | None:
    v = comum.numero(valor)
    return None if v is None else int(round(v))


class ConectorAtlasDesastres(Conector):
    id = "atlas-desastres"
    fonte = FonteInfo(
        "Histórico de desastres do Recife (Atlas Digital de Desastres no Brasil)",
        "Sedec/MIDR e Ceped/UFSC — Atlas Digital de Desastres no Brasil",
        "https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml",
        "observada",
        None,  # a página não declara licença
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        pagina = self.http.get(PAGINA_DOWNLOADS, timeout=60)
        pagina.raise_for_status()
        url = link_do_csv(pagina.text)
        resp = self.http.get(url, stream=True, timeout=(30, 300))
        resp.raise_for_status()
        controle = {"sha": hashlib.sha256(), "bytes": 0}
        resumo, registros = filtrar_recife(linhas_latin1(resp.iter_content(BLOCO), controle))
        if not registros:
            raise FonteSemDados(
                "O consolidado do Atlas Digital não traz nenhum registro do Recife (2611606)."
            )
        consolidado = _consolidado(url)
        arquivo = {
            "tipo": "arquivo",
            "url": url,
            "versao": url.rsplit("/", 1)[-1],
            "consolidado_em": consolidado.isoformat() if consolidado else None,
            "sha256": controle["sha"].hexdigest(),
            "bytes": controle["bytes"],
            "registros_recife": len(registros),
            **resumo,
        }
        return [arquivo, *({"tipo": "evento", **r} for r in registros)]

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {}
        arquivo = bruto[bruto["tipo"] == "arquivo"].iloc[0]
        consolidado = _data_iso(arquivo.get("consolidado_em"))
        linhas = []
        vistos: set[str] = set()
        for r in bruto[bruto["tipo"] == "evento"].to_dict("records"):
            protocolo = str(r.get("protocolo") or "").strip()
            dia = _data(r.get("data_evento"))
            if not protocolo:
                self.descartes["sem_protocolo"] = self.descartes.get("sem_protocolo", 0) + 1
                continue
            if dia is None:
                self.descartes["sem_data_do_evento"] = self.descartes.get("sem_data_do_evento", 0) + 1
                continue
            if protocolo in vistos:
                self.descartes["protocolo_repetido"] = self.descartes.get("protocolo_repetido", 0) + 1
                continue
            vistos.add(protocolo)
            cobrade = str(r.get("cobrade") or "").strip()
            linhas.append(
                {
                    "protocolo": protocolo,
                    "data_evento": dia,
                    "data_registro": _data(r.get("data_registro")),
                    "cobrade": cobrade[:10] or None,
                    "tipologia": str(r.get("tipologia") or "").strip()[:120] or None,
                    "status": str(r.get("status") or "").strip()[:30] or None,
                    **{c: _inteiro(r.get(c)) for c in CAMPOS_INTEIROS},
                    **{c: comum.numero(r.get(c)) for c in CAMPOS_REAIS},
                    "chuva_relacionada": chuva_relacionada(cobrade),
                    "versao_fonte": str(arquivo["versao"])[:200],
                    "consolidado_em": consolidado,
                }
            )
        return pd.DataFrame(linhas)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        """O consolidado é republicado inteiro uma vez por ano: troca a tabela numa única transação."""
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.desastres_atlas"))
            c.execute(
                text(
                    "insert into silver.desastres_atlas (protocolo, data_evento, data_registro, cobrade, tipologia, "
                    "status, mortos, feridos, desabrigados, desalojados, outros_afetados, danos_humanos_total, "
                    "danos_materiais_rs, prejuizo_publico_rs, prejuizo_privado_rs, chuva_relacionada, versao_fonte, "
                    "consolidado_em, coletado_em, execucao_id) values (:protocolo, :data_evento, :data_registro, "
                    ":cobrade, :tipologia, :status, :mortos, :feridos, :desabrigados, :desalojados, "
                    ":outros_afetados, :danos_humanos_total, :danos_materiais_rs, :prejuizo_publico_rs, "
                    ":prejuizo_privado_rs, :chuva_relacionada, :versao_fonte, :consolidado_em, :coletado_em, :ex)"
                ),
                [
                    {
                        **{k: comum.valor_sql(v, inteiro=k in CAMPOS_INTEIROS) for k, v in r.items()},
                        "coletado_em": ctx.agora,
                        "ex": ctx.execucao_id,
                    }
                    for r in df.to_dict("records")
                ],
            )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_DESASTRES)


def _data_iso(texto) -> date | None:
    try:
        return date.fromisoformat(str(texto)) if texto else None
    except ValueError:
        return None
