"""Setores de risco da Defesa Civil do Recife (Sedec) → `silver.areas_risco` (RF-04, RF-02).

Camada ArcGIS `Hosted/Setores_Risco_SEDEC/FeatureServer/0` do portal ESIG do Recife (consulta pública, sem
autenticação), 677 polígonos em 21 bairros de cinco regionais (Norte, Noroeste, Nordeste, Oeste e Sul). NÃO cobre a
cidade inteira: a tela deve rotular "cobertura parcial". A cobertura real (regionais, bairros, setores por grau) é
calculada a cada carga e impressa. Como a camada já inclui a Regional Sul, o CKAN `defesa-civil` não é usado.

Campos: `risco` (grau R1 a R4 da Sedec), `regional`, `bairro` (sem acento, "Ibura / Cohab" etc.), `localidade`,
`cod_setor` (único), `edificacoe` (nº de edificações). A camada NÃO informa o tipo de perigo (deslizamento ou
alagamento): `tipo` recebe o nome do mapeamento ("setor-de-risco-sedec"). Nada identifica pessoa.

Bairro oficial: o da malha oficial com MAIOR área de interseção com o setor; setor fora da malha, pelo nome do bairro
da camada. O nome que a Sedec escreve nem sempre coincide com a malha (148 de 677 setores caem, em área, em outro
bairro, p. ex. "Alto José Bonifácio" sobre Alto Santa Terezinha): o conector conta quantos e imprime na carga.
"""

from __future__ import annotations

import json
import re
from collections import Counter

import pandas as pd
from shapely.geometry import shape
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URL_CAMADA = (
    "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/Hosted/Setores_Risco_SEDEC/FeatureServer/0"
)
CAMPOS = "id,cod_setor,bairro,localidade,risco,regional,edificacoe"
POR_PAGINA = 2000
TIPO = "setor-de-risco-sedec"
GRAUS = {"R1", "R2", "R3", "R4"}


def _malha_bairros() -> list[tuple[str, object]]:
    """[(bairro_id, geometria shapely)] da malha oficial local."""
    from climasense.territorio.carga import slug
    from climasense.territorio.geometria import carregar_malha_bairros

    malha = carregar_malha_bairros(baixar=False) or {"features": []}
    saida = []
    for f in malha["features"]:
        p = f["properties"]
        nome = p.get("EBAIRRNOME") or p.get("EBAIRRNOMEOF") or ""
        saida.append((f"bairro-{slug(nome)}", shape(f["geometry"])))
    return saida


def bairro_de_maior_sobreposicao(geom, bairros: list[tuple[str, object]]) -> str | None:
    setor = geom if hasattr(geom, "intersection") else shape(geom)
    melhor, area = None, 0.0
    for bairro_id, poligono in bairros:
        if not setor.intersects(poligono):
            continue
        a = setor.intersection(poligono).area
        if a > area:
            melhor, area = bairro_id, a
    return melhor


def _arredondar(c, casas: int = 6):
    if isinstance(c[0], (int, float)):
        return [round(c[0], casas), round(c[1], casas)]
    return [_arredondar(x, casas) for x in c]


class ConectorRecifeAreasRisco(Conector):
    id = "recife-areas-risco"
    fonte = FonteInfo(
        "Setores de risco da Defesa Civil (Sedec), cobertura parcial",
        "Prefeitura do Recife (ESIG, Defesa Civil)",
        URL_CAMADA,
        "observada",
        "Camada pública do portal ESIG Recife (licença não declarada na camada)",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}
        self.cobertura: dict = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        feicoes, deslocamento = [], 0
        while True:
            r = self.http.get(
                f"{URL_CAMADA}/query",
                params={
                    "where": "1=1",
                    "outFields": CAMPOS,
                    "outSR": 4326,
                    "returnGeometry": "true",
                    "resultOffset": deslocamento,
                    "resultRecordCount": POR_PAGINA,
                    "f": "geojson",
                },
                timeout=120,
            )
            r.raise_for_status()
            corpo = r.json()
            if "error" in corpo:
                raise FonteSemDados(f"Camada de setores de risco: {str(corpo['error'])[:200]}")
            pagina = corpo.get("features") or []
            feicoes += pagina
            deslocamento += POR_PAGINA
            if len(pagina) < POR_PAGINA:
                break
        if not feicoes:
            raise FonteSemDados("A camada Setores_Risco_SEDEC não devolveu nenhum setor.")
        return [
            {"registro": "consulta", "url": URL_CAMADA, "setores": len(feicoes)},
            *(
                {"registro": "setor", **(f.get("properties") or {}), "geometry": f.get("geometry")}
                for f in feicoes
            ),
        ]

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        from climasense.ml.alagamento.ocorrencias import mapa_bairros, resolver_bairro

        mapa, malha = mapa_bairros(), _malha_bairros()
        self.descartes = {}
        itens, usados, divergentes = [], set(), 0
        for r in bruto[bruto["registro"] == "setor"].to_dict("records"):
            geom = r.get("geometry")
            if not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
                self.descartes["geometria_invalida"] = self.descartes.get("geometria_invalida", 0) + 1
                continue
            nomes = [
                a[0]
                for a in (resolver_bairro(p, mapa) for p in re.split(r"\s*/\s*", str(r.get("bairro") or "")))
                if a
            ]
            bairro = bairro_de_maior_sobreposicao(shape(geom), malha)
            if bairro is None and nomes:
                bairro = nomes[0]
            elif bairro is not None and nomes and bairro not in nomes:
                divergentes += 1
            codigo = str(r.get("cod_setor") or "").strip()
            chave = f"sedec-{codigo}" if codigo else f"sedec-fid-{r.get('fid')}"
            if chave in usados:
                chave = f"{chave}-{r.get('fid')}"
            usados.add(chave)
            grau = str(r.get("risco") or "").strip().upper()
            itens.append(
                {
                    "id": chave,
                    "tipo": TIPO,
                    "grau": grau if grau in GRAUS else None,
                    "regional": str(r.get("regional") or "").strip() or None,
                    "bairro_id": bairro,
                    "geometria": {"type": geom["type"], "coordinates": _arredondar(geom["coordinates"])},
                }
            )
        df = pd.DataFrame(itens)
        if not df.empty:
            com_bairro = df[df["bairro_id"].notna()]
            self.cobertura = {
                "setores": len(df),
                "regionais": dict(Counter(df["regional"].fillna("sem regional"))),
                "graus": dict(sorted(Counter(df["grau"].fillna("sem grau")).items())),
                "bairros_com_setor": sorted(com_bairro["bairro_id"].unique()),
                "n_bairros_com_setor": int(com_bairro["bairro_id"].nunique()),
                "n_bairros_oficiais": len(mapa),
                "setores_sem_bairro": int(df["bairro_id"].isna().sum()),
                "setores_em_bairro_diferente_do_nome_da_fonte": divergentes,
            }
        return df

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        linhas = [
            {
                "id": r["id"],
                "tipo": r["tipo"],
                "grau": comum.valor_sql(r["grau"]),
                "regional": comum.valor_sql(r["regional"]),
                "bairro_id": comum.valor_sql(r["bairro_id"]),
                "g": json.dumps(r["geometria"], separators=(",", ":")),
                "f": self.id,
                "ex": ctx.execucao_id,
            }
            for r in df.to_dict("records")
        ]
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.areas_risco where fonte_id = :f"), {"f": self.id})
            c.execute(
                text(
                    "insert into silver.areas_risco (id, tipo, grau, regional, bairro_id, geometria, fonte_id, "
                    "execucao_id) values (:id, :tipo, :grau, :regional, :bairro_id, cast(:g as jsonb), :f, :ex)"
                ),
                linhas,
            )
        c = self.cobertura
        print(
            f"[areas-risco] COBERTURA PARCIAL: {c.get('setores')} setores, regionais {c.get('regionais')}, "
            f"graus {c.get('graus')}, {c.get('n_bairros_com_setor')} de {c.get('n_bairros_oficiais')} bairros, "
            f"{c.get('setores_sem_bairro')} sem bairro, {c.get('setores_em_bairro_diferente_do_nome_da_fonte')} em bairro "
            f"diferente do nome escrito pela Sedec. Bairros: {', '.join(c.get('bairros_com_setor', []))}"
        )
        return len(linhas)
