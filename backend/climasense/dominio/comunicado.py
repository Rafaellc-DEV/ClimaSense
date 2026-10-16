"""Comunicado: conteúdo de uma versão, hash, diferença entre versões e legibilidade (RF-11). Domínio puro."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

NIVEIS = ("informativo", "atencao", "alerta", "critico")
PUBLICOS = {"populacao": "População", "equipes_saude": "Equipes de saúde"}
MAX_TITULO, MAX_TEXTO, MAX_ORIENTACOES, MAX_ORIENTACAO = 120, 1200, 5, 300
PALAVRAS_FRASE_LONGA = 25
EMITIDO_POR = "Vigilância em Saúde do Recife"


@dataclass(frozen=True)
class Conteudo:
    """Tudo o que a landing mostra. Uma versão aprovada é exatamente este conteúdo (RN-04)."""

    titulo: str
    texto: str
    orientacoes: tuple[str, ...]
    territorios: tuple[str, ...]
    publico: str
    nivel: str
    validade_inicio: datetime
    validade_fim: datetime

    def hash(self) -> str:
        d = asdict(self)
        # sempre em UTC: o banco devolve no fuso da sessão, e o hash não pode depender disso
        d["validade_inicio"] = self.validade_inicio.astimezone(UTC).isoformat()
        d["validade_fim"] = self.validade_fim.astimezone(UTC).isoformat()
        d["orientacoes"], d["territorios"] = list(self.orientacoes), list(self.territorios)
        return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def problemas(c: Conteudo) -> list[str]:
    """Erros que impedem salvar a versão, em linguagem simples."""
    erros = []
    if not c.titulo.strip():
        erros.append("Escreva um título.")
    if len(c.titulo) > MAX_TITULO:
        erros.append(f"O título passou de {MAX_TITULO} caracteres.")
    if len(c.texto) > MAX_TEXTO:
        erros.append(f"O texto passou de {MAX_TEXTO} caracteres.")
    if len(c.orientacoes) > MAX_ORIENTACOES:
        erros.append(f"Use no máximo {MAX_ORIENTACOES} orientações.")
    if any(len(o) > MAX_ORIENTACAO for o in c.orientacoes):
        erros.append(f"Cada orientação pode ter até {MAX_ORIENTACAO} caracteres.")
    if not c.territorios:
        erros.append("Escolha pelo menos um território.")
    if c.nivel not in NIVEIS:
        erros.append("Escolha o nível do aviso.")
    if c.publico not in PUBLICOS:
        erros.append("Escolha o público do aviso.")
    if c.validade_inicio >= c.validade_fim:
        erros.append("O fim da validade precisa ser depois do início.")
    return erros


def frases_longas(texto: str, limite: int = PALAVRAS_FRASE_LONGA) -> list[dict]:
    """Frases com mais de `limite` palavras (RF-11.8): difíceis para quem lê com dificuldade."""
    resultado = []
    for i, frase in enumerate(f for f in re.split(r"(?<=[.!?])\s+|\n+", texto) if f.strip()):
        n = len(frase.split())
        if n > limite:
            resultado.append({"frase": i + 1, "palavras": n, "inicio": " ".join(frase.split()[:6]) + "…"})
    return resultado


def diferenca(antes: str, depois: str) -> list[dict]:
    """Diferença por palavra: [{"tipo": "igual"|"removido"|"inserido", "texto": ...}]."""
    a, b = re.findall(r"\S+|\s+", antes), re.findall(r"\S+|\s+", depois)
    trechos: list[dict] = []

    def junta(tipo: str, partes: list[str]) -> None:
        texto = "".join(partes)
        if not texto:
            return
        if trechos and trechos[-1]["tipo"] == tipo:
            trechos[-1]["texto"] += texto
        else:
            trechos.append({"tipo": tipo, "texto": texto})

    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            junta("igual", a[i1:i2])
        else:
            junta("removido", a[i1:i2])
            junta("inserido", b[j1:j2])
    return trechos
