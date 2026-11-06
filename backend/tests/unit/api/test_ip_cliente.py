"""IP do cliente: X-Forwarded-For só vale vindo de proxy confiável (RNF-01, T0.4)."""

from __future__ import annotations

import ipaddress

import pytest

from climasense.api.autorizacao import resolver_ip
from climasense.config import Configuracao

PROXY = [ipaddress.ip_network("10.0.0.0/8")]


def test_sem_proxy_confiavel_o_cabecalho_e_ignorado():
    assert resolver_ip("203.0.113.9", "1.2.3.4", []) == "203.0.113.9"


def test_cabecalho_de_quem_nao_e_proxy_confiavel_e_ignorado():
    assert resolver_ip("203.0.113.9", "1.2.3.4", PROXY) == "203.0.113.9"


def test_proxy_confiavel_entrega_o_ip_do_cliente():
    assert resolver_ip("10.0.0.5", "198.51.100.7", PROXY) == "198.51.100.7"


def test_ip_forjado_a_esquerda_nao_vale():
    # o cliente mandou "9.9.9.9"; o proxy acrescentou o IP real à direita
    assert resolver_ip("10.0.0.5", "9.9.9.9, 198.51.100.7", PROXY) == "198.51.100.7"


def test_cadeia_de_proxies_confiaveis():
    assert resolver_ip("10.0.0.5", "198.51.100.7, 10.1.1.1", PROXY) == "198.51.100.7"


def test_cabecalho_malformado_cai_no_ip_do_soquete():
    assert resolver_ip("10.0.0.5", "nao-e-ip", PROXY) == "10.0.0.5"


@pytest.mark.parametrize("host", [None, "testclient", ""])
def test_host_invalido_vira_none(host):
    assert resolver_ip(host, "1.2.3.4", PROXY) is None


def test_ipv6_e_normalizado():
    assert resolver_ip("2001:DB8::1", None, []) == "2001:db8::1"


def test_configuracao_aceita_lista_e_recusa_lixo():
    c = Configuracao(_env_file=None, proxies_confiaveis="10.0.0.0/8, 192.168.1.1")
    assert [str(r) for r in c.redes_proxy] == ["10.0.0.0/8", "192.168.1.1/32"]
    assert Configuracao(_env_file=None).proxies_confiaveis == []
    with pytest.raises(ValueError, match="PROXIES_CONFIAVEIS"):
        Configuracao(_env_file=None, proxies_confiaveis="nao-e-ip")
