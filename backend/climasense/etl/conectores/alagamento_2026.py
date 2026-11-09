"""Retrato do alagamento de 2026 por bairro: comunidades alagadas, lotes e trechos de rua (RF-02, RF-04).

Camadas ArcGIS do portal ESIG do Recife (consulta pública, sem autenticação):
- `Hosted/Poligonos_Alagamentos_2026_5` (78 polígonos de comunidades, com `qtd_registros`);
- `Hosted/Lotes_Areas_Alagadas_2026_V1` (5.761 lotes atingidos; só `qtdunhab`, unidades habitacionais);
- `Hosted/Logradouros_Alagamentos_2026_V1` (552 trechos de rua alagados; só o identificador do trecho).

NENHUMA camada traz data por registro: é o retrato acumulado de um evento. O rótulo é "evento de 2026, sem data por
registro". O significado exato de `qtd_registros` não é documentado na camada (pergunta aberta).

Privacidade (RN-13, RNF-03): os lotes e logradouros têm endereço, número, complemento e inscrição do imóvel; o conector
pede SÓ `qtdunhab` (lotes) e o identificador do trecho (logradouros). Da geometria de lote e de trecho NADA é gravado
(nem na bronze): ela vira o `bairro_id` ainda na extração (ponto representativo do lote e ponto médio do trecho dentro
da malha oficial) e a coordenada é descartada, porque a posição de um imóvel é dado de residência. A camada
`Base_Celpe_*` (nome de cliente, medidor, endereço) NÃO é lida. `Alagamento_2026_V2` (42 polígonos, sem
`qtd_registros`) também não: é uma versão anterior das mesmas comunidades.

Bairro da comunidade: o da malha oficial com MAIOR área de interseção com o polígono (uma comunidade que cruza bairros
é atribuída a um só; a camada não traz o bairro).
"""

from __future__ import annotations

import pandas as pd
from shapely.geometry import shape
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores import geo_territorial as geo
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo

COMUNIDADES = "Poligonos_Alagamentos_2026_5"
LOTES = "Lotes_Areas_Alagadas_2026_V1"
TRECHOS = "Logradouros_Alagamentos_2026_V1"
CAMPOS = {COMUNIDADES: "id,comunidade,rpa,qtd_registros", LOTES: "qtdunhab", TRECHOS: "fid"}
ROTULO = "evento de 2026, sem data por registro"
PREFIXO = "alagamento_2026_"
OBSERVACAO = "Retrato acumulado do evento de 2026, sem data por registro. Bairro sem registro na camada = sem dado, nunca zero."


def _arredondar(c, casas: int = 6):
    if isinstance(c[0], (int, float)):
        return [round(c[0], casas), round(c[1], casas)]
    return [_arredondar(x, casas) for x in c]


class ConectorRecifeAlagamento2026(Conector):
    id = "recife-alagamento-2026"
    fonte = FonteInfo(
        "Alagamento de 2026: comunidades, lotes e trechos alagados (retrato sem data por registro)",
        "Prefeitura do Recife (ESIG)",
        geo.URL_ESIG,
        "observada",
        "Camadas públicas do portal ESIG Recife (licença não declarada nas camadas)",
    )

    def __init__(self, http=None, malha=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.malha = malha  # só em teste
        self.descartes: dict[str, int] = {}
        self.cobertura: dict = {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        indice = geo.IndiceBairros(self.malha)
        amostra = ctx.limite is not None
        saida: list[dict] = []
        for camada in (COMUNIDADES, LOTES, TRECHOS):
            feicoes = geo.consultar_camada(self.http, camada, CAMPOS[camada], ctx.limite)
            saida.append(
                {
                    "registro": "consulta",
                    "camada": camada,
                    "url": geo.url_camada(camada),
                    "feicoes": len(feicoes),
                    "amostra": amostra,  # extração parcial = amostra (RN-10)
                    "ultima_edicao_fonte": geo.ultima_edicao(self.http, camada),
                }
            )
            for f in feicoes:
                p, g = f.get("properties") or {}, f.get("geometry")
                if camada == COMUNIDADES:
                    saida.append(
                        {
                            "registro": "comunidade",
                            "id": p.get("id"),
                            "comunidade": p.get("comunidade"),
                            "rpa": p.get("rpa"),
                            "qtd_registros": p.get("qtd_registros"),
                            "geometry": g
                            and {"type": g["type"], "coordinates": _arredondar(g["coordinates"])},
                        }
                    )
                    continue
                bairro = self._bairro_do_ponto(g, indice)
                if camada == LOTES:
                    saida.append({"registro": "lote", "bairro_id": bairro, "qtdunhab": p.get("qtdunhab")})
                else:
                    saida.append({"registro": "trecho", "bairro_id": bairro})
        return saida

    @staticmethod
    def _bairro_do_ponto(geom: dict | None, indice: geo.IndiceBairros) -> str | None:
        """Bairro do ponto representativo (lote) ou do ponto médio (trecho); a coordenada não sai daqui."""
        if not isinstance(geom, dict) or not geom.get("coordinates"):
            return None
        g = shape(geom)
        ponto = (
            g.interpolate(0.5, normalized=True) if g.geom_type in ("LineString", "MultiLineString") else None
        )
        if ponto is None:
            p = geo.poligonal(g)
            ponto = p.representative_point() if p is not None and not p.is_empty else None
        return indice.do_ponto(ponto) if ponto is not None else None

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {}
        indice = geo.IndiceBairros(self.malha)
        linhas: list[dict] = []
        for coluna in ("bairro_id", "qtdunhab"):
            if coluna not in bruto:
                bruto = bruto.assign(**{coluna: None})
        for r in bruto[bruto["registro"] == "comunidade"].to_dict("records"):
            geom = r.get("geometry")
            g = (
                geo.poligonal(shape(geom))
                if isinstance(geom, dict) and geom.get("type") in ("Polygon", "MultiPolygon")
                else None
            )
            bairro = indice.de_maior_sobreposicao(g) if g is not None and not g.is_empty else None
            if bairro is None:
                self._conta("comunidade_fora_da_malha")
                continue
            qtd = comum.numero(r.get("qtd_registros"))
            linhas.append(
                {
                    "id": f"com-{int(r['id'])}",
                    "camada": "comunidades",
                    "bairro_id": bairro,
                    "comunidade": str(r.get("comunidade") or "").strip() or None,
                    "rpa": None if comum.real(r.get("rpa")) is None else int(r["rpa"]),
                    "itens": 1,
                    "qtd_registros": None if qtd is None else int(qtd),
                    "unidades_habitacionais": None,
                }
            )
        lotes = bruto[bruto["registro"] == "lote"]
        for bairro, grupo in lotes[lotes["bairro_id"].notna()].groupby("bairro_id"):
            un = pd.to_numeric(grupo["qtdunhab"], errors="coerce").dropna()
            un = un[un >= 0]
            linhas.append(
                {
                    "id": f"lotes-{bairro}",
                    "camada": "lotes",
                    "bairro_id": bairro,
                    "comunidade": None,
                    "rpa": None,
                    "itens": len(grupo),
                    "qtd_registros": None,
                    "unidades_habitacionais": int(un.sum()) if len(un) else None,
                }
            )
        trechos = bruto[bruto["registro"] == "trecho"]
        for bairro, grupo in trechos[trechos["bairro_id"].notna()].groupby("bairro_id"):
            linhas.append(
                {
                    "id": f"trechos-{bairro}",
                    "camada": "trechos",
                    "bairro_id": bairro,
                    "comunidade": None,
                    "rpa": None,
                    "itens": len(grupo),
                    "qtd_registros": None,
                    "unidades_habitacionais": None,
                }
            )
        self.descartes["lote_fora_da_malha"] = int(lotes["bairro_id"].isna().sum())
        self.descartes["trecho_fora_da_malha"] = int(trechos["bairro_id"].isna().sum())
        self.descartes = {k: v for k, v in self.descartes.items() if v}
        df = pd.DataFrame(linhas)
        if not df.empty:
            por = {
                c: df[df["camada"] == c]["bairro_id"].nunique() for c in ("comunidades", "lotes", "trechos")
            }
            self.cobertura = {
                "n_bairros_oficiais": len(indice.ids),
                "bairros_por_camada": {k: int(v) for k, v in por.items()},
                "n_bairros_com_algum_registro": int(df["bairro_id"].nunique()),
                "comunidades": int((df["camada"] == "comunidades").sum()),
                "lotes": int(df.loc[df["camada"] == "lotes", "itens"].sum()),
                "trechos": int(df.loc[df["camada"] == "trechos", "itens"].sum()),
            }
        return df

    def _conta(self, motivo: str) -> None:
        self.descartes[motivo] = self.descartes.get(motivo, 0) + 1

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        if ctx.limite is not None:
            print(
                "[alagamento-2026] AMOSTRA (--limite): só a bronze foi gravada; a silver anterior fica intacta."
            )
            return 0
        linhas = [
            {**{k: comum.valor_sql(v) for k, v in r.items()}, "f": self.id, "ex": ctx.execucao_id}
            for r in df.to_dict("records")
        ]
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.alagamento_2026 where fonte_id = :f"), {"f": self.id})
            c.execute(
                text(
                    "insert into silver.alagamento_2026 (id, camada, bairro_id, comunidade, rpa, itens, "
                    "qtd_registros, unidades_habitacionais, fonte_id, execucao_id) values (:id, :camada, :bairro_id, "
                    ":comunidade, :rpa, :itens, :qtd_registros, :unidades_habitacionais, :f, :ex)"
                ),
                linhas,
            )
        k = self.cobertura
        print(
            f"[alagamento-2026] {k.get('n_bairros_com_algum_registro')} de {k.get('n_bairros_oficiais')} bairros com "
            f"algum registro; bairros por camada {k.get('bairros_por_camada')}; comunidades {k.get('comunidades')}, "
            f"lotes {k.get('lotes')}, trechos {k.get('trechos')}; descartes {self.descartes}"
        )
        return len(linhas)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        if ctx.limite is not None:
            return

        def ind(nome, unidade, o, consulta):
            return geo.Indicador(f"{PREFIXO}{nome}", ROTULO, unidade, "2026", f"{o} {OBSERVACAO}", consulta)

        base = "from silver.alagamento_2026 where fonte_id = :f and camada = "
        indicadores = [
            ind(
                "comunidades",
                "comunidades",
                "Comunidades alagadas cuja maior parte está no bairro.",
                f"select bairro_id, sum(itens)::double precision as valor {base}'comunidades' group by bairro_id",  # noqa: S608
            ),
            ind(
                "registros",
                "registros",
                "Soma de `qtd_registros` das comunidades do bairro (significado exato não documentado na camada).",
                "select bairro_id, sum(qtd_registros)::double precision as valor "  # noqa: S608
                f"{base}'comunidades' group by bairro_id",
            ),
            ind(
                "lotes",
                "lotes",
                "Lotes atingidos no bairro.",
                f"select bairro_id, sum(itens)::double precision as valor {base}'lotes' group by bairro_id",  # noqa: S608
            ),
            ind(
                "unidades_habitacionais",
                "unidades_habitacionais",
                "Soma de `qtdunhab` dos lotes atingidos; lote sem o campo não entra na soma.",
                "select bairro_id, sum(unidades_habitacionais)::double precision as valor "  # noqa: S608
                f"{base}'lotes' group by bairro_id",
            ),
            ind(
                "trechos",
                "trechos_de_rua",
                "Trechos de rua alagados no bairro (pelo ponto médio do trecho).",
                f"select bairro_id, sum(itens)::double precision as valor {base}'trechos' group by bairro_id",  # noqa: S608
            ),
        ]
        with ctx.engine.begin() as c:
            geo.gravar_indicadores(c, self.id, ctx.agora, indicadores)
