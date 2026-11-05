"""Geometria do território (porte de `area_km2` do load_mongo.py, Aula 07) + simplificação para a web."""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import mapping, shape

_GEOD = Geod(ellps="WGS84")


def area_km2(geometry: dict) -> float:
    """Área geodésica WGS84; subtrai anéis internos, preserva multipolígonos."""
    if geometry["type"] not in ("Polygon", "MultiPolygon"):
        raise ValueError("Esperado Polygon ou MultiPolygon.")
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    total = 0.0
    for rings in polygons:
        areas = []
        for ring in rings:
            lon, lat = zip(*[(point[0], point[1]) for point in ring], strict=True)
            areas.append(abs(_GEOD.polygon_area_perimeter(lon, lat)[0]))
        total += areas[0] - sum(areas[1:])
    return total / 1_000_000


def simplificar_web(geometry: dict, tolerancia_graus: float = 0.00005) -> dict:
    """Geometria leve para o navegador (~5 m). A original continua guardada para cálculos."""
    simples = mapping(shape(geometry).simplify(tolerancia_graus, preserve_topology=True))
    return {"type": simples["type"], "coordinates": _arredondar(simples["coordinates"])}


def _arredondar(coords, casas: int = 6):
    """6 casas decimais ≈ 0,1 m: precisão de sobra para desenhar, com metade do tamanho."""
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], casas), round(coords[1], casas)]
    return [_arredondar(c, casas) for c in coords]


def ponto_representativo(geometry: dict) -> tuple[float, float]:
    """(lon, lat) garantidamente dentro do polígono — usado para buscar clima por distrito."""
    p = shape(geometry).representative_point()
    return p.x, p.y


# ----------------------------------------------------------------------- ponto em polígono (bairro / distrito)
URL_MALHA_BAIRROS = (
    "https://dados.recife.pe.gov.br/dataset/1702c764-ec7a-4ef0-9861-8acd0e40c819/resource/"
    "5c67ce14-1799-40c4-a37c-9daa04d1761c/download/bairros-do-recife.geojson"
)
ARQUIVO_MALHA_BAIRROS = "bairros-do-recife.geojson"  # Dados Abertos do Recife, conjunto "área urbana" (ODbL)


def carregar_malha_bairros(pasta=None, baixar: bool = True, http=None) -> dict | None:
    """Polígonos oficiais dos 94 bairros (CRS84). Lê a cópia em data/territorio; sem ela, baixa uma vez.
    None quando não há arquivo nem rede: quem chama cai para o distrito (precisão honesta, RN-07)."""
    import json
    from pathlib import Path

    from climasense.config import RAIZ_REPOSITORIO

    caminho = Path(pasta or RAIZ_REPOSITORIO / "data" / "territorio") / ARQUIVO_MALHA_BAIRROS
    if not caminho.exists():
        if not baixar:
            return None
        try:
            import requests

            r = (http or requests).get(URL_MALHA_BAIRROS, timeout=120)
            r.raise_for_status()
            json.loads(r.content)
            caminho.write_bytes(r.content)
        except Exception:  # noqa: BLE001 — sem malha, a associação fica no distrito
            return None
    return json.loads(caminho.read_text(encoding="utf-8"))


class Localizador:
    """Associa (lon, lat) ao bairro e ao distrito oficiais por ponto-em-polígono.

    Bairros vêm da malha oficial (nome → id `bairro-<slug>`); o distrito do bairro vem do vínculo oficial
    distrito→bairros. Sem malha de bairros, o ponto é associado só ao distrito, pela geometria do distrito.
    """

    def __init__(self, distritos: dict, malha_bairros: dict | None = None) -> None:
        from shapely.prepared import prep

        from climasense.territorio.carga import slug

        self._slug = slug
        self.distritos = []
        self.bairro_para_distrito: dict[str, str] = {}
        for f in distritos["features"]:
            ds = f"ds-{f['properties']['cdistscodi']}"
            self.distritos.append((ds, prep(shape(f["geometry"]))))
            for b in f["properties"].get("bairros", []):
                self.bairro_para_distrito[f"bairro-{slug(b)}"] = ds
        self.bairros = []
        for f in (malha_bairros or {}).get("features", []):
            p = f["properties"]
            nome = (
                p.get("EBAIRRNOME") or p.get("EBAIRRNOMEOF") or ""
            )  # o "OF" traz sufixos ("Cohab - Ibura de Cima")
            self.bairros.append((f"bairro-{slug(nome)}", prep(shape(f["geometry"]))))
        self.tem_bairros = bool(self.bairros)

    def localizar(self, lon: float | None, lat: float | None) -> tuple[str | None, str | None]:
        """(bairro_id, distrito_id); (None, None) fora do Recife ou sem coordenada."""
        from shapely.geometry import Point

        if lon is None or lat is None:
            return None, None
        p = Point(float(lon), float(lat))
        bairro = next((b for b, g in self.bairros if g.covers(p)), None)
        if bairro and bairro in self.bairro_para_distrito:
            return bairro, self.bairro_para_distrito[bairro]
        distrito = next((d for d, g in self.distritos if g.covers(p)), None)
        return None, distrito


def contorno_recife(distritos: dict):
    """União dos oito distritos (shapely), para filtrar alertas por interseção com o Recife."""
    from shapely.ops import unary_union

    return unary_union([shape(f["geometry"]) for f in distritos["features"]])
