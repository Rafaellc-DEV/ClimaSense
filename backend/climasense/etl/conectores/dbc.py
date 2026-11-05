"""Leitor de .dbc do DATASUS em Python puro (sem dependência nativa).

O .dbc é um DBF (dBase III) cujo corpo foi comprimido com o PKWare DCL "implode". A descompressão é uma porta do
`blast.c` de Mark Adler (zlib/contrib/blast, licença zlib), o mesmo algoritmo que o `pyreaddbc` do PySUS usa em C.

Layout: os bytes 8–9 trazem o tamanho do cabeçalho DBF; o cabeçalho vai sem compressão, seguido de 4 bytes (CRC) e
do corpo comprimido.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable, Iterator

_MAXBITS = 13


class DbcInvalido(ValueError):
    """O arquivo não é um .dbc válido (truncado, corrompido ou outro formato)."""


class _Huffman:
    def __init__(self, representacao: list[int]) -> None:
        comprimentos: list[int] = []
        for b in representacao:
            comprimentos += [b & 15] * ((b >> 4) + 1)
        self.contagem = [0] * (_MAXBITS + 1)
        for c in comprimentos:
            self.contagem[c] += 1
        desloc = [0] * (_MAXBITS + 1)
        for i in range(1, _MAXBITS):
            desloc[i + 1] = desloc[i] + self.contagem[i]
        self.simbolo = [0] * len(comprimentos)
        for s, c in enumerate(comprimentos):
            if c:
                self.simbolo[desloc[c]] = s
                desloc[c] += 1


# Tabelas fixas do formato (blast.c)
_LIT = _Huffman(
    [11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8, 9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24, 12,
     11, 7, 9, 11, 12, 6, 7, 22, 5, 7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12, 8, 12, 5,
     38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27, 44, 253, 253, 253, 252, 252, 252, 13, 12, 45, 12,
     45, 12, 61, 12, 45, 44, 173]
)  # fmt: skip
_COMP = _Huffman([2, 35, 36, 53, 38, 23])
_DIST = _Huffman([2, 20, 53, 230, 247, 151, 248])
_BASE = [3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264]
_EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]


def descomprimir(dados: bytes) -> bytes:
    """PKWare DCL implode → bytes originais (porta de `blast()`)."""
    pos = 0
    buf = 0
    cnt = 0
    saida = bytearray()
    n = len(dados)

    def bits(necessarios: int) -> int:
        nonlocal pos, buf, cnt
        v = buf
        while cnt < necessarios:
            if pos >= n:
                raise DbcInvalido("Arquivo .dbc truncado.")
            v |= dados[pos] << cnt
            pos += 1
            cnt += 8
        buf = v >> necessarios
        cnt -= necessarios
        return v & ((1 << necessarios) - 1)

    def decodificar(h: _Huffman) -> int:
        codigo = primeiro = indice = 0
        for comp in range(1, _MAXBITS + 1):
            codigo |= bits(1) ^ 1
            c = h.contagem[comp]
            if codigo < primeiro + c:
                return h.simbolo[indice + (codigo - primeiro)]
            indice += c
            primeiro = (primeiro + c) << 1
            codigo <<= 1
        raise DbcInvalido("Código de compressão inválido no .dbc.")

    literal_codificado = bits(8)
    dicionario = bits(8)
    if literal_codificado > 1 or not 4 <= dicionario <= 6:
        raise DbcInvalido("Cabeçalho de compressão inválido no .dbc.")
    while True:
        if bits(1):
            s = decodificar(_COMP)
            comprimento = _BASE[s] + bits(_EXTRA[s])
            if comprimento == 519:  # fim do fluxo
                break
            b = 2 if comprimento == 2 else dicionario
            distancia = (decodificar(_DIST) << b) + bits(b) + 1
            if distancia > len(saida):
                raise DbcInvalido("Distância inválida no .dbc.")
            for _ in range(comprimento):
                saida.append(saida[-distancia])
        else:
            saida.append(decodificar(_LIT) if literal_codificado else bits(8))
    return bytes(saida)


def ler(conteudo: bytes, colunas: Iterable[str] | None = None) -> tuple[list[str], Iterator[dict[str, str]]]:
    """(nomes de todos os campos, iterador de registros) com os valores como texto sem espaços.

    `colunas` restringe o que é decodificado em cada registro: quem chama escolhe só os campos não identificáveis
    (minimização, LGPD) e nada mais sai daqui."""
    if len(conteudo) < 32:
        raise DbcInvalido("Arquivo .dbc vazio ou truncado.")
    tam_cabecalho = struct.unpack("<H", conteudo[8:10])[0]
    dbf = conteudo[:tam_cabecalho] + descomprimir(conteudo[tam_cabecalho + 4 :])
    n_registros = struct.unpack("<I", dbf[4:8])[0]
    tam_registro = struct.unpack("<H", dbf[10:12])[0]
    campos: list[tuple[str, int, int]] = []  # nome, início no registro, tamanho
    i, inicio = 32, 1  # o 1º byte do registro é a marca de apagado
    while i < len(dbf) and dbf[i] != 0x0D:
        nome = dbf[i : i + 11].split(b"\0")[0].decode("latin-1")
        tamanho = dbf[i + 16]
        campos.append((nome, inicio, tamanho))
        inicio += tamanho
        i += 32
    nomes = [c[0] for c in campos]
    escolhidos = [c for c in campos if colunas is None or c[0] in set(colunas)]

    def registros() -> Iterator[dict[str, str]]:
        for r in range(n_registros):
            base = tam_cabecalho + r * tam_registro
            reg = dbf[base : base + tam_registro]
            if not reg or reg[0:1] == b"*":  # registro apagado
                continue
            yield {nome: reg[ini : ini + tam].decode("latin-1").strip() for nome, ini, tam in escolhidos}

    return nomes, registros()
