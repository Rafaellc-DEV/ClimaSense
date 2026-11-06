"""Simulador de cenário por regras (PRD §8, RF-23 a RF-25, RF-28). Domínio puro, sem I/O. EXPERIMENTAL (RN-11).

A usuária preenche as premissas; cada território recebe uma CLASSE ORDINAL de alagamento e de deslizamento, no
vocabulário dos estágios (`sem_dados`, `observacao`, `atencao`, `alerta`, `critico`). Nunca é probabilidade nem
percentual (RN-06). Os limiares são os MESMOS dos gatilhos de estágio (`dominio.estagio.Parametros`): quem muda o
limiar muda o estágio sugerido e o simulador juntos.

Como as premissas viram gatilhos
- Chuva prevista (mm em `duracao_h` horas), espalhada por igual na duração: o que cai nas 24 h mais chuvosas é
  `mm × min(1, 24 / duracao)` (limiares de chuva prevista em 24 h); o que cai em 72 h é `mm × min(1, 72 / duracao)`
  (limiares de 72 h). A duração é no máximo 72 h.
- Chuva acumulada nas 72 h anteriores (solo saturado): comparada com os limiares de 72 h.
- Maré: nível previsto junto do pico de chuva; a partir de `mare_alta_m` sobe um nível do alagamento (só
  alagamento: a maré não interfere em encosta).

Alagamento: maior nível entre os três gatilhos; maré alta sobe um nível (a partir de atenção); histórico do bairro
com ocorrências de alagamento (≥ `ocorrencias_bairro_minimo`) sobe um nível (a partir de atenção).
Deslizamento: maior nível entre os três gatilhos; solo saturado (acumulada ≥ limiar de atenção de 72 h) junto de
chuva prevista em atenção ou mais sobe um nível; histórico de deslizamento do bairro (≥ mínimo) sobe um nível.

Ausência de dado nunca vira classe baixa (RN-01):
- sem carga de ocorrências na fonte → alagamento e deslizamento `sem_dados`;
- bairro sem NENHUM registro de deslizamento → deslizamento `sem_dados`, "sem histórico de deslizamento na base".
  Não há camada de áreas de risco nem declividade: sem histórico, não há como dizer que o bairro é seguro.
  Zero de alagamento com a fonte carregada é zero medido (RN-02) e é classificado.

Limiar sensível (PRD §6.3, prefere falso positivo): bairro com histórico no mínimo e que ficou em observação, mas
com algum gatilho em 80% ou mais do limite de atenção, sobe para atenção.

Estágio sugerido = a maior das duas classes; se a conhecida é só observação e a outra é `sem_dados`, o estágio é
`sem_dados` (não se afirma observação quando um perigo é desconhecido). É apoio à decisão: a equipe é quem declara.

Confiança: `insuficiente` (as duas classes sem dados), `baixa` (uma sem dados), `media` (regras com as duas
classes). `alta` fica reservada para depois de validação temporal documentada (RN-11) e hoje nunca é devolvida.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from climasense.dominio import estagio as dom

Classe = Literal["sem_dados", "observacao", "atencao", "alerta", "critico"]
Confianca = Literal["alta", "media", "baixa", "insuficiente"]
ESCADA = dom.ESCADA
FRACAO_SENSIVEL = 0.8
MOTIVO_SEM_DESLIZAMENTO = "sem histórico de deslizamento na base"
MOTIVO_SEM_ALAGAMENTO = "sem histórico de ocorrências de alagamento na base"
MOTIVO_IMPACTO_PENDENTE = "Dados insuficientes: população vulnerável ainda não integrada (Etapa 6)"
MAX_MOTIVOS = 3
MOTIVO_SEM_ACUMULADA = "sem chuva acumulada informada"
MOTIVO_SEM_MARE = "sem maré informada"


@dataclass(frozen=True)
class Premissas:
    chuva_prevista_mm: float
    duracao_h: float
    chuva_acumulada_mm: float | None
    mare_m: float | None
    horizonte_h: int
    abrigos_abertos: int | None = None
    capacidade_abrigos: int | None = None


@dataclass(frozen=True)
class Historico:
    """Ocorrências do território. `None` = a fonte nunca foi carregada; 0 = medido e nenhum."""

    alagamento: int | None
    deslizamento: int | None
    desde: int | None = None  # ano do registro mais antigo da fonte


@dataclass(frozen=True)
class Vulneraveis:
    """Reservado à Etapa 6 (IBGE e equipamentos de saúde). Campo `None` = sem fonte."""

    idosos: int | None = None
    criancas: int | None = None
    equipamentos_saude: int | None = None


@dataclass
class Resultado:
    classe_alagamento: Classe
    classe_deslizamento: Classe
    estagio_sugerido: Classe
    confianca: Confianca
    motivos: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Gatilho:
    rotulo: str
    valor: float
    nivel: Classe
    limite_atencao: float
    limite_nivel: float | None  # limite do nível atingido; None em observação


def _num(v: float) -> str:
    return str(int(round(v))) if abs(v - round(v)) < 0.05 else f"{v:.1f}".replace(".", ",")


def _mm(v: float) -> str:
    return f"{_num(v)} mm"


def _m(v: float) -> str:
    return f"{_num(v)} m"


def chuva_na_janela(p: Premissas, horas: int) -> float:
    """Chuva prevista que cai na janela mais chuvosa de `horas` horas (distribuição uniforme na duração)."""
    return round(p.chuva_prevista_mm * min(1.0, horas / p.duracao_h), 1)


def gatilhos(p: Premissas, par: dom.Parametros) -> list[Gatilho]:
    entradas = [
        (f"{_mm(chuva_na_janela(p, 24))} previstos em 24 h", chuva_na_janela(p, 24), "chuva_prev_24h"),
        (f"{_mm(chuva_na_janela(p, 72))} previstos em 72 h", chuva_na_janela(p, 72), "chuva_prev_72h"),
    ]
    if p.chuva_acumulada_mm is not None:  # premissa desconhecida não vira zero (RN-01): gatilho não avaliado
        entradas.append(
            (
                f"{_mm(p.chuva_acumulada_mm)} acumulados nas 72 h anteriores",
                p.chuva_acumulada_mm,
                "chuva_prev_72h",
            )
        )
    saida = []
    for rotulo, valor, chave in entradas:
        lim = [getattr(par, f"{chave}_{n}_mm") for n in ("atencao", "alerta", "critico")]
        nivel = dom.nivel_por_limiar(valor, *lim)
        assert nivel is not None
        limite = lim[ESCADA.index(nivel) - 1] if nivel != "observacao" else None
        saida.append(Gatilho(rotulo, valor, nivel, lim[0], limite))
    return saida


def _maior_nivel(gs: list[Gatilho]) -> Classe:
    nivel: Classe = "observacao"
    for g in gs:
        nivel = dom.maior(nivel, g.nivel)  # type: ignore[arg-type]
    return nivel


def _motivo_gatilho(g: Gatilho) -> str:
    return f"{g.rotulo}, acima do limiar de {dom.ROTULO[g.nivel].lower()} ({_mm(g.limite_nivel or 0)})"


def _motivos_gatilhos(gs: list[Gatilho]) -> list[str]:
    """O gatilho de maior nível (e só ele): 1 frase curta, para o texto caber (RNF-09)."""
    mais_alto = [g for g in gs if g.nivel != "observacao"]
    if not mais_alto:
        return [f"nenhum gatilho de chuva passou do limiar de atenção ({_mm(gs[0].limite_atencao)} em 24 h)"]
    topo = max(mais_alto, key=lambda g: (ESCADA.index(g.nivel), g.valor))  # type: ignore[arg-type]
    return [_motivo_gatilho(topo)]


def _historico_texto(n: int, tipo: str, desde: int | None) -> str:
    plural = "atendimento" if n == 1 else "atendimentos"
    return f"{n} {plural} de {tipo}" + (f" desde {desde}" if desde else "")


def _quase(gs: list[Gatilho]) -> Gatilho | None:
    perto = [g for g in gs if g.valor >= FRACAO_SENSIVEL * g.limite_atencao]
    return max(perto, key=lambda g: g.valor / g.limite_atencao) if perto else None


def classificar_alagamento(
    p: Premissas, par: dom.Parametros, hist: Historico
) -> tuple[Classe, list[str], bool]:
    """(classe, motivos, histórico_disparou). Motivos sem a marcação de `sem_dados` ficam separados do histórico."""
    gs = gatilhos(p, par)
    base = _maior_nivel(gs)
    motivos = _motivos_gatilhos(gs)
    if hist.alagamento is None:
        return "sem_dados", [*motivos, MOTIVO_SEM_ALAGAMENTO], False
    if base != "observacao" and p.mare_m is not None and p.mare_m >= par.mare_alta_m:
        base = dom.subir(base)  # type: ignore[arg-type]
        motivos.append(f"maré de {_m(p.mare_m)} junto do pico: sobe um nível")
    forte = hist.alagamento >= par.ocorrencias_bairro_minimo
    if base != "observacao" and forte:
        base = dom.subir(base)  # type: ignore[arg-type]
    if hist.alagamento > 0 and (forte or base != "observacao"):
        motivos.append(_historico_texto(hist.alagamento, "alagamento", hist.desde))
    if base == "observacao" and forte:
        perto = _quase(gs)
        if perto:
            base = "atencao"
            motivos.append(
                f"{perto.rotulo}, perto do limiar de atenção ({_mm(perto.limite_atencao)}) em bairro com histórico"
            )
    return base, motivos, forte


def classificar_deslizamento(p: Premissas, par: dom.Parametros, hist: Historico) -> tuple[Classe, list[str]]:
    gs = gatilhos(p, par)
    base = _maior_nivel(gs)
    motivos = _motivos_gatilhos(gs)
    if not hist.deslizamento:
        return "sem_dados", [MOTIVO_SEM_DESLIZAMENTO]
    previstos = _maior_nivel(gs[:2])
    saturado = p.chuva_acumulada_mm is not None and p.chuva_acumulada_mm >= par.chuva_prev_72h_atencao_mm
    if previstos != "observacao" and saturado:
        base = dom.subir(base)  # type: ignore[arg-type]
        motivos.append(f"solo saturado ({_mm(p.chuva_acumulada_mm)} nas 72 h anteriores): sobe um nível")
    forte = hist.deslizamento >= par.ocorrencias_bairro_minimo
    if base != "observacao" and forte:
        base = dom.subir(base)  # type: ignore[arg-type]
    motivos.append(_historico_texto(hist.deslizamento, "deslizamento", hist.desde))
    if base == "observacao" and forte:
        perto = _quase(gs)
        if perto:
            base = "atencao"
            motivos.append(f"{perto.rotulo}, perto do limiar de atenção, em bairro com histórico")
    return base, motivos


def estagio_sugerido(alag: Classe, desl: Classe) -> Classe:
    conhecidas = [c for c in (alag, desl) if c != "sem_dados"]
    if not conhecidas:
        return "sem_dados"
    topo: Classe = "observacao"
    for c in conhecidas:
        topo = dom.maior(topo, c)  # type: ignore[arg-type]
    if topo == "observacao" and len(conhecidas) < 2:
        return "sem_dados"
    return topo


def confianca(alag: Classe, desl: Classe, p: Premissas | None = None) -> Confianca:
    sem = [c == "sem_dados" for c in (alag, desl)]
    if all(sem):
        return "insuficiente"
    if any(sem):
        return "baixa"
    if p is not None and (p.chuva_acumulada_mm is None or p.mare_m is None):
        return "baixa"  # insumo que importa para a classe não foi informado
    return "media"  # `alta` só depois de validação temporal documentada (RN-11)


def motivos_premissas_ausentes(p: Premissas, alag: Classe) -> list[str]:
    faltas = []
    if p.chuva_acumulada_mm is None:
        faltas.append(MOTIVO_SEM_ACUMULADA)
    if p.mare_m is None and alag != "sem_dados":
        faltas.append(MOTIVO_SEM_MARE)
    return faltas


def _escolher_motivos(
    alag_motivos: list[str],
    desl_motivos: list[str],
    desl: Classe,
    alag: Classe,
    faltas: list[str] | None = None,
) -> list[str]:
    """No máximo 3 frases. As de `sem_dados` têm vaga garantida: a falta de dado é o que a pessoa precisa ler."""
    essenciais: list[str] = []
    if desl == "sem_dados":
        essenciais.append(MOTIVO_SEM_DESLIZAMENTO)
    if alag == "sem_dados":
        essenciais.append(MOTIVO_SEM_ALAGAMENTO)
    essenciais = [*essenciais, *(faltas or [])][:MAX_MOTIVOS]
    gerais: list[str] = []
    for m in [*alag_motivos, *desl_motivos]:
        if m not in essenciais and m not in gerais:
            gerais.append(m)
    return [*gerais[: max(0, MAX_MOTIVOS - len(essenciais))], *essenciais][:MAX_MOTIVOS]


def classificar_bairro(p: Premissas, par: dom.Parametros, hist: Historico) -> Resultado:
    alag, m_alag, _ = classificar_alagamento(p, par, hist)
    desl, m_desl = classificar_deslizamento(p, par, hist)
    return Resultado(
        classe_alagamento=alag,
        classe_deslizamento=desl,
        estagio_sugerido=estagio_sugerido(alag, desl),
        confianca=confianca(alag, desl, p),
        motivos=_escolher_motivos(m_alag, m_desl, desl, alag, motivos_premissas_ausentes(p, alag)),
    )


def agregar_distrito(bairros: list[tuple[str, Resultado]]) -> Resultado:
    """Distrito = o pior dos seus bairros, por classe. Bairro sem dado não puxa o distrito para baixo: o que falta
    entra nos motivos e a confiança cai. Sem nenhum bairro com dado, `sem_dados`."""

    def pior(classes: list[Classe]) -> Classe:
        conhecidas = [c for c in classes if c != "sem_dados"]
        if not conhecidas:
            return "sem_dados"
        topo: Classe = "observacao"
        for c in conhecidas:
            topo = dom.maior(topo, c)  # type: ignore[arg-type]
        return topo

    alag = pior([r.classe_alagamento for _, r in bairros])
    desl = pior([r.classe_deslizamento for _, r in bairros])
    estagio = estagio_sugerido(alag, desl)
    n = len(bairros)
    sem = sum(1 for _, r in bairros if r.estagio_sugerido == "sem_dados")
    motivos: list[str] = []
    if estagio not in ("sem_dados", "observacao"):
        em_estagio = [nome for nome, r in bairros if r.estagio_sugerido == estagio]
        nomes = ", ".join(em_estagio[:2]) + (" e outros" if len(em_estagio) > 2 else "")
        motivos.append(f"{len(em_estagio)} de {n} bairros em {dom.ROTULO[estagio].lower()}: {nomes}")
    elif estagio == "observacao":
        motivos.append(f"nenhum dos {n - sem} bairros com dados passou da observação")
    if sem:
        motivos.append(f"{sem} de {n} bairros sem dados suficientes")
    if desl == "sem_dados":
        motivos.append(MOTIVO_SEM_DESLIZAMENTO)
    if alag == "sem_dados":
        motivos.append(MOTIVO_SEM_ALAGAMENTO)
    for falta in (MOTIVO_SEM_ACUMULADA, MOTIVO_SEM_MARE):
        if any(falta in r.motivos for _, r in bairros) and falta not in motivos:
            motivos.append(falta)
    conf: Confianca = confianca(alag, desl)
    if conf == "media" and (sem or any(r.confianca == "baixa" for _, r in bairros)):
        conf = "baixa"
    faltas = [m for m in motivos if m in (MOTIVO_SEM_ACUMULADA, MOTIVO_SEM_MARE)]
    resto = [m for m in motivos if m not in faltas]
    return Resultado(alag, desl, estagio, conf, [*resto[: MAX_MOTIVOS - len(faltas[:2])], *faltas[:2]])


def pressao_abrigos(p: Premissas) -> str | None:
    """Só repete o que foi informado: não inventa demanda de abrigo."""
    n, cap = p.abrigos_abertos, p.capacidade_abrigos
    if n is None and cap is None:
        return None
    if n is not None and cap is not None:
        if n == 0:
            return "nenhum abrigo aberto informado"
        abrigos = "abrigo" if n == 1 else "abrigos"
        return f"capacidade informada de {cap} pessoas em {n} {abrigos}"
    if n is not None:
        return (
            "nenhum abrigo aberto informado"
            if n == 0
            else f"{n} abrigo(s) aberto(s), capacidade não informada"
        )
    return f"capacidade informada de {cap} pessoas, número de abrigos abertos não informado"


def impacto_pessoas(estagio: Classe, vulneraveis: Vulneraveis | None) -> dict | None:
    """Pessoas e equipamentos expostos no território quando o estágio sugerido é atenção ou mais. `None` enquanto
    não houver fonte de população vulnerável (Etapa 6) ou sem estágio. Soma só o que tem fonte."""
    if vulneraveis is None or estagio in ("sem_dados", "observacao"):
        return None
    partes = [v for v in (vulneraveis.idosos, vulneraveis.criancas) if v is not None]
    return {
        "idosos": vulneraveis.idosos,
        "criancas": vulneraveis.criancas,
        "equipamentos_saude": vulneraveis.equipamentos_saude,
        "total_pessoas": sum(partes) if partes else None,
        "criterio": "população do território, exposta quando o estágio sugerido é atenção ou mais",
    }


def resumo_por_classe(resultados: list[Resultado]) -> dict[str, dict[str, int]]:
    ordem = ("sem_dados", *ESCADA)
    saida: dict[str, dict[str, int]] = {}
    for chave, campo in (
        ("alagamento", "classe_alagamento"),
        ("deslizamento", "classe_deslizamento"),
        ("estagio_sugerido", "estagio_sugerido"),
    ):
        saida[chave] = {c: sum(1 for r in resultados if getattr(r, campo) == c) for c in ordem}
    return saida
