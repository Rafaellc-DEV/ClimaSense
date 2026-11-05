"""Avisos oficiais que atingem o Recife (F7: origem e localização em todo alerta).

Quatro origens públicas, sem cadastro; cada uma é consultada de forma independente (uma fora do ar não impede
as outras, e a falha aparece em `motivos_descarte`):

- APAC `GET /alertas`: aceita só aviso cuja `regioes_afetadas` inclui a mesorregião "Metropolitana de Recife";
- INMET `GET /avisos/ativos` ({hoje, futuro}): geocode IBGE 2611606 ou polígono que intercepta o Recife;
- Cemaden `wsAlertas2`: `codibge` = 2611606 (alerta municipal, sem validade: vale enquanto estiver no feed);
- IDAP (Defesa Civil Nacional, CAP 1.2 em Atom): geocode IBGE 2611606 ou polígono que intercepta o Recife.

Aviso já vencido na hora da coleta é descartado ("vencido"). A bronze guarda só o que toca Pernambuco
(pré-filtro barato: geocode 26xxxxx, UF PE ou área "/PE") e um resumo de cada consulta (itens e sha256): o feed
nacional inteiro (~15 MB a cada 15 min) estouraria o Atlas gratuito sem acrescentar nada ao Recife.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import xml.etree.ElementTree as ET

import pandas as pd
from shapely.geometry import Polygon, shape
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URLS = {
    "apac": "https://api.apac.pe.gov.br/api.php/alertas",
    "inmet": "https://apiprevmet3.inmet.gov.br/avisos/ativos",
    "cemaden": "https://painelalertas.cemaden.gov.br/wsAlertas2",
    "idap": "https://idapfile.mdr.gov.br/idap/api/rss/cap",
}
PAGINAS = {
    "apac": "https://www.apac.pe.gov.br/",
    "inmet": "https://portal.inmet.gov.br/",
    "cemaden": "https://painelalertas.cemaden.gov.br/",
    "idap": "https://idap.mdr.gov.br/",
}
REGIAO_APAC = "metropolitana de recife"
NIVEIS = {
    "amarelo": "amarelo",
    "laranja": "laranja",
    "vermelho": "vermelho",
    "perigo potencial": "amarelo",
    "perigo": "laranja",
    "grande perigo": "vermelho",
    "moderado": "amarelo",
    "alto": "laranja",
    "muito alto": "vermelho",
    "minor": "amarelo",
    "moderate": "amarelo",
    "severe": "laranja",
    "extreme": "vermelho",
}
CAP = {"atom": "http://www.w3.org/2005/Atom", "cap": "urn:oasis:names:tc:emergency:cap:1.2"}
CEMADEN_SEM_VALIDADE_H = 2  # alerta do Cemaden sem fim declarado: vigente enquanto aparecer no feed


def xml_seguro(conteudo: bytes | str):
    """CAP/Atom sem DTD: recusar DOCTYPE/ENTITY impede expansão de entidades ("billion laughs") e entidades
    externas; o ElementTree da biblioteca padrão já não busca recursos externos."""
    amostra = conteudo if isinstance(conteudo, str) else conteudo.decode("utf-8", "ignore")
    if "<!DOCTYPE" in amostra or "<!ENTITY" in amostra:
        raise ValueError("XML com DTD recusado")
    return ET.fromstring(conteudo)  # noqa: S314 — DTD recusado acima


def nivel(texto) -> str | None:
    return NIVEIS.get(" ".join(str(texto or "").lower().replace("-", " ").split()))


def _cortar(v, n):
    return None if v is None else str(v).strip()[:n] or None


class ConectorAlertasOficiais(Conector):
    id = "alertas-oficiais"
    fonte = FonteInfo(
        "Avisos oficiais que atingem o Recife (APAC, INMET, Cemaden, IDAP)",
        "APAC / INMET / Cemaden / Defesa Civil Nacional",
        URLS["idap"],
        "observada",
    )

    def __init__(self, http=None, contorno=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self._contorno = contorno
        self.descartes: dict[str, int] = {}

    @property
    def contorno(self):
        return self._contorno if self._contorno is not None else comum.contorno_recife()

    def _conta(self, motivo: str, n: int = 1) -> None:
        self.descartes[motivo] = self.descartes.get(motivo, 0) + n

    # ------------------------------------------------------------------ extract
    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        self.descartes, registros, falhas = {}, [], []
        for origem in URLS:
            try:
                r = self.http.get(URLS[origem], timeout=180)
                r.raise_for_status()
                itens = getattr(self, f"_pe_{origem}")(r.content)
            except Exception as e:  # noqa: BLE001 — uma origem fora do ar não derruba as outras
                falhas.append(origem)
                self._conta(f"origem_indisponivel:{origem}")
                registros.append({"origem": origem, "tipo": "consulta", "erro": type(e).__name__})
                continue
            registros.append(
                {
                    "origem": origem,
                    "tipo": "consulta",
                    "url": URLS[origem],
                    "bytes": len(r.content),
                    "sha256": hashlib.sha256(r.content).hexdigest(),
                    "itens_pe": len(itens),
                }
            )
            registros.extend({"origem": origem, "tipo": "aviso", "aviso": i} for i in itens)
        if len(falhas) == len(URLS):
            raise FonteSemDados("Nenhuma das origens de alertas respondeu (APAC, INMET, Cemaden, IDAP).")
        return registros

    @staticmethod
    def _pe_apac(conteudo: bytes) -> list[dict]:
        corpo = json.loads(conteudo)
        if not isinstance(corpo, list):
            raise FonteSemDados(f"APAC: {str(corpo)[:200]}")
        return [{k: v for k, v in a.items() if k not in ("corpo_html", "imagem_base64")} for a in corpo]

    @staticmethod
    def _pe_inmet(conteudo: bytes) -> list[dict]:
        corpo = json.loads(conteudo)
        saida = []
        for grupo in ("hoje", "futuro"):
            for a in corpo.get(grupo) or []:
                geocodes = str(a.get("geocodes") or "")
                if re.search(r"(^|,)\s*26\d{5}", geocodes) or "Pernambuco" in str(a.get("estados") or ""):
                    saida.append({**{k: v for k, v in a.items() if k != "icone"}, "_grupo": grupo})
        return saida

    @staticmethod
    def _pe_cemaden(conteudo: bytes) -> list[dict]:
        corpo = json.loads(conteudo)
        return [a for a in corpo.get("alertas") or [] if str(a.get("uf", "")).upper() == "PE"]

    @staticmethod
    def _pe_idap(conteudo: bytes) -> list[dict]:
        raiz = xml_seguro(conteudo)
        saida = []
        for entrada in raiz.findall("atom:entry", CAP):
            bruto = ET.tostring(entrada, encoding="unicode")
            if re.search(r"<(?:\w+:)?value>26\d{5}</", bruto) or "/PE<" in bruto:
                saida.append({"xml": bruto})
        return saida

    # ------------------------------------------------------------------ transform
    def _intercepta(self, geometria) -> bool:
        try:
            g = geometria if geometria.is_valid else geometria.buffer(0)
            return g.intersects(self.contorno)
        except Exception:  # noqa: BLE001 — polígono malformado não vale como localização
            return False

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        linhas = []
        for r in bruto.to_dict("records"):
            if r.get("tipo") != "aviso":
                continue
            try:
                a = getattr(self, f"_t_{r['origem']}")(r["aviso"])
            except Exception:  # noqa: BLE001
                self._conta(f"aviso_malformado:{r['origem']}")
                continue
            if a is None:
                self._conta(f"fora_do_recife:{r['origem']}")
                continue
            if a["expira_em"] is not None and a["expira_em"] <= ctx.agora:
                self._conta(f"vencido:{r['origem']}")
                continue
            linhas.append({**a, "origem": r["origem"]})
        df = pd.DataFrame(linhas)
        return df.drop_duplicates(["origem", "codigo_fonte"], keep="last") if not df.empty else df

    def _t_apac(self, a: dict) -> dict | None:
        regioes = a.get("regioes_afetadas") or []
        if isinstance(regioes, str):  # às vezes chega como repr de lista Python
            try:
                regioes = ast.literal_eval(regioes)
            except (ValueError, SyntaxError):
                regioes = [{"nome": regioes}]
        nomes = [str(x.get("nome", "") if isinstance(x, dict) else x).lower() for x in regioes]
        if not any(REGIAO_APAC in n for n in nomes):
            return None
        return {
            "codigo_fonte": str(a.get("numero_aviso_meteorologico") or a["id"]),
            "evento": f"{str(a.get('tipo') or 'Aviso').capitalize()} — APAC",
            "nivel": nivel(a.get("nivel_aviso")),
            "nivel_original": _cortar(a.get("nivel_aviso"), 60),
            "emitido_em": comum.hora_local(a.get("data_envio")),
            "inicio_em": comum.hora_local(a.get("data_envio")),
            "expira_em": comum.hora_local(a.get("data_validade_aviso")),
            "url": a.get("url_aviso") or PAGINAS["apac"],
            "descricao": _cortar(a.get("texto_aviso"), 2000),
            "area": "Mesorregião Metropolitana de Recife",
            "criterio_geo": "regiao",
        }

    def _t_inmet(self, a: dict) -> dict | None:
        geocodes = {g.strip() for g in str(a.get("geocodes") or "").split(",")}
        criterio = "geocode" if comum.GEOCODE_RECIFE in geocodes else None
        if criterio is None and a.get("poligono"):
            poligono = a["poligono"]
            poligono = json.loads(poligono) if isinstance(poligono, str) else poligono
            criterio = "poligono" if self._intercepta(shape(poligono)) else None
        if criterio is None:
            return None
        return {
            "codigo_fonte": str(a.get("codigo") or a.get("id")),
            "evento": f"{a.get('descricao') or 'Aviso'} — INMET",
            "nivel": nivel(a.get("severidade")),
            "nivel_original": _cortar(a.get("severidade"), 60),
            "emitido_em": comum.hora_local(a.get("created_at")),
            "inicio_em": comum.hora_local(a.get("inicio")),
            "expira_em": comum.hora_local(a.get("fim")),
            "url": PAGINAS["inmet"],
            "descricao": _cortar(" ".join(str(a.get(k) or "") for k in ("riscos", "instrucoes")), 2000),
            "area": _cortar(a.get("estados"), 300),
            "criterio_geo": criterio,
        }

    def _t_cemaden(self, a: dict) -> dict | None:
        if str(a.get("codibge")) != comum.GEOCODE_RECIFE or str(a.get("status", "1")) != "1":
            return None
        return {
            "codigo_fonte": str(a["cod_alerta"]),
            "evento": f"{a.get('evento') or 'Alerta'} — Cemaden",
            "nivel": nivel(a.get("nivel")),
            "nivel_original": _cortar(a.get("nivel"), 60),
            "emitido_em": comum.hora_local(a.get("datahoracriacao")),
            "inicio_em": comum.hora_local(a.get("datahoracriacao")),
            "expira_em": None,
            "url": PAGINAS["cemaden"],
            "descricao": None,
            "area": f"{a.get('municipio')}/{a.get('uf')}",
            "criterio_geo": "geocode",
        }

    def _t_idap(self, a: dict) -> dict | None:
        entrada = xml_seguro(a["xml"])
        alerta = entrada.find(".//cap:alert", CAP)
        info = alerta.find("cap:info", CAP)
        geocodes = {v.text for v in info.findall("cap:area/cap:geocode/cap:value", CAP)}
        criterio = "geocode" if comum.GEOCODE_RECIFE in geocodes else None
        if criterio is None:
            for p in info.findall("cap:area/cap:polygon", CAP):
                pares = [tuple(map(float, x.split(","))) for x in (p.text or "").split()]
                if len(pares) >= 3 and self._intercepta(Polygon([(lon, lat) for lat, lon in pares])):
                    criterio = "poligono"
                    break
        if criterio is None:
            return None

        def campo(no, nome):
            el = no.find(f"cap:{nome}", CAP)
            return el.text if el is not None else None

        return {
            "codigo_fonte": campo(alerta, "identifier"),
            "evento": f"{campo(info, 'event') or 'Alerta'} — Defesa Civil (IDAP)",
            "nivel": nivel(campo(info, "severity")),
            "nivel_original": _cortar(campo(info, "severity"), 60),
            "emitido_em": comum.hora_local(campo(alerta, "sent")),
            "inicio_em": comum.hora_local(campo(info, "onset")),
            "expira_em": comum.hora_local(campo(info, "expires")),
            "url": campo(info, "web") or PAGINAS["idap"],
            "descricao": _cortar(campo(info, "headline") or campo(info, "description"), 2000),
            "area": _cortar(", ".join(e.text or "" for e in info.findall("cap:area/cap:areaDesc", CAP)), 300),
            "criterio_geo": criterio,
        }

    # ------------------------------------------------------------------ load
    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        colunas = (
            "origem", "codigo_fonte", "evento", "nivel", "nivel_original", "emitido_em", "inicio_em", "expira_em",
            "url", "descricao", "area", "criterio_geo",
        )  # fmt: skip
        registros = [
            {
                **{c: (None if pd.isna(r.get(c)) else r.get(c)) for c in colunas},
                "agora": ctx.agora,
                "ex": ctx.execucao_id,
            }
            for r in df.to_dict("records")
        ]
        for reg in registros:
            for c in ("emitido_em", "inicio_em", "expira_em"):
                if reg[c] is not None and hasattr(reg[c], "to_pydatetime"):
                    reg[c] = reg[c].to_pydatetime()
        with ctx.engine.begin() as c:
            c.execute(
                text(
                    "insert into silver.alertas_oficiais (origem, codigo_fonte, evento, nivel, nivel_original, "
                    "emitido_em, inicio_em, expira_em, url, descricao, area, criterio_geo, primeira_vez_em, visto_em, "
                    "execucao_id) values (:origem, :codigo_fonte, :evento, :nivel, :nivel_original, :emitido_em, "
                    ":inicio_em, :expira_em, :url, :descricao, :area, :criterio_geo, :agora, :agora, :ex) "
                    "on conflict (origem, codigo_fonte) do update set evento = excluded.evento, nivel = excluded.nivel, "
                    "nivel_original = excluded.nivel_original, inicio_em = excluded.inicio_em, "
                    "expira_em = excluded.expira_em, url = excluded.url, descricao = excluded.descricao, "
                    "area = excluded.area, criterio_geo = excluded.criterio_geo, visto_em = excluded.visto_em, "
                    "execucao_id = excluded.execucao_id"
                ),
                registros,
            )
        return len(registros)


def vigentes_sql() -> str:
    """Avisos em vigor em :agora (expira no futuro; sem validade, visto na última coleta recente)."""
    return (
        "select origem, evento, coalesce(nivel, 'indefinido') as nivel, nivel_original, "
        "coalesce(emitido_em, primeira_vez_em) as emitido_em, inicio_em, expira_em, url, area, criterio_geo, "
        "visto_em from silver.alertas_oficiais where (expira_em > :agora) or (expira_em is null and visto_em >= "
        ":agora - make_interval(hours => :sem_validade_h)) order by "
        "case nivel when 'vermelho' then 3 when 'laranja' then 2 when 'amarelo' then 1 else 0 end desc, emitido_em desc"
    )
