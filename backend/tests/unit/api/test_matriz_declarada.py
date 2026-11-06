"""Matriz de autorização, parte que não precisa de banco: toda rota declara o papel mínimo (ou é pública).
A parte que exercita cada papel contra o banco está em tests/integration/test_matriz_autorizacao.py."""

from __future__ import annotations

from climasense.dominio.papeis import Permissao
from tests.integration.test_matriz_autorizacao import PUBLICAS, ROTAS

ESPERADAS = {
    ("GET", "/api/v1/painel/situacao"): Permissao.CONSULTAR,
    ("GET", "/api/v1/painel/acoes"): Permissao.CONSULTAR,
    ("GET", "/api/v1/painel/resumo"): Permissao.CONSULTAR,
    ("GET", "/api/v1/territorios/prioridades"): Permissao.CONSULTAR,
    ("POST", "/api/v1/comunicados/{comunicado_id}/publicar"): Permissao.PUBLICAR,
    ("POST", "/api/v1/avaliacoes/{avaliacao_id}/aprovar"): Permissao.REVISAR,
    ("GET", "/api/v1/admin/auditoria"): Permissao.ADMINISTRAR,
    ("POST", "/api/v1/admin/login/liberar"): Permissao.ADMINISTRAR,
    # evento de chuva (specs/foco-chuvas.md): consultar todos; registrar e declarar = editar;
    # limiares só coordenação e administrador
    ("GET", "/api/v1/estagios"): Permissao.CONSULTAR,
    ("POST", "/api/v1/estagios"): Permissao.EDITAR,
    ("GET", "/api/v1/estagios/parametros"): Permissao.CONSULTAR,
    ("PUT", "/api/v1/estagios/parametros"): Permissao.PARAMETRIZAR,
    ("POST", "/api/v1/estagios/mensagem"): Permissao.CONSULTAR,
    ("POST", "/api/v1/abrigos"): Permissao.EDITAR,
    ("PATCH", "/api/v1/abrigos/{abrigo_id}"): Permissao.EDITAR,
    ("POST", "/api/v1/acoes"): Permissao.EDITAR,
    ("PATCH", "/api/v1/acoes/{acao_id}"): Permissao.EDITAR,
    ("GET", "/api/v1/boletim"): Permissao.CONSULTAR,
}


def test_so_coordenacao_e_administrador_alteram_limiares():
    from climasense.dominio.papeis import pode

    assert [
        p
        for p in ("analista", "revisor", "coordenacao", "administrador")
        if pode([p], Permissao.PARAMETRIZAR)
    ] == [
        "coordenacao",
        "administrador",
    ]


def test_toda_rota_declara_papel_ou_e_publica():
    soltas = [(m, p) for m, p, perm, aut in ROTAS if perm is None and not aut and (m, p) not in PUBLICAS]
    assert not soltas, f"Rotas sem exige(...) nem contexto_autenticado: {soltas}"


def test_rotas_novas_e_criticas_tem_o_papel_minimo_esperado():
    declaradas = {(m, p): perm for m, p, perm, _ in ROTAS}
    for rota, permissao in ESPERADAS.items():
        assert declaradas.get(rota) == permissao, rota


def test_rotas_publicas_sao_so_as_da_landing():
    assert all(
        p.startswith(("/api/v1/publico/", "/api/v1/health", "/api/v1/auth/entrar")) for _, p in PUBLICAS
    )
