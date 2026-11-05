"""Painel inicial (T6.6, RF-04.5): o que precisa de mim agora, em 4 blocos."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Meta, RecorteMeta, RespostaDados
from climasense.api.esquemas_decisao import AcoesAgora, SituacaoAgora
from climasense.api.routers.publico import AvisoPublico, vigentes
from climasense.dominio.papeis import Permissao, pode
from climasense.dominio.recorte import granularidade
from climasense.infra.postgres import obter_sessao
from climasense.servicos import abrigos as servico_abrigos
from climasense.servicos import decisao
from climasense.servicos import fontes as servico_fontes
from climasense.servicos.territorio import no_maximo_distrito

router = APIRouter(prefix="/painel", tags=["Painel"])
consultar = exige(Permissao.CONSULTAR)
ORDEM = {"critico": 3, "alerta": 2, "atencao": 1}
ROTULO = {"critico": "Situação crítica", "alerta": "Alerta", "atencao": "Atenção"}


class ItemRevisao(BaseModel):
    tipo: str  # avaliacao | comunicado
    id: uuid.UUID
    titulo: str
    autor_nome: str
    enviado_em: datetime


class TerritorioAtencao(BaseModel):
    territorio_id: str
    territorio_nome: str
    nivel: str
    motivo: str


class FonteSaude(BaseModel):
    id: str
    nome: str
    status: str
    ultima_atualizacao: datetime | None


class Contadores(BaseModel):
    avaliacoes: int
    comunicados: int


class TotaisAbrigos(BaseModel):
    """Primeiras métricas no pico do evento (F3): só o que a equipe registrou; null = ninguém informou."""

    abrigos_abertos: int
    pessoas_abrigadas: int | None
    desabrigados: int | None
    atualizado_em: datetime | None


class ResumoPainel(BaseModel):
    avisos: list[AvisoPublico]
    abrigos: TotaisAbrigos
    pode_revisar: bool
    aguardando_revisao: list[ItemRevisao]
    territorios_em_atencao: list[TerritorioAtencao]
    fontes: list[FonteSaude]
    contadores: Contadores


def _aguardando(db: Session, usuario_id: uuid.UUID) -> list[ItemRevisao]:
    """Só o que ESTA pessoa pode revisar: em revisão e escrito por outra pessoa (RN-05)."""
    linhas = db.execute(
        text(
            "select 'avaliacao' as tipo, a.id, 'Avaliação: ' || t.nome_exibicao as titulo, u.nome as autor_nome, "
            "a.atualizado_em as enviado_em from app.avaliacoes a "
            "join app.avaliacao_versoes v on v.avaliacao_id = a.id and v.numero = a.versao_atual "
            "join app.usuarios u on u.id = v.autor_id join app.territorios t on t.id = a.territorio_id "
            "where a.estado = 'em_revisao' and v.autor_id <> :u "
            "union all "
            "select 'comunicado', c.id, v.titulo, u.nome, c.atualizado_em from app.comunicados c "
            "join app.comunicado_versoes v on v.comunicado_id = c.id and v.numero = c.versao_atual "
            "join app.usuarios u on u.id = v.autor_id where c.estado = 'em_revisao' and v.autor_id <> :u "
            "order by enviado_em"
        ),
        {"u": usuario_id},
    ).mappings()
    return [ItemRevisao(**r) for r in linhas]


def _em_atencao(db: Session, avisos: list[AvisoPublico], agora: datetime) -> list[TerritorioAtencao]:
    candidatos: dict[str, TerritorioAtencao] = {}

    def considerar(tid: str, nome: str, nivel: str, motivo: str) -> None:
        atual = candidatos.get(tid)
        if atual is None or ORDEM[nivel] > ORDEM[atual.nivel]:
            candidatos[tid] = TerritorioAtencao(
                territorio_id=tid, territorio_nome=nome, nivel=nivel, motivo=motivo
            )

    for a in avisos:
        if a.nivel in ORDEM:
            for t in a.territorios:
                considerar(t.id, t.nome_exibicao, a.nivel, f"Aviso publicado: {a.titulo}")
    for tid, nome, prioridade, estado in db.execute(
        text(
            "select a.territorio_id, t.nome_exibicao, v.prioridade, a.estado from app.avaliacoes a "
            "join app.avaliacao_versoes v on v.avaliacao_id = a.id and v.numero = a.versao_atual "
            "join app.territorios t on t.id = a.territorio_id "
            "where a.estado in ('em_revisao', 'aprovado') and v.prioridade in ('atencao', 'alerta', 'critico')"
        )
    ):
        quando = "aprovada" if estado == "aprovado" else "em revisão"
        considerar(tid, nome, prioridade, f"Avaliação {quando} sugere {ROTULO[prioridade].lower()}.")
    for tid, nome, saida in db.execute(
        text(
            "select distinct on (p.territorio_id) p.territorio_id, t.nome_exibicao, p.saida "
            "from silver.previsoes_emitidas p join app.territorios t on t.id = p.territorio_id "
            "where p.emitida_em >= :desde order by p.territorio_id, p.emitida_em desc"
        ),
        {"desde": agora - timedelta(hours=6)},
    ):
        prioridade = saida.get("prioridade")
        if prioridade in ORDEM:
            considerar(
                tid,
                nome,
                prioridade,
                f"Cenário experimental indica {ROTULO[prioridade].lower()} nas próximas horas.",
            )
    return sorted(candidatos.values(), key=lambda t: -ORDEM[t.nivel])[:5]


@router.get(
    "/resumo", response_model=ResumoPainel, summary="Avisos, revisões pendentes, territórios e fontes"
)
def resumo(
    ctx: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> ResumoPainel:
    avisos = vigentes(db, agora)
    revisa = pode(ctx.usuario.papeis, Permissao.REVISAR)
    aguardando = _aguardando(db, ctx.usuario.id) if revisa else []
    return ResumoPainel(
        avisos=avisos,
        abrigos=TotaisAbrigos(**servico_abrigos.totais_recife(db)),
        pode_revisar=revisa,
        aguardando_revisao=aguardando,
        territorios_em_atencao=_em_atencao(db, avisos, agora),
        fontes=[
            FonteSaude(id=f["id"], nome=f["nome"], status=f["status"], ultima_atualizacao=f["ultimo_sucesso"])
            for f in servico_fontes.linhas(db, agora)
        ],
        contadores=Contadores(
            avaliacoes=sum(1 for i in aguardando if i.tipo == "avaliacao"),
            comunicados=sum(1 for i in aguardando if i.tipo == "comunicado"),
        ),
    )


@router.get(
    "/situacao",
    response_model=RespostaDados[SituacaoAgora],
    summary="Situação agora: chuva recente, pico previsto, maré, risco e frescor",
)
def situacao_agora(
    territorio_id: str = Query(default="recife", description="recife, ds-1 a ds-8 (bairro vira o distrito)"),
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[SituacaoAgora]:
    t = no_maximo_distrito(db, territorio_id)
    d = decisao.situacao(db, t.usado, agora)
    dados = SituacaoAgora(territorio_id=t.usado, territorio_nome=t.nome, gerado_em=agora, **d)
    sem = [
        n
        for n, ok in (
            ("a chuva das últimas 24 h", d["chuva_24h"]["status"] == "ok"),
            ("a chuva das últimas 72 h", d["chuva_72h"]["status"] == "ok"),
            ("a previsão de chuva", d["pico"]["status"] == "ok"),
            ("a previsão de maré", d["mare"]["status"] == "ok"),
        )
        if not ok
    ]
    avisos = [*t.avisos, "Experimental: o risco é uma indicação para avaliar, não uma chance de alagar."]
    if sem:
        avisos.append("Sem dado suficiente para: " + ", ".join(sem) + ".")
    ids = ("open-meteo-historico", "open-meteo-previsao", "open-meteo-mare")
    return RespostaDados(
        dados=dados,
        meta=Meta(
            fontes=[servico_fontes.meta(db, f, agora) for f in ids],
            recorte=RecorteMeta(territorio_id=t.usado, granularidade=granularidade(t.usado)),
            avisos=avisos,
            dados_insuficientes=d["risco"]["prioridade"] == "dados_insuficientes"
            and d["pico"]["status"] != "ok"
            and d["chuva_72h"]["status"] != "ok",
        ),
    )


@router.get(
    "/acoes",
    response_model=AcoesAgora,
    summary="O que fazer agora: fila curta por urgência (revisões, publicações, avisos, fontes, territórios)",
)
def acoes_agora(
    ctx: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> AcoesAgora:
    avisos = vigentes(db, agora)
    revisa = pode(ctx.usuario.papeis, Permissao.REVISAR)
    publica = pode(ctx.usuario.papeis, Permissao.PUBLICAR)
    itens = decisao.acoes(
        db, ctx.usuario, revisa, publica, agora, avisos, _aguardando(db, ctx.usuario.id) if revisa else []
    )
    return AcoesAgora(
        gerado_em=agora,
        itens=itens,
        nota=None
        if itens
        else "Nada pendente agora. A lista considera revisões, publicações, avisos, fontes e territórios.",
    )
