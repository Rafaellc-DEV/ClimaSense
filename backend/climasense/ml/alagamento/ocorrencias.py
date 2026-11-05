"""Rótulo do modelo: atendimentos de ALAGAMENTO da Defesa Civil do Recife (Dados Abertos, ODbL).

O conector `recife-alagamento` do ETL ainda não existe (situação "planejada"), então o estudo baixa o CSV
público para um cache local em `tmp/alagamento/` (ignorado pelo Git), sem tocar no ETL nem no banco.

Conjunto: `registro-de-atendimentos-da-defesa-civil` (um CSV por ano). Não há uma tabela de "ocorrências de
alagamento": há atendimentos (vistoria, monitoramento, ação social) que a própria Defesa Civil classifica.
Dois critérios, lidos só das categorias (o endereço NUNCA é lido: há ruas chamadas "Alagoinha"):

- `evento` (padrão, rótulo do modelo): a OCORRÊNCIA registrada é de alagamento (`Alagamentos`,
  `Imóveis Alagados`) ou a solicitação é vistoria/monitoramento de SETOR alagado (`Vistoria Alagado`,
  `Vistoria Setor Alagado`, `Monitoramento Setor Alagado`). São atendimentos motivados por um evento;
- `amplo`: qualquer categoria que cite alagamento, incluindo `Monitoramento Alagado` e
  `Identificação de Setor de Risco (Alagado)`, que são rotinas e campanhas de mapeamento planejadas
  (acontecem também em dias secos). Mantido só como comparação no relatório.

O rótulo é "houve atendimento de alagamento no bairro no dia", um indicador indireto e incompleto do
alagamento real: ausência de registro não prova que não alagou.

A data do arquivo é a da SOLICITAÇÃO/vistoria, que pode vir alguns dias depois do alagamento: o rótulo usa
uma janela de tolerância (ver `base.JANELA_ROTULO_DIAS`).

O arquivo tem defeitos conhecidos (colunas deslocadas em alguns anos, aspas quebradas no endereço,
codificação mista). A leitura é por linha e ancora os campos pelas datas no formato AAAA-MM-DD.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import requests

from climasense.config import RAIZ_REPOSITORIO

PASTA_CACHE = RAIZ_REPOSITORIO / "tmp" / "alagamento"
CKAN = "https://dados.recife.pe.gov.br/api/3/action/package_show"
CONJUNTO = "registro-de-atendimentos-da-defesa-civil"
URL_CONJUNTO = f"https://dados.recife.pe.gov.br/dataset/{CONJUNTO}"

_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ANO_RECURSO = re.compile(r"(20\d\d)")
_ALAGAMENTO = re.compile(r"alag", re.IGNORECASE)
_SOLICITACAO_EVENTO = re.compile(r"vistoria.*alag|monitoramento\s+setor\s+alag", re.IGNORECASE)
CRITERIOS = ("evento", "amplo")

# Grafias da fonte que não batem com o nome oficial do bairro (verificadas no arquivo; sem adivinhação).
APELIDOS_BAIRRO = {
    "ibura-de-baixo": "ibura",
    "ibura-de-cima": "ibura",
    "ipsep": "ipsep",
    "jordao-alto": "jordao",
    "jordao-baixo": "jordao",
    "poco-da-panela": "poco",
    "alto-santa-teresinha": "alto-santa-terezinha",
    "hipodromo": "hipodromo",
}


def _slug(nome: str) -> str:
    from climasense.territorio.carga import slug

    return slug(nome)


def mapa_bairros() -> dict[str, tuple[str, str]]:
    """slug do bairro → (territorio_id, distrito_id), a partir da base territorial oficial local."""
    from climasense.territorio.carga import geo_local

    mapa: dict[str, tuple[str, str]] = {}
    for f in geo_local()["features"]:
        ds = f"ds-{f['properties']['cdistscodi']}"
        for bairro in f["properties"]["bairros"]:
            s = _slug(bairro)
            mapa[s] = (f"bairro-{s}", ds)
    return mapa


def resolver_bairro(nome: str, mapa: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    s = _slug(nome or "")
    s = APELIDOS_BAIRRO.get(s, s)
    return mapa.get(s)


# ----------------------------------------------------------------------------- download (cache local)
def recursos_por_ano(http=None) -> dict[int, str]:
    """Ano → URL do CSV mais recente daquele ano (o portal repete recursos em cada republicação)."""
    http = http or requests.Session()
    r = http.get(CKAN, params={"id": CONJUNTO}, timeout=60)
    r.raise_for_status()
    melhores: dict[int, tuple[str, str]] = {}
    for rec in r.json()["result"]["resources"]:
        m = _ANO_RECURSO.search(rec.get("name") or "")
        if not m or not str(rec.get("url", "")).lower().endswith(".csv"):
            continue
        ano, quando = int(m.group(1)), rec.get("last_modified") or rec.get("created") or ""
        if ano not in melhores or quando > melhores[ano][0]:
            melhores[ano] = (quando, rec["url"])
    return {ano: url for ano, (_, url) in sorted(melhores.items())}


def baixar(pasta: Path | None = None, http=None) -> list[Path]:
    """Baixa os CSVs que ainda não estão no cache. Nunca escreve no banco."""
    pasta = (pasta or PASTA_CACHE) / "defesa-civil"
    pasta.mkdir(parents=True, exist_ok=True)
    http = http or requests.Session()
    arquivos = []
    for ano, url in recursos_por_ano(http).items():
        destino = pasta / f"atendimentos-{ano}.csv"
        if not destino.exists():
            r = http.get(url, timeout=300)
            r.raise_for_status()
            destino.write_bytes(r.content)
        arquivos.append(destino)
    return arquivos


# ----------------------------------------------------------------------------- leitura robusta
def _texto(conteudo: bytes) -> str:
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("latin-1")


def ler_registros(conteudo: bytes) -> Iterator[dict]:
    """Cada linha vira {data, bairro, ocorrencia, solicitacao, acao}. Linhas sem as âncoras são puladas.

    Âncoras: a primeira data AAAA-MM-DD entre os 5 primeiros campos é a data da solicitação; os 9 últimos
    campos são fixos (Bairro, Localidade, Grau, Data_da_Acao, Tipo_da_Acao, Quantidade, Altura, Largura,
    Area), então o bairro é sempre o 9º a partir do fim, mesmo quando o endereço quebra em dois campos.
    """
    linhas = _texto(conteudo).splitlines()
    for linha in linhas[1:]:
        campos = [c.strip().strip('"').strip() for c in linha.split(";")]
        if len(campos) < 14:
            continue
        i = next((k for k, c in enumerate(campos[:5]) if _DATA.match(c)), None)
        if i is None or not _DATA.match(campos[-6]):
            continue
        yield {
            "data": campos[i],
            "ocorrencia": campos[i + 1],
            "solicitacao": campos[i + 2],
            "bairro": campos[-9],
            "acao": campos[-5],
        }


def e_alagamento(registro: dict, criterio: str = "evento") -> bool:
    if criterio == "amplo":
        return bool(
            _ALAGAMENTO.search(f"{registro['ocorrencia']}|{registro['solicitacao']}|{registro['acao']}")
        )
    if criterio != "evento":
        raise ValueError(f"Critério desconhecido: {criterio}")
    return bool(
        _ALAGAMENTO.search(registro["ocorrencia"]) or _SOLICITACAO_EVENTO.search(registro["solicitacao"])
    )


def ocorrencias_alagamento(
    arquivos: list[Path] | None = None,
    mapa: dict[str, tuple[str, str]] | None = None,
    criterio: str = "evento",
) -> pd.DataFrame:
    """Um registro por (dia, bairro) com atendimento de alagamento: data, territorio_id, distrito_id, registros.

    `df.attrs` guarda o que foi descartado (bairro fora da base oficial) para o relatório.
    """
    if arquivos is None:
        arquivos = sorted((PASTA_CACHE / "defesa-civil").glob("atendimentos-*.csv")) or baixar()
    mapa = mapa if mapa is not None else mapa_bairros()
    linhas, sem_territorio, total = [], Counter(), 0
    for caminho in arquivos:
        for reg in ler_registros(Path(caminho).read_bytes()):
            total += 1
            if not e_alagamento(reg, criterio):
                continue
            alvo = resolver_bairro(reg["bairro"], mapa)
            if alvo is None:
                sem_territorio[reg["bairro"] or "(vazio)"] += 1
                continue
            linhas.append({"data": reg["data"], "territorio_id": alvo[0], "distrito_id": alvo[1]})
    df = pd.DataFrame(linhas, columns=["data", "territorio_id", "distrito_id"])
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["data"])
    n_registros = len(df)
    df = df.groupby(["data", "territorio_id", "distrito_id"]).size().rename("registros").reset_index()
    df.attrs.update(
        registros_lidos=total,
        registros_alagamento=n_registros + sum(sem_territorio.values()),
        registros_sem_territorio=dict(sem_territorio.most_common()),
        fonte=URL_CONJUNTO,
        criterio=criterio,
    )
    return df
