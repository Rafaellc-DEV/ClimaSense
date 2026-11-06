"""Equipamentos de saúde do Recife (CNES, Ministério da Saúde) → `silver.equipamentos_saude` (RF-04, RF-02).

API de dados abertos do Ministério da Saúde, `GET /cnes/estabelecimentos?codigo_municipio=261160`, paginada de 20 em
20 (o servidor ignora `limit` maior). A resposta traz TODOS os estabelecimentos do município (cerca de 4.700, a maioria
consultórios e clínicas privadas, farmácias e unidades móveis), com telefone, e-mail, CNPJ e razão social.

Filtro (feito em `extrair`, ANTES da bronze; RN-13, RNF-03):
- descarta estabelecimento desabilitado, consultório isolado (tipo 22, em geral de pessoa física), farmácia, unidade
  móvel, academia da saúde e qualquer tipo fora da lista `TIPOS`;
- fica o que é PÚBLICO (natureza jurídica 1xxx, empresa pública 2011 ou economia mista 2038) e, nos tipos hospitalares
  e de urgência, também o que atende o SUS (hospital filantrópico ou privado conveniado). Clínicas (36) e laboratórios
  (39) só entram se forem municipais ou estaduais (clínicas-escola federais e fundações ficam de fora);
- guarda só: código CNES, nome fantasia, tipo, natureza jurídica, atende SUS, bairro escrito, coordenada, data de
  atualização. Razão social, CNPJ, telefone, e-mail, endereço e número NÃO vão para a bronze.

Atenção: `descricao_esfera_administrativa` da API é a esfera de GESTÃO (clínicas privadas aparecem como "MUNICIPAL"),
por isso a esfera gravada vem da natureza jurídica.

Bairro: ponto-em-polígono na malha oficial de bairros; sem coordenada (ou fora do Recife), pelo nome do bairro do CNES
(normalizado); senão nulo. A rede municipal do CKAN (`rede-de-saude-municipal`) não traz código CNES (só nome, tipo e
polígono), então não serve de chave para completar coordenada.

`--limite N` lê só N páginas: a execução é uma AMOSTRA (RN-10), rotulada na bronze, e nesse caso a silver só recebe
upsert (nada é removido).
"""

from __future__ import annotations

import time

import pandas as pd
import requests
from sqlalchemy import text

from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados

URL = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
URL_FONTE = "https://apidadosabertos.saude.gov.br/v1/"
MUNICIPIO = "261160"
POR_PAGINA = 20
TENTATIVAS = 3

# Código CNES de tipo de unidade → rótulo. Os hospitalares e de urgência aceitam também o que atende o SUS.
TIPOS: dict[int, str] = {
    1: "Posto de saúde",
    2: "Centro de saúde / UBS / USF",
    4: "Policlínica",
    5: "Hospital geral",
    7: "Hospital especializado (inclui maternidades)",
    15: "Unidade mista",
    20: "Pronto-socorro geral",
    21: "Pronto-socorro especializado",
    36: "Clínica / centro de especialidades",
    39: "Laboratório / apoio diagnóstico",
    62: "Hospital-dia",
    69: "Hemocentro",
    70: "CAPS",
    71: "Centro de apoio à saúde da família",
    73: "UPA / pronto atendimento",
    76: "Central de regulação das urgências (SAMU)",
    80: "Laboratório central de saúde pública",
    85: "Centro de imunização",
}
TIPOS_HOSPITALARES = {5, 7, 15, 20, 21, 62, 73}
TIPOS_SO_MUNICIPAL_ESTADUAL = {36, 39}
CONSULTORIO_ISOLADO = 22
ESFERA_DA_NATUREZA = {
    "1015": "federal",
    "1058": "federal",
    "1104": "federal",
    "1139": "federal",
    "1023": "estadual",
    "1112": "estadual",
    "1147": "estadual",
    "1244": "municipal",
    "1120": "municipal",
    "1155": "municipal",
    "1031": "municipal",
}


def eh_publico(natureza: str) -> bool:
    return natureza[:1] == "1" or natureza in ("2011", "2038")


def esfera_de(natureza: str, publico: bool) -> str:
    if not publico:
        return "privada-sus"
    return ESFERA_DA_NATUREZA.get(natureza, "publica")


def classificar(r: dict) -> tuple[str, str] | str:
    """(tipo, esfera) se o estabelecimento fica; senão o motivo do descarte."""
    try:
        tipo = int(r.get("codigo_tipo_unidade"))
    except (TypeError, ValueError):
        return "tipo_invalido"
    if r.get("codigo_motivo_desabilitacao_estabelecimento"):
        return "desabilitado"
    if tipo == CONSULTORIO_ISOLADO:
        return "consultorio_isolado"
    if tipo not in TIPOS:
        return "tipo_fora_do_escopo"
    natureza = str(r.get("descricao_natureza_juridica_estabelecimento") or "").strip()
    publico = eh_publico(natureza)
    sus = str(r.get("estabelecimento_faz_atendimento_ambulatorial_sus") or "").upper() == "SIM"
    if tipo in TIPOS_SO_MUNICIPAL_ESTADUAL:
        if natureza not in ("1244", "1023"):
            return "nao_publico_municipal_ou_estadual"
    elif not publico and not (tipo in TIPOS_HOSPITALARES and sus):
        return "nao_publico_nem_sus"
    return TIPOS[tipo], esfera_de(natureza, publico)


def so_o_necessario(r: dict) -> dict:
    """Lista fechada de campos: nome, telefone, e-mail, CNPJ, razão social e endereço ficam de fora."""
    return {
        "registro": "estabelecimento",
        "codigo_cnes": str(r.get("codigo_cnes")),
        "nome_fantasia": " ".join(str(r.get("nome_fantasia") or "").split())[:160] or None,
        "codigo_tipo_unidade": int(r["codigo_tipo_unidade"]),
        "natureza_juridica": str(r.get("descricao_natureza_juridica_estabelecimento") or ""),
        "atende_sus": str(r.get("estabelecimento_faz_atendimento_ambulatorial_sus") or "").upper() == "SIM",
        "bairro_cnes": " ".join(str(r.get("bairro_estabelecimento") or "").split()) or None,
        "latitude": comum.real(r.get("latitude_estabelecimento_decimo_grau")),
        "longitude": comum.real(r.get("longitude_estabelecimento_decimo_grau")),
        "data_atualizacao": r.get("data_atualizacao"),
    }


class ConectorCnesEquipamentos(Conector):
    id = "cnes-equipamentos"
    fonte = FonteInfo(
        "Equipamentos de saúde do Recife (CNES)",
        "Ministério da Saúde (CNES, dados abertos)",
        URL_FONTE,
        "observada",
        "Dados abertos do Governo Federal (acesso público)",
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}
        self.amostra = False
        self.estatisticas: dict[str, int] = {}

    def _pagina(self, deslocamento: int) -> list[dict]:
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                r = self.http.get(
                    URL,
                    params={"codigo_municipio": MUNICIPIO, "limit": POR_PAGINA, "offset": deslocamento},
                    timeout=60,
                )
                r.raise_for_status()
                corpo = r.json()
                break
            except (requests.RequestException, ValueError):
                if tentativa == TENTATIVAS:
                    raise
                time.sleep(2 * tentativa)
        if not isinstance(corpo, dict) or "estabelecimentos" not in corpo:
            raise FonteSemDados("A API do CNES respondeu sem a lista de estabelecimentos.")
        return corpo["estabelecimentos"]

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        self.descartes = {}
        self.amostra = bool(ctx.limite)
        mantidos, lidos, paginas, deslocamento = [], 0, 0, 0
        while True:
            pagina = self._pagina(deslocamento)
            paginas += 1
            for r in pagina:
                lidos += 1
                veredito = classificar(r)
                if isinstance(veredito, str):
                    self.descartes[veredito] = self.descartes.get(veredito, 0) + 1
                else:
                    mantidos.append(so_o_necessario(r))
            deslocamento += POR_PAGINA
            if len(pagina) < POR_PAGINA or (ctx.limite and paginas >= ctx.limite):
                break
        if lidos == 0:
            raise FonteSemDados("A API do CNES não devolveu nenhum estabelecimento para o Recife.")
        resumo = {
            "registro": "consulta",
            "url": URL,
            "codigo_municipio": MUNICIPIO,
            "paginas": paginas,
            "estabelecimentos_lidos": lidos,
            "estabelecimentos_mantidos": len(mantidos),
            "descartados_por_motivo": dict(self.descartes),
            "amostra": self.amostra,
        }
        if self.amostra:
            for m in mantidos:
                m["amostra"] = True
        return [resumo, *mantidos]

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        from climasense.ml.alagamento.ocorrencias import mapa_bairros, resolver_bairro

        mapa = mapa_bairros()
        loc = comum.localizador()
        itens = []
        est = {"bairro_por_ponto": 0, "bairro_por_nome": 0, "sem_bairro": 0, "sem_coordenada": 0}
        for r in bruto[bruto["registro"] == "estabelecimento"].to_dict("records"):
            tipo, esfera = classificar_de_bronze(r)
            lat, lon = comum.real(r.get("latitude")), comum.real(r.get("longitude"))
            bairro = distrito = None
            if lat is not None and lon is not None:
                bairro, distrito = loc.localizar(lon, lat)
                if bairro is None and distrito is None:  # fora do Recife: coordenada duvidosa, não usar
                    lat = lon = None
            if bairro is not None:
                est["bairro_por_ponto"] += 1
            else:
                alvo = resolver_bairro(str(r.get("bairro_cnes") or ""), mapa)
                if alvo:
                    bairro, distrito = alvo
                    est["bairro_por_nome"] += 1
                else:
                    est["sem_bairro"] += 1
            if lat is None:
                est["sem_coordenada"] += 1
            itens.append(
                {
                    "cnes": str(r["codigo_cnes"]),
                    "nome": r.get("nome_fantasia") or f"CNES {r['codigo_cnes']}",
                    "tipo": tipo,
                    "esfera": esfera,
                    "bairro_id": bairro,
                    "distrito_id": distrito,
                    "latitude": lat,
                    "longitude": lon,
                }
            )
        self.estatisticas = est
        return pd.DataFrame(itens)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        linhas = [
            {**{k: comum.valor_sql(v) for k, v in r.items()}, "f": self.id, "ex": ctx.execucao_id}
            for r in df.to_dict("records")
        ]
        with ctx.engine.begin() as c:
            c.execute(
                text(
                    "insert into silver.equipamentos_saude (cnes, nome, tipo, esfera, bairro_id, distrito_id, "
                    "latitude, longitude, fonte_id, execucao_id) values (:cnes, :nome, :tipo, :esfera, :bairro_id, "
                    ":distrito_id, :latitude, :longitude, :f, :ex) on conflict (cnes) do update set "
                    "nome = excluded.nome, tipo = excluded.tipo, esfera = excluded.esfera, "
                    "bairro_id = excluded.bairro_id, distrito_id = excluded.distrito_id, "
                    "latitude = excluded.latitude, longitude = excluded.longitude, "
                    "fonte_id = excluded.fonte_id, execucao_id = excluded.execucao_id"
                ),
                linhas,
            )
            if not self.amostra:  # cadastro completo: quem saiu do CNES (ou foi desabilitado) sai da silver
                c.execute(
                    text("delete from silver.equipamentos_saude where cnes <> all(:codigos)"),
                    {"codigos": [r["cnes"] for r in linhas]},
                )
        print(f"[cnes] {len(linhas)} equipamentos; {self.estatisticas}; amostra={self.amostra}")
        return len(linhas)


def classificar_de_bronze(r: dict) -> tuple[str, str]:
    """Rótulo e esfera a partir do que ficou na bronze (mesma regra do filtro de extração)."""
    tipo = TIPOS[int(r["codigo_tipo_unidade"])]
    natureza = str(r.get("natureza_juridica") or "")
    return tipo, esfera_de(natureza, eh_publico(natureza))
