"""Conectores de vulnerabilidade e equipamentos (Etapa 6), sem rede nem banco.

- CNES: 22 estabelecimentos REAIS da resposta de 06/11/2026 (nomes de consultórios, razão social, telefone, e-mail
  e endereço dos privados trocados por "APAGADO");
- IBGE: linhas reais do CSV de demografia por bairro (Censo 2022) de 5 bairros do Recife e 1 de Rondônia;
- áreas de risco: 11 setores reais da camada Setores_Risco_SEDEC (5 regionais), em GeoJSON.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from climasense.etl.conectores import CONECTORES, IMPLEMENTADOS, areas_risco, cnes, ibge_censo
from climasense.etl.conectores.base import FonteSemDados
from tests.unit.etl.test_conectores_chuva import Http, Resposta, bronze, ctx

FIX = Path(__file__).parent / "fixtures"


class BancoFalso:
    """Registra o que o conector mandaria ao Postgres (begin() → conexão com execute())."""

    def __init__(self) -> None:
        self.comandos: list[tuple[str, object]] = []

    def begin(self):
        banco = self

        class Conexao:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                banco.comandos.append((str(sql), params))

        return Conexao()


def ctx_banco(limite=None):
    c = ctx(limite=limite)
    c.engine = BancoFalso()
    return c


def test_conectores_novos_registrados_e_implementados():
    for fid in ("cnes-equipamentos", "ibge-censo-2022-bairro", "recife-areas-risco"):
        assert fid in CONECTORES and fid in IMPLEMENTADOS
        assert CONECTORES[fid].id == fid


# ----------------------------------------------------------------------------------------- CNES
def _cnes_http():
    todos = json.loads((FIX / "cnes_estabelecimentos_2026-11-06.json").read_text(encoding="utf-8"))

    def pagina(params):
        d = params["offset"]
        return Resposta({"estabelecimentos": todos[d : d + params["limit"]]})

    return todos, Http({"cnes/estabelecimentos": pagina})


def test_cnes_filtra_e_so_a_lista_fechada_de_campos_chega_a_bronze():
    todos, http = _cnes_http()
    c = cnes.ConectorCnesEquipamentos(http=http)
    registros = c.extrair(ctx())
    resumo, itens = registros[0], registros[1:]
    assert len(http.pedidos) == 2  # 20 + 2: a segunda página curta encerra
    assert resumo["estabelecimentos_lidos"] == len(todos) == 22
    assert resumo["amostra"] is False and resumo["estabelecimentos_mantidos"] == len(itens) == 12
    assert c.descartes == {
        "consultorio_isolado": 1,
        "desabilitado": 4,
        "nao_publico_municipal_ou_estadual": 2,
        "tipo_fora_do_escopo": 2,
        "nao_publico_nem_sus": 1,
    }
    nomes = {i["nome_fantasia"] for i in itens}
    assert "VANITA" not in nomes
    # nada de telefone, e-mail, CNPJ, razão social ou endereço, em nenhum documento
    assert all("APAGADO" not in json.dumps(i, ensure_ascii=False) for i in itens)
    assert set(itens[0]) == {
        "registro", "codigo_cnes", "nome_fantasia", "codigo_tipo_unidade", "natureza_juridica",
        "atende_sus", "bairro_cnes", "latitude", "longitude", "data_atualizacao",
    }  # fmt: skip
    assert {i["codigo_cnes"] for i in itens} >= {"1511", "6481876", "701", "752", "1120"}


def test_cnes_hospital_conveniado_ao_sus_fica_como_privada_sus_e_universidade_federal_sai():
    _, http = _cnes_http()
    c = cnes.ConectorCnesEquipamentos(http=http)
    df = c.transformar(bronze(c.extrair(ctx())), ctx()).set_index("cnes")
    assert df.loc["1120", "esfera"] == "privada-sus" and df.loc["1120", "tipo"] == "Hospital geral"
    assert df.loc["6481876", "esfera"] == "estadual"  # UPA do Estado
    assert df.loc["1511", "esfera"] == "municipal"
    assert "4737989" not in df.index  # clínica da UFPE (federal)
    assert "9632158" not in df.index  # consultório isolado de pessoa física


def test_cnes_bairro_por_ponto_em_poligono_depois_por_nome_e_senao_nulo():
    _, http = _cnes_http()
    c = cnes.ConectorCnesEquipamentos(http=http)
    br = bronze(c.extrair(ctx()))
    sem_coord = br["codigo_cnes"] == "833"  # sem coordenada: pelo nome do bairro do CNES
    br.loc[sem_coord, ["latitude", "longitude"]] = [None, None]
    sp = br["codigo_cnes"] == "752"  # coordenada em São Paulo e bairro que não existe
    br.loc[sp, ["latitude", "longitude"]] = [-23.55, -46.63]
    br.loc[sp, "bairro_cnes"] = "NAO EXISTE"
    df = c.transformar(br, ctx()).set_index("cnes")
    assert df.loc["1511", "bairro_id"] == "bairro-iputinga" and df.loc["1511", "distrito_id"].startswith(
        "ds-"
    )
    assert df.loc["833", "bairro_id"] == "bairro-boa-viagem" and pd.isna(df.loc["833", "latitude"])
    # coordenada fora do Recife é descartada e o bairro escrito não existe: nulo, sem inventar
    assert pd.isna(df.loc["752", "bairro_id"]) and pd.isna(df.loc["752", "latitude"])
    assert c.estatisticas["bairro_por_nome"] == 1 and c.estatisticas["sem_bairro"] == 1


def test_cnes_limite_vira_amostra_rotulada_e_a_silver_so_recebe_upsert():
    _, http = _cnes_http()
    c = cnes.ConectorCnesEquipamentos(http=http)
    registros = c.extrair(ctx(limite=1))
    assert len(http.pedidos) == 1 and registros[0]["amostra"] is True and registros[0]["paginas"] == 1
    assert all(r["amostra"] is True for r in registros[1:])
    cx = ctx_banco(limite=1)
    df = c.transformar(bronze(registros), cx)
    assert c.gravar_silver(df, cx) == len(df)
    assert [s for s, _ in cx.engine.comandos if "delete" in s.lower()] == []


def test_cnes_carga_completa_remove_quem_saiu_do_cadastro_e_grava_nas_colunas_do_esquema():
    _, http = _cnes_http()
    c = cnes.ConectorCnesEquipamentos(http=http)
    cx = ctx_banco()
    df = c.transformar(bronze(c.extrair(cx)), cx)
    c.gravar_silver(df, cx)
    insert, delete = cx.engine.comandos
    assert "silver.equipamentos_saude" in insert[0] and "on conflict (cnes)" in insert[0]
    linha = insert[1][0]
    assert linha["f"] == "cnes-equipamentos" and linha["ex"] == "exec-1" and isinstance(linha["cnes"], str)
    assert "delete from silver.equipamentos_saude" in delete[0]
    assert sorted(delete[1]["codigos"]) == sorted(df["cnes"])


def test_cnes_resposta_sem_lista_ou_vazia_vira_falha_explicada():
    with pytest.raises(FonteSemDados, match="sem a lista"):
        cnes.ConectorCnesEquipamentos(http=Http({"cnes": Resposta({"erro": "x"})})).extrair(ctx())
    with pytest.raises(FonteSemDados, match="nenhum estabelecimento"):
        cnes.ConectorCnesEquipamentos(http=Http({"cnes": Resposta({"estabelecimentos": []})})).extrair(ctx())


# ----------------------------------------------------------------------------------------- IBGE
def _csv_ibge() -> str:
    return (FIX / "ibge_demografia_bairros_amostra.csv").read_bytes().decode("latin-1")


def _zip_ibge(csv_texto: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Agregados_por_bairros_demografia_BR.csv", csv_texto.encode("latin-1"))
    return buf.getvalue()


def _ibge(csv_texto: str | None = None):
    http = Http({"Agregados_por_bairros_demografia": Resposta(conteudo=_zip_ibge(csv_texto or _csv_ibge()))})
    c = ibge_censo.ConectorIbgeCenso2022Bairro(http=http)
    return c, c.extrair(ctx())


def test_ibge_filtra_o_recife_soma_as_faixas_e_casa_o_bairro_com_apelido():
    c, registros = _ibge()
    assert registros[0]["linhas_brasil"] == 6 and registros[0]["linhas_recife"] == 5
    assert len(registros[0]["sha256"]) == 64
    df = c.transformar(bronze(registros), ctx())
    assert c.nao_casados == [] and df["bairro_id"].nunique() == 5
    assert "bairro-sitio-dos-pintos" in set(df["bairro_id"])  # "Sítio dos Pintos - São Brás"
    assert set(df["faixa"]) == {"0-4", "0-14", "60+", "70+", "total"}  # sem "80+": não existe por bairro
    assert (df["ano"] == 2022).all() and not df["suprimido"].any()
    recife = {r["faixa"]: r["pessoas"] for r in df[df["bairro_id"] == "bairro-recife"].to_dict("records")}
    # linha real do bairro Recife: V01006=537; 0-4=38; 5-9=61; 10-14=52; 60-69=41; 70+=16
    assert recife == {"total": 537, "0-4": 38, "0-14": 151, "60+": 57, "70+": 16}


def test_ibge_celula_suprimida_vira_nula_e_nunca_zero():
    c, registros = _ibge()
    br = bronze(registros)
    br.loc[br["nm_bairro"] == "Pina", "V01032"] = "X"  # 5 a 9 anos suprimido
    br.loc[br["nm_bairro"] == "Pina", "V01041"] = ""
    df = c.transformar(br, ctx())
    pina = df[df["bairro_id"] == "bairro-pina"].set_index("faixa")
    assert pd.isna(pina.loc["0-14", "pessoas"]) and bool(pina.loc["0-14", "suprimido"])
    assert pd.isna(pina.loc["60+", "pessoas"]) and bool(pina.loc["70+", "suprimido"])
    assert pina.loc["0-4", "pessoas"] > 0 and not pina.loc["0-4", "suprimido"]
    assert pina.loc["total", "pessoas"] > 0


def test_ibge_bairro_sem_par_oficial_e_contado_e_nao_atribuido_a_outro():
    c, registros = _ibge()
    br = bronze(registros)
    br.loc[br["nm_bairro"] == "Pina", "nm_bairro"] = "Bairro Inventado"
    df = c.transformar(br, ctx())
    assert c.nao_casados == ["Bairro Inventado"] and c.descartes == {"bairro_do_ibge_sem_par_oficial": 1}
    assert df["bairro_id"].nunique() == 4


def test_ibge_grava_nas_colunas_do_esquema_com_pessoas_inteiras_e_substitui_a_carga_anterior():
    c, registros = _ibge()
    cx = ctx_banco()
    df = c.transformar(bronze(registros), cx)
    assert c.gravar_silver(df, cx) == 25
    delete, insert = cx.engine.comandos
    assert "delete from silver.populacao_bairro" in delete[0]
    linha = insert[1][0]
    assert set(linha) == {"bairro_id", "ano", "faixa", "pessoas", "suprimido", "f", "ex"}
    assert isinstance(linha["pessoas"], int) and linha["f"] == "ibge-censo-2022-bairro"


def test_ibge_layout_diferente_ou_sem_recife_vira_falha_explicada():
    http = Http({"bairros_demografia": Resposta(conteudo=_zip_ibge('"CD_BAIRRO";"NM_BAIRRO"\n"1";"A"\n'))})
    with pytest.raises(FonteSemDados, match="faltam colunas"):
        ibge_censo.ConectorIbgeCenso2022Bairro(http=http).extrair(ctx())
    linhas = _csv_ibge().splitlines()
    so_fora = "\n".join([linhas[0], *[ln for ln in linhas if ln.startswith('"1100015')]])
    http = Http({"bairros_demografia": Resposta(conteudo=_zip_ibge(so_fora))})
    with pytest.raises(FonteSemDados, match="nenhum bairro do Recife"):
        ibge_censo.ConectorIbgeCenso2022Bairro(http=http).extrair(ctx())


# ----------------------------------------------------------------------------------------- áreas de risco
def _risco():
    corpo = json.loads((FIX / "areas_risco_sedec_2026-11-06.geojson").read_text(encoding="utf-8"))
    http = Http({"Setores_Risco_SEDEC": Resposta(corpo)})
    c = areas_risco.ConectorRecifeAreasRisco(http=http)
    return c, http, c.extrair(ctx())


def test_areas_risco_pede_wgs84_com_geometria_e_guarda_os_setores_na_bronze():
    _, http, registros = _risco()
    url, params = http.pedidos[0]
    assert url.endswith("Setores_Risco_SEDEC/FeatureServer/0/query")
    assert params["outSR"] == 4326 and params["returnGeometry"] == "true" and params["f"] == "geojson"
    assert registros[0]["setores"] == 11 and len(registros) == 12
    assert registros[1]["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_areas_risco_atribui_bairro_grau_regional_e_calcula_a_cobertura_parcial():
    c, _, registros = _risco()
    df = c.transformar(bronze(registros), ctx()).set_index("id")
    assert len(df) == 11 and df["tipo"].eq("setor-de-risco-sedec").all()
    assert set(df["grau"]) == {"R1", "R3", "R4"}
    assert df.loc["sedec-JDA-01", "grau"] == "R4" and df.loc["sedec-JDA-01", "regional"] == "Sul"
    assert df.loc["sedec-JDA-01", "bairro_id"] == "bairro-jordao"
    assert df.loc["sedec-3CA-09", "bairro_id"] in ("bairro-ibura", "bairro-cohab")  # "Ibura / Cohab"
    assert df["geometria"].map(lambda g: g["type"]).isin(["Polygon", "MultiPolygon"]).all()
    cob = c.cobertura
    assert cob["setores"] == 11 and cob["n_bairros_oficiais"] == 94
    assert set(cob["regionais"]) == {"Sul", "Norte", "Noroeste", "Nordeste", "Oeste"}
    assert cob["n_bairros_com_setor"] < 94 and cob["setores_sem_bairro"] == 0


def test_areas_risco_geometria_invalida_e_descartada_e_grava_geojson_como_jsonb():
    c, _, registros = _risco()
    br = bronze(registros)
    br.at[1, "geometry"] = {"type": "Point", "coordinates": [0, 0]}
    cx = ctx_banco()
    df = c.transformar(br, cx)
    assert c.descartes == {"geometria_invalida": 1} and len(df) == 10
    assert c.gravar_silver(df, cx) == 10
    delete, insert = cx.engine.comandos
    assert "delete from silver.areas_risco" in delete[0] and "cast(:g as jsonb)" in insert[0]
    g = json.loads(insert[1][0]["g"])
    assert g["type"] in ("Polygon", "MultiPolygon") and insert[1][0]["f"] == "recife-areas-risco"


def test_areas_risco_erro_do_servidor_ou_camada_vazia_vira_falha_explicada():
    http = Http({"Setores_Risco_SEDEC": Resposta({"error": {"code": 400, "message": "Invalid query"}})})
    with pytest.raises(FonteSemDados, match="Invalid query"):
        areas_risco.ConectorRecifeAreasRisco(http=http).extrair(ctx())
    http = Http({"Setores_Risco_SEDEC": Resposta({"type": "FeatureCollection", "features": []})})
    with pytest.raises(FonteSemDados, match="nenhum setor"):
        areas_risco.ConectorRecifeAreasRisco(http=http).extrair(ctx())
