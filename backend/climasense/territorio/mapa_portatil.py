"""HTML portátil e offline do território — porte do `gerar_mapa.py` (Aula 07), com os mesmos assets."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import folium

ASSETS = Path(__file__).resolve().parent / "assets"
TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"


def gerar(geo: dict, water: dict, source: str, agora: datetime | None = None) -> str:
    mapa = folium.Map(
        location=[-8.05, -34.9],
        zoom_start=11,
        tiles=None,
        control_scale=False,
        prefer_canvas=False,
        zoom_control=True,
        zoom_snap=0.25,
        zoom_delta=0.5,
    )
    mapa.default_js = []
    mapa.default_css = []
    folium.TileLayer(
        TILES,
        attr="Tiles &copy; Esri — Sources: Esri, HERE, Garmin, USGS, OpenStreetMap contributors",
        name="Mapa de ruas",
        max_zoom=19,
    ).add_to(mapa)
    districts = folium.GeoJson(
        geo,
        name="Distritos sanitários",
        style_function=lambda _: {
            "fillColor": "#7caf68",
            "color": "#476744",
            "weight": 1.2,
            "fillOpacity": 0.72,
        },
    ).add_to(mapa)
    folium.map.CustomPane("hidrografia", z_index=410).add_to(mapa)
    water_layer = folium.GeoJson(
        water,
        name="Faixas marginais dos recursos hídricos",
        pane="hidrografia",
        style_function=lambda _: {
            "fillColor": "#168bb8",
            "color": "#148dbb",
            "weight": 0.8,
            "fillOpacity": 0.28,
            "opacity": 0.8,
        },
    ).add_to(mapa)
    html = mapa.get_root().render()
    leaflet_js = (ASSETS / "vendor/leaflet.js").read_text(encoding="utf-8")
    leaflet_css = (ASSETS / "vendor/leaflet.css").read_text(encoding="utf-8")
    css = (ASSETS / "styles.css").read_text(encoding="utf-8")
    head = '<title>Recife / Atlas — Distritos Sanitários</title>\n<link rel="icon" href="data:,">\n'
    head += "<style>" + leaflet_css + "\n" + css + "</style>\n<script>" + leaflet_js + "</script>\n"
    html = html.replace("<html>", '<html lang="pt-BR">').replace("</head>", head + "</head>")
    html = html.replace("<body>", "<body>\n" + (ASSETS / "layout.html").read_text(encoding="utf-8"))
    metadata = {
        "source": source,
        "date": (agora or datetime.now()).strftime("%d/%m/%Y"),
        "waterCount": len(water["features"]),
    }
    app = (ASSETS / "app.js").read_text(encoding="utf-8")
    for key, value in {
        "__MAP__": mapa.get_name(),
        "__DISTRICTS__": districts.get_name(),
        "__WATER__": water_layer.get_name(),
        "__METADATA__": json.dumps(metadata, ensure_ascii=True),
    }.items():
        app = app.replace(key, value)
    before, after = html.rsplit("</script>", 1)
    return (
        before + "\n" + (ASSETS / "model.js").read_text(encoding="utf-8") + "\n" + app + "\n</script>" + after
    )
