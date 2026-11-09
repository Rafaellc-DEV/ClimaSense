"""F2, F3, F4 e F5 no domínio: mensagem de WhatsApp, ações e texto do boletim."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from climasense.dominio import acoes, mensagem
from climasense.dominio.evento import RegistroInvalido

AGORA = datetime(2026, 11, 4, 18, 30, tzinfo=UTC)  # 15:30 no Recife


# ---------------------------------------------------------------- F2 mensagem
def test_mensagem_padronizada_em_portugues_com_hora_do_recife():
    t = mensagem.mensagem_estagio(
        "alerta", ["Distrito Sanitário IV", "Afogados"], AGORA, "Chuva  forte\nà tarde"
    )
    linhas = t.splitlines()
    assert linhas[0] == "*ClimaSense · Vigidesastres*"
    assert "Estágio: *ALERTA*" in t
    assert "Territórios: Distrito 4, Afogados" in t
    assert "Motivo: Chuva forte à tarde" in t  # espaços e quebras normalizados
    assert "Hora: 04/11/2026 15:30" in t
    assert "O que fazer: " in t and linhas[-1] == mensagem.ASSINATURA
    assert "APAC" in t and "Cemaden" in t


def test_mensagem_sem_justificativa_nao_tem_motivo_e_lista_longa_e_resumida():
    nomes = [f"Bairro {i}" for i in range(15)]
    t = mensagem.mensagem_estagio("atencao", nomes, AGORA)
    assert "Motivo:" not in t
    assert "e mais 5" in t and "Bairro 10" not in t


def test_wa_me_url_codifica_o_texto_inteiro():
    t = mensagem.mensagem_estagio("critico", ["Recife"], AGORA, "Maré & chuva #1")
    url = mensagem.wa_me_url(t)
    assert url.startswith("https://wa.me/?text=")
    assert " " not in url and "\n" not in url and "&" not in url.split("?", 1)[1]
    assert parse_qs(urlparse(url).query)["text"][0] == t


def test_numero_ausente_nao_vira_zero():
    assert mensagem.numero(None, "mm") == "sem dado"
    assert mensagem.numero(0.0, "mm") == "0,0 mm"
    assert mensagem.numero(12.345, "m", 2) == "12,35 m"  # vírgula decimal (RN-16)


def test_texto_do_boletim():
    t = mensagem.texto_boletim(
        "Recife",
        AGORA,
        [("Distrito Sanitário I", "alerta", "declarado"), ("Distrito Sanitário II", "sem_dados", "sugerido")],
        {
            "chuva_24h": (None, None),
            "chuva_prev_24h": (42.0, "Distrito Sanitário I"),
            "chuva_prev_72h": (80.5, "DS I"),
        },
        (1.2, AGORA + timedelta(hours=2)),
        3,
        acoes_concluidas=0,
        saude=[{"nome": "Dengue", "casos": None, "ultima_semana": None}],
    )
    assert "- Distrito 1: Alerta (declarado)" in t
    assert "- Distrito 2: Sem dados (sugerido)" in t
    assert "- Últimas 24 h: sem dado" in t
    assert "- Prevista 24 h: 42,0 mm (maior: Distrito 1)" in t
    assert "Maré máxima: 1,20 m às 04/11 17:30" in t
    assert "Estágio oficial do COP (cidade): sem registro" in t
    assert "Ações em andamento: 3" in t and "Ações concluídas no período: 0" in t
    assert "- Dengue: sem dado caso(s)" in t


# ---------------------------------------------------------------- F4 ações
def test_transicoes_de_acao():
    acoes.validar_transicao("planejada", "em_andamento")
    acoes.validar_transicao("em_andamento", "concluida")
    acoes.validar_transicao("concluida", "concluida")  # sem mudança é permitido
    with pytest.raises(RegistroInvalido) as e:
        acoes.validar_transicao("concluida", "em_andamento")
    assert e.value.status == 409
    with pytest.raises(RegistroInvalido):
        acoes.validar_tipo("festa")


def test_horarios_preenchidos_ao_mudar_situacao():
    assert acoes.horarios("em_andamento", None, None, AGORA) == (AGORA, None)
    inicio = AGORA - timedelta(hours=2)
    assert acoes.horarios("concluida", inicio, None, AGORA) == (inicio, AGORA)
    assert acoes.horarios("cancelada", None, None, AGORA) == (None, AGORA)
    with pytest.raises(RegistroInvalido):
        acoes.horarios("concluida", AGORA, AGORA - timedelta(hours=1), AGORA)


def test_licao_aprendida_so_ao_encerrar():
    acoes.validar_licao("concluida", "Avisar a escola mais cedo.")
    acoes.validar_licao("em_andamento", None)
    with pytest.raises(RegistroInvalido):
        acoes.validar_licao("em_andamento", "cedo demais")
