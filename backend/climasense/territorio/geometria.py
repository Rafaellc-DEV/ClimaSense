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
