"""Cobertura futura, ausência de dados e repetição HTTP limitada, sem rede nem bancos."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from urllib3.response import HTTPResponse

from climasense.etl.conectores import comum
from climasense.etl.conectores.base import ExecucaoCtx, FonteSemDados
from climasense.etl.conectores.open_meteo import ConectorOpenMeteoMare, ConectorOpenMeteoPrevisao

AGORA = datetime(2026, 11, 13, 23, 15, tzinfo=UTC)


@pytest.mark.parametrize("classe", [ConectorOpenMeteoPrevisao, ConectorOpenMeteoMare])
def test_quatro_dias_de_calendario_cobrem_72_h_ate_o_final_do_dia(classe):
    c = classe()
    assert c.parametros_extra["forecast_days"] == 4
    inicio = AGORA.replace(hour=0, minute=0)
    horas = [inicio + timedelta(hours=h) for h in range(24 * c.parametros_extra["forecast_days"])]
    ctx = ExecucaoCtx("teste", None, None, None, AGORA)
    registros = [
        {"territorio_id": t, "hora_utc": h.isoformat(), "valor": 0.1} for t, _, _ in c.pontos() for h in horas
    ]
    df = c.transformar(pd.DataFrame(registros), ctx)
    c.validar(df, ctx)
    with pytest.raises(FonteSemDados, match="72 h"):
        c.validar(df[df.observado_em < inicio + timedelta(days=3)], ctx)


@pytest.mark.parametrize("valor", [None, float("inf"), float("nan"), -1])
def test_chuva_invalida_nao_vira_coleta_bem_sucedida(valor):
    c = ConectorOpenMeteoPrevisao()
    ctx = ExecucaoCtx("teste", None, None, None, AGORA)
    bruto = pd.DataFrame([{"territorio_id": "ds-1", "hora_utc": AGORA.isoformat(), "valor": valor}])
    df = c.transformar(bruto, ctx)
    assert pd.isna(df.valor.iloc[0])
    with pytest.raises(FonteSemDados):
        c.validar(df, ctx)


def test_retentativas_so_get_limite_e_retry_after_limitado():
    with comum.sessao_http() as http:
        politica = http.get_adapter("https://api.apac.pe.gov.br").max_retries
        assert politica.total == 2 and politica.allowed_methods == {"GET"}
        assert all(politica.is_retry("GET", status) for status in (429, 500, 502, 503, 504))
        assert not politica.is_retry("POST", 503) and not politica.is_retry("GET", 401)
        assert politica.get_retry_after(HTTPResponse(headers={"Retry-After": "3600"})) == 15


def test_operacional_bloqueia_remoto_antes_de_criar_engine(monkeypatch, capsys):
    from climasense.etl import __main__ as cli
    from tests.conftest import configuracao_teste

    config = configuracao_teste(
        database_url="postgresql://localhost/teste", mongo_uri="mongodb://exemplo.invalid"
    )
    monkeypatch.setattr(cli, "obter_configuracao", lambda: config)
    monkeypatch.setattr(cli, "engine_do_dono", lambda *a: pytest.fail("Abriu engine antes da aprovação"))
    assert cli.main(["operacional"]) == 2
    assert "aprovação prévia" in capsys.readouterr().err
