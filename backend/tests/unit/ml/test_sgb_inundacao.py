"""Teste determinístico: sem rede e sem escrita em banco ou arquivos operacionais."""

from __future__ import annotations

import pandas as pd
import pytest
from shapely.geometry import box

from climasense.ml.alagamento.comparar_sgb import ler_sgb, preparar_base
from climasense.ml.alagamento.sgb_inundacao import cruzar_bairros, validar_feicoes


@pytest.mark.parametrize("corpo", [None, [], "indisponível", {"error": {"message": "erro do provedor"}}])
def test_resposta_sgb_invalida_tem_erro_controlado(corpo):
    from types import SimpleNamespace

    from climasense.ml.alagamento.sgb_inundacao import _resposta

    resposta = SimpleNamespace(raise_for_status=lambda: None, json=lambda: corpo)
    sessao = SimpleNamespace(get=lambda *args, **kwargs: resposta)
    with pytest.raises(RuntimeError, match="resposta inválida ou erro REST"):
        _resposta(sessao, "https://exemplo.test/query", {})


def _feature(oid, classe, geom, processo="Inundação", municipio="RECIFE"):
    from shapely.geometry import mapping

    return {
        "type": "Feature",
        "properties": {
            "objectid": oid,
            "uf": "PE",
            "municipio": municipio,
            "processo": processo,
            "classe": classe,
            "ano": 2015,
        },
        "geometry": mapping(geom),
    }


def test_intersecao_sem_dupla_contagem_e_ausencia_nao_zero():
    bairro = box(-35.00, -8.10, -34.99, -8.09)
    longe = box(-34.95, -8.10, -34.94, -8.09)
    # 50% alta, média começa em 30% e se sobrepõe à alta (20%).
    fonte = {
        "type": "FeatureCollection",
        "features": [
            _feature(1, "Alta", box(-35.00, -8.10, -34.995, -8.09)),
            _feature(2, "Média", box(-34.997, -8.10, -34.99, -8.09)),
            _feature(3, "Alta", box(-35.00, -8.10, -34.99, -8.09), "Deslizamento"),
            _feature(4, "Baixa", box(-35.00, -8.10, -34.99, -8.09), municipio="OLINDA"),
        ],
    }
    df, relatorio = cruzar_bairros(fonte, [("bairro-a", bairro), ("bairro-b", longe)])
    a = df.set_index("territorio_id").loc["bairro-a"]
    b = df.set_index("territorio_id").loc["bairro-b"]
    assert a.sgb_frac_alta == pytest.approx(0.5, abs=0.01)
    assert a.sgb_frac_media == pytest.approx(0.5, abs=0.01)
    assert a.sgb_cobertura == pytest.approx(1, abs=0.01)
    assert a.sgb_sem_carta == 0
    assert pd.isna(b.sgb_frac_alta)
    assert pd.isna(b.sgb_cobertura)
    assert b.sgb_sem_carta == 1
    assert relatorio["descartes"]["processo_nao_inundacao"] == 1
    assert relatorio["descartes"]["fora_recife"] == 1
    assert relatorio["sobreposicao_entre_classes_km2"] > 0


def test_sem_inundacao_deve_falhar():
    fonte = {
        "type": "FeatureCollection",
        "features": [
            _feature(1, "Alta", box(-35, -8.1, -34.99, -8.09), "Enxurrada"),
        ],
    }
    with pytest.raises(RuntimeError, match="INUNDAÇÃO"):
        validar_feicoes(fonte)


def test_csv_com_falta_nao_pode_ser_zero(tmp_path):
    csv = tmp_path / "sgb.csv"
    pd.DataFrame(
        [
            {
                "territorio_id": "bairro-a",
                "sgb_frac_alta": 0.0,
                "sgb_frac_media": 0.0,
                "sgb_cobertura": 0.0,
                "sgb_sem_carta": 1,
            },
            {
                "territorio_id": "bairro-b",
                "sgb_frac_alta": 0.5,
                "sgb_frac_media": 0.1,
                "sgb_cobertura": 0.6,
                "sgb_sem_carta": 0,
            },
        ]
    ).to_csv(csv, index=False)
    with pytest.raises(ValueError, match="NaN"):
        ler_sgb(csv)


def test_preparar_rejeita_malha_incompativel():
    b = pd.DataFrame(
        {
            "territorio_id": ["bairro-x"],
            "data": [pd.Timestamp("2023-01-01")],
            "alagou": [0],
        }
    )
    geo = pd.DataFrame({"territorio_id": ["bairro-y"], "sgb_sem_carta": [1]})
    with pytest.raises(ValueError, match="não coincidem"):
        preparar_base(b, geo)


def test_baixar_exige_filtro_municipal_e_paginacao():
    from climasense.ml.alagamento.sgb_inundacao import baixar_recife

    class FakeResp:
        def __init__(self, dados):
            self.dados = dados

        def raise_for_status(self):
            pass

        def json(self):
            return self.dados

    class FakeSession:
        chamadas = []

        def get(self, url, params, timeout):
            self.chamadas.append(params)
            if params["f"] == "json":
                return FakeResp({"objectIds": [101, 102]})
            return FakeResp(
                {
                    "type": "FeatureCollection",
                    "features": [
                        _feature(101, "Alta", box(-35, -8.1, -34.99, -8.09)),
                        _feature(102, "Média", box(-35, -8.1, -34.99, -8.09)),
                    ],
                }
            )

    session = FakeSession()
    saida = baixar_recife(session)
    assert len(saida["features"]) == 2
    assert session.chamadas[0]["where"] == "uf = 'PE' AND municipio = 'RECIFE'"
    assert session.chamadas[1]["objectIds"] == "101,102"


def test_comparacao_modelos_mesma_amostra_sem_escrita_remota():
    from climasense.ml.alagamento.base import ATRIBUTOS
    from climasense.ml.alagamento.comparar_sgb import comparar

    datas = pd.date_range("2016-01-01", "2024-12-01", freq="MS")
    linhas = []
    for i, dia in enumerate(datas):
        for j, bairro in enumerate(("bairro-a", "bairro-b")):
            linhas.append(
                {
                    "territorio_id": bairro,
                    "data": dia,
                    "ano": dia.year,
                    "registro": int(j == 0 and i % 5 == 0),
                    "alagou": int(j == 0 and i % 5 == 0),
                    "chuva_1d": float((i % 7) * 4 + j),
                    "chuva_3d": float((i % 7) * 8 + j),
                    "chuva_7d": float((i % 7) * 16 + j),
                    "mare_max_m": float(i % 3),
                    "mes": dia.month,
                    "hist_dias_ano": float(i // 12),
                }
            )
    base = pd.DataFrame(linhas)
    assert set(ATRIBUTOS).issubset(base.columns)
    base.attrs["janela_rotulo_dias"] = 0
    sgb = pd.DataFrame(
        [
            {
                "territorio_id": "bairro-a",
                "sgb_frac_alta": 0.5,
                "sgb_frac_media": 0.2,
                "sgb_cobertura": 0.8,
                "sgb_sem_carta": 0,
            },
            {
                "territorio_id": "bairro-b",
                "sgb_frac_alta": float("nan"),
                "sgb_frac_media": float("nan"),
                "sgb_cobertura": float("nan"),
                "sgb_sem_carta": 1,
            },
        ]
    )
    r = comparar(base, sgb)
    a = r["modelo_original_mesma_amostra"]
    b = r["modelo_com_sgb_mesma_amostra"]
    assert a["linhas_treino"] == b["linhas_treino"]
    assert a["linhas_teste"] == b["linhas_teste"]
    assert a["positivos_teste"] == b["positivos_teste"]
    assert 0 <= a["auc_pr_oof_treino"] <= 1
    assert 0 <= b["auc_pr_oof_treino"] <= 1
    assert r["status"] == "PESQUISA_LOCAL_NAO_VALIDADA"
