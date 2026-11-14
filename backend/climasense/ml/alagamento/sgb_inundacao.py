"""Pesquisa local: frações de suscetibilidade à INUNDAÇÃO do SGB por bairro do Recife.

Não executa ETL, não modifica Neon/Atlas e não representa previsão nem risco operacional.
Fonte: https://geoportal.sgb.gov.br/server/rest/services/gestaoterritorial/inundacao/FeatureServer/0
Carta do Recife: CPRM (2015), escala 1:45.000.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from shapely import force_2d, union_all
from shapely.geometry import shape

from climasense.config import RAIZ_REPOSITORIO
from climasense.etl.conectores import geo_territorial as geo

URL_CAMADA = "https://geoportal.sgb.gov.br/server/rest/services/gestaoterritorial/inundacao/FeatureServer/0"
FONTE_OFICIAL = "SGB/CPRM, Carta de Suscetibilidade do Recife, 2015, escala 1:45.000"
CRS_ORIGEM = "EPSG:4326"
CLASSES = ("alta", "media", "baixa")
ATRIBUTOS_SGB = ("sgb_frac_alta", "sgb_frac_media", "sgb_cobertura", "sgb_sem_carta")
PASTA_RESULTADOS = RAIZ_REPOSITORIO / "tmp" / "experimentos"


def _normalizar(valor: Any) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", str(valor or "").strip().lower())
        if not unicodedata.combining(c)
    )


def _resposta(session: requests.Session, url: str, params: dict[str, Any]) -> dict:
    try:
        resposta = session.get(url, params=params, timeout=(15, 120))
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError("Não foi possível consultar o serviço de inundação do SGB.") from exc
    if not isinstance(dados, dict) or "error" in dados:
        raise RuntimeError("SGB: resposta inválida ou erro REST; confira a disponibilidade da camada.")
    return dados


def baixar_recife(session: requests.Session | None = None) -> dict:
    """Extrai somente Recife/PE, nunca todas as feições do serviço nacional.

    Obtém IDs primeiro e consulta feições em blocos. Falha explicitamente se o
    ArcGIS não retornar todos os IDs; não produz indicadores a partir de amostra.
    """
    session = session or requests.Session()
    onde = "uf = 'PE' AND municipio = 'RECIFE'"
    endpoint = f"{URL_CAMADA}/query"
    identificadores = _resposta(
        session,
        endpoint,
        {
            "f": "json",
            "where": onde,
            "returnIdsOnly": "true",
            "returnGeometry": "false",
        },
    )
    ids = identificadores.get("objectIds")
    if not isinstance(ids, list) or not ids:
        raise RuntimeError("O serviço SGB não retornou polígonos para Recife/PE; confira o filtro e a fonte.")
    if len(ids) != len(set(ids)):
        raise RuntimeError("O serviço SGB retornou identificadores duplicados.")
    feicoes: list[dict] = []
    for inicio in range(0, len(ids), 250):
        lote = ids[inicio : inicio + 250]
        dados = _resposta(
            session,
            endpoint,
            {
                "f": "geojson",
                "objectIds": ",".join(map(str, lote)),
                "outFields": "objectid,uf,municipio,processo,classe,fonte,ano,projeto,execucao,executor",
                "returnGeometry": "true",
                "outSR": 4326,
            },
        )
        pagina = dados.get("features")
        if not isinstance(pagina, list):
            raise RuntimeError("SGB retornou página sem lista de feições.")
        feicoes.extend(pagina)
    if len(feicoes) != len(ids):
        raise RuntimeError(f"Consulta SGB incompleta: {len(feicoes)} feições para {len(ids)} IDs.")
    return {"type": "FeatureCollection", "features": feicoes, "fonte": URL_CAMADA}


def validar_feicoes(colecao: dict) -> tuple[dict[str, list], dict]:
    """Diferencia inundação de deslizamento/enxurrada e valida atributos/geometrias."""
    por_classe: dict[str, list] = {classe: [] for classe in CLASSES}
    descartes: dict[str, int] = {}
    anos: set[int] = set()
    origens: set[str] = set()
    ids: set[str] = set()

    def descartar(chave: str) -> None:
        descartes[chave] = descartes.get(chave, 0) + 1

    for f in colecao.get("features", []):
        props = f.get("properties") or {}
        if _normalizar(props.get("uf")) != "pe" or _normalizar(props.get("municipio")) != "recife":
            descartar("fora_recife")
            continue
        processo = _normalizar(props.get("processo"))
        if "inund" not in processo:
            descartar("processo_nao_inundacao")
            continue
        classe = _normalizar(props.get("classe"))
        if classe not in CLASSES:
            descartar("classe_desconhecida")
            continue
        try:
            geom = geo.poligonal(force_2d(shape(f.get("geometry"))))
            if geom is None or geom.is_empty:
                raise ValueError("empty")
            geom_projetada = geo.projetar(geom)
            if geom_projetada.area <= 0:
                raise ValueError("no area")
        except (TypeError, ValueError, AttributeError, KeyError):
            descartar("geometria_invalida")
            continue
        oid = props.get("objectid", f.get("id"))
        if oid is not None:
            if str(oid) in ids:
                raise RuntimeError(f"Polígono SGB duplicado: {oid}")
            ids.add(str(oid))
        if props.get("fonte"):
            origens.add(str(props["fonte"])[:150])
        if props.get("ano") is not None:
            try:
                anos.add(int(props["ano"]))
            except (ValueError, TypeError):
                descartar("ano_invalido")
        por_classe[classe].append(geom_projetada)
    if not any(por_classe.values()):
        raise RuntimeError("Nenhum polígono válido de INUNDAÇÃO do Recife foi encontrado na fonte SGB.")
    return por_classe, {
        "poligonos_por_classe": {k: len(v) for k, v in por_classe.items()},
        "descartes": descartes,
        "anos_informados": sorted(anos),
        "fontes_declaradas_na_camada": sorted(origens),
    }


def cruzar_bairros(colecao: dict, bairros: list[tuple[str, Any]] | None = None) -> tuple[pd.DataFrame, dict]:
    """Frações de área em EPSG:31985 (m²). Zonas de classes distintas não se contam duas vezes.

    Na sobreposição entre classes, prioriza alta > média > baixa e registra
    a área conflitante. Bairro não coberto mantém NaN, nunca 0.
    """
    por_classe, qualidade = validar_feicoes(colecao)
    uniao = {c: union_all(p) for c, p in por_classe.items() if p}
    cobertura_total = union_all(list(uniao.values()))
    conflitos = (sum(g.area for g in uniao.values()) - cobertura_total.area) / 1e6
    if bairros is None:
        indice = geo.IndiceBairros()
        bairros = list(zip(indice.ids, indice.geoms, strict=True))
        if len(bairros) != 94:
            raise RuntimeError(f"Esperados 94 bairros oficiais, recebidos {len(bairros)}.")
    if len({i for i, _ in bairros}) != len(bairros):
        raise ValueError("Há IDs de bairro repetidos na malha fornecida.")
    linhas = []
    for bairro_id, geometria in bairros:
        b = geo.poligonal(force_2d(geometria))
        if b is None or b.is_empty:
            raise ValueError(f"Geometria de bairro inválida: {bairro_id}")
        b = geo.projetar(b)
        area = b.area
        if area <= 0:
            raise ValueError(f"Área inválida para bairro {bairro_id}")
        cobertura = b.intersection(cobertura_total)
        if cobertura.is_empty or cobertura.area <= 0:
            linhas.append(
                {
                    "territorio_id": bairro_id,
                    "sgb_frac_alta": float("nan"),
                    "sgb_frac_media": float("nan"),
                    "sgb_frac_baixa": float("nan"),
                    "sgb_cobertura": float("nan"),
                    "sgb_sem_carta": 1,
                }
            )
            continue
        # Exclusão de sobreposição entre as classes (prioridade conservadora).
        vazia = b.difference(b)
        alta = b.intersection(uniao["alta"]) if "alta" in uniao else vazia
        media = b.intersection(uniao["media"]).difference(alta) if "media" in uniao else vazia
        baixa = b.intersection(uniao["baixa"]).difference(alta.union(media)) if "baixa" in uniao else vazia
        linhas.append(
            {
                "territorio_id": bairro_id,
                "sgb_frac_alta": min(1.0, alta.area / area),
                "sgb_frac_media": min(1.0, media.area / area),
                "sgb_frac_baixa": min(1.0, baixa.area / area),
                "sgb_cobertura": min(1.0, cobertura.area / area),
                "sgb_sem_carta": 0,
            }
        )
    tabela = pd.DataFrame(linhas).sort_values("territorio_id").reset_index(drop=True)
    qualidade.update(
        {
            "bairros_total": len(tabela),
            "bairros_com_carta": int((tabela.sgb_sem_carta == 0).sum()),
            "bairros_sem_carta": int((tabela.sgb_sem_carta == 1).sum()),
            "sobreposicao_entre_classes_km2": round(max(0.0, conflitos), 4),
            "observacao": (
                "Área sem carta = desconhecida, não suscetibilidade baixa. "
                "Classes alta/média/baixa não são probabilidades."
            ),
            "fonte": FONTE_OFICIAL,
            "url": URL_CAMADA,
        }
    )
    return tabela, qualidade


def gerar_tabela(
    *,
    cache: Path | None = None,
    atualizar_fonte: bool = False,
    fonte_geojson: Path | None = None,
    pasta: Path = PASTA_RESULTADOS,
) -> tuple[Path, Path]:
    """Somente arquivos locais ignorados pelo Git. Não lê nem modifica bancos."""
    pasta.mkdir(parents=True, exist_ok=True)
    cache = cache or pasta / "sgb_inundacao_recife.geojson"
    if fonte_geojson is not None:
        colecao = json.loads(fonte_geojson.read_text(encoding="utf-8"))
    elif cache.exists() and not atualizar_fonte:
        colecao = json.loads(cache.read_text(encoding="utf-8"))
    else:
        colecao = baixar_recife()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(colecao, ensure_ascii=False), encoding="utf-8")
    tabela, qualidade = cruzar_bairros(colecao)
    qualidade["gerado_em"] = datetime.now(UTC).isoformat()
    csv = pasta / "sgb_inundacao_por_bairro.csv"
    relatorio = pasta / "sgb_inundacao_qualidade.json"
    tabela.to_csv(csv, index=False, encoding="utf-8-sig")
    relatorio.write_text(json.dumps(qualidade, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv, relatorio


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--atualizar-fonte",
        action="store_true",
        help="Ignora o cache local e busca a fonte SGB novamente",
    )
    p.add_argument("--fonte-geojson", type=Path, help="GeoJSON oficial já baixado, para uso sem internet")
    args = p.parse_args()
    csv, meta = gerar_tabela(atualizar_fonte=args.atualizar_fonte, fonte_geojson=args.fonte_geojson)
    print("Tabela territorial gerada:", csv)
    print("Relatório de qualidade:", meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
