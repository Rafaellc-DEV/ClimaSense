"""População vulnerável por território (PRD §7.1, RF-02 a RF-04, RF-25). Domínio puro.

Só contagens agregadas por bairro (RN-13). Duas supressões: a do IBGE (célula oculta na origem, `pessoas` nulo com
`suprimido`) e a do projeto (contagem de 1 a `minimo - 1`, RNF-03). Zero medido continua zero (RN-02); campo sem
dado é nulo e nunca vira zero (RN-01). Contagem de pessoas residentes, não probabilidade (RN-06).
"""

from __future__ import annotations

from climasense.dominio.supressao import suprimir

# campo publicado -> faixa gravada pelo ETL em silver.populacao_bairro
CAMPOS: dict[str, str] = {
    "criancas_0_4": "0-4",
    "criancas_0_14": "0-14",
    "idosos_60_mais": "60+",
    "idosos_70_mais": "70+",
    "total": "total",
}
FALTA_DEFICIENCIA = "Dados insuficientes: não há dado público de deficiência por bairro (Censo 2022 só por área de ponderação)"
TOTAL_BAIRROS = 94

# faixa -> (pessoas, suprimido na origem)
Celulas = dict[str, tuple[int | None, bool]]


def publicar_bairro(celulas: Celulas | None, minimo: int) -> tuple[dict[str, int | None], dict[str, bool]]:
    """Valores publicáveis do bairro e a marca de supressão por campo (IBGE ou do projeto)."""
    valores: dict[str, int | None] = {}
    marcas: dict[str, bool] = {}
    for campo, faixa in CAMPOS.items():
        pessoas, ibge = (celulas or {}).get(faixa, (None, False))
        valor, projeto = suprimir(pessoas, minimo)
        valores[campo] = valor
        marcas[campo] = bool(ibge or projeto)
    return valores, marcas


def somar_bairros(bairros: list[Celulas | None]) -> dict[str, int | None]:
    """Soma de um distrito (ou do município) pelos valores reais dos bairros, que formam um agregado grande.
    Se algum bairro não tem o número (sem dado ou oculto pelo IBGE), o total fica nulo: soma parcial seria
    um número subestimado apresentado como completo (RN-01)."""
    saida: dict[str, int | None] = {}
    for campo, faixa in CAMPOS.items():
        partes = [(c or {}).get(faixa, (None, False))[0] for c in bairros]
        saida[campo] = None if not partes or any(p is None for p in partes) else sum(partes)
    return saida


def somar_publicados(valores: list[int | None]) -> tuple[int | None, bool]:
    """(soma dos números publicados, parcial). `parcial` = algum território ficou fora da soma por não ter número.
    Nenhum número publicado = nulo."""
    conhecidos = [v for v in valores if v is not None]
    if not conhecidos:
        return None, bool(valores)
    return sum(conhecidos), len(conhecidos) < len(valores)
