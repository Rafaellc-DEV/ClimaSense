"""Avaliações territoriais (RF-10): Rascunho → Em revisão → Aprovada ou Devolvida → Encerrada.

Versões imutáveis (RN-03); estado, revisão e auditoria na mesma transação (T7.2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from climasense.dominio.fluxo_revisao import (
    Acao,
    Alvo,
    Estado,
    Situacao,
    TransicaoNegada,
    acoes_possiveis,
    aplicar,
)
from climasense.dominio.recorte import validar_territorio
from climasense.infra.modelos_sql import Avaliacao, AvaliacaoVersao, Usuario
from climasense.servicos import fluxo

ALVO = "avaliacao"
PRIORIDADES = ("sem_indicacao", "atencao", "alerta", "critico")


@dataclass(frozen=True)
class ConteudoAvaliacao:
    prioridade: str
    justificativa: str
    limitacoes: str | None
    evidencias: list[dict]


class ServicoAvaliacoes:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _obter(self, avaliacao_id: uuid.UUID, travar: bool = False) -> Avaliacao:
        consulta = select(Avaliacao).where(Avaliacao.id == avaliacao_id)
        a = self.db.scalars(consulta.with_for_update() if travar else consulta).first()
        if a is None:
            raise TransicaoNegada(404, "Avaliação não encontrada.")
        return a

    def versao(self, a: Avaliacao, numero: int | None = None) -> AvaliacaoVersao:
        v = self.db.scalars(
            select(AvaliacaoVersao).where(
                AvaliacaoVersao.avaliacao_id == a.id, AvaliacaoVersao.numero == (numero or a.versao_atual)
            )
        ).first()
        if v is None:
            raise TransicaoNegada(404, f"Versão {numero} não encontrada.")
        return v

    def _situacao(self, a: Avaliacao, v: AvaliacaoVersao) -> Situacao:
        return Situacao(Alvo.AVALIACAO, Estado(a.estado), str(v.autor_id), a.versao_atual)

    def versoes(self, avaliacao_id: uuid.UUID) -> list[dict]:
        return [
            dict(r)
            for r in self.db.execute(
                text(
                    "select v.id, v.numero, v.criado_em, v.prioridade, u.nome as autor_nome, v.autor_id "
                    "from app.avaliacao_versoes v join app.usuarios u on u.id = v.autor_id "
                    "where v.avaliacao_id = :a order by v.numero"
                ),
                {"a": avaliacao_id},
            ).mappings()
        ]

    def detalhe(self, avaliacao_id: uuid.UUID, ator: Usuario, agora: datetime) -> dict:
        a = self._obter(avaliacao_id)
        v = self.versao(a)
        versoes = self.versoes(a.id)
        return {
            "avaliacao": a,
            "versao": v,
            "autor_nome": next(x["autor_nome"] for x in versoes if x["numero"] == v.numero),
            "versoes": versoes,
            "linha_do_tempo": fluxo.linha_do_tempo(self.db, ALVO, versoes),
            "acoes": [
                x.value for x in acoes_possiveis(self._situacao(a, v), str(ator.id), ator.papeis, agora)
            ],
        }

    def listar(
        self,
        estado: str | None = None,
        territorio_id: str | None = None,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[dict]:
        linhas = self.db.execute(
            text(
                "select a.id, a.estado, a.territorio_id, t.nome_exibicao as territorio_nome, a.periodo_inicio, "
                "a.periodo_fim, a.versao_atual, a.atualizado_em, v.prioridade, v.autor_id, u.nome as autor_nome "
                "from app.avaliacoes a join app.avaliacao_versoes v on v.avaliacao_id = a.id and v.numero = a.versao_atual "
                "join app.usuarios u on u.id = v.autor_id join app.territorios t on t.id = a.territorio_id "
                "where (cast(:e as varchar) is null or a.estado = :e) "
                "and (cast(:t as varchar) is null or a.territorio_id = :t or t.pai_id = :t) "
                "and (cast(:i as date) is null or a.periodo_fim >= :i) "
                "and (cast(:f as date) is null or a.periodo_inicio <= :f) order by a.atualizado_em desc"
            ),
            {"e": estado, "t": territorio_id, "i": inicio, "f": fim},
        ).mappings()
        return [dict(r) for r in linhas]

    def _nova_versao(
        self, a: Avaliacao, numero: int, c: ConteudoAvaliacao, autor: Usuario, agora: datetime
    ) -> None:
        if c.prioridade not in PRIORIDADES:
            raise TransicaoNegada(422, "Escolha a prioridade sugerida.")
        if not c.justificativa.strip():
            raise TransicaoNegada(
                422, "Escreva a justificativa: por que este território precisa (ou não) de atenção."
            )
        self.db.add(
            AvaliacaoVersao(
                avaliacao_id=a.id,
                numero=numero,
                prioridade=c.prioridade,
                justificativa=c.justificativa.strip(),
                limitacoes=(c.limitacoes or "").strip() or None,
                evidencias=fluxo.validar_evidencias(self.db, c.evidencias),
                autor_id=autor.id,
                criado_em=agora,
            )
        )
        a.versao_atual, a.atualizado_em = numero, agora

    def criar(
        self,
        territorio_id: str,
        periodo_inicio: date,
        periodo_fim: date,
        c: ConteudoAvaliacao,
        autor: Usuario,
        ip: str | None,
        agora: datetime,
    ) -> Avaliacao:
        try:
            validar_territorio(territorio_id)
            fluxo.validar_territorios(self.db, [territorio_id])
            if periodo_inicio > periodo_fim:
                raise TransicaoNegada(422, "O início do período precisa ser antes do fim.")
            a = Avaliacao(
                id=uuid.uuid4(),
                territorio_id=territorio_id,
                periodo_inicio=periodo_inicio,
                periodo_fim=periodo_fim,
                estado=Estado.RASCUNHO.value,
                versao_atual=1,
                criado_por=autor.id,
                criado_em=agora,
                atualizado_em=agora,
            )
            self.db.add(a)
            self.db.flush()
            self._nova_versao(a, 1, c, autor, agora)
            fluxo.auditar(self.db, "avaliacao_criada", autor, ALVO, a.id, ip, versao=1)
            self.db.commit()
            return a
        except Exception:
            self.db.rollback()
            raise

    def editar(
        self, avaliacao_id: uuid.UUID, c: ConteudoAvaliacao, autor: Usuario, ip: str | None, agora: datetime
    ) -> Avaliacao:
        try:
            a = self._obter(avaliacao_id, travar=True)
            novo = aplicar(self._situacao(a, self.versao(a)), Acao.EDITAR, str(autor.id), autor.papeis, agora)
            anterior = a.estado
            self._nova_versao(a, a.versao_atual + 1, c, autor, agora)
            a.estado = novo.value
            fluxo.auditar(
                self.db,
                "avaliacao_editada",
                autor,
                ALVO,
                a.id,
                ip,
                versao=a.versao_atual,
                estado_anterior=anterior,
            )
            self.db.commit()
            return a
        except Exception:
            self.db.rollback()
            raise

    def transicao(
        self,
        avaliacao_id: uuid.UUID,
        acao: Acao,
        ator: Usuario,
        ip: str | None,
        agora: datetime,
        justificativa: str | None = None,
    ) -> Avaliacao:
        try:
            a = self._obter(avaliacao_id, travar=True)
            v = self.versao(a)
            novo = aplicar(self._situacao(a, v), acao, str(ator.id), ator.papeis, agora, justificativa)
            fluxo.registrar_revisao(self.db, ALVO, v.id, ator, acao, justificativa, agora)
            a.estado, a.atualizado_em = novo.value, agora
            fluxo.auditar(
                self.db,
                fluxo.acao_auditoria(ALVO, acao),
                ator,
                ALVO,
                a.id,
                ip,
                versao=v.numero,
                justificativa=(justificativa or "").strip() or None,
            )
            self.db.commit()
            return a
        except Exception:
            self.db.rollback()
            raise
