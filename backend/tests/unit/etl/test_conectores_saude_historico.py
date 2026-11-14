"""SAMU Recife, SISAGUA e Atlas Digital de Desastres com respostas REAIS gravadas em 06/11/2026, sem rede nem banco.

Fixtures (fixtures/):
- `samu_2026_amostra.csv` e `samu_2025_amostra.csv`: linhas reais do CSV do SAMU; endereço, origem do chamado, sexo,
  idade, motivos e hora vieram trocados por "APAGADO" (ou 00:00:00) antes de entrar no repositório;
- `samu_ckan_pacote_2026.json`: resposta real do CKAN (`package_show`) do conjunto de 2026;
- `sisagua_recife_2026_amostra.json`: linhas reais da API (49), com número da amostra, descrição do local e local
  trocados por "APAGADO" e sem coordenadas;
- `atlas_recife_amostra.csv`: o cabeçalho real, os 16 registros reais do Recife e 6 de outros municípios (latin-1);
- `atlas_downloads_2026-11-06.html`: a página real de downloads.

Os testes de "campo individual" montam também linhas sintéticas com valores-sentinela (marcadas como tal) para provar
que nada disso chega à bronze, independentemente do conteúdo da fixture.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from climasense.etl import frescor, gold
from climasense.etl.conectores import CONECTORES, IMPLEMENTADOS, atlas, samu, sisagua
from climasense.etl.conectores.base import Conector, FonteSemDados
from tests.unit.etl.test_conectores_chuva import bronze, ctx

FIX = Path(__file__).parent / "fixtures"


class R:
    """Resposta HTTP mínima (JSON, bytes, texto e fluxo em blocos)."""

    def __init__(
        self, corpo=None, conteudo: bytes | None = None, texto: str | None = None, status: int = 200
    ):
        self.corpo, self.status_code = corpo, status
        self.content = conteudo if conteudo is not None else json.dumps(corpo).encode()
        self.text = texto if texto is not None else self.content.decode("utf-8", "replace")

    def json(self):
        return self.corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, tamanho):
        for i in range(0, len(self.content), 7919):  # blocos de tamanho primo: corta linhas e letras no meio
            yield self.content[i : i + 7919]


class Http:
    def __init__(self, rotas):
        self.rotas, self.pedidos = rotas, []

    def get(self, url, params=None, timeout=None, stream=False):
        self.pedidos.append((url, params))
        for trecho, resposta in self.rotas.items():
            if trecho in url:
                return resposta(url, params) if callable(resposta) else resposta
        raise AssertionError(f"URL inesperada: {url}")


def _bytes(nome: str) -> bytes:
    return (FIX / nome).read_bytes()


# ================================================================================================ SAMU
def _linhas_samu(nome: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(_bytes(nome).decode("utf-8")), delimiter=";"))[1:]


def _esperado_samu(nome: str, ano: int) -> Counter:
    """Contagem independente do conector: lê a fixture por posição e conta com datetime e dicionário."""
    esperado: Counter = Counter()
    for r in _linhas_samu(nome):
        data, municipio, bairro, subtipo = r[0], r[2], r[3], r[7]
        if municipio != "RECIFE" or not data.startswith(str(ano)):
            continue
        dia = date.fromisoformat(data)
        domingo = dia.fromordinal(dia.toordinal() - (dia.weekday() + 1) % 7)
        esperado[(domingo.isoformat(), bairro, "total")] += 1
        grupo = samu.GRUPOS.get(subtipo)
        if grupo:
            esperado[(domingo.isoformat(), bairro, grupo)] += 1
    return esperado


def test_samu_agrega_na_leitura_por_semana_bairro_e_grupo():
    resumo, agregados = samu.agregar_csv(_bytes("samu_2026_amostra.csv"), 2026)
    obtido = Counter({(a["inicio"], a["bairro_fonte"], a["grupo"]): a["n"] for a in agregados})
    assert obtido == _esperado_samu("samu_2026_amostra.csv", 2026)
    assert resumo["linhas"] == 50 and resumo["chamados_recife"] == 47
    assert resumo["motivos"] == {"outro_municipio_da_regulacao": 3}
    assert (resumo["primeiro_dia"], resumo["ultimo_dia"]) == ("2026-01-01", "2026-05-16")
    # a SE 53 de 2025 vai de 28/12/2025 a 03/01/2026: 01/01/2026 cai no domingo anterior, em outro ano civil
    assert any(a["inicio"] == "2025-12-28" for a in agregados)
    # semana de 10/05/2026 em Boa Viagem: cada subtipo conta uma vez no grupo e uma vez no total
    boa = {
        a["grupo"]: a["n"]
        for a in agregados
        if a["inicio"] == "2026-05-10" and a["bairro_fonte"] == "BOA VIAGEM"
    }
    assert boa["total"] >= sum(v for g, v in boa.items() if g != "total")
    assert resumo["colunas_individuais_descartadas"] == sorted(samu.INDIVIDUAIS)


def test_samu_grupos_por_subtipo_sem_acento_e_espacos():
    assert samu.grupo_do_subtipo("DESIDRATACAO") == "desidratacao"
    assert samu.grupo_do_subtipo(" Desidratação ") == "desidratacao"
    assert samu.grupo_do_subtipo("INFECCAO  GASTROINTESTINAL") == "infeccao_gastrointestinal"
    assert samu.grupo_do_subtipo("DOR ABDOMINAL") is None  # sintoma que não é do recorte: só entra no total
    assert samu.grupo_do_subtipo("") is None


def test_samu_nenhum_campo_individual_chega_a_bronze():
    """Sentinelas em todas as colunas individuais: nenhuma sobrevive ao agregar, nem em chave nem em valor."""
    sentinelas = [
        "RUA-SENTINELA-77",
        "SEXO-SENTINELA",
        "IDADE-SENTINELA-91",
        "ORIGEM-SENTINELA",
        "DESFECHO-SENTINELA",
    ]
    cabecalho = "data;hora_minuto;municipio;bairro;endereco;origem_chamado;tipo;subtipo;sexo;idade;motivo_finalizacao;motivo_desfecho"
    corpo = "\n".join(
        [
            cabecalho,
            f"2026-05-12;13:45:59;RECIFE;PINA;{sentinelas[0]};{sentinelas[3]};GASTROINTESTINAL;DIARREIA;{sentinelas[1]};{sentinelas[2]};x;{sentinelas[4]}",
            f"2026-05-12;13:46:00;RECIFE;PINA;{sentinelas[0]};{sentinelas[3]};GERAIS/OUTROS;FEBRE;{sentinelas[1]};{sentinelas[2]};x;{sentinelas[4]}",
        ]
    )
    resumo, agregados = samu.agregar_csv(corpo.encode(), 2026)
    serializado = json.dumps([resumo, agregados], ensure_ascii=False)
    assert not any(s in serializado for s in sentinelas)
    assert "13:45" not in serializado  # a hora do atendimento também sai
    chaves = {k for a in agregados for k in a} | set(resumo)
    assert chaves == {
        "inicio", "bairro_fonte", "grupo", "n",  # contagens
        "linhas", "chamados_recife", "primeiro_dia", "ultimo_dia", "colunas", "colunas_individuais_descartadas", "motivos",
    }  # fmt: skip
    assert {(a["grupo"], a["n"]) for a in agregados} == {("total", 2), ("diarreia", 1), ("febre", 1)}


def _http_samu(anos_publicados: dict[int, str]):
    pacote = json.loads(_bytes("samu_ckan_pacote_2026.json"))

    def ckan(url, params):
        ano = int(params["id"].rsplit("-", 1)[1])
        if ano not in anos_publicados:
            return R({"success": False}, status=404)
        p = json.loads(json.dumps(pacote))
        p["result"]["resources"][0]["url"] = f"https://portal.exemplo/samu-{ano}.csv"
        p["result"]["resources"].insert(  # um CSV que não é de solicitações: tem de ser ignorado
            0,
            {"name": "Remoções", "url": "https://portal.exemplo/remocoes.csv", "last_modified": "2099-01-01"},
        )
        return R(p)

    rotas = {"package_show": ckan}
    for ano, nome in anos_publicados.items():
        rotas[f"samu-{ano}.csv"] = R(conteudo=_bytes(nome))
    return Http(rotas)


def test_samu_extrai_so_os_anos_publicados_e_o_csv_de_solicitacoes():
    http = _http_samu({2025: "samu_2025_amostra.csv", 2026: "samu_2026_amostra.csv"})
    c = samu.ConectorSamuRecife(http=http)
    registros = c.extrair(ctx())  # anos pedidos: 2022 a 2026; 2022 a 2024 respondem 404 e são pulados
    arquivos = [r for r in registros if r["tipo"] == "arquivo"]
    assert [a["ano"] for a in arquivos] == [2025, 2026]
    assert all("remocoes" not in a["url"] for a in arquivos)
    assert arquivos[1]["sha256"] == hashlib.sha256(_bytes("samu_2026_amostra.csv")).hexdigest()
    assert (
        arquivos[1]["atualizado_em"] == "2026-11-06T18:39:32.106687"
    )  # last_modified real do recurso de 2026
    assert c.anos(ctx()) == [2022, 2023, 2024, 2025, 2026]


def test_samu_bronze_so_tem_contagens_e_resumo():
    c = samu.ConectorSamuRecife(http=_http_samu({2026: "samu_2026_amostra.csv"}))
    registros = c.extrair(ctx())
    serializado = json.dumps(registros, ensure_ascii=False)
    assert "APAGADO" not in serializado  # nem o texto de substituição das colunas individuais
    assert {r["tipo"] for r in registros} == {"arquivo", "agregado"}
    assert all(
        set(r) == {"tipo", "ano", "inicio", "bairro_fonte", "grupo", "n"}
        for r in registros
        if r["tipo"] == "agregado"
    )


def test_samu_transforma_soma_arquivos_na_semana_que_cruza_o_ano_e_marca_semana_incompleta():
    c = samu.ConectorSamuRecife(
        http=_http_samu({2025: "samu_2025_amostra.csv", 2026: "samu_2026_amostra.csv"})
    )
    df = c.transformar(bronze(c.extrair(ctx())), ctx())
    esperado = _esperado_samu("samu_2025_amostra.csv", 2025) + _esperado_samu("samu_2026_amostra.csv", 2026)
    obtido = Counter({(str(r.inicio), r.bairro_fonte, r.grupo): r.chamados for r in df.itertuples()})
    assert obtido == esperado
    # SE 53/2025 (28/12 a 03/01) recebe linhas dos dois arquivos
    se53 = df[df["inicio"] == date(2025, 12, 28)]
    assert se53["chamados"].sum() == sum(
        v for (i, _, g), v in esperado.items() if i == "2025-12-28" and g == "total"
    ) + sum(v for (i, _, g), v in esperado.items() if i == "2025-12-28" and g != "total")
    # bairro oficial casado; zero medido não existe como linha (linha ausente em semana coberta = 0)
    assert set(df.loc[df["bairro_fonte"] == "BOA VIAGEM", "territorio_id"]) == {"bairro-boa-viagem"}
    assert df["chamados"].min() >= 1
    # primeira semana (começo da amostra, 28/12 só tem 4 dias) e última (parou em 16/05, sábado 16/05 = fim da semana)
    assert df["primeiro_dia_dado"].iloc[0] == date(2025, 12, 28) and df["ultimo_dia_dado"].iloc[0] == date(
        2026, 5, 16
    )
    assert not df.loc[df["inicio"] == date(2026, 5, 10), "incompleta"].any()  # 10 a 16/05 cabe inteira
    assert (
        df.loc[df["inicio"] == date(2025, 12, 28), "incompleta"].eq(False).all()
    )  # início da série = primeiro dia


def test_samu_semana_depois_do_ultimo_dia_do_arquivo_e_incompleta():
    corpo = (
        b"data;hora_minuto;municipio;bairro;endereco;origem_chamado;tipo;subtipo;sexo;idade;motivo_finalizacao;motivo_desfecho\n"
        b"2026-10-25;00:00:00;RECIFE;PINA;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
        b"2026-10-31;00:00:00;RECIFE;PINA;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
    )
    resumo, agregados = samu.agregar_csv(corpo, 2026)
    assert resumo["ultimo_dia"] == "2026-10-31"
    df = samu.ConectorSamuRecife().transformar(
        bronze(
            [
                {"tipo": "arquivo", "ano": 2026, "atualizado_em": "2026-11-06T18:39:32", **resumo},
                *({"tipo": "agregado", "ano": 2026, **a} for a in agregados),
            ]
        ),
        ctx(),
    )
    # 25/10 a 31/10 termina em 31/10 (sábado): completa; 01/11 em diante não existe (sem dado, não zero)
    assert df["inicio"].tolist()[0] == date(2026, 10, 25) and not df["incompleta"].any()
    assert df["fonte_atualizada_em"].iloc[0] == date(2026, 11, 6)


def test_samu_descarta_outros_municipios_data_invalida_e_linha_quebrada_com_motivo():
    corpo = (
        b"data;hora_minuto;municipio;bairro;endereco;origem_chamado;tipo;subtipo;sexo;idade;motivo_finalizacao;motivo_desfecho\n"
        b"2026-05-12;00:00:00;OLINDA;CARMO;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
        b"2026;;;\n"
        b"ontem;00:00:00;RECIFE;PINA;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
        b"2025-05-12;00:00:00;RECIFE;PINA;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
        b"2026-05-12;00:00:00;RECIFE;;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
    )
    resumo, agregados = samu.agregar_csv(corpo, 2026)
    assert resumo["motivos"] == {
        "outro_municipio_da_regulacao": 1,
        "linha_malformada": 1,
        "data_invalida": 1,
        "data_fora_do_ano_do_arquivo": 1,
    }
    assert {a["bairro_fonte"] for a in agregados} == {
        samu.SEM_BAIRRO
    }  # sem bairro entra no município, não no mapa


def test_samu_csv_sem_colunas_obrigatorias_falha_com_mensagem():
    with pytest.raises(FonteSemDados, match="subtipo"):
        samu.agregar_csv(b"data;municipio;bairro;tipo\n2026-01-01;RECIFE;PINA;X\n", 2026)


def test_samu_sem_nenhum_conjunto_publicado_falha_em_vez_de_gravar_zero():
    c = samu.ConectorSamuRecife(http=_http_samu({}))
    with pytest.raises(FonteSemDados, match="SAMU"):
        c.extrair(ctx())


def test_samu_rotulo_e_demanda_de_urgencia_nao_caso_de_doenca():
    assert samu.ROTULO == "demanda de urgência (SAMU)"
    assert "caso" not in samu.ConectorSamuRecife.fonte.nome.lower()


# ================================================================================================ SISAGUA
def _sisagua() -> list[dict]:
    return json.loads(_bytes("sisagua_recife_2026_amostra.json"))["parametros"]


def _servir(linhas_por_ano: dict[int, list[dict]], tamanho_pagina: int):
    def resposta(url, params):
        lote = linhas_por_ano.get(params["ano"], [])
        assert params["codigo_ibge"] == 261160 and params["limit"] == tamanho_pagina
        return R({"parametros": lote[params["offset"] : params["offset"] + params["limit"]]})

    return Http({"vigilancia-parametros-basicos": resposta})


def test_sisagua_classifica_ecoli_e_cloro_sem_percentual():
    assert sisagua.classe("ecoli", "PRESENTE") == "presente"
    assert sisagua.classe("ecoli", "Ausente") == "ausente"
    assert sisagua.classe("ecoli", "<1") is None  # resultado que não dá para contar
    assert sisagua.classe("cloro", "0,2") == "dentro" and sisagua.classe("cloro", "0,19") == "fora"
    assert sisagua.classe("cloro", "5,0") == "dentro" and sisagua.classe("cloro", "5,01") == "fora"
    assert sisagua.classe("cloro", "0,0") == "fora"  # zero medido é medida, fora da faixa
    assert sisagua.classe("cloro", None) is None and sisagua.classe("cloro", "-") is None
    assert sisagua.grandeza("Cloro residual livre (mg/L)") == "cloro"
    assert sisagua.grandeza("Escherichia coli") == "ecoli"
    assert sisagua.grandeza("Coliformes totais") is None and sisagua.grandeza("Turbidez (uT)") is None
    assert sisagua.motivo_grupo("Rotina") == "rotina" and sisagua.motivo_grupo("Surto") == "dirigida"


def test_sisagua_pagina_ate_acabar_e_pula_ano_sem_analise(monkeypatch):
    monkeypatch.setattr(sisagua, "PAGINA", 10)
    http = _servir({2026: _sisagua()}, 10)
    c = sisagua.ConectorSisagua(http=http)
    registros = c.extrair(ctx())
    assert [r["ano"] for r in registros if r["tipo"] == "arquivo"] == [
        2026
    ]  # 2025 sem linha: sem dado, não zero
    assert [p[1]["offset"] for p in http.pedidos if p[1]["ano"] == 2026] == [0, 10, 20, 30, 40]
    assert [p[1]["ano"] for p in http.pedidos if p[1]["offset"] == 0] == [2025, 2026]
    assert next(r for r in registros if r["tipo"] == "arquivo")["linhas"] == 49


def test_sisagua_agrega_na_leitura_e_nenhum_campo_de_local_chega_a_bronze(monkeypatch):
    linhas = _sisagua()
    sentinelas = {
        "numero_da_amostra": "AMOSTRA-SENTINELA-5",
        "descricao_do_local": "RUA-SENTINELA-8",
        "local": "LOCAL-SENTINELA-3",
    }
    linhas = [
        {**r, **sentinelas, "latitude": -8.123, "longitude": -34.123} for r in linhas
    ]  # sintético: só os 5 campos
    c = sisagua.ConectorSisagua(http=_servir({2026: linhas}, sisagua.PAGINA))
    registros = c.extrair(ctx())
    serializado = json.dumps(registros, ensure_ascii=False)
    assert not any(v in serializado for v in sentinelas.values()) and "APAGADO" not in serializado
    assert "-8.123" not in serializado and "latitude" not in serializado
    assert {k for r in registros if r["tipo"] == "agregado" for k in r} == {
        "tipo", "ano", "inicio", "bairro_fonte", "motivo_grupo", "grandeza", "classe", "n",
    }  # fmt: skip
    assert {k for r in registros if r["tipo"] == "arquivo" for k in r} == {
        "tipo", "ano", "url", "linhas", "ultima_coleta", "ultimo_registro", "parametros", "motivos",
    }  # fmt: skip


def test_sisagua_contagens_batem_com_conta_independente_e_separam_rotina_de_dirigida():
    linhas = _sisagua()
    c = sisagua.ConectorSisagua(http=_servir({2026: linhas}, sisagua.PAGINA))
    df = c.transformar(bronze(c.extrair(ctx())), ctx())
    ecoli = [
        r
        for r in linhas
        if r["parametro"] == "Escherichia coli" and r["resultado"] in ("PRESENTE", "AUSENTE")
    ]
    cloro = [r for r in linhas if r["parametro"].startswith("Cloro residual livre")]
    assert df["analises_ecoli"].sum() == len(ecoli)
    assert df["ecoli_presente"].sum() == sum(r["resultado"] == "PRESENTE" for r in ecoli) >= 3
    assert df["analises_cloro"].sum() == len(cloro)
    assert df["cloro_fora_padrao"].sum() == sum(
        not 0.2 <= float(r["resultado"].replace(",", ".")) <= 5 for r in cloro
    )
    dirigidas = df[df["motivo_grupo"] == "dirigida"]
    assert len(dirigidas) >= 1  # surto: linha própria, não soma na rotina
    assert dirigidas["analises_ecoli"].sum() == sum(r["motivo_da_coleta"] != "Rotina" for r in ecoli)
    assert (df["ecoli_presente"] <= df["analises_ecoli"]).all() and (
        df["cloro_fora_padrao"] <= df["analises_cloro"]
    ).all()
    assert set(df.loc[df["bairro_fonte"] == "BOA VIAGEM", "territorio_id"]) == {"bairro-boa-viagem"}
    # o que o conector não usa (turbidez, coliformes totais) não vira contagem nem descarte
    assert c.descartes.get("resultado_nao_contavel", 0) == 0


def test_sisagua_semanas_recentes_sao_marcadas_incompletas():
    linhas = _sisagua()  # coletas de maio e de 26 a 28/10; último registro em 03/11/2026
    c = sisagua.ConectorSisagua(http=_servir({2026: linhas}, sisagua.PAGINA))
    df = c.transformar(bronze(c.extrair(ctx())), ctx())
    assert df["ultimo_registro"].iloc[0] == date(2026, 11, 3)
    assert df.loc[df["inicio"] == date(2026, 10, 25), "incompleta"].all()
    assert not df.loc[df["inicio"] == date(2026, 5, 10), "incompleta"].any()


def test_sisagua_sem_nenhuma_analise_falha_e_resposta_sem_chave_falha():
    with pytest.raises(FonteSemDados, match="nenhuma análise"):
        sisagua.ConectorSisagua(http=_servir({}, sisagua.PAGINA)).extrair(ctx())
    http = Http({"vigilancia-parametros-basicos": R({"erro": "indisponível"})})
    with pytest.raises(FonteSemDados, match="parametros"):
        sisagua.ConectorSisagua(http=http).extrair(ctx())


# ================================================================================================ Atlas
def _http_atlas(csv_bytes: bytes | None = None):
    csv_bytes = csv_bytes if csv_bytes is not None else _bytes("atlas_recife_amostra.csv")
    html = (FIX / "atlas_downloads_2026-11-06.html").read_text(encoding="utf-8")
    return Http(
        {"downloads.xhtml": R(texto=html, conteudo=html.encode()), "Consolidado.csv": R(conteudo=csv_bytes)}
    )


def _atlas_df():
    c = atlas.ConectorAtlasDesastres(http=_http_atlas())
    return c, c.transformar(bronze(c.extrair(ctx())), ctx())


def test_atlas_descobre_o_link_do_csv_na_pagina_de_downloads():
    html = (FIX / "atlas_downloads_2026-11-06.html").read_text(encoding="utf-8")
    assert atlas.link_do_csv(html) == (
        "https://atlasdigital.mdr.gov.br/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv"
    )
    novo = html + '<a href="/arquivos/2027/BD_Atlas_1991_2026_v1.0_2027.07.01_Consolidado.csv">novo</a>'
    assert atlas.link_do_csv(novo).endswith("2027.07.01_Consolidado.csv")  # vale o consolidado mais novo
    with pytest.raises(FonteSemDados, match="endereço mudou"):
        atlas.link_do_csv("<html>sem links</html>")


def test_atlas_filtra_so_o_recife_em_fluxo_e_guarda_sha_e_versao():
    conteudo = _bytes("atlas_recife_amostra.csv")
    registros = atlas.ConectorAtlasDesastres(http=_http_atlas()).extrair(ctx())
    arquivo, eventos = registros[0], registros[1:]
    assert len(eventos) == 16 and all(e["tipo"] == "evento" for e in eventos)
    assert (
        arquivo["linhas_brasil"] == 22 and arquivo["registros_recife"] == 16
    )  # os 6 de outros municípios morrem
    assert arquivo["sha256"] == hashlib.sha256(conteudo).hexdigest() and arquivo["bytes"] == len(conteudo)
    assert arquivo["versao"] == "BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv"
    assert arquivo["consolidado_em"] == "2026-08-06"
    assert not any("Olinda" in json.dumps(e) for e in eventos)


def test_atlas_bronze_so_tem_colunas_administrativas_sem_texto_livre():
    registros = atlas.ConectorAtlasDesastres(http=_http_atlas()).extrair(ctx())
    chaves = {k for r in registros if r["tipo"] == "evento" for k in r}
    assert chaves == {"tipo", *atlas.COLUNAS.values()}
    serializado = json.dumps(registros, ensure_ascii=False)
    assert "Monteverde" not in serializado and "Descricao" not in serializado  # narrativa do município
    assert "Setores" not in serializado


def test_atlas_evento_de_2022_traz_dano_status_e_decodifica_latin1():
    _, df = _atlas_df()
    e = (
        df[df["protocolo"] == "PE-F-2611606-13214-20220529"]
        if (df["protocolo"] == "PE-F-2611606-13214-20220529").any()
        else df[df["data_evento"] == date(2022, 5, 29)]
    )
    e = e.iloc[0]
    assert (e["status"], e["tipologia"], e["cobrade"]) == ("Reconhecido", "Chuvas Intensas", "13214")
    assert (e["mortos"], e["desabrigados"], e["desalojados"], e["outros_afetados"]) == (
        43,
        3874,
        831,
        1532177,
    )
    assert e["danos_materiais_rs"] == 61664230.93 and e["prejuizo_publico_rs"] == 7397162.12
    assert bool(e["chuva_relacionada"]) is True
    assert any(df["tipologia"].str.contains("Inundações")) and any(df["tipologia"].str.contains("Doenças"))


def test_atlas_todos_os_16_registros_e_chuva_relacionada_so_na_tipologia_certa():
    c, df = _atlas_df()
    assert len(df) == 16 and df["protocolo"].is_unique and c.descartes == {}
    chuva = df.groupby("tipologia")["chuva_relacionada"].all()
    assert chuva["Enxurradas"] and chuva["Movimento de Massa"] and chuva["Alagamentos"]
    assert not chuva["Estiagem e Seca"] and not chuva["Doenças infecciosas"]
    assert df["data_evento"].min() == date(1991, 5, 25) and df["data_evento"].max() == date(2022, 5, 29)
    assert set(df["versao_fonte"]) == {"BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv"}


def test_atlas_vazio_e_ausente_zero_continua_zero():
    cab = "Protocolo_S2iD;Data_Evento;Data_Registro;Cod_Cobrade;descricao_tipologia;Status;DH_MORTOS;DH_FERIDOS;DH_DESABRIGADOS;DH_DESALOJADOS;DH_OUTROS AFETADOS;DH_total_danos_humanos_diretos;DM_total_danos_materiais;PEPL_total_publico;PEPR_total_privado;Cod_IBGE_Mun"
    linhas = [
        cab,
        "A-1;01/02/2020;01/02/2020;12300;Alagamentos;Registro;;0;5;;0;5;;0.00;;2611606",
        "A-2;31/02/2020;;12300;Alagamentos;Registro;1;;;;;;;;;2611606",
    ]
    _, registros = atlas.filtrar_recife(linha + "\n" for linha in linhas)
    c = atlas.ConectorAtlasDesastres(http=_http_atlas())
    df = c.transformar(
        bronze(
            [
                {"tipo": "arquivo", "versao": "x.csv", "consolidado_em": None},
                *({"tipo": "evento", **r} for r in registros),
            ]
        ),
        ctx(),
    )
    a1 = df.iloc[0]
    assert (
        pd.isna(a1["mortos"])
        and a1["feridos"] == 0
        and a1["desabrigados"] == 5
        and pd.isna(a1["danos_materiais_rs"])
    )
    assert a1["prejuizo_publico_rs"] == 0
    assert c.descartes == {
        "sem_data_do_evento": 1
    }  # 31/02 não existe: evento sem data não entra na linha do tempo


def test_atlas_csv_sem_registro_do_recife_ou_sem_coluna_falha_com_mensagem():
    cab = _bytes("atlas_recife_amostra.csv").splitlines()[0]
    with pytest.raises(FonteSemDados, match="nenhum registro do Recife"):
        atlas.ConectorAtlasDesastres(http=_http_atlas(cab + b"\r\n")).extrair(ctx())
    with pytest.raises(FonteSemDados, match="Cod_IBGE_Mun"):
        atlas.filtrar_recife(["Protocolo_S2iD;Data_Evento\n"])


# ================================================================================================ registro e frescor
def test_tres_conectores_registrados_com_limite_de_frescor_e_licenca():
    for fid in ("samu-recife", "sisagua", "atlas-desastres"):
        assert fid in IMPLEMENTADOS and issubclass(CONECTORES[fid], Conector) and CONECTORES[fid].id == fid
        assert CONECTORES[fid].fonte.tipo == "observada"
    assert frescor.limite_frescor_h("samu-recife") == 1440  # mensal
    assert frescor.limite_frescor_h("sisagua") == 192  # semanal
    assert frescor.limite_frescor_h("atlas-desastres") == 13140  # anual
    assert samu.ConectorSamuRecife.fonte.licenca == "ODbL"
    assert (
        sisagua.ConectorSisagua.fonte.licenca is None and atlas.ConectorAtlasDesastres.fonte.licenca is None
    )


def test_gold_declara_as_tres_tabelas_e_so_lê_da_silver():
    assert set(gold.TABELAS_SAMU) | set(gold.TABELAS_AGUA) | set(gold.TABELAS_DESASTRES) == {
        "gold.samu_demanda_semana",
        "gold.agua_vigilancia_semana",
        "gold.desastres_historico",
    }
    assert set(gold.VERIFICADAS) >= {
        "gold.samu_demanda_semana",
        "gold.agua_vigilancia_semana",
        "gold.desastres_historico",
    }
    for consulta in (gold.SAMU_DEMANDA_SEMANA, gold.AGUA_VIGILANCIA_SEMANA, gold.DESASTRES_HISTORICO):
        assert "silver." in consulta and "bronze" not in consulta


def test_samu_semana_que_passa_do_ultimo_dia_do_arquivo_fica_incompleta():
    corpo = (
        b"data;hora_minuto;municipio;bairro;endereco;origem_chamado;tipo;subtipo;sexo;idade;motivo_finalizacao;motivo_desfecho\n"
        b"2026-10-18;00:00:00;RECIFE;PINA;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
        b"2026-10-28;00:00:00;RECIFE;PINA;x;x;GERAIS/OUTROS;FEBRE;x;x;x;x\n"
    )  # arquivo parou numa quarta-feira
    resumo, agregados = samu.agregar_csv(corpo, 2026)
    registros = [{"tipo": "arquivo", "ano": 2026, "atualizado_em": None, **resumo}]
    registros += [{"tipo": "agregado", "ano": 2026, **a} for a in agregados]
    df = samu.ConectorSamuRecife().transformar(bronze(registros), ctx())
    por_semana = df.groupby("inicio")["incompleta"].all().to_dict()
    assert por_semana == {
        date(2026, 10, 18): False,
        date(2026, 10, 25): True,
    }  # a de 25/10 vai até sábado 31/10
    assert df["fonte_atualizada_em"].isna().all()  # sem data de publicação, fica vazio (não inventa)
