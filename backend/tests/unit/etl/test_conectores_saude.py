"""Conectores da saúde depois da chuva, sem rede nem banco.

- InfoDengue: as 10 semanas mais recentes da resposta REAL de 05/11/2026 (dengue, Recife);
- SINAN: um .dbc mínimo montado aqui (DBF + implode só com literais, formato aceito pelo `blast`), porque o
  arquivo real tem 1 MB; o leitor foi conferido contra o LEPTBR26.dbc real (14.848 registros, 331 do Recife);
- arboviroses: linhas reais dos CSVs de 2015 e 2025 com número da notificação, nascimento, logradouro e CEP
  trocados por "APAGADO".
"""

from __future__ import annotations

import json
import struct
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from climasense.etl.conectores import arboviroses, dbc, infodengue, leptospirose
from climasense.etl.conectores.base import FonteSemDados
from tests.unit.etl.test_conectores_chuva import Http, Resposta, bronze, ctx

FIX = Path(__file__).parent / "fixtures"
AGORA = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


# ----------------------------------------------------------------------------------------- .dbc de teste
class _Bits:
    def __init__(self) -> None:
        self.saida, self.buf, self.n = bytearray(), 0, 0

    def por(self, valor: int, n: int) -> None:  # LSB primeiro, como o `bits()` do blast
        self.buf |= valor << self.n
        self.n += n
        while self.n >= 8:
            self.saida.append(self.buf & 0xFF)
            self.buf >>= 8
            self.n -= 8

    def fim(self) -> bytes:
        if self.n:
            self.saida.append(self.buf & 0xFF)
        return bytes(self.saida)


def _codigo(h, simbolo: int) -> tuple[int, int]:
    """Código canônico (comprimento, valor) de um símbolo na tabela do blast."""
    primeiro = indice = 0
    for comp in range(1, 14):
        c = h.contagem[comp]
        for k in range(c):
            if h.simbolo[indice + k] == simbolo:
                return comp, primeiro + k
        indice += c
        primeiro = (primeiro + c) << 1
    raise AssertionError(simbolo)


def implodir_literal(dados: bytes) -> bytes:
    b = _Bits()
    b.por(0, 8)  # literais sem codificação
    b.por(4, 8)  # dicionário de 1 KB
    for byte in dados:
        b.por(0, 1)
        b.por(byte, 8)
    b.por(1, 1)  # fim: comprimento 519 = símbolo 15 (base 264) + 8 bits extras de 255
    comp, valor = _codigo(dbc._COMP, 15)
    for i in range(comp - 1, -1, -1):  # o decodificador lê o código do bit mais alto, invertido
        b.por(((valor >> i) & 1) ^ 1, 1)
    b.por(255, 8)
    return b.fim()


def montar_dbc(campos: list[tuple[str, int]], linhas: list[dict]) -> bytes:
    tam_cab = 32 + 32 * len(campos) + 1
    tam_reg = 1 + sum(t for _, t in campos)
    cab = bytearray(32)
    cab[0] = 3
    cab[4:8] = struct.pack("<I", len(linhas))
    cab[8:10] = struct.pack("<H", tam_cab)
    cab[10:12] = struct.pack("<H", tam_reg)
    for nome, tam in campos:
        d = bytearray(32)
        d[: len(nome)] = nome.encode("latin-1")
        d[11] = ord("C")
        d[16] = tam
        cab += d
    cab += b"\x0d"
    corpo = b"".join(
        b" " + b"".join(str(r.get(n, "")).ljust(t).encode("latin-1") for n, t in campos) for r in linhas
    )
    return bytes(cab) + b"\0\0\0\0" + implodir_literal(corpo + b"\x1a")


CAMPOS_LEPTO = [
    ("NU_NOTIFIC", 7),
    ("DT_NOTIFIC", 8),
    ("SEM_PRI", 6),
    ("ID_MN_RESI", 6),
    ("CLASSI_FIN", 1),
    ("EVOLUCAO", 1),
    ("ANT_CB_LAM", 1),
]


def _lepto(**kw):
    base = {"NU_NOTIFIC": "1234567", "DT_NOTIFIC": "20260512", "ID_MN_RESI": "261160", "EVOLUCAO": "1"}
    return {**base, **kw}


LINHAS_LEPTO = [
    _lepto(SEM_PRI="202619", CLASSI_FIN="1", ANT_CB_LAM="1"),
    _lepto(SEM_PRI="202619", CLASSI_FIN="1", ANT_CB_LAM="2", EVOLUCAO="2"),
    _lepto(SEM_PRI="202619", CLASSI_FIN="2"),
    _lepto(SEM_PRI="202621", CLASSI_FIN=""),
    _lepto(SEM_PRI="202619", CLASSI_FIN="1", ID_MN_RESI="260790"),  # Jaboatão: fora
    _lepto(SEM_PRI="201452", CLASSI_FIN="1", DT_NOTIFIC="20150103"),  # sintomas antes da série
    _lepto(SEM_PRI="202640", CLASSI_FIN="", DT_NOTIFIC="20261010"),
]


def test_leitor_dbc_le_o_dbf_comprimido_e_so_as_colunas_pedidas():
    conteudo = montar_dbc(CAMPOS_LEPTO, LINHAS_LEPTO)
    nomes, registros = dbc.ler(conteudo, ["SEM_PRI", "ID_MN_RESI"])
    lidos = list(registros)
    assert nomes == [n for n, _ in CAMPOS_LEPTO]
    assert lidos[0] == {"SEM_PRI": "202619", "ID_MN_RESI": "261160"}  # NU_NOTIFIC nunca é decodificado
    assert len(lidos) == len(LINHAS_LEPTO)
    with pytest.raises(dbc.DbcInvalido):
        dbc.ler(conteudo[:-6])


class FtpFalso:
    def __init__(self, conteudos: dict[tuple[str, str], tuple[str, bytes]]) -> None:
        self.conteudos = conteudos

    def arquivos(self):
        return [
            {"pasta": p, "arquivo": a, "ano": 2000 + int(a[6:8]), "atualizado_em": quando}
            for (p, a), (quando, _) in self.conteudos.items()
        ]

    def baixar(self, pasta, arquivo):
        return self.conteudos[(pasta, arquivo)][1]


def test_leptospirose_agrega_por_semana_de_sintomas_sem_linha_individual_na_bronze():
    lepto26 = montar_dbc(CAMPOS_LEPTO, LINHAS_LEPTO)
    final14 = montar_dbc(CAMPOS_LEPTO, [_lepto(SEM_PRI="201401", CLASSI_FIN="1", DT_NOTIFIC="20140110")])
    ftp = FtpFalso(
        {
            ("PRELIM", "LEPTBR26.dbc"): ("2026-11-03T14:16:00Z", lepto26),
            ("FINAIS", "LEPTBR14.dbc"): ("2026-07-15T17:11:00Z", final14),  # antes de 2015: nem é baixado
        }
    )
    c = leptospirose.ConectorSinanLeptospirose(ftp=ftp)
    registros = c.extrair(ctx(agora=AGORA))
    assert {r["tipo"] for r in registros} == {"arquivo", "agregado"}
    assert all("NU_NOTIFIC" not in r and "nu_notific" not in r for r in registros)
    arquivo = next(r for r in registros if r["tipo"] == "arquivo")
    assert (arquivo["registros_brasil"], arquivo["registros_recife"]) == (7, 6)
    assert arquivo["ultima_notificacao"] == "2026-10-10"

    df = c.transformar(bronze(registros), ctx(agora=AGORA)).set_index("inicio")
    se19 = df.loc[date(2026, 5, 10)]  # SE 19 de 2026 começa no domingo 10/05
    assert (se19["notificados"], se19["confirmados"], se19["descartados"]) == (3, 2, 1)
    assert (se19["obitos"], se19["expostos_enchente"], se19["em_investigacao"]) == (1, 1, 0)
    assert bool(se19["incompleta"]) is False and bool(se19["preliminar"]) is True
    se20 = df.loc[date(2026, 5, 17)]
    assert se20["notificados"] == 0  # semana coberta pelo arquivo, sem notificação: zero
    assert df.loc[date(2026, 5, 24), "em_investigacao"] == 1  # SE 21, sem encerramento
    # a série vai até a semana da última notificação (10/10 → SE 40, de 04/10); as 6 últimas ficam incompletas
    assert df.index.max() == date(2026, 10, 4)
    assert df.loc[date(2026, 10, 4), "notificados"] == 1
    assert bool(df.loc[date(2026, 8, 30), "incompleta"]) is True
    assert bool(df.loc[date(2026, 8, 23), "incompleta"]) is False
    assert df.index.min() == date(2015, 1, 4)
    assert c.descartes == {"sintomas_antes_de_2015": 1}


def test_leptospirose_sem_arquivo_desde_2015_e_falha_explicada():
    ftp = FtpFalso({("FINAIS", "LEPTBR14.dbc"): ("2026-07-15T17:11:00Z", b"")})
    with pytest.raises(FonteSemDados, match="LEPTBR"):
        leptospirose.ConectorSinanLeptospirose(ftp=ftp).extrair(ctx(agora=AGORA))


# ----------------------------------------------------------------------------------------- InfoDengue
def _infodengue(agravo_corpo=None):
    corpo = json.loads((FIX / "infodengue_dengue_2026-11-05.json").read_text(encoding="utf-8"))

    def responder(params):
        return Resposta(corpo if params["disease"] == "dengue" else (agravo_corpo or []))

    return Http({"alertcity": responder}), corpo


def test_infodengue_semana_epidemiologica_nowcasting_e_semanas_incompletas():
    http, corpo = _infodengue()
    c = infodengue.ConectorInfoDengue(http=http)
    registros = c.extrair(ctx(agora=AGORA))
    assert [p[1]["disease"] for p in http.pedidos] == ["dengue", "chikungunya"]  # zika fica de fora
    assert http.pedidos[0][1]["geocode"] == "2611606" and http.pedidos[0][1]["ey_start"] == 2015
    df = c.transformar(bronze(registros), ctx(agora=AGORA))
    assert len(df) == 10 and set(df["agravo"]) == {"dengue"}
    ultima = df.iloc[-1]
    assert (ultima["ano"], ultima["semana"], ultima["inicio"]) == (2026, 43, date(2026, 10, 25))
    assert (ultima["casos"], ultima["casos_est"], ultima["casos_est_min"], ultima["casos_est_max"]) == (
        36,
        221.0,
        123,
        414,
    )
    assert ultima["nivel"] == 2 and round(ultima["rt"], 3) == 1.025
    incompletas = df.loc[df["incompleta"], "semana"].tolist()
    # as 4 mais recentes (40–43) e a 39, com estimativa 217 contra 183 notificados (> 10%)
    assert incompletas == [39, 40, 41, 42, 43]


def test_infodengue_resposta_fora_do_formato_falha_sem_inventar():
    http = Http({"alertcity": Resposta({"erro": "x"})})
    with pytest.raises(FonteSemDados, match="formato"):
        infodengue.ConectorInfoDengue(http=http).extrair(ctx(agora=AGORA))


# ----------------------------------------------------------------------------------------- arboviroses
def _ckan_pacote():
    return {
        "result": {
            "resources": [
                {"name": "Casos de Dengue 2025", "url": "https://d/casos-de-dengue-2025.csv",
                 "last_modified": "2026-03-07T01:10:16"},
                {"name": "Casos de Dengue em 2015", "url": "https://d/dengue2015.csv",
                 "last_modified": "2026-03-13T14:41:56"},
                {"name": "Casos confirmados de Zika 2025", "url": "https://d/zika-2025.csv"},
                {"name": "Metadados dos Casos Confirmados de Dengue a partir de 2016", "url": "https://d/m.json"},
                {"name": "Tabela de Bairros", "url": "https://d/tabela-de-bairros.csv"},
            ]
        }
    }  # fmt: skip


def _http_arbo():
    return Http(
        {
            "package_show": Resposta(_ckan_pacote()),
            "casos-de-dengue-2025.csv": Resposta(
                conteudo=(FIX / "arboviroses_dengue_2025_amostra.csv").read_bytes()
            ),
            "dengue2015.csv": Resposta(conteudo=(FIX / "arboviroses_dengue_2015_amostra.csv").read_bytes()),
        }
    )


def test_arboviroses_agregam_por_bairro_e_nao_guardam_campo_pessoal():
    c = arboviroses.ConectorRecifeArboviroses(http=_http_arbo())
    registros = c.extrair(ctx(agora=AGORA))
    assert {(r["agravo"], r["ano"]) for r in registros} == {("dengue", 2025), ("dengue", 2015)}  # sem zika
    texto = json.dumps(registros, ensure_ascii=False)
    assert "APAGADO" not in texto  # nenhum valor de logradouro, CEP, nascimento ou notificação sai do CSV
    arquivo = next(r for r in registros if r["tipo"] == "arquivo" and r["ano"] == 2025)
    assert {"nm_logrado", "nu_cep", "dt_nasc"} <= set(arquivo["colunas_sensiveis_descartadas"])
    agregados = [r for r in registros if r["tipo"] == "agregado"]
    assert set(agregados[0]) == {"tipo", "agravo", "ano", "bairro_fonte", "classificacao", "n"}

    df = c.transformar(bronze(registros), ctx(agora=AGORA))
    d25 = df[df["ano"] == 2025].set_index("bairro_fonte")
    assert d25.loc["PINA", ["territorio_id", "confirmados", "notificados"]].tolist() == ["bairro-pina", 1, 1]
    assert d25.loc["BOA VIAGEM", ["confirmados", "outros"]].tolist() == [0, 2]  # classificação em branco
    assert d25.loc["TORREAO", "outros"] == 1  # 8 = inconclusivo
    d15 = df[df["ano"] == 2015].set_index("bairro_fonte")
    # layout antigo ("10.0", "5.0"): 3 confirmados e 3 descartados em Santo Amaro
    assert d15.loc["SANTO AMARO", ["territorio_id", "confirmados", "descartados"]].tolist() == [
        "bairro-santo-amaro",
        3,
        3,
    ]
    assert str(df["fonte_atualizada_em"].iloc[0]) in ("2026-03-07", "2026-03-13")


def test_arboviroses_bairro_em_branco_ou_fora_da_base_fica_sem_territorio():
    conteudo = (
        b'"NU_ANO";"ID_MN_RESI";"NM_BAIRRO";"CLASSI_FIN"\n'
        b'"2025";"261160";"";"10"\n"2025";"261160";"GRAAS";"10"\n"2025";"260790";"PINA";"10"\n'
    )  # ALTERADO: três linhas mínimas (bairro vazio, grafia truncada real "GRAAS", outro município)
    resumo, agregados = arboviroses.agregar_csv(conteudo)
    assert resumo["motivos"] == {"residente_fora_do_recife": 1}
    assert {a["bairro_fonte"] for a in agregados} == {arboviroses.SEM_BAIRRO, "GRAAS"}
    c = arboviroses.ConectorRecifeArboviroses(http=None)
    df = c.transformar(
        bronze(
            [{"tipo": "arquivo", "agravo": "dengue", "ano": 2025, "motivos": resumo["motivos"]}]
            + [{"tipo": "agregado", "agravo": "dengue", "ano": 2025, **a} for a in agregados]
        ),
        ctx(agora=AGORA),
    )
    assert df["territorio_id"].isna().all() and df["confirmados"].sum() == 2
    assert c.descartes == {"residente_fora_do_recife": 1, "bairro_fora_da_base_oficial": 1}


def test_arboviroses_sem_colunas_esperadas_e_falha():
    with pytest.raises(FonteSemDados, match="bairro"):
        arboviroses.agregar_csv(b'"a";"b"\n"1";"2"\n')
