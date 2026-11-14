"""Regressões da versão corrigida. Dados artificiais exclusivamente nos testes."""

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest

from climasense.ml.alagamento import armazenamento, base, modelo, ocorrencias, servico
from tests.unit.ml.test_alagamento import _artefato, _base_sintetica, _chuva_fake


def test_cache_do_estudo_descarta_endereco_sem_alterar_rotulos():
    from tests.unit.ml.test_alagamento import LINHAS, _csv

    bruto = _csv(*LINHAS)
    sanitizado = ocorrencias.csv_sanitizado(bruto)
    assert b"Rua" not in sanitizado and b"Endereco" not in sanitizado
    assert list(ocorrencias.ler_registros(bruto)) == list(ocorrencias.ler_registros(sanitizado))


def test_cli_fonte_indisponivel_nao_salva_artefato_ou_relatorio(monkeypatch, capsys):
    import requests

    from climasense.ml import __main__ as cli
    from climasense.ml.alagamento import estudo

    def falhar(**kwargs):
        resposta = requests.Response()
        resposta.status_code = 503
        raise requests.HTTPError(response=resposta)

    monkeypatch.setattr(estudo, "executar", falhar)
    monkeypatch.setattr(estudo, "salvar", lambda *a: pytest.fail("Salvou estudo interrompido"))
    assert cli.main(["alagamento", "--sem-banco"]) == 1
    assert "HTTP 503" in capsys.readouterr().err


@pytest.fixture(scope="module")
def estudo_sintetico():
    return _base_sintetica()


@pytest.fixture(scope="module")
def art(estudo_sintetico):
    return _artefato(estudo_sintetico)


def test_equivalencia_classes_pontuacoes_e_metricas(art, estudo_sintetico, tmp_path):
    tabela, _ = estudo_sintetico
    _, teste = modelo.dividir(tabela, 2022)
    antes = modelo.pontuar(art.modelo, teste, art.atributos)
    lido = armazenamento.carregar(armazenamento.salvar(art, tmp_path / "modelo.joblib"))
    depois = modelo.pontuar(lido.modelo, teste, lido.atributos)
    np.testing.assert_allclose(antes, depois, rtol=0, atol=0)
    a, b = modelo.classificar(antes, art.limiares), modelo.classificar(depois, lido.limiares)
    np.testing.assert_array_equal(a, b)
    assert modelo.metricas(teste.alagou, a != "baixo", antes) == modelo.metricas(
        teste.alagou, b != "baixo", depois
    )
    assert lido.ambiente == art.ambiente and lido.versao_atributos == base.VERSAO_ATRIBUTOS
    assert lido.modelo.get_params() == art.modelo.get_params()


def test_artefato_conta_so_registros_reais_do_treino(art, estudo_sintetico):
    tabela, _ = estudo_sintetico
    treino, teste = modelo.dividir(tabela, 2022)
    for b in art.territorios:
        real = treino[(treino.territorio_id == b) & (treino.registro == 1)]
        assert art.historico_bairros.get(b, 0) == len(real)
        assert all(d < teste.data.min().date().isoformat() for d in art.dias_atendimento_bairros.get(b, []))


def test_paridade_features_janela_expandida_e_dia_futuro():
    dias = pd.date_range("2022-01-01", periods=12)
    chuva = pd.DataFrame({"territorio_id": "ds-1", "data": dias, "mm": np.arange(12, dtype=float)})
    rot = pd.DataFrame({"territorio_id": "b", "data": [dias[3], dias[10]]})
    tabela = base.montar_base(rot, chuva, pd.Series(1.2, index=dias), {"b": "ds-1"}, dias[0], dias[-1], 3)
    dia = dias[8].date()
    x = base.atributos_diarios(
        dict(zip(dias.date, chuva.mm, strict=True)),
        dia,
        1.2,
        [d.date().isoformat() for d in rot.data],
        str(dias[0].date()),
    )
    assert list(x) == base.ATRIBUTOS
    assert all(isinstance(v, float) for v in x.values())
    np.testing.assert_allclose(list(x.values()), tabela[tabela.data == dias[8]][base.ATRIBUTOS].iloc[0])
    assert x["hist_dias_ano"] == 1.0  # futuro e os positivos expandidos não contam


def test_intervalo_de_seguranca_treino_teste_e_folds(estudo_sintetico):
    tabela, _ = estudo_sintetico
    treino, teste = modelo.dividir(tabela, 2022, janela_dias=3)
    assert treino.data.max() + pd.Timedelta(days=3) < teste.data.min()
    for tr, va in modelo.folds_temporais(treino):
        assert treino.loc[tr].data.max() + pd.Timedelta(days=3) < treino.loc[va].data.min()
    assert teste.data.max() == tabela.data.max() - pd.Timedelta(days=3)


def test_artefato_nao_conta_dias_expandidos_no_historico(estudo_sintetico, art):
    from tests.unit.ml.test_alagamento import CONJUNTOS_PEQUENOS, GRADE_PEQUENA

    tabela, rot = estudo_sintetico
    tabela = tabela.copy()
    tabela["alagou"] = base.rotulo_com_janela(rot, tabela, 3)
    tabela.attrs["janela_rotulo_dias"] = 3
    r = modelo.treinar(tabela, grade=GRADE_PEQUENA, conjuntos=CONJUNTOS_PEQUENOS, ano_teste=2022)
    novo = modelo.montar_artefato(r, tabela, art.mare_harmonicos, "teste")
    treino, _ = modelo.dividir(tabela, 2022)
    assert treino.alagou.sum() > treino.registro.sum()
    assert sum(novo.historico_bairros.values()) == treino.registro.sum()
    assert r.janela_dias == 3


def test_gate_rejeita_metricas_nao_finitas():
    perf = {"treino": {"positivos": 500}, "teste": {"positivos": 100}}
    ok, motivo = modelo.avaliar_publicacao(
        perf, {"modelo": {"recall": float("nan"), "auc_pr": float("nan")}, "limiar_chuva": {"auc_pr": 0.05}}
    )
    assert not ok and "inválidas" in motivo


def test_artefato_retrospectivo_nao_herda_publicacao(estudo_sintetico, art):
    tabela, _ = estudo_sintetico
    # A rotina de treino usa o gate estatístico original; o artefato exige validação operacional.
    from tests.unit.ml.test_alagamento import CONJUNTOS_PEQUENOS, GRADE_PEQUENA

    r = modelo.treinar(tabela, grade=GRADE_PEQUENA, conjuntos=CONJUNTOS_PEQUENOS, ano_teste=2022)
    novo = modelo.montar_artefato(r, tabela, art.mare_harmonicos, "teste")
    assert r.publicavel and not novo.publicavel
    assert "retrospectiva" in novo.motivo


def test_arquivo_invalido_legado_e_ordem_errada_nao_carregam(art, tmp_path):
    import copy

    p = tmp_path / "modelo.joblib"
    p.write_bytes(b"arquivo invalido")
    assert armazenamento.carregar(p) is None
    legado = copy.deepcopy(art)
    del legado.__dict__["versao_atributos"]
    assert armazenamento.carregar(armazenamento.salvar(legado, p)) is None
    errado = copy.deepcopy(art)
    errado.atributos = list(reversed(errado.atributos))
    assert not armazenamento.compativel(errado)
    sem_validacao = copy.deepcopy(art)
    sem_validacao.validacao["avaliacao_operacional"] = False
    assert not armazenamento.compativel(sem_validacao)
    reprovado = copy.deepcopy(art)
    reprovado.validacao["metricas_teste"]["modelo"]["auc_pr"] = 0.0
    assert not armazenamento.compativel(reprovado)
    sem_metadados = copy.deepcopy(art)
    sem_metadados.validacao = None
    assert not armazenamento.compativel(sem_metadados)


@pytest.mark.parametrize("faltante", [None, float("nan"), float("inf"), -1])
def test_feature_ausente_ou_invalida_nao_vira_zero(faltante):
    chuva = {d.date(): 0.0 for d in pd.date_range("2026-01-01", periods=7)}
    chuva[date(2026, 1, 7)] = faltante
    assert base.atributos_diarios(chuva, date(2026, 1, 7), 1.0, [], "2014-01-01") is None


def test_chuva_duplicada_nao_completa_dia():
    chuva = _chuva_fake({"ds-1": {pd.Timestamp("2026-05-01"): 24}})
    chuva = pd.concat([chuva.iloc[:23], chuva.iloc[:1]])
    assert servico.chuva_por_dia(chuva) == {}


@pytest.mark.parametrize("invalido", [-1, float("inf"), float("nan"), None, "invalido"])
def test_hora_invalida_nao_e_mascarada_por_soma_diaria(invalido):
    from climasense.ml.alagamento.clima import chuva_diaria

    chuva = _chuva_fake({"ds-1": {pd.Timestamp("2026-05-01"): 24}})
    chuva["mm"] = chuva["mm"].astype(object)
    chuva.loc[0, "mm"] = invalido
    assert servico.chuva_por_dia(chuva) == {}
    assert chuva_diaria(chuva).empty


def test_inferencia_sem_fit_e_territorio_desconhecido(art, monkeypatch):
    monkeypatch.setattr(type(art.modelo), "fit", lambda *a, **k: pytest.fail("Treinamento na inferência"))
    dias = pd.date_range("2026-05-04", "2026-05-11")
    h = _chuva_fake({"ds-1": {d: 40.0 for d in dias}})
    monkeypatch.setattr(servico, "chuva_recente", lambda *a: h)
    monkeypatch.setattr(servico, "bairros", lambda _: {"bairro-a": ("A", "ds-1"), "bairro-x": ("X", "ds-99")})
    r = servico.risco_por_territorio(None, datetime(2026, 5, 10, 15, tzinfo=UTC), art)
    assert r["bairro-x"]["classe"] == "sem_dados"
    assert r["bairro-a"]["classe"] != "sem_dados"
    assert "posterior ao treino" in " ".join(r["bairro-a"]["fatores"])


def test_dia_parcial_nao_esconde_falta_de_amanha(art, monkeypatch):
    dias = pd.date_range("2026-05-04", "2026-05-10")
    monkeypatch.setattr(servico, "chuva_recente", lambda *a: _chuva_fake({"ds-1": {d: 20.0 for d in dias}}))
    monkeypatch.setattr(servico, "bairros", lambda _: {"bairro-a": ("A", "ds-1")})
    r = servico.risco_por_territorio(None, datetime(2026, 5, 10, 15, tzinfo=UTC), art)
    assert r["bairro-a"]["classe"] == "sem_dados"
