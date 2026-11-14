"""Risco de alagamento (F6). Somente dados SINTÉTICOS: nenhum teste baixa arquivo nem toca no banco."""

from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeClassifier

from climasense.ml.alagamento import armazenamento, base, clima, modelo, ocorrencias, servico

GRADE_PEQUENA = {"max_depth": [2, 3], "min_samples_leaf": [20], "class_weight": [None]}
CONJUNTOS_PEQUENOS = {"chuva": ["chuva_1d", "chuva_3d", "chuva_7d"], "completo": list(base.ATRIBUTOS)}
CABECALHO = (
    '"Regional";"Ano";"Mês";"Data";"Ocorrencia";"Solicitacao";"Endereco";"Bairro";"Localidade";'
    '"Grau_de_Risco";"Data_da_Acao";"Tipo_da_Acao";"Quantidade";"Altura";"Largura";"Area_m"'
)
MAPA = {
    "varzea": ("bairro-varzea", "ds-4"),
    "ibura": ("bairro-ibura", "ds-8"),
    "pina": ("bairro-pina", "ds-6"),
}


# ----------------------------------------------------------------------------- rótulo (CSV da Defesa Civil)
def _csv(*linhas: str) -> bytes:
    return ("\n".join([CABECALHO, *linhas]) + "\n").encode("latin-1")


LINHAS = [
    # normal
    '"Oeste";"2022";"Maio";"2022-05-28";"Alagamentos";"Vistoria";"Rua A, 1";"Varzea";"X";"";"2022-05-28";"Atendimento Social";"";"";"";"0"',
    # sem Regional e endereço quebrado em dois campos (defeito real da fonte)
    '"2022";"Maio";"2022-05-29";"";"Vistoria Setor Alagado";"""Rua B";" #$[""";"Ibura de Baixo";"X";"";"2022-05-29";"Mapeamento de Area de Risco";"";"";"";"0"',
    # rua com "Alag" no nome: NÃO é alagamento
    '"Sul";"2022";"Maio";"2022-05-29";"Imóveis com Danos / Risco";"Vistoria";"Rua Alagoinha, 3";"Pina";"X";"";"2022-05-29";"Analise Visual Estrutural";"";"";"";"0"',
    # monitoramento de rotina: só no critério amplo
    '"Sul";"2022";"Maio";"2022-05-30";"";"Monitoramento Alagado";"Rua C";"Pina";"X";"";"2022-05-30";"Mapeamento de Area de Risco";"";"";"";"0"',
    # bairro fora da base oficial
    '"Sul";"2022";"Maio";"2022-05-30";"Alagamentos";"";"Rua D";"Iraque";"X";"";"2022-05-30";"";"";"";"";"0"',
    # linha quebrada sem âncoras
    '"lixo";"sem data"',
]


def test_leitura_robusta_realinha_colunas():
    regs = list(ocorrencias.ler_registros(_csv(*LINHAS)))
    assert len(regs) == 5
    assert regs[1]["data"] == "2022-05-29" and regs[1]["bairro"] == "Ibura de Baixo"
    assert regs[1]["solicitacao"] == "Vistoria Setor Alagado"


def test_criterio_le_so_categorias_nunca_endereco():
    regs = list(ocorrencias.ler_registros(_csv(*LINHAS)))
    evento = [ocorrencias.e_alagamento(r, "evento") for r in regs]
    amplo = [ocorrencias.e_alagamento(r, "amplo") for r in regs]
    assert evento == [True, True, False, False, True]
    assert amplo == [True, True, False, True, True]
    with pytest.raises(ValueError):
        ocorrencias.e_alagamento(regs[0], "inventado")


def test_ocorrencias_agrega_por_bairro_e_dia(tmp_path):
    arq = tmp_path / "atendimentos-2022.csv"
    arq.write_bytes(_csv(*LINHAS, LINHAS[0]))  # repetida no mesmo dia → 1 bairro-dia com 2 registros
    df = ocorrencias.ocorrencias_alagamento([arq], MAPA)
    assert set(df["territorio_id"]) == {"bairro-varzea", "bairro-ibura"}  # apelido "Ibura de Baixo" → Ibura
    assert df.loc[df["territorio_id"] == "bairro-varzea", "registros"].item() == 2
    assert df.attrs["registros_sem_territorio"] == {"Iraque": 1}


def test_recursos_por_ano_escolhe_a_republicacao_mais_recente():
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "result": {
                    "resources": [
                        {"name": "Atendimentos 2023 CSV", "url": "a/old.csv", "last_modified": "2026-03-04"},
                        {"name": "Atendimentos 2023 CSV", "url": "a/new.csv", "last_modified": "2026-03-06"},
                        {"name": "Dicionário", "url": "a/d.json"},
                    ]
                }
            }

    class Http:
        def get(self, *a, **k):
            return Resp()

    assert ocorrencias.recursos_por_ano(Http()) == {2023: "a/new.csv"}


# ----------------------------------------------------------------------------- clima
def test_chuva_diaria_so_dias_completos():
    horas = pd.date_range("2022-01-01", periods=47, freq="h")  # 2º dia com 23 horas
    h = pd.DataFrame({"territorio_id": "ds-1", "hora": horas, "mm": 1.0})
    d = clima.chuva_diaria(h)
    assert list(d["mm"]) == [24.0]


def test_mare_harmonica_recupera_serie_periodica():
    horas = pd.date_range("2023-01-01", periods=24 * 400, freq="h")
    t = (horas - pd.Timestamp("2000-01-01")).total_seconds() / 3600
    nivel = 0.9 * np.cos(np.deg2rad(28.9841042) * t) + 0.3 * np.sin(np.deg2rad(30.0) * t + 1)
    h = clima.ajustar_mare(pd.DataFrame({"hora": horas, "nivel_m": nivel}))
    assert h["r2"] > 0.999 and h["rmse_m"] < 0.01
    antes = pd.date_range("2015-06-01", periods=48, freq="h")  # reconstrói fora do período ajustado
    t2 = (antes - pd.Timestamp("2000-01-01")).total_seconds() / 3600
    real = 0.9 * np.cos(np.deg2rad(28.9841042) * t2) + 0.3 * np.sin(np.deg2rad(30.0) * t2 + 1)
    assert np.abs(clima.prever_mare(h, antes) - real).max() < 0.02
    m = clima.mare_max_diaria(h, pd.DatetimeIndex(["2015-06-01", "2015-06-02"]))
    assert len(m) == 2 and (m <= 1.25).all()


# ----------------------------------------------------------------------------- base sintética
def _base_sintetica(semente: int = 0, sinal: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(semente)
    dias = pd.date_range("2014-01-01", "2024-12-31", freq="D")
    diaria = pd.concat(
        [
            pd.DataFrame({"territorio_id": ds, "data": dias, "mm": rng.gamma(0.6, 10.0, len(dias))})
            for ds in ("ds-1", "ds-2")
        ]
    )
    bairros = {"bairro-a": "ds-1", "bairro-b": "ds-1", "bairro-c": "ds-2", "bairro-d": "ds-2"}
    vulneravel = {"bairro-a": 1.0, "bairro-b": 0.3, "bairro-c": 0.8, "bairro-d": 0.1}
    rot = []
    for b, ds in bairros.items():
        mm = diaria[diaria["territorio_id"] == ds].set_index("data")["mm"]
        tres = mm.rolling(3).sum().fillna(0)
        for d in dias:
            chance = vulneravel[b] * (tres[d] > 45) if sinal else 0.003
            if rng.random() < chance:
                rot.append({"data": d, "territorio_id": b, "distrito_id": ds})
    rotulos = pd.DataFrame(rot, columns=["data", "territorio_id", "distrito_id"])
    mare = pd.Series(1.0 + 0.2 * np.sin(np.arange(len(dias))), index=dias)
    return base.montar_base(rotulos, diaria, mare, bairros, "2014-01-01", "2024-12-31", 0), rotulos


@pytest.fixture(scope="module")
def sintetica():
    return _base_sintetica()


def test_acumulados_somam_janela_e_faltante_vira_nulo():
    dias = pd.date_range("2022-01-01", periods=10, freq="D")
    d = pd.DataFrame({"territorio_id": "ds-1", "data": dias, "mm": 1.0}).drop(index=4)
    a = base.acumulados(d, dias[0], dias[-1]).set_index("data")
    assert a.loc[dias[2], "chuva_3d"] == 3.0
    assert np.isnan(a.loc[dias[4], "chuva_1d"]) and np.isnan(a.loc[dias[5], "chuva_3d"])
    assert np.isnan(a.loc[dias[6], "chuva_7d"])  # janela de 7 dias inclui o dia faltante


def test_historico_nao_vaza_o_proprio_dia_nem_o_futuro():
    dias = pd.date_range("2014-01-01", periods=800, freq="D")
    rot = pd.DataFrame({"territorio_id": ["b1", "b1"], "data": [dias[400], dias[500]]})
    h = base.historico(rot, ["b1"], dias, dias[0]).set_index("data")["hist_dias_ano"]
    assert h.loc[dias[400]] == 0  # o próprio dia não conta
    assert h.loc[dias[401]] > 0 and h.loc[dias[500]] < h.loc[dias[401]]  # taxa só cai sem evento novo
    assert h.loc[dias[501]] > h.loc[dias[500]]


def test_rotulo_com_janela_marca_dias_anteriores_ao_atendimento():
    dias = pd.date_range("2022-01-01", periods=10, freq="D")
    grade = pd.DataFrame({"territorio_id": "b1", "data": dias})
    rot = pd.DataFrame({"territorio_id": ["b1"], "data": [dias[5]]})
    y = base.rotulo_com_janela(rot, grade, 3)
    assert list(y) == [0, 0, 1, 1, 1, 1, 0, 0, 0, 0]


# ----------------------------------------------------------------------------- modelo
def test_somente_arvore_de_decisao():
    m = modelo.novo_modelo(max_depth=3)
    assert isinstance(m, DecisionTreeClassifier) and m.random_state == 42


def test_limiar_para_recall_e_metricas():
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.4, 0.1, 0.7, 0.3, 0.2, 0.05])
    t = modelo.limiar_para_recall(y, s, 0.75)
    assert t == 0.4 and ((s >= t) & (y == 1)).sum() / 4 >= 0.75
    m = modelo.metricas(y, s >= t, s)
    assert m["recall"] == 0.75 and m["vp"] == 3 and m["fp"] == 1 and m["fn"] == 1
    assert 0 < m["auc_pr"] <= 1


def test_eventos_avisados_olha_a_janela_antes_do_atendimento():
    dias = pd.date_range("2022-01-01", periods=6, freq="D")
    t = pd.DataFrame({"territorio_id": "b1", "data": dias, "registro": [0, 0, 0, 1, 0, 1]})
    alerta = np.array([0, 1, 0, 0, 0, 0])
    r = modelo.eventos_avisados(t, alerta, janela_dias=2)
    assert r["eventos"] == 2 and r["eventos_avisados"] == 1  # o 1º foi avisado 2 dias antes; o 2º não


def test_folds_temporais_validam_sempre_no_futuro(sintetica):
    tabela, _ = sintetica
    treino, teste = modelo.dividir(tabela)
    assert treino["ano"].max() < modelo.ANO_TESTE <= teste["ano"].min()
    for idx_tr, idx_va in modelo.folds_temporais(treino):
        assert treino.loc[idx_tr, "data"].max() < treino.loc[idx_va, "data"].min()
        assert set(idx_va).isdisjoint(teste.index)


def test_treino_com_sinal_supera_referencias_e_publica(sintetica):
    tabela, _ = sintetica
    r = modelo.treinar(tabela, None, GRADE_PEQUENA, CONJUNTOS_PEQUENOS, ano_teste=2022)
    assert r.escolhida.conjunto == "completo"  # a vulnerabilidade do bairro (histórico) importa
    assert r.teste["modelo"]["recall"] >= 0.6
    assert r.teste["modelo"]["auc_pr"] > r.teste["limiar_chuva"]["auc_pr"]
    assert r.publicavel and r.motivo is None
    assert r.limiares["alto"] >= r.limiares["moderado"]


def test_sem_ocorrencias_suficientes_nao_publica():
    tabela, rot = _base_sintetica(semente=1, sinal=False)
    poucas = tabela.copy()
    poucas.loc[poucas["ano"] >= 2022, "alagou"] = 0
    poucas.loc[poucas[poucas["ano"] >= 2022].index[:5], "alagou"] = 1
    r = modelo.treinar(poucas, None, GRADE_PEQUENA, CONJUNTOS_PEQUENOS, ano_teste=2022)
    assert not r.publicavel and "insuficientes" in r.motivo


def test_sem_ganho_sobre_a_referencia_nao_publica(sintetica):
    perf = {"treino": {"positivos": 500}, "teste": {"positivos": 100}}
    teste = {
        "modelo": {"recall": 0.9, "auc_pr": 0.10},
        "limiar_chuva": {"recall": 0.9, "auc_pr": 0.10},
    }
    ok, motivo = modelo.avaliar_publicacao(perf, teste)
    assert not ok and "referência" in motivo


# ----------------------------------------------------------------------------- produto (servico)
def _artefato(sintetica, publicavel=True) -> modelo.Artefato:
    tabela, _ = sintetica
    r = modelo.treinar(tabela, None, GRADE_PEQUENA, CONJUNTOS_PEQUENOS, ano_teste=2022)
    harm = {"componentes": list(clima.COMPONENTES), "coeficientes": [0.0] * (1 + 2 * len(clima.COMPONENTES))}
    art = modelo.montar_artefato(r, tabela, harm, "sintetico")
    art.publicavel, art.motivo = publicavel, None if publicavel else "teste"
    # Aprovação exclusivamente sintética para exercitar inferência; nunca salva dado no produto.
    art.validacao["avaliacao_operacional"] = publicavel
    return art


def _chuva_fake(mm_por_dia: dict) -> pd.DataFrame:
    linhas = []
    for ds, dias in mm_por_dia.items():
        for dia, mm in dias.items():
            for h in range(24):
                linhas.append(
                    {"territorio_id": ds, "hora": pd.Timestamp(dia) + pd.Timedelta(hours=h), "mm": mm / 24,
                     "fonte_id": servico.FONTE_HISTORICO}
                )  # fmt: skip
    return pd.DataFrame(linhas)


def test_risco_por_territorio_classes_fatores_e_sem_dados(sintetica, monkeypatch):
    art = _artefato(sintetica)
    agora = datetime(2026, 5, 10, 15, 0, tzinfo=UTC)
    dias = pd.date_range("2026-05-04", "2026-05-11", freq="D")
    chuva = _chuva_fake({"ds-1": {d: 40.0 for d in dias}})  # ds-2 sem chuva → sem_dados
    monkeypatch.setattr(servico, "chuva_recente", lambda db, a, b, agora=None: chuva)
    monkeypatch.setattr(servico, "bairros", lambda db: {"bairro-a": ("A", "ds-1"), "bairro-d": ("D", "ds-2")})
    r = servico.risco_por_territorio(None, agora, art)
    assert r["bairro-a"]["classe"] in {"moderado", "alto"}
    assert r["bairro-d"]["classe"] == "sem_dados"  # dado ausente nunca vira risco baixo (RN-01)
    texto = " ".join(f for v in r.values() for f in v["fatores"])
    assert "%" not in texto and "chance" not in texto.lower() and "probabilidade" not in texto.lower()
    assert any("Regra do modelo" in f for f in r["bairro-a"]["fatores"])
    assert any("herda a chuva do distrito" in f for f in r["bairro-a"]["fatores"])


def test_modelo_nao_publicado_nao_gera_itens(sintetica, monkeypatch):
    art = _artefato(sintetica, publicavel=False)
    assert servico.risco_por_territorio(None, datetime(2026, 5, 10, tzinfo=UTC), art) == {}
    monkeypatch.setattr(armazenamento, "carregar_em_cache", lambda: art)
    p = servico.payload(None, datetime(2026, 5, 10, tzinfo=UTC))
    assert p["disponivel"] is False and p["itens"] == [] and p["motivo"]


def test_payload_sem_arquivo_de_modelo(monkeypatch):
    monkeypatch.setattr(armazenamento, "carregar_em_cache", lambda: None)
    p = servico.payload(None, datetime(2026, 5, 10, tzinfo=UTC))
    assert p == {"disponivel": False, "motivo": p["motivo"], "modelo": None, "itens": []} and p["motivo"]


def test_hoje_recife_usa_utc_menos_3():
    assert servico.hoje_recife(datetime(2026, 5, 11, 2, 0, tzinfo=UTC)) == date(2026, 5, 10)
    assert servico.hoje_recife(datetime(2026, 5, 11, 4, 0)) == date(2026, 5, 11)


def test_por_distrito_pega_a_maior_classe():
    r = servico.por_distrito(
        {"b1": {"classe": "baixo", "fatores": []}, "b2": {"classe": "alto", "fatores": []}},
        {"b1": ("B1", "ds-1"), "b2": ("B2", "ds-1")},
    )
    assert r["ds-1"]["classe"] == "alto" and "B2" in r["ds-1"]["fatores"][0]
    sem = servico.por_distrito({"b": {"classe": "sem_dados", "fatores": []}}, {"b": ("B", "ds-1")})
    assert sem["ds-1"]["confianca"] == "insuficiente"


def test_armazenamento_salva_e_le(sintetica, tmp_path):
    art = _artefato(sintetica)
    caminho = armazenamento.salvar(art, tmp_path / "m.joblib")
    lido = armazenamento.carregar(caminho)
    assert lido.versao == modelo.VERSAO and lido.limiares == art.limiares
    assert armazenamento.carregar(tmp_path / "nao-existe.joblib") is None


def test_adaptador_do_backend(monkeypatch):
    from climasense.ml import risco_alagamento

    monkeypatch.setattr(armazenamento, "carregar_em_cache", lambda: None)
    r = risco_alagamento.risco_por_bairro(None, datetime(2026, 5, 10, tzinfo=UTC))
    assert set(r) >= {"disponivel", "motivo", "itens"} and r["disponivel"] is False


def test_router_declara_permissao():
    from climasense.api.routers import risco_alagamento

    rota = next(r for r in risco_alagamento.router.routes if r.path == "/risco-alagamento")
    deps = [d.call for d in rota.dependant.dependencies]
    assert any(hasattr(d, "permissao") for d in deps)
