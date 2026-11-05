"""Estágio operacional por território (F1, specs/foco-chuvas.md). Domínio puro, sem I/O.

O sistema SUGERE um estágio a partir de limiares configuráveis; quem DECLARA é uma pessoa (a sugestão nunca muda
o estágio sozinha). Regras:

1. cada gatilho de chuva (últimas 24 h, prevista 24 h, prevista 72 h) dá um nível pelos limiares de atenção,
   alerta e crítico; o estágio-base é o maior deles (sem nenhum gatilho → observação);
2. maré alta (≥ `mare_alta_m`) a até `mare_janela_h` horas do pico de chuva sobe um nível, a partir de atenção;
3. histórico de alagamento do bairro (≥ `ocorrencias_bairro_minimo` ocorrências) sobe um nível, a partir de
   atenção;
4. o risco do modelo de ML (F6, experimental) só pode subir o estágio, nunca baixar, e só entra se existir;
5. faltando a previsão de chuva ou a maré → `sem_dados` (RN-01). Os gatilhos que dispararam com o que havia
   continuam nos motivos, para a equipe não perder um sinal real.

Estágio não é probabilidade de alagar (RN-06). Os limiares padrão são uma proposta a validar com a equipe (P5).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
from typing import Literal

Estagio = Literal["sem_dados", "observacao", "atencao", "alerta", "critico"]
ESCADA: tuple[Estagio, ...] = ("observacao", "atencao", "alerta", "critico")
DECLARAVEIS = ESCADA  # “sem dados” é estado do sistema, não decisão de alguém
# Encerrar também é decisão de alguém: nova linha no histórico (que é só de inclusão) que faz o território voltar
# a “sem declaração”. Não entra na escada nem vira sugestão.
ENCERRADO = "encerrado"
ROTULO: dict[str, str] = {
    "sem_dados": "Sem dados",
    "observacao": "Observação",
    "atencao": "Atenção",
    "alerta": "Alerta",
    "critico": "Crítico",
    "encerrado": "Encerrado",
}
# horas mínimas de previsão para somar uma janela: a previsão vem com 3 dias corridos, então as 72 h a partir
# de agora quase nunca estão completas (o que falta fica dito nos motivos)
MIN_HORAS_PREVISAO = {24: 22, 72: 48}
# classes do modelo de ML (F6) → estágio mínimo que elas indicam; classes baixas não rebaixam nada
CLASSE_ML: dict[str, Estagio] = {
    "moderado": "atencao",
    "medio": "atencao",
    "media": "atencao",
    "alto": "alerta",
    "muito_alto": "critico",
    "muito alto": "critico",
}


@dataclass(frozen=True)
class Parametros:
    """Limiares editáveis pela coordenação (proposta inicial, a validar com a Vigilância, P5)."""

    chuva_24h_atencao_mm: float = 25.0
    chuva_24h_alerta_mm: float = 50.0
    chuva_24h_critico_mm: float = 90.0
    chuva_prev_24h_atencao_mm: float = 25.0
    chuva_prev_24h_alerta_mm: float = 50.0
    chuva_prev_24h_critico_mm: float = 90.0
    chuva_prev_72h_atencao_mm: float = 60.0
    chuva_prev_72h_alerta_mm: float = 100.0
    chuva_prev_72h_critico_mm: float = 150.0
    mare_alta_m: float = 0.6  # acima do nível médio do mar (mesmo limite da regra de cenários)
    mare_janela_h: float = 3.0
    ocorrencias_bairro_minimo: float = 3.0

    def como_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def de_dict(cls, valores: dict) -> Parametros:
        """Campos desconhecidos são ignorados; os ausentes ficam com o padrão."""
        nomes = {f.name for f in fields(cls)}
        return cls(**{k: float(v) for k, v in valores.items() if k in nomes and v is not None})


GATILHOS_CHUVA = (
    ("chuva_24h", "Chuva das últimas 24 h"),
    ("chuva_prev_24h", "Chuva prevista nas próximas 24 h"),
    ("chuva_prev_72h", "Chuva prevista nas próximas 72 h"),
)


def problemas_parametros(p: Parametros) -> list[str]:
    """Erros que impedem salvar os limiares, em linguagem simples."""
    erros = []
    for chave, nome in GATILHOS_CHUVA:
        a, b, c = (getattr(p, f"{chave}_{n}_mm") for n in ("atencao", "alerta", "critico"))
        if min(a, b, c) <= 0:
            erros.append(f"{nome}: os limites precisam ser maiores que zero.")
        elif not a < b < c:
            erros.append(
                f"{nome}: o limite de atenção precisa ser menor que o de alerta, e este menor que o crítico."
            )
    if p.mare_alta_m <= 0:
        erros.append("A maré alta precisa ser maior que zero.")
    if not 0 < p.mare_janela_h <= 24:
        erros.append("A janela entre maré e pico de chuva precisa ficar entre 1 e 24 horas.")
    if p.ocorrencias_bairro_minimo < 1:
        erros.append("O mínimo de ocorrências do bairro precisa ser pelo menos 1.")
    return erros


@dataclass(frozen=True)
class Insumos:
    chuva_24h_mm: float | None = None  # últimas 24 h (reanálise ou horas já passadas da previsão)
    chuva_prev_24h_mm: float | None = None
    chuva_prev_72h_mm: float | None = None
    horas_previstas_72h: int | None = None
    pico_chuva_em: datetime | None = None
    mare_max_m: float | None = None  # máxima das próximas 72 h
    mare_max_em: datetime | None = None
    mare_no_pico_m: float | None = None  # máxima perto do pico de chuva
    risco_ml: str | None = None  # classe do modelo F6; None = modelo não publicado
    ocorrencias_historicas: int | None = None  # só bairro; None = fonte sem carga
    herdado_de: str | None = None  # bairro herda a chuva e a maré do distrito (RN-07)

    def como_dict(self) -> dict:
        return asdict(self)


@dataclass
class Sugestao:
    estagio: Estagio
    motivos: list[str] = field(default_factory=list)
    faltando: list[str] = field(default_factory=list)


def _mm(v: float) -> str:
    return f"{v:.1f}".replace(".", ",") + " mm"


def _m(v: float) -> str:
    return f"{v:.2f}".replace(".", ",") + " m"


def subir(e: Estagio, n: int = 1) -> Estagio:
    return ESCADA[min(ESCADA.index(e) + n, len(ESCADA) - 1)]


def maior(a: Estagio, b: Estagio) -> Estagio:
    return a if ESCADA.index(a) >= ESCADA.index(b) else b


def nivel_por_limiar(valor: float | None, atencao: float, alerta: float, critico: float) -> Estagio | None:
    if valor is None:
        return None
    if valor >= critico:
        return "critico"
    if valor >= alerta:
        return "alerta"
    if valor >= atencao:
        return "atencao"
    return "observacao"


def acumulado_previsto(
    chuva: list[tuple[datetime, float | None]], inicio: datetime, horas: int
) -> tuple[float | None, int]:
    """Soma das horas previstas em [inicio, inicio + horas). Devolve (mm, horas com dado); o total só existe
    com pelo menos MIN_HORAS_PREVISAO[horas] horas, para não parecer pouca chuva quando falta previsão."""
    fim = inicio + timedelta(hours=horas)
    validas = [v for t, v in chuva if inicio <= t < fim and v is not None]
    minimo = MIN_HORAS_PREVISAO.get(horas, horas)
    return (round(sum(validas), 1) if len(validas) >= minimo else None), len(validas)


def pico(chuva: list[tuple[datetime, float | None]], inicio: datetime, horas: int = 72) -> datetime | None:
    fim = inicio + timedelta(hours=horas)
    validas = [(t, v) for t, v in chuva if inicio <= t < fim and v is not None and v > 0]
    return max(validas, key=lambda p: p[1])[0] if validas else None


def mare_perto_do_pico(
    mare: list[tuple[datetime, float | None]], pico_em: datetime | None, janela_h: float
) -> float | None:
    """Maior nível do mar a até `janela_h` horas do pico de chuva; None sem pico ou sem maré na janela."""
    if pico_em is None:
        return None
    perto = [v for t, v in mare if v is not None and abs((t - pico_em).total_seconds()) <= janela_h * 3600]
    return max(perto) if perto else None


def sugerir(ins: Insumos, p: Parametros) -> Sugestao:
    motivos: list[str] = []
    faltando = [
        nome
        for nome, valor in (
            ("a previsão de chuva das próximas 24 h", ins.chuva_prev_24h_mm),
            ("a previsão de chuva das próximas 72 h", ins.chuva_prev_72h_mm),
            ("a previsão de maré", ins.mare_max_m),
        )
        if valor is None
    ]

    base: Estagio = "observacao"
    for chave, nome in GATILHOS_CHUVA:
        valor = getattr(ins, f"{chave}_mm")
        limites = [getattr(p, f"{chave}_{n}_mm") for n in ("atencao", "alerta", "critico")]
        nivel = nivel_por_limiar(valor, *limites)
        if nivel and nivel != "observacao":
            limite = limites[ESCADA.index(nivel) - 1]
            motivos.append(
                f"{nome}: {_mm(valor)}, acima do limite de {ROTULO[nivel].lower()} ({_mm(limite)})."
            )
            base = maior(base, nivel)
    if (
        ins.chuva_prev_72h_mm is not None
        and ins.horas_previstas_72h is not None
        and ins.horas_previstas_72h < 72
    ):
        motivos.append(f"A previsão cobre {ins.horas_previstas_72h} das próximas 72 h.")
    if ins.chuva_24h_mm is None:
        motivos.append("Sem a chuva das últimas 24 h: este gatilho não entrou no cálculo.")

    if base != "observacao" and ins.mare_no_pico_m is not None and ins.mare_no_pico_m >= p.mare_alta_m:
        novo = subir(base)
        motivos.append(
            f"Maré alta ({_m(ins.mare_no_pico_m)}) perto do pico de chuva: sobe de {ROTULO[base].lower()} "
            f"para {ROTULO[novo].lower()}, porque dificulta a drenagem."
        )
        base = novo

    if (
        base != "observacao"
        and ins.ocorrencias_historicas is not None
        and ins.ocorrencias_historicas >= p.ocorrencias_bairro_minimo
    ):
        novo = subir(base)
        motivos.append(
            f"Bairro com {ins.ocorrencias_historicas} ocorrência(s) de alagamento registradas: sobe de "
            f"{ROTULO[base].lower()} para {ROTULO[novo].lower()}."
        )
        base = novo

    if ins.risco_ml is not None:
        indicado = CLASSE_ML.get(ins.risco_ml.strip().lower())
        if indicado and ESCADA.index(indicado) > ESCADA.index(base):
            motivos.append(
                f"Modelo experimental de alagamento indica risco “{ins.risco_ml}”: sobe para "
                f"{ROTULO[indicado].lower()}."
            )
            base = indicado
        else:
            motivos.append(f"Modelo experimental de alagamento indica risco “{ins.risco_ml}”.")

    if ins.herdado_de:
        motivos.append(f"A chuva e a maré são do distrito ({ins.herdado_de}): o bairro herda os valores.")

    if faltando:
        texto = "Faltam dados para sugerir o estágio: " + ", ".join(faltando) + "."
        sinal = (
            f" Com o que há, os gatilhos já indicam pelo menos {ROTULO[base].lower()}."
            if base != "observacao"
            else ""
        )
        return Sugestao("sem_dados", [texto + sinal, *motivos], faltando)

    if base == "observacao":
        motivos.insert(0, "Nenhum gatilho passou dos limites de atenção.")
    return Sugestao(base, motivos, [])
