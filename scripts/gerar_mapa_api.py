"""Gera o MAPA INTERNO DA API (docs/api-gestao.md) a partir do OpenAPI da própria aplicação.

Para cada rota: método, caminho, papel mínimo (lido das dependências `exige(...)`), telas do frontend que a
chamam (varredura de frontend/src pelas strings de caminho), formato da resposta (envelope `dados/meta` ou
direto), exemplo gerado do esquema e notas (parâmetros e descrição).

É reproduzível e não sobe servidor: usa `app.openapi()` em memória.
Uso:  .venv\\Scripts\\python scripts/gerar_mapa_api.py        (a partir da raiz do repositório)
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
warnings.filterwarnings("ignore")

from climasense.api.autorizacao import contexto_autenticado
from climasense.api.main import PREFIXO, ROTEADORES, app
from climasense.dominio.papeis import PERMISSOES, Papel

SAIDA = RAIZ / "docs" / "api-gestao.md"
FRONT = RAIZ / "frontend" / "src"
IGNORAR = ("api-tipos.ts",)
ACOES_FLUXO = {"enviar", "aprovar", "devolver", "publicar", "encerrar"}
ROTULO_PAPEL = {
    Papel.ANALISTA: "analista",
    Papel.REVISOR: "revisor",
    Papel.COORDENACAO: "coordenação",
    Papel.ADMINISTRADOR: "administrador",
}


def papel_minimo(permissao) -> str:
    for papel in Papel:  # ordem: analista < revisor < coordenação < administrador
        if permissao in PERMISSOES[papel]:
            return ROTULO_PAPEL[papel]
    return "administrador"


def papeis_das_rotas() -> dict[tuple[str, str], str]:
    mapa: dict[tuple[str, str], str] = {}
    for roteador in ROTEADORES:
        for rota in roteador.routes:
            deps = [d.call for d in rota.dependant.dependencies]
            permissao = next(
                (
                    getattr(d, "permissao", None)
                    for d in deps
                    if hasattr(d, "permissao")
                ),
                None,
            )
            if permissao is not None:
                papel = papel_minimo(permissao)
            elif contexto_autenticado in deps:
                papel = "qualquer conta autenticada"
            else:
                papel = "público"
            for metodo in rota.methods:
                mapa[(metodo, PREFIXO + rota.path)] = papel
    return mapa


# ------------------------------------------------------------------ telas que usam a rota
def arquivos_front() -> dict[Path, str]:
    resultado = {}
    for caminho in FRONT.rglob("*"):
        if (
            caminho.suffix not in (".ts", ".tsx")
            or caminho.name in IGNORAR
            or ".test." in caminho.name
        ):
            continue
        resultado[caminho] = caminho.read_text(encoding="utf-8", errors="ignore")
    return resultado


def tela_de(caminho: Path) -> str:
    partes = caminho.relative_to(FRONT).parts
    return (
        f"{partes[0]}/{partes[1]}"
        if partes[0] == "features" and len(partes) > 2
        else partes[0]
    )


def regex_do_caminho(caminho: str) -> re.Pattern:
    relativo = caminho.removeprefix(PREFIXO)
    segmentos = [
        r"[^/\"'`]+" if s.startswith("{") else re.escape(s)
        for s in relativo.split("/")[1:]
    ]
    return re.compile(r"[\"'`]/" + "/".join(segmentos) + r"(?![A-Za-z0-9_./-])")


def telas_que_usam(caminho: str, arquivos: dict[Path, str]) -> list[str]:
    padrao = regex_do_caminho(caminho)
    # um caminho curto (ex.: /series) não deve casar com /series/referencia: o lookahead acima já impede
    telas = {tela_de(p) for p, texto in arquivos.items() if padrao.search(texto)}
    # ações do fluxo de revisão são chamadas por `${base}/${acao}` (AcoesFluxo)
    if caminho.rsplit("/", 1)[-1] in ACOES_FLUXO:
        telas |= {
            tela_de(p) for p, texto in arquivos.items() if "${base}/${acao}" in texto
        }
    return sorted(telas)


# ------------------------------------------------------------------ exemplos a partir do esquema
def resolver(esquema: dict, spec: dict) -> dict:
    while "$ref" in esquema:
        esquema = spec["components"]["schemas"][esquema["$ref"].rsplit("/", 1)[-1]]
    return esquema


def exemplo(esquema: dict, spec: dict, profundidade: int = 0):
    esquema = resolver(esquema, spec)
    if "anyOf" in esquema:
        opcoes = [o for o in esquema["anyOf"] if o.get("type") != "null"]
        return exemplo(opcoes[0], spec, profundidade) if opcoes else None
    if "example" in esquema:
        return esquema["example"]
    if "enum" in esquema:
        return esquema["enum"][0]
    if "const" in esquema:
        return esquema["const"]
    tipo = esquema.get("type")
    if tipo == "object" or "properties" in esquema:
        if profundidade > 4:
            return {}
        return {
            k: exemplo(v, spec, profundidade + 1)
            for k, v in esquema.get("properties", {}).items()
        }
    if tipo == "array":
        return (
            []
            if profundidade > 4
            else [exemplo(esquema.get("items", {}), spec, profundidade + 1)]
        )
    fmt = esquema.get("format")
    if tipo == "string":
        return {
            "date-time": "2026-10-15T20:00:00Z",
            "date": "2026-10-15",
            "uuid": "00000000-0000-0000-0000-000000000000",
        }.get(fmt, "texto")
    if tipo in ("integer", "number"):
        return 0 if tipo == "integer" else 0.0
    if tipo == "boolean":
        return True
    return None


def nome_resposta(operacao: dict, spec: dict) -> tuple[str, dict | None]:
    resposta = operacao.get("responses", {}).get("200") or operacao.get(
        "responses", {}
    ).get("201")
    if not resposta:
        return "sem corpo", None
    conteudo = resposta.get("content", {})
    if "application/json" not in conteudo:
        tipo = next(iter(conteudo), "sem corpo")
        return tipo, None
    esquema = conteudo["application/json"].get("schema", {})
    resolvido = resolver(esquema, spec)
    props = resolvido.get("properties", {})
    if "dados" in props and "meta" in props:
        return "envelope `{dados, meta}`", esquema
    if esquema.get("type") == "array":
        return "lista direta", esquema
    return "objeto direto", esquema


def parametros(operacao: dict) -> str:
    itens = []
    for p in operacao.get("parameters", []):
        marca = "*" if p.get("required") else ""
        itens.append(f"`{p['name']}{marca}`")
    return ", ".join(itens)


def cortar(texto: str, limite: int = 1400) -> str:
    return texto if len(texto) <= limite else texto[:limite] + "\n  ...(cortado)"


def gerar() -> str:
    spec = app.openapi()
    papeis = papeis_das_rotas()
    arquivos = arquivos_front()
    linhas = [
        "# Mapa interno da API de gestão",
        "",
        "> Gerado por `scripts/gerar_mapa_api.py` a partir do OpenAPI da aplicação. Não edite à mão: rode o script.",
        (
            f"> Versão da API: {spec['info']['version']}. Prefixo: `{PREFIXO}`. Cookies `cs_sessao` e `cs_csrf`;"
            " métodos que alteram dados exigem o cabeçalho `X-CSRF-Token`."
        ),
        "",
        (
            "Convenções: o envelope `{dados, meta}` traz fontes, recorte, cobertura, amostra, avisos e"
            " `dados_insuficientes` (RN-01: sem dado nunca vira zero). Erros seguem `application/problem+json`"
            " com `title` e `detail` prontos para a tela. Datas em UTC (ISO 8601). `*` marca parâmetro obrigatório."
        ),
        "",
        "## Resumo",
        "",
        "| Método | Caminho | Papel mínimo | Telas que usam | Resposta |",
        "|---|---|---|---|---|",
    ]
    por_tag: dict[str, list[tuple[str, str, dict]]] = {}
    for caminho, itens in spec["paths"].items():
        for metodo, operacao in itens.items():
            m = metodo.upper()
            tag = (operacao.get("tags") or ["Outros"])[0]
            por_tag.setdefault(tag, []).append((m, caminho, operacao))
            telas = ", ".join(telas_que_usam(caminho, arquivos)) or "(nenhuma ainda)"
            forma, _ = nome_resposta(operacao, spec)
            linhas.append(
                f"| {m} | `{caminho}` | {papeis.get((m, caminho), '?')} | {telas} | {forma} |"
            )
    linhas += ["", "## Detalhe por grupo", ""]
    for tag, rotas in por_tag.items():
        linhas += [f"### {tag}", ""]
        for m, caminho, operacao in rotas:
            forma, esquema = nome_resposta(operacao, spec)
            linhas.append(f"#### `{m} {caminho}`")
            linhas.append("")
            linhas.append(f"- **Resumo:** {operacao.get('summary', '')}")
            linhas.append(f"- **Papel mínimo:** {papeis.get((m, caminho), '?')}")
            telas = ", ".join(telas_que_usam(caminho, arquivos)) or "nenhuma ainda"
            linhas.append(f"- **Telas que usam:** {telas}")
            linhas.append(f"- **Resposta:** {forma}")
            if parametros(operacao):
                linhas.append(f"- **Parâmetros:** {parametros(operacao)}")
            if operacao.get("description"):
                linhas.append(f"- **Notas:** {operacao['description'].strip()}")
            if esquema is not None:
                corpo = json.dumps(exemplo(esquema, spec), ensure_ascii=False, indent=2)
                linhas += [
                    "- **Exemplo (gerado do esquema, valores ilustrativos):**",
                    "",
                    "  ```json",
                ]
                linhas += ["  " + linha for linha in cortar(corpo).splitlines()]
                linhas += ["  ```"]
            linhas.append("")
    return "\n".join(linhas).rstrip() + "\n"


if __name__ == "__main__":
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(gerar(), encoding="utf-8", newline="\n")
    print(f"Escrito {SAIDA.relative_to(RAIZ)}")
