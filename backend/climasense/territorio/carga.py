"""Carga territorial oficial no Atlas — porte do `load_mongo.py` (Desktop/AVD, Aula 07), sem alterar a regra.

    python -m climasense.territorio carregar [--baixar]

Upsert por código (não apaga a coleção), correções DS VII/VIII documentadas, área geodésica,
faixas hídricas com geometria simplificada para a web e sincronização de app.territorios.
"""

from __future__ import annotations

import copy
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.config import RAIZ_REPOSITORIO
from climasense.infra.mongo import COLECAO_DISTRITOS, COLECAO_HIDROGRAFIA
from climasense.territorio.geometria import area_km2, simplificar_web

DATA = RAIZ_REPOSITORIO / "data" / "territorio"
BASE = "https://dados.recife.pe.gov.br/dataset/"
SOURCES = {
    "distritos-sanitarios-do-recife.geojson": BASE
    + "09ae25d3-7330-4fff-af57-9e9191a4c2f6/resource/8d43533d-100b-4de2-9b08-65703d910320/download/distritos-sanitarios-do-recife.geojson",
    "distritos-sanitarios-descricao-dos-bairros.csv": BASE
    + "09ae25d3-7330-4fff-af57-9e9191a4c2f6/resource/d8d649d6-5bf7-44af-9686-436162766037/download/distritos-sanitarios-descricao-dos-bairros.csv",
    "faixas-marginais-dos-recursos-hidricos.geojson": BASE
    + "1bf02d9c-2754-41cc-aede-1ac8e237f166/resource/81310c02-4bb8-4fea-b676-0c42977b4aef/download/faixas-marginais-dos-recursos-hidricos.geojson",
}
FONTE_USF = "https://www2.recife.pe.gov.br/servico/localizacao-das-usf"
ROMANOS = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}


class ErroTerritorio(ValueError):
    pass


def baixar_dados(destino: Path = DATA) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for filename, url in SOURCES.items():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        if filename.endswith(".geojson") and response.json().get("type") != "FeatureCollection":
            raise ErroTerritorio("A fonte não retornou uma FeatureCollection.")
        (destino / filename).write_bytes(response.content)


def carregar_arquivos(origem: Path = DATA) -> tuple[dict, list[dict]]:
    geo = json.loads((origem / "distritos-sanitarios-do-recife.geojson").read_text(encoding="utf-8-sig"))
    with (origem / "distritos-sanitarios-descricao-dos-bairros.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        bairros = list(csv.DictReader(stream, delimiter=";"))
    return geo, bairros


def carregar_hidrografia(origem: Path = DATA) -> dict:
    return json.loads(
        (origem / "faixas-marginais-dos-recursos-hidricos.geojson").read_text(encoding="utf-8-sig")
    )


def corrigir_vinculos(bairros: list[dict], origem: Path = DATA) -> list[dict]:
    """Correções explícitas, verificáveis e separadas do arquivo original da aula."""
    corrections = json.loads((origem / "correcoes-bairros.json").read_text(encoding="utf-8"))
    result = copy.deepcopy(bairros)
    for row in result:
        row["distrito_sanitario_original"] = int(row["distrito_sanitario"])
        code = corrections["bairros"].get(row["bairro"], int(row["distrito_sanitario"]))
        row["distrito_sanitario"] = str(code)
        if code in (7, 8):
            row["descricao_distrito"] = "DS " + ("VII" if code == 7 else "VIII")
    return result


def enriquecer_distritos(geo: dict, bairros: list[dict]) -> dict:
    result = copy.deepcopy(geo)
    groups: dict[int, dict[str, Any]] = {}
    for row in bairros:
        code = int(row["distrito_sanitario"])
        group = groups.setdefault(
            code, {"nome": row["descricao_distrito"], "bairros": set(), "auditoria": {}}
        )
        group["bairros"].add(row["bairro"].strip())
        group["auditoria"][row["bairro"].strip()] = int(row.get("distrito_sanitario_original", code))
    codes = set()
    for feature in result["features"]:
        props = feature["properties"]
        code = int(props["cdistscodi"])
        if code not in groups or code in codes:
            raise ErroTerritorio(f"Distrito duplicado ou sem correspondência no CSV: {code}")
        codes.add(code)
        group = groups[code]
        props.update(
            cdistscodi=code,
            nome_distrito=group["nome"],
            bairros=sorted(group["bairros"]),
            quantidade_bairros=len(group["bairros"]),
            area_km2=round(area_km2(feature["geometry"]), 3),
        )
        props["codigos_originais_csv"] = group["auditoria"]
        props["fonte_vinculo_bairros"] = (
            FONTE_USF if code in (7, 8) else SOURCES["distritos-sanitarios-descricao-dos-bairros.csv"]
        )
    if codes != set(groups):
        raise ErroTerritorio("Há bairros cujo distrito não possui geometria.")
    result["features"].sort(key=lambda feature: feature["properties"]["cdistscodi"])
    return result


def preparar_hidrografia(water: dict) -> list[dict]:
    """Cada faixa ganha `geometry_web` simplificada e um id estável para upsert."""
    feicoes = []
    for i, f in enumerate(water["features"]):
        doc = copy.deepcopy(f)
        doc["properties"]["id_faixa"] = doc["properties"].get("objectid", i + 1)
        doc["geometry_web"] = simplificar_web(f["geometry"])
        feicoes.append(doc)
    return feicoes


# ----------------------------------------------------------------------- Atlas
def salvar_atlas(cliente, geo: dict, banco: str) -> int:
    colecao = cliente[banco][COLECAO_DISTRITOS]
    for f in geo["features"]:  # upsert por código, como no load_mongo.py: nunca apaga a coleção
        colecao.update_one({"properties.cdistscodi": f["properties"]["cdistscodi"]}, {"$set": f}, upsert=True)
    return len(geo["features"])


def salvar_hidrografia(cliente, feicoes: list[dict], banco: str) -> int:
    colecao = cliente[banco][COLECAO_HIDROGRAFIA]
    for f in feicoes:
        colecao.update_one({"properties.id_faixa": f["properties"]["id_faixa"]}, {"$set": f}, upsert=True)
    return len(feicoes)


def ler_atlas(cliente, banco: str) -> dict:
    features = list(
        cliente[banco][COLECAO_DISTRITOS].find(
            {"properties.cdistscodi": {"$in": list(range(1, 9))}}, {"_id": 0}
        )
    )
    if len(features) != 8 or len({f["properties"]["cdistscodi"] for f in features}) != 8:
        raise ErroTerritorio(
            "O Atlas deve conter os oito distritos, sem duplicação. Rode: python -m climasense.territorio carregar"
        )
    features.sort(key=lambda f: f["properties"]["cdistscodi"])
    return {"type": "FeatureCollection", "features": features}


def ler_hidrografia(cliente, banco: str, web: bool = True) -> dict:
    features = []
    for doc in cliente[banco][COLECAO_HIDROGRAFIA].find({}, {"_id": 0}):
        geom = doc.pop("geometry_web", None)
        if web and geom:
            doc["geometry"] = geom
        features.append(doc)
    return {"type": "FeatureCollection", "features": features}


# ----------------------------------------------------------------------- app.territorios (Postgres)
def slug(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def sincronizar_territorios(db: Session, geo: dict) -> int:
    linhas = [("recife", "municipio", "Recife", "Recife inteiro", None, "2611606")]
    for f in geo["features"]:
        p = f["properties"]
        ds = f"ds-{p['cdistscodi']}"
        romano = ROMANOS[p["cdistscodi"]]
        linhas.append(
            (
                ds,
                "distrito",
                p["nome_distrito"],
                f"Distrito Sanitário {romano}",
                "recife",
                str(p["cdistscodi"]),
            )
        )
        for bairro in p["bairros"]:
            linhas.append((f"bairro-{slug(bairro)}", "bairro", bairro, bairro, ds, None))
    for linha in linhas:
        db.execute(
            text(
                "insert into app.territorios (id, tipo, nome_oficial, nome_exibicao, pai_id, codigo_oficial) "
                "values (:i, :t, :o, :e, :p, :c) on conflict (id) do update set tipo = excluded.tipo, "
                "nome_oficial = excluded.nome_oficial, nome_exibicao = excluded.nome_exibicao, "
                "pai_id = excluded.pai_id, codigo_oficial = excluded.codigo_oficial"
            ),
            dict(zip("itoepc", linha, strict=True)),
        )
    db.commit()
    return len(linhas)


def geo_local() -> dict:
    """Base enriquecida a partir dos arquivos oficiais locais (modo explícito --local)."""
    geo, bairros = carregar_arquivos()
    return enriquecer_distritos(geo, corrigir_vinculos(bairros))
