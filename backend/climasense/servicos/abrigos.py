"""Abrigos e desabrigados (F3): cadastro manual da equipe, com autor, hora e histórico de cada atualização."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.dominio import abrigos as dom
from climasense.dominio.evento import RegistroInvalido
from climasense.infra.modelos_sql import Usuario
from climasense.servicos import fluxo

ALVO = "abrigo"
CAMPOS = (
    "nome",
    "bairro_id",
    "endereco",
    "capacidade",
    "aberto",
    "pessoas_abrigadas",
    "desabrigados",
    "observacao",
    "latitude",
    "longitude",
)

SQL_LISTA = """
with equipe as (
  select abrigo_id, max(em) as em from app.abrigo_atualizacoes where autor_id is not null group by abrigo_id
)
select a.id, a.nome, a.bairro_id, b.nome_exibicao as bairro_nome, b.pai_id as distrito_id,
       d.nome_exibicao as distrito_nome, a.endereco, a.capacidade, a.aberto, a.pessoas_abrigadas, a.desabrigados,
       a.observacao, a.latitude, a.longitude, a.origem, a.criado_em, a.atualizado_em,
       u.nome as atualizado_por_nome,
       -- quem disse que está aberto ou fechado: a equipe (a última palavra) ou o COP; nulo = ninguém informou ainda
       case when e.em is not null and (a.status_lido_em is null or e.em >= a.status_lido_em) then 'equipe'
            when a.status_origem = 'cop' then 'cop'
            when a.origem = 'manual' then 'equipe' end as status_fonte,
       case when e.em is not null and (a.status_lido_em is null or e.em >= a.status_lido_em) then e.em
            when a.status_origem = 'cop' then a.status_lido_em
            when a.origem = 'manual' then a.atualizado_em end as status_informado_em
from app.abrigos a join app.territorios b on b.id = a.bairro_id
left join app.territorios d on d.id = b.pai_id
left join app.usuarios u on u.id = a.atualizado_por
left join equipe e on e.abrigo_id = a.id
where (cast(:id as uuid) is null or a.id = :id)
  and (cast(:ds as varchar) is null or b.pai_id = :ds or a.bairro_id = :ds)
order by a.aberto desc, a.atualizado_em desc, a.nome
"""


def _linhas(db: Session, abrigo_id: uuid.UUID | None = None, distrito_id: str | None = None) -> list[dict]:
    return [dict(r) for r in db.execute(text(SQL_LISTA), {"id": abrigo_id, "ds": distrito_id}).mappings()]


def totais(linhas: list[dict]) -> dict:
    t = dom.totais(
        [
            dom.SituacaoAbrigo(r["aberto"], r["pessoas_abrigadas"], r["desabrigados"], r["atualizado_em"])
            for r in linhas
        ]
    )
    return t.__dict__.copy()


def listar(db: Session, aberto: bool | None = None, distrito_id: str | None = None) -> dict:
    """Os totais valem para o recorte de distrito inteiro (abertos e fechados), não para o filtro `aberto`."""
    todas = _linhas(db, distrito_id=distrito_id)
    return {
        "itens": [r for r in todas if aberto is None or r["aberto"] == aberto],
        "totais": totais(todas),
    }


def obter(db: Session, abrigo_id: uuid.UUID) -> dict:
    linhas = _linhas(db, abrigo_id=abrigo_id)
    if not linhas:
        raise RegistroInvalido(404, "Abrigo não encontrado.")
    return linhas[0]


def _validar(db: Session, dados: dict) -> None:
    if ("latitude" in dados) != ("longitude" in dados) or (
        (dados.get("latitude") is None) != (dados.get("longitude") is None)
    ):
        raise RegistroInvalido(422, "Informe latitude e longitude juntas (ou nenhuma das duas).")
    erros = dom.problemas(
        dados.get("nome"), dados.get("capacidade"), dados.get("pessoas_abrigadas"), dados.get("desabrigados")
    )
    if erros:
        raise RegistroInvalido(422, " ".join(erros))
    if "bairro_id" in dados:
        tipo = db.execute(
            text("select tipo from app.territorios where id = :i"), {"i": dados["bairro_id"]}
        ).scalar()
        if tipo != "bairro":
            raise RegistroInvalido(422, "Escolha o bairro onde fica o abrigo.")


def _limpar(dados: dict) -> dict:
    saida = {}
    for k, v in dados.items():
        if k not in CAMPOS:
            continue
        if isinstance(v, str):
            v = " ".join(v.split()) if k != "observacao" else v.strip()
            v = v or None
        saida[k] = v
    return saida


def _historico(
    db: Session, abrigo_id, atual: dict, autor: Usuario, agora: datetime, alteracoes: dict
) -> None:
    db.execute(
        text(
            "insert into app.abrigo_atualizacoes (abrigo_id, em, autor_id, aberto, capacidade, pessoas_abrigadas, "
            "desabrigados, observacao, alteracoes) values (:a, :em, :u, :ab, :c, :p, :d, :o, cast(:alt as jsonb))"
        ),
        {
            "a": abrigo_id,
            "em": agora,
            "u": autor.id,
            "ab": atual["aberto"],
            "c": atual.get("capacidade"),
            "p": atual.get("pessoas_abrigadas"),
            "d": atual.get("desabrigados"),
            "o": atual.get("observacao"),
            "alt": json.dumps(alteracoes, ensure_ascii=False, default=str),
        },
    )


def criar(db: Session, dados: dict, autor: Usuario, ip: str | None, agora: datetime) -> dict:
    dados = _limpar(dados)
    if not dados.get("nome"):
        raise RegistroInvalido(422, "Escreva o nome do abrigo.")
    if not dados.get("bairro_id"):
        raise RegistroInvalido(422, "Escolha o bairro onde fica o abrigo.")
    dados.setdefault("aberto", False)
    _validar(db, dados)
    try:
        abrigo_id = uuid.uuid4()
        db.execute(
            text(
                "insert into app.abrigos (id, nome, bairro_id, endereco, capacidade, aberto, pessoas_abrigadas, "
                "desabrigados, observacao, latitude, longitude, origem, criado_por, criado_em, atualizado_por, "
                "atualizado_em) values "
                "(:id, :nome, :bairro_id, :endereco, :capacidade, :aberto, :pessoas_abrigadas, :desabrigados, "
                ":observacao, :latitude, :longitude, 'manual', :u, :em, :u, :em)"
            ),
            {**{c: dados.get(c) for c in CAMPOS}, "id": abrigo_id, "u": autor.id, "em": agora},
        )
        _historico(db, abrigo_id, dados, autor, agora, dom.alteracoes({}, dados))
        fluxo.auditar(
            db, "abrigo_cadastrado", autor, ALVO, abrigo_id, ip, nome=dados["nome"], aberto=dados["aberto"]
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, abrigo_id)


def atualizar(
    db: Session, abrigo_id: uuid.UUID, dados: dict, autor: Usuario, ip: str | None, agora: datetime
) -> dict:
    """Só os campos enviados mudam; cada atualização vira uma linha de histórico (mesmo sem mudança, conta
    como confirmação dos números naquela hora)."""
    antes = obter(db, abrigo_id)
    dados = _limpar(dados)
    if "nome" in dados and not dados["nome"]:
        raise RegistroInvalido(422, "Escreva o nome do abrigo.")
    if "aberto" in dados and dados["aberto"] is None:
        dados.pop("aberto")
    _validar(db, dados)
    depois = {**antes, **dados}
    mudou = dom.alteracoes(antes, dados)
    if "bairro_id" in dados and dados["bairro_id"] != antes["bairro_id"]:
        mudou["bairro_id"] = {"de": antes["bairro_id"], "para": dados["bairro_id"]}
    try:
        db.execute(
            text(
                "update app.abrigos set nome = :nome, bairro_id = :bairro_id, endereco = :endereco, "
                "capacidade = :capacidade, aberto = :aberto, pessoas_abrigadas = :pessoas_abrigadas, "
                "desabrigados = :desabrigados, observacao = :observacao, latitude = :latitude, "
                "longitude = :longitude, atualizado_por = :u, atualizado_em = :em "
                "where id = :id"
            ),
            {**{c: depois.get(c) for c in CAMPOS}, "id": abrigo_id, "u": autor.id, "em": agora},
        )
        _historico(db, abrigo_id, depois, autor, agora, mudou)
        fluxo.auditar(db, "abrigo_atualizado", autor, ALVO, abrigo_id, ip, alteracoes=mudou)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obter(db, abrigo_id)


def historico(db: Session, abrigo_id: uuid.UUID) -> list[dict]:
    obter(db, abrigo_id)
    return [
        dict(r)
        for r in db.execute(
            text(
                "select h.id, h.em, u.nome as autor_nome, h.aberto, h.capacidade, h.pessoas_abrigadas, "
                "h.desabrigados, h.observacao, h.alteracoes from app.abrigo_atualizacoes h "
                "left join app.usuarios u on u.id = h.autor_id where h.abrigo_id = :a order by h.em desc, h.id desc"
            ),
            {"a": abrigo_id},
        ).mappings()
    ]


def totais_recife(db: Session) -> dict:
    """Topo do painel: abrigos abertos e desabrigados, com a hora da última atualização."""
    return totais(_linhas(db))


def ocupacao_atualizada_em(db: Session) -> datetime | None:
    """Última atualização lançada por uma pessoa da equipe (a fonte "Registro da equipe")."""
    return db.execute(text("select max(em) from app.abrigo_atualizacoes where autor_id is not null")).scalar()


def situacao_evento(db: Session) -> dict:
    """Totais da cidade e de cada distrito sanitário (RF-08, RF-09), com a hora e o autor da última atualização.
    Contagem operacional de abrigo: não há supressão (não é agravo de saúde)."""
    linhas = _linhas(db)

    def _bloco(recorte: list[dict]) -> dict:
        d = dom.totais_situacao(
            [
                dom.SituacaoAbrigo(r["aberto"], r["pessoas_abrigadas"], r["desabrigados"], r["atualizado_em"])
                for r in recorte
            ]
        ).__dict__.copy()
        datados = [r for r in recorte if r["atualizado_em"]]
        ultimo = max(datados, key=lambda r: r["atualizado_em"], default=None)
        d["atualizado_por_nome"] = ultimo["atualizado_por_nome"] if ultimo else None
        return d

    distritos = db.execute(
        text("select id, nome_exibicao from app.territorios where tipo = 'distrito' order by id")
    ).all()
    return {
        "cidade": _bloco(linhas),
        "distritos": [
            {"distrito_id": i, "distrito_nome": n, **_bloco([r for r in linhas if r["distrito_id"] == i])}
            for i, n in distritos
        ],
        "ocupacao_atualizada_em": ocupacao_atualizada_em(db),
    }
