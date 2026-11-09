"""Apoio dos conectores da cobertura territorial dos 94 bairros (suscetibilidade, grau de risco dos atendimentos,
alagamento de 2026): consulta às camadas ArcGIS do portal ESIG da Prefeitura, interseção geométrica com a malha
oficial dos bairros e gravação da gold por bairro (`gold.indicador_territorial`) e da cobertura por indicador
(`gold.cobertura_indicador`).

Só agregados (RN-13): nenhum desses conectores lê endereço, CEP, nome de morador ou de cliente. Quem pede só os campos
da lista fechada é o conector; aqui nada é "pedido por padrão" (`outFields` nunca é `*`).
"""

from __future__ import annotations

import functools
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import make_valid
from sqlalchemy import text

from climasense.etl.conectores.base import FonteSemDados

URL_ESIG = "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted"
POR_PAGINA = 2000
CRS_AREA = "EPSG:31985"  # SIRGAS 2000 / UTM 25S: áreas em metros quadrados no Recife


def url_camada(nome: str, camada: int = 0) -> str:
    return f"{URL_ESIG}/{nome}/FeatureServer/{camada}"


def semsotaque(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


# ------------------------------------------------------------------------------------------- consulta ArcGIS
def ultima_edicao(http, nome: str) -> str | None:
    """Data da última edição que o servidor informa para a camada (ISO, UTC); None se não informar (RF-19)."""
    try:
        r = http.get(url_camada(nome), params={"f": "json"}, timeout=60)
        r.raise_for_status()
        ms = ((r.json() or {}).get("editingInfo") or {}).get("lastEditDate")
        return datetime.fromtimestamp(ms / 1000, UTC).isoformat() if isinstance(ms, (int, float)) else None
    except Exception:  # noqa: BLE001 — metadado é complemento: sem ele a carga segue, com a data em branco
        return None


def consultar_camada(http, nome: str, campos: str, limite: int | None = None) -> list[dict]:
    """Feições GeoJSON (WGS84) da camada, paginadas. `limite` corta a extração (o conector rotula como amostra)."""
    feicoes, deslocamento = [], 0
    while True:
        tamanho = POR_PAGINA if limite is None else min(POR_PAGINA, limite - len(feicoes))
        r = http.get(
            f"{url_camada(nome)}/query",
            params={
                "where": "1=1",
                "outFields": campos,
                "outSR": 4326,
                "returnGeometry": "true",
                "resultOffset": deslocamento,
                "resultRecordCount": tamanho,
                "f": "geojson",
            },
            timeout=180,
        )
        r.raise_for_status()
        corpo = r.json()
        if "error" in corpo:
            raise FonteSemDados(f"Camada {nome}: {str(corpo['error'])[:200]}")
        pagina = corpo.get("features") or []
        feicoes += pagina
        deslocamento += tamanho
        if len(pagina) < tamanho or (limite is not None and len(feicoes) >= limite):
            break
    if not feicoes:
        raise FonteSemDados(f"A camada {nome} não devolveu nenhuma feição.")
    return feicoes


# ------------------------------------------------------------------------------------------- malha dos bairros
def poligonal(geom):
    """Geometria válida e só com polígonos (make_valid pode devolver coleção com linhas)."""
    g = geom if geom.is_valid else make_valid(geom)
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    partes = [p for p in getattr(g, "geoms", []) if p.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(partes) if partes else None


@functools.lru_cache(maxsize=1)
def _projetor():
    from pyproj import Transformer

    return Transformer.from_crs("EPSG:4326", CRS_AREA, always_xy=True).transform


def projetar(geom):
    return shapely.transform(geom, lambda xy: np.column_stack(_projetor()(xy[:, 0], xy[:, 1])))


class IndiceBairros:
    """Os bairros oficiais (malha local) com índice espacial: ponto em polígono e maior sobreposição."""

    def __init__(self, bairros: list[tuple[str, object]] | None = None) -> None:
        self.bairros = bairros if bairros is not None else self._da_malha_oficial()
        self.ids = [b for b, _ in self.bairros]
        self.geoms = [poligonal(g) for _, g in self.bairros]
        self._arvore = STRtree(self.geoms)

    @staticmethod
    def _da_malha_oficial() -> list[tuple[str, object]]:
        from climasense.territorio.carga import slug
        from climasense.territorio.geometria import carregar_malha_bairros

        malha = carregar_malha_bairros(baixar=False) or {"features": []}
        saida = []
        for f in malha["features"]:
            p = f["properties"]
            nome = p.get("EBAIRRNOME") or p.get("EBAIRRNOMEOF") or ""
            saida.append((f"bairro-{slug(nome)}", shape(f["geometry"])))
        return saida

    def do_ponto(self, ponto) -> str | None:
        for i in sorted(self._arvore.query(ponto, predicate="intersects")):
            return self.ids[int(i)]
        return None

    def de_maior_sobreposicao(self, geom) -> str | None:
        melhor, area = None, 0.0
        for i in self._arvore.query(geom, predicate="intersects"):
            a = geom.intersection(self.geoms[int(i)]).area
            if a > area:
                melhor, area = self.ids[int(i)], a
        return melhor


# ------------------------------------------------------------------------------------------- gold por bairro
@dataclass(frozen=True)
class Indicador:
    id: str
    rotulo: str  # texto que a tela deve exibir junto do número
    unidade: str
    periodo: str
    observacao: str
    consulta: str  # select (bairro_id, valor) na silver, com :f (fonte) e demais parâmetros nomeados
    parametros: tuple = ()


def gravar_indicadores(c, fonte_id: str, agora: datetime, indicadores: list[Indicador]) -> None:
    """Refaz as linhas desta fonte em `gold.indicador_territorial` e `gold.cobertura_indicador` a partir da silver.

    Ausência não vira zero: o indicador só tem linha no bairro em que a consulta devolve valor. A cobertura conta em
    quantos dos bairros oficiais (`app.territorios`) o indicador existe e em quantos o valor é positivo.
    """
    c.execute(text("delete from gold.indicador_territorial where fonte_id = :f"), {"f": fonte_id})
    c.execute(text("delete from gold.cobertura_indicador where fonte_id = :f"), {"f": fonte_id})
    for i in indicadores:
        base = {"f": fonte_id, **dict(i.parametros)}
        c.execute(
            text(
                "insert into gold.indicador_territorial (bairro_id, indicador, valor, unidade, rotulo, periodo, "  # noqa: S608
                f"fonte_id, atualizado_em) select q.bairro_id, :ind, q.valor, :u, :r, :p, :f, :agora from ({i.consulta}) q "
                "where q.valor is not null"
            ),
            {**base, "ind": i.id, "u": i.unidade, "r": i.rotulo, "p": i.periodo, "agora": agora},
        )
        c.execute(
            text(
                "insert into gold.cobertura_indicador (indicador, fonte_id, rotulo, periodo, observacao, "
                "bairros_com_dado, bairros_com_valor_positivo, bairros_total, atualizado_em) "
                "select :ind, :f, :r, :p, :o, count(*), count(*) filter (where valor > 0), "
                "(select count(*) from app.territorios where tipo = 'bairro'), :agora "
                "from gold.indicador_territorial where indicador = :ind and fonte_id = :f"
            ),
            {"ind": i.id, "f": fonte_id, "r": i.rotulo, "p": i.periodo, "o": i.observacao, "agora": agora},
        )
