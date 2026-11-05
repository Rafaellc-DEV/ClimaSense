"""Abrigos e pontos de apoio do Recife → `app.abrigos` (F3), sem nunca apagar o que a equipe registrou.

Modo `cadastro` (padrão), lista de locais que PODEM ser ativados:
- CKAN `abrigos-temporarios-disponiveis` (Ação Inverno 2022, 17 locais, ODbL);
- `data/abrigos/abrigos-curados.csv`, lista curada pela equipe do projeto (camada ABRIGOS_2023 da Prefeitura,
  Censo SUAS 2024, Plano de Contingência 2026); vai para a bronze com o sha256 do arquivo. Linha a menos de
  `RAIO_MESMO_LOCAL_M` de um local do CKAN (ou com o mesmo nome) é o mesmo local: completa, não duplica.
Upsert por (origem='dados-abertos', codigo_fonte). Nome, endereço, bairro e coordenada só são atualizados
enquanto a equipe nunca editou o abrigo; `aberto`, capacidade da equipe, ocupação e observação nunca são tocados.

Modo `ativos` (a cada 15 min): feed público "Abrigos Ativos" do COP Recife (ArcGIS). Estar no feed = aberto
agora (salvo `status` explícito de inativo). Casa com o cadastrado por nome ou coordenada (ou cria) e grava
`aberto=true`, `status_origem='cop'`, `status_lido_em`. Quem some do feed volta a `aberto=false` SÓ se o último
status veio do COP. Um registro da equipe mais recente que a leitura do COP sempre prevalece.

LGPD: o feed e a camada trazem nome e telefone de coordenadores (e usuários do ArcGIS). Esses campos nem são
pedidos à fonte e, por garantia, são removidos antes da bronze.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from climasense.config import RAIZ_REPOSITORIO
from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

CKAN = "https://dados.recife.pe.gov.br/api/3/action"
RESOURCE_ID = "35566d21-a428-4595-89dc-eb405380b33e"
URL_DATASET = "https://dados.recife.pe.gov.br/dataset/abrigos-temporarios-disponiveis"
ARQUIVO_CURADO = RAIZ_REPOSITORIO / "data" / "abrigos" / "abrigos-curados.csv"
URL_COP = "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/COP/Abrigos_Ativos/FeatureServer/0"
CAMPOS_COP = (
    "objectid,globalid,no_entidade,tipo,tipo_de_uso,endereco,latitude,longitude,status,estagio_operacional,"
    "qt_salas_utilizadas,qtd_pessoas_estimadas_sala,qtd_vagas_estimadas_quadra,last_edited_date"
)
PESSOAIS = re.compile(
    r"coordenador|contato|telefone|fone|celular|email|e_mail|responsavel|_user$", re.IGNORECASE
)
RAIO_MESMO_LOCAL_M = 120
STATUS_INATIVO = re.compile(r"inativ|fechad|desativ|encerrad", re.IGNORECASE)


def sem_dados_pessoais(registro: dict) -> dict:
    return {k: v for k, v in registro.items() if not PESSOAIS.search(str(k))}


def distancia_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """(lat, lon) → metros (equirretangular; suficiente para < 1 km)."""
    x = math.radians(b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2))
    y = math.radians(b[0] - a[0])
    return 6_371_000 * math.hypot(x, y)


def _slug(nome: str) -> str:
    from climasense.territorio.carga import slug

    return slug(re.sub(r"\((abrigo|ponto de apoio)\)", "", nome or "", flags=re.IGNORECASE))


GENERICAS = {
    "escola", "municipal", "estadual", "creche", "igreja", "abrigo", "ponto", "apoio", "professor", "professora",
    "centro", "associacao", "paroquia", "batista", "cras", "unidade", "dos", "das", "de", "do", "da", "e",
}  # fmt: skip


def _tokens(nome: str) -> set[str]:
    return {t for t in _slug(nome).split("-") if len(t) > 2 and t not in GENERICAS}


def capacidade_do_texto(texto: str | None) -> int | None:
    """'capacidade estimada (pessoas): 100 em salas + 150 em quadra' → 250."""
    m = re.search(r"capacidade estimada \(pessoas\):\s*([^,;]+)", texto or "", re.IGNORECASE)
    if not m:
        return None
    numeros = [int(n) for n in re.findall(r"\d+", m.group(1))]
    return sum(numeros) or None


def _texto(v, n):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return " ".join(str(v).split())[:n] or None


def _endereco(v) -> str | None:
    """Endereço sem o ", Brazil" que o geocodificador da fonte acrescenta ao final."""
    t = _texto(v, 300)
    return re.sub(r"[,\s]+(brazil|brasil)\s*$", "", t, flags=re.IGNORECASE) or None if t else None


class ConectorRecifeAbrigos(Conector):
    id = "recife-abrigos"
    fonte = FonteInfo(
        "Abrigos e pontos de apoio (Ação Inverno)",
        "Prefeitura do Recife (Dados Abertos)",
        URL_DATASET,
        "observada",
        "ODbL",
    )

    def __init__(
        self, http=None, arquivo_curado: Path | None = ARQUIVO_CURADO, localizador=None, **kw
    ) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.arquivo_curado = arquivo_curado
        self._localizador = localizador
        self.descartes: dict[str, int] = {}

    @property
    def localizador(self):
        return self._localizador or comum.localizador()

    def colecao_bronze(self, ctx: ExecucaoCtx):
        return ctx.mongo[self.banco_bronze][
            "recife_abrigos_ativos" if ctx.modo == "ativos" else "recife_abrigos"
        ]

    def _conta(self, motivo):
        self.descartes[motivo] = self.descartes.get(motivo, 0) + 1

    # ------------------------------------------------------------------ extract
    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        self.descartes = {}
        if ctx.modo == "ativos":
            r = self.http.get(
                f"{URL_COP}/query",
                params={"where": "1=1", "outFields": CAMPOS_COP, "returnGeometry": "false", "f": "json"},
                timeout=60,
            )
            r.raise_for_status()
            corpo = r.json()
            if "error" in corpo:
                raise FonteSemDados(f"Feed de abrigos ativos do COP: {str(corpo['error'])[:200]}")
            feicoes = [sem_dados_pessoais(f.get("attributes") or {}) for f in corpo.get("features") or []]
            # o resumo da consulta vai junto: um feed vazio também é informação (ninguém aberto agora)
            return [{"registro": "consulta", "url": URL_COP, "itens": len(feicoes)}] + [
                {**f, "registro": "abrigo_ativo"} for f in feicoes
            ]
        if ctx.modo not in (None, "cadastro"):
            raise ValueError(f"Modo desconhecido: {ctx.modo}")
        registros = []
        meta = self.http.get(f"{CKAN}/resource_show", params={"id": RESOURCE_ID}, timeout=60)
        meta.raise_for_status()
        modificado = (meta.json().get("result") or {}).get("last_modified")
        dados = self.http.get(
            f"{CKAN}/datastore_search", params={"resource_id": RESOURCE_ID, "limit": 1000}, timeout=60
        )
        dados.raise_for_status()
        for rec in dados.json()["result"]["records"]:
            registros.append(
                {
                    **sem_dados_pessoais(rec),
                    "registro": "ckan",
                    "ckan_id": rec.get("_id"),
                    "fonte_data": modificado,
                }
            )
        if self.arquivo_curado and Path(self.arquivo_curado).exists():
            conteudo = Path(self.arquivo_curado).read_bytes()
            linhas = list(csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig")), delimiter=";"))
            registros.append(
                {
                    "registro": "arquivo_curado",
                    "arquivo": Path(self.arquivo_curado).name,
                    "sha256": hashlib.sha256(conteudo).hexdigest(),
                    "linhas": len(linhas),
                }
            )
            registros.extend(
                {**sem_dados_pessoais(r), "registro": "curado", "n_linha": i} for i, r in enumerate(linhas, 2)
            )
        return registros

    # ------------------------------------------------------------------ transform
    def _local(self, lat, lon, bairro_texto) -> tuple[str | None, float | None, float | None]:
        lat, lon = comum.real(lat), comum.real(lon)
        bairro = None
        if lat is not None and lon is not None:
            bairro, _ = self.localizador.localizar(lon, lat)
        if bairro is None and bairro_texto:
            from climasense.ml.alagamento.ocorrencias import mapa_bairros, resolver_bairro

            alvo = resolver_bairro(bairro_texto, mapa_bairros())
            bairro = alvo[0] if alvo else None
        if lat is None or lon is None:
            lat = lon = None
        return bairro, lat, lon

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        if ctx.modo == "ativos":
            return self._transformar_ativos(bruto, ctx)
        itens: list[dict] = []
        for r in bruto.to_dict("records"):
            if r.get("registro") not in ("ckan", "curado"):
                continue
            ckan = r["registro"] == "ckan"
            nome = _texto(r.get("equipamento_publico_disponivel") if ckan else r.get("nome"), 160)
            if not nome:
                self._conta("sem_nome")
                continue
            bairro, lat, lon = self._local(r.get("latitude"), r.get("longitude"), r.get("bairro"))
            if bairro is None:
                self._conta("fora_do_recife_ou_sem_bairro")
                continue
            fonte_data = r.get("fonte_data")
            try:
                fonte_data = date.fromisoformat(str(fonte_data)[:10]) if fonte_data else None
            except ValueError:
                fonte_data = None
            item = {
                "codigo_fonte": (("ckan:" if ckan else "curado:") + _slug(nome))[:80],
                "nome": nome,
                "endereco": _endereco(r.get("endereco")),
                "bairro_id": bairro,
                "latitude": lat,
                "longitude": lon,
                "tipo_local": _texto(r.get("tipo"), 40),
                "fonte_url": URL_DATASET if ckan else _texto(r.get("fonte_url"), 500),
                "fonte_data": fonte_data,
                "capacidade_fonte": None if ckan else capacidade_do_texto(r.get("observacao")),
                "observacao_fonte": _texto(
                    f"Dados Abertos (Ação Inverno 2022): {r.get('municipal_estadual')}"
                    if ckan
                    else r.get("observacao"),
                    1000,
                ),
            }
            # dentro da mesma fonte só o nome igual junta; entre fontes, nome ou nome parecido + coordenada
            igual = next(
                (
                    i
                    for i in itens
                    if (
                        i["codigo_fonte"].split(":")[0] != item["codigo_fonte"].split(":")[0]
                        and self._mesmo_local(i, item)
                    )
                    or _slug(i["nome"]) == _slug(item["nome"])
                ),
                None,
            )
            if igual is not None:  # o curado completa o do CKAN (capacidade, tipo), sem duplicar o local
                for campo in ("capacidade_fonte", "tipo_local", "endereco"):
                    igual[campo] = igual[campo] or item[campo]
                self._conta("mesmo_local_de_outra_fonte")
                continue
            itens.append(item)
        return pd.DataFrame(itens)

    @staticmethod
    def _mesmo_local(a: dict, b: dict) -> bool:
        """Mesmo nome (sem acento e sem "(ABRIGO)"), ou coordenadas a até RAIO_MESMO_LOCAL_M com nomes que
        compartilham a parte distintiva (ex.: "Adauto Pontes" × "Professor Adauto Pontes"). Escolas vizinhas
        com nomes diferentes continuam sendo locais diferentes."""
        if _slug(a["nome"]) == _slug(b["nome"]):
            return True
        if None in (a.get("latitude"), b.get("latitude")):
            return False
        perto = (
            distancia_m((a["latitude"], a["longitude"]), (b["latitude"], b["longitude"]))
            <= RAIO_MESMO_LOCAL_M
        )
        ta, tb = _tokens(a["nome"]), _tokens(b["nome"])
        return perto and bool(ta and tb) and len(ta & tb) / min(len(ta), len(tb)) >= 0.6

    def _transformar_ativos(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        itens = []
        for r in bruto.to_dict("records"):
            if r.get("registro") != "abrigo_ativo":
                continue
            nome = _texto(r.get("no_entidade"), 160)
            if not nome:
                self._conta("sem_nome")
                continue
            if STATUS_INATIVO.search(str(r.get("status") or "")):
                self._conta("status_inativo_no_feed")
                continue
            bairro, lat, lon = self._local(r.get("latitude"), r.get("longitude"), None)
            if bairro is None:
                self._conta("fora_do_recife_ou_sem_bairro")
                continue
            salas = (comum.numero(r.get("qt_salas_utilizadas")) or 0) * (
                comum.numero(r.get("qtd_pessoas_estimadas_sala")) or 0
            )
            capacidade = int(salas + (comum.numero(r.get("qtd_vagas_estimadas_quadra")) or 0)) or None
            editado = comum.real(r.get("last_edited_date"))
            itens.append(
                {
                    "codigo_fonte": f"cop:{r.get('globalid') or _slug(nome)}"[:80],
                    "nome": nome,
                    "endereco": _endereco(r.get("endereco")),
                    "bairro_id": bairro,
                    "latitude": lat,
                    "longitude": lon,
                    "tipo_local": _texto(r.get("tipo"), 40),
                    "capacidade_fonte": capacidade,
                    "lido_em": datetime.fromtimestamp(editado / 1000, UTC) if editado else ctx.agora,
                }
            )
        # feed vazio também é leitura (ninguém aberto agora): uma linha-marcador garante que a carga rode
        return pd.DataFrame(itens) if itens else pd.DataFrame([{"_vazio": True}])

    # ------------------------------------------------------------------ load
    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        if ctx.modo == "ativos":
            return self._gravar_ativos(df[df["_vazio"].isna()] if "_vazio" in df else df, ctx)
        registros = [
            {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.items()}
            for r in df.to_dict("records")
        ]
        with ctx.engine.begin() as c:
            for r in registros:
                c.execute(
                    text(
                        "insert into app.abrigos (nome, bairro_id, endereco, latitude, longitude, origem, codigo_fonte, "
                        "fonte_url, fonte_data, tipo_local, capacidade_fonte, observacao, aberto, criado_em, atualizado_em) "
                        "values (:nome, :bairro_id, :endereco, :latitude, :longitude, 'dados-abertos', :codigo_fonte, "
                        ":fonte_url, :fonte_data, :tipo_local, :capacidade_fonte, :observacao_fonte, false, :agora, :agora) "
                        "on conflict (origem, codigo_fonte) do update set fonte_url = excluded.fonte_url, "
                        "fonte_data = excluded.fonte_data, tipo_local = excluded.tipo_local, "
                        "capacidade_fonte = excluded.capacidade_fonte, "
                        # descritivos só enquanto a equipe nunca editou; status e ocupação nunca
                        "nome = case when app.abrigos.atualizado_por is null then excluded.nome else app.abrigos.nome end, "
                        "bairro_id = case when app.abrigos.atualizado_por is null then excluded.bairro_id "
                        "else app.abrigos.bairro_id end, "
                        "endereco = case when app.abrigos.atualizado_por is null then excluded.endereco "
                        "else app.abrigos.endereco end, "
                        "latitude = case when app.abrigos.atualizado_por is null then excluded.latitude "
                        "else app.abrigos.latitude end, "
                        "longitude = case when app.abrigos.atualizado_por is null then excluded.longitude "
                        "else app.abrigos.longitude end"
                    ),
                    {**r, "agora": ctx.agora},
                )
            # local que saiu do cadastro (ou passou a ser o mesmo de outra fonte): só sai se ninguém nunca mexeu
            removidos = c.execute(
                text(
                    "delete from app.abrigos a where a.origem = 'dados-abertos' "
                    "and split_part(a.codigo_fonte, ':', 1) in ('ckan', 'curado') and a.codigo_fonte <> all(:codigos) "
                    "and a.atualizado_por is null and a.status_origem is null "
                    "and not exists (select 1 from app.abrigo_atualizacoes h where h.abrigo_id = a.id)"
                ),
                {"codigos": [r["codigo_fonte"] for r in registros]},
            ).rowcount
            if removidos:
                self._conta("removido_do_cadastro_sem_uso")
                self.descartes["removido_do_cadastro_sem_uso"] = removidos
        return len(registros)

    def _gravar_ativos(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        mudou = 0
        with ctx.engine.begin() as c:
            cadastrados = [
                dict(r)
                for r in c.execute(
                    text(
                        "select a.id, a.nome, a.latitude, a.longitude, a.aberto, a.status_origem, a.status_lido_em, "
                        "(select max(h.em) from app.abrigo_atualizacoes h where h.abrigo_id = a.id "
                        " and h.autor_id is not null) as equipe_em from app.abrigos a"
                    )
                ).mappings()
            ]
            vistos = set()
            for r in df.to_dict("records"):
                alvo = next((a for a in cadastrados if self._mesmo_local(r, a)), None)
                if alvo is None:
                    alvo_id = c.execute(
                        text(
                            "insert into app.abrigos (nome, bairro_id, endereco, latitude, longitude, origem, "
                            "codigo_fonte, fonte_url, tipo_local, capacidade_fonte, aberto, criado_em, atualizado_em) "
                            "values (:nome, :bairro_id, :endereco, :latitude, :longitude, 'dados-abertos', :codigo_fonte, "
                            ":url, :tipo_local, :capacidade_fonte, false, :agora, :agora) "
                            "on conflict (origem, codigo_fonte) do update set nome = excluded.nome returning id"
                        ),
                        {**r, "url": URL_COP, "agora": ctx.agora},
                    ).scalar_one()
                    alvo = {"id": alvo_id, "aberto": False, "status_origem": None, "equipe_em": None}
                vistos.add(alvo["id"])
                if alvo["equipe_em"] is not None and alvo["equipe_em"] > r["lido_em"]:
                    self._conta("equipe_informou_depois_do_cop")
                    continue
                mudou += self._status(c, alvo, True, r["lido_em"], ctx, r.get("capacidade_fonte"))
            for a in cadastrados:  # sumiu do feed: fecha só o que o COP abriu e a equipe não mexeu depois
                if a["id"] in vistos or not a["aberto"] or a["status_origem"] != "cop":
                    continue
                if (
                    a["equipe_em"] is not None
                    and a["status_lido_em"]
                    and a["equipe_em"] > a["status_lido_em"]
                ):
                    continue
                mudou += self._status(c, a, False, ctx.agora, ctx, None)
        return mudou

    @staticmethod
    def _status(c, abrigo: dict, aberto: bool, lido_em: datetime, ctx: ExecucaoCtx, capacidade) -> int:
        c.execute(
            text(
                "update app.abrigos set aberto = :ab, status_origem = 'cop', status_lido_em = :lido, "
                "capacidade_fonte = coalesce(:cap, capacidade_fonte) where id = :id"
            ),
            {"ab": aberto, "lido": lido_em, "cap": capacidade, "id": abrigo["id"]},
        )
        if abrigo.get("aberto") == aberto and abrigo.get("status_origem") == "cop":
            return 0
        atual = (
            c.execute(
                text(
                    "select capacidade, pessoas_abrigadas, desabrigados, observacao from app.abrigos where id = :id"
                ),
                {"id": abrigo["id"]},
            )
            .mappings()
            .one()
        )
        c.execute(
            text(
                "insert into app.abrigo_atualizacoes (abrigo_id, em, autor_id, aberto, capacidade, pessoas_abrigadas, "
                "desabrigados, observacao, alteracoes) values (:a, :em, null, :ab, :c, :p, :d, :o, cast(:alt as jsonb))"
            ),
            {
                "a": abrigo["id"],
                "em": ctx.agora,
                "ab": aberto,
                "c": atual["capacidade"],
                "p": atual["pessoas_abrigadas"],
                "d": atual["desabrigados"],
                "o": atual["observacao"],
                "alt": json.dumps(
                    {"aberto": {"de": bool(abrigo.get("aberto")), "para": aberto}, "origem": "cop"}
                ),
            },
        )
        return 1
