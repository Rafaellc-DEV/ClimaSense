"""Gera o traço cartográfico do ClimaSense a partir dos arquivos oficiais em data/territorio/.

Saídas (em frontend/src/assets/tracos/):
- rios.svg        faixas marginais dos recursos hídricos + contorno da cidade (fundo da landing)
- distritos.json  os 8 distritos sanitários como caminhos SVG (mapa vivo "Onde há aviso agora"), com os bairros
                  de cada um (vínculo já corrigido em distritos-enriquecidos.geojson)

É reproduzível: a mesma entrada gera exatamente os mesmos arquivos.
Uso:  python scripts/gerar_tracos.py
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data" / "territorio"
SAIDA = RAIZ / "frontend" / "src" / "assets" / "tracos"
ROMANOS = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}
# Bairros conhecidos citados na chamada de cada distrito no mapa, para quem não sabe o número do seu distrito.
REFERENCIAS = {
    1: ["Boa Vista", "Santo Amaro"],
    2: ["Encruzilhada", "Campo Grande"],
    3: ["Casa Amarela", "Gracas"],
    4: ["Madalena", "Varzea"],
    5: ["Afogados", "Mustardinha"],
    6: ["Boa Viagem", "Pina"],
    7: ["Nova Descoberta", "Macaxeira"],
    8: ["Ibura", "Cohab"],
}


def _slug(nome: str) -> str:
    """O mesmo id de bairro de climasense.territorio.carga.slug (bairro-<slug>)."""
    sem_acento = unicodedata.normalize("NFD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def _ler(nome: str) -> dict:
    return json.loads((DADOS / nome).read_text(encoding="utf-8-sig"))


class Projecao:
    """Equiretangular simples centrada no Recife: suficiente para desenho, não para medir."""

    def __init__(self, limites: tuple[float, float, float, float], lado: float, margem: float = 0):
        self.minx, self.miny, self.maxx, self.maxy = limites
        self.k = math.cos(math.radians((self.miny + self.maxy) / 2))
        self.escala = lado / max((self.maxx - self.minx) * self.k, self.maxy - self.miny)
        self.margem = margem
        self.largura = round((self.maxx - self.minx) * self.k * self.escala + 2 * margem)
        self.altura = round((self.maxy - self.miny) * self.escala + 2 * margem)

    def ponto(self, x: float, y: float) -> tuple[float, float]:
        return (
            (x - self.minx) * self.k * self.escala + self.margem,
            (self.maxy - y) * self.escala + self.margem,
        )

    def caminho(self, geom, tolerancia: float) -> str:
        geom = geom.simplify(tolerancia, preserve_topology=True)
        poligonos = [geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))
        partes = []
        for p in poligonos:
            if p.geom_type != "Polygon" or p.is_empty:
                continue
            pts = [self.ponto(x, y) for x, y in p.exterior.coords]
            partes.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + "Z")
        return "".join(partes)


def gerar() -> dict[str, int]:
    distritos = _ler("distritos-sanitarios-do-recife.geojson")["features"]
    rios = _ler("faixas-marginais-dos-recursos-hidricos.geojson")["features"]
    bairros = {
        int(f["properties"]["cdistscodi"]): f["properties"]["bairros"]
        for f in _ler("distritos-enriquecidos.geojson")["features"]
    }
    cidade = unary_union([shape(f["geometry"]) for f in distritos]).buffer(0)
    SAIDA.mkdir(parents=True, exist_ok=True)

    # Fundo da landing: rios + contorno, viewBox de ~1000 px no lado maior.
    pr = Projecao(cidade.bounds, 1000)
    agua = "".join(pr.caminho(shape(f["geometry"]), 0.00012) for f in rios)
    contorno = pr.caminho(cidade, 0.0003)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {pr.largura} {pr.altura}" aria-hidden="true">'
        f'<path class="cidade" d="{contorno}"/><path class="agua" d="{agua}"/></svg>\n'
    )
    (SAIDA / "rios.svg").write_text(svg, encoding="utf-8")

    # Mapa vivo: 8 distritos, viewBox de ~560 px, com ponto para o rótulo.
    pd = Projecao(cidade.bounds, 560, margem=10)
    itens = []
    for f in sorted(distritos, key=lambda f: int(f["properties"]["cdistscodi"])):
        codigo = int(f["properties"]["cdistscodi"])
        g = shape(f["geometry"])
        x, y = pd.ponto(*g.representative_point().coords[0])
        itens.append(
            {
                "id": f"ds-{codigo}",
                "codigo": codigo,
                "rotulo": ROMANOS[codigo],
                "nome": f"Distrito Sanitário {ROMANOS[codigo]}",
                "d": pd.caminho(g, 0.0004),
                "x": round(x),
                "y": round(y),
                "referencias": REFERENCIAS[codigo],
                "bairros": [{"id": f"bairro-{_slug(b)}", "nome": b} for b in bairros[codigo]],
            }
        )
    dados = {"largura": pd.largura, "altura": pd.altura, "distritos": itens}
    (SAIDA / "distritos.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"rios.svg": len(svg.encode()), "distritos.json": (SAIDA / "distritos.json").stat().st_size}


if __name__ == "__main__":
    for nome, tamanho in gerar().items():
        print(f"{nome}: {tamanho / 1024:.0f} KB")
