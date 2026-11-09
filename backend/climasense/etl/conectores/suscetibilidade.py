"""Suscetibilidade do terreno a deslizamento (carta do SGB/CPRM, 2012 a 2014, escala 1:45.000) → fração da área de cada
bairro por classe (RF-02, RF-04).

Camada ArcGIS `Hosted/Suscebilidade_Deslizamento/FeatureServer/0` do portal ESIG do Recife (consulta pública, sem
autenticação): 489 polígonos Alta, Média e Baixa que cobrem 99% do município. É SUSCETIBILIDADE DO TERRENO modelada
(validada em campo pela CPRM), não setor de risco, não previsão e não mapeia moradias: o rótulo é sempre "suscetibilidade
do terreno (carta 2012–2014, escala 1:45.000)", nunca "risco" (RN-11 vale para qualquer previsão derivada).

Cálculo: por bairro oficial e por classe, `fração = área(bairro ∩ união dos polígonos da classe) / área(bairro)`, em
SIRGAS 2000 UTM 25S (EPSG:31985, metros). A classe "coberta" é a fração do bairro com qualquer classe da carta (o resto
fica sem carta: ausência de dado, não "baixa"). A união por classe evita contar duas vezes polígonos sobrepostos.
"""

from __future__ import annotations

import re

import pandas as pd
from shapely import union_all
from shapely.geometry import shape
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores import geo_territorial as geo
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo

CAMADA = "Suscebilidade_Deslizamento"
CAMPOS = "classe,processo,fonte"
CLASSES = ("alta", "media", "baixa")
ROTULO = "suscetibilidade do terreno (carta 2012–2014, escala 1:45.000)"
PREFIXO = "suscetibilidade_deslizamento_"
OBSERVACAO = (
    "Suscetibilidade modelada do terreno (SGB/CPRM), não é setor de risco nem previsão. 'Baixa' ou ausência de "
    "'Alta' não significa ausência de ocorrência."
)


def classe_de(valor) -> str | None:
    """'Alta' | 'Média' | 'Baixa' (com ou sem acento, ou com o byte quebrado da fonte) → alta | media | baixa."""
    t = geo.semsotaque(str(valor or "")).strip().lower()
    if re.fullmatch(r"m.{0,3}dia", t):
        return "media"
    return t if t in ("alta", "baixa") else None


class ConectorSgbSuscetibilidadeDeslizamento(Conector):
    id = "sgb-suscetibilidade-deslizamento"
    fonte = FonteInfo(
        "Suscetibilidade do terreno a deslizamento (carta SGB/CPRM 2012–2014)",
        "SGB/CPRM, publicada pela Prefeitura do Recife (ESIG)",
        geo.url_camada(CAMADA),
        "derivada",
        "Camada pública do portal ESIG Recife (licença não declarada na camada)",
    )

    def __init__(self, http=None, malha=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.malha = malha  # [(bairro_id, geometria)] — só em teste; senão a malha oficial local
        self.descartes: dict[str, int] = {}
        self.cobertura: dict = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        feicoes = geo.consultar_camada(self.http, CAMADA, CAMPOS, ctx.limite)
        return [
            {
                "registro": "consulta",
                "url": geo.url_camada(CAMADA),
                "poligonos": len(feicoes),
                "amostra": ctx.limite is not None,  # extração parcial = amostra (RN-10)
                "ultima_edicao_fonte": geo.ultima_edicao(self.http, CAMADA),
            },
            *(
                {"registro": "poligono", **(f.get("properties") or {}), "geometry": f.get("geometry")}
                for f in feicoes
            ),
        ]

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {}
        por_classe: dict[str, list] = {c: [] for c in CLASSES}
        for r in bruto[bruto["registro"] == "poligono"].to_dict("records"):
            if "desliz" not in geo.semsotaque(str(r.get("processo") or "")).lower():
                self._conta("processo_fora_do_escopo")
                continue
            classe = classe_de(r.get("classe"))
            geom = r.get("geometry")
            if classe is None:
                self._conta("classe_desconhecida")
            elif not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
                self._conta("geometria_invalida")
            else:
                g = geo.poligonal(shape(geom))
                if g is None or g.is_empty:
                    self._conta("geometria_invalida")
                else:
                    por_classe[classe].append(geo.projetar(g))
        if not any(por_classe.values()):
            return pd.DataFrame()
        uniao = {c: union_all(p) for c, p in por_classe.items() if p}
        cobertas = union_all(list(uniao.values()))
        sobreposto_km2 = (
            sum(u.area for u in uniao.values()) - cobertas.area
        ) / 1e6  # área contada em mais de uma classe
        indice = geo.IndiceBairros(self.malha)
        linhas = []
        for bairro_id, g in zip(indice.ids, indice.geoms, strict=True):
            gb = geo.projetar(g)
            area_b = gb.area
            partes = {c: gb.intersection(u).area for c, u in uniao.items()}
            partes["coberta"] = gb.intersection(cobertas).area
            if partes["coberta"] <= 0:
                continue  # a carta não toca o bairro: sem dado (nunca "baixa")
            for classe in (*CLASSES, "coberta"):
                a = partes.get(classe, 0.0)
                linhas.append(
                    {
                        "bairro_id": bairro_id,
                        "classe": classe,
                        "area_km2": a / 1e6,
                        "fracao": min(1.0, a / area_b),
                    }
                )
        df = pd.DataFrame(linhas)
        if not df.empty:
            ids = df[df["classe"] == "coberta"]["bairro_id"]
            relevantes = {c: int(((df["classe"] == c) & (df["fracao"] >= 0.01)).sum()) for c in CLASSES}
            self.cobertura = {
                "poligonos_por_classe": {c: len(p) for c, p in por_classe.items()},
                "n_bairros_com_carta": int(ids.nunique()),
                "n_bairros_oficiais": len(indice.ids),
                "bairros_com_pelo_menos_1_pct_por_classe": relevantes,
                "area_sobreposta_entre_classes_km2": round(sobreposto_km2, 4),
                "area_do_municipio_coberta_km2": round(cobertas.area / 1e6, 2),
            }
        return df

    def _conta(self, motivo: str) -> None:
        self.descartes[motivo] = self.descartes.get(motivo, 0) + 1

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        if ctx.limite is not None:
            print(
                "[suscetibilidade] AMOSTRA (--limite): só a bronze foi gravada; a silver anterior fica intacta."
            )
            return 0
        linhas = [
            {
                "b": r["bairro_id"],
                "c": r["classe"],
                "a": float(r["area_km2"]),
                "fr": float(r["fracao"]),
                "f": self.id,
                "ex": ctx.execucao_id,
            }
            for r in df.to_dict("records")
        ]
        with ctx.engine.begin() as c:
            c.execute(
                text("delete from silver.suscetibilidade_deslizamento where fonte_id = :f"), {"f": self.id}
            )
            c.execute(
                text(
                    "insert into silver.suscetibilidade_deslizamento (bairro_id, classe, area_km2, fracao, fonte_id, "
                    "execucao_id) values (:b, :c, :a, :fr, :f, :ex)"
                ),
                linhas,
            )
        k = self.cobertura
        print(
            f"[suscetibilidade] {k.get('n_bairros_com_carta')} de {k.get('n_bairros_oficiais')} bairros com carta; "
            f"polígonos {k.get('poligonos_por_classe')}; bairros com >= 1% por classe "
            f"{k.get('bairros_com_pelo_menos_1_pct_por_classe')}; área sobreposta entre classes "
            f"{k.get('area_sobreposta_entre_classes_km2')} km2"
        )
        return len(linhas)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        if ctx.limite is not None:
            return
        nomes = {
            "alta": "Fração da área do bairro com suscetibilidade ALTA",
            "media": "Fração da área do bairro com suscetibilidade MÉDIA",
            "baixa": "Fração da área do bairro com suscetibilidade BAIXA",
            "coberta": "Fração da área do bairro que a carta cobre (o resto é sem dado)",
        }
        indicadores = [
            geo.Indicador(
                f"{PREFIXO}{classe}",
                ROTULO,
                "fracao_da_area_do_bairro",
                "2012-2014",
                f"{nomes[classe]}. {OBSERVACAO}",
                "select bairro_id, fracao as valor from silver.suscetibilidade_deslizamento "
                "where fonte_id = :f and classe = :c",
                (("c", classe),),
            )
            for classe in (*CLASSES, "coberta")
        ]
        with ctx.engine.begin() as c:
            geo.gravar_indicadores(c, self.id, ctx.agora, indicadores)
