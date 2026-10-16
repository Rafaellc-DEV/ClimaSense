"""Comunicados (RF-11): rascunho → revisão → aprovado → publicado → encerrado, com versões imutáveis e hash.

Cada mudança de estado grava a revisão (quando há decisão) e a auditoria na MESMA transação: ou tudo
acontece, ou nada (T7.2/T7.3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from climasense.dominio import comunicado as dominio
from climasense.dominio.fluxo_revisao import (
    Acao,
    Alvo,
    Estado,
    Situacao,
    TransicaoNegada,
    acoes_possiveis,
    aplicar,
)
from climasense.infra.modelos_sql import Comunicado, ComunicadoVersao, Usuario
from climasense.servicos import fluxo

ALVO = "comunicado"


def _conteudo(v: ComunicadoVersao) -> dominio.Conteudo:
    return dominio.Conteudo(
        titulo=v.titulo,
        texto=v.texto,
        orientacoes=tuple(v.orientacoes),
        territorios=tuple(v.territorios),
        publico=v.publico,
        nivel=v.nivel,
        validade_inicio=v.validade_inicio,
        validade_fim=v.validade_fim,
    )


class ServicoComunicados:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ leitura
    def _obter(self, comunicado_id: uuid.UUID, travar: bool = False) -> Comunicado:
        consulta = select(Comunicado).where(Comunicado.id == comunicado_id)
        c = self.db.scalars(consulta.with_for_update() if travar else consulta).first()
        if c is None:
            raise TransicaoNegada(404, "Comunicado não encontrado.")
        return c

    def versao(self, c: Comunicado, numero: int | None = None) -> ComunicadoVersao:
        v = self.db.scalars(
            select(ComunicadoVersao).where(
                ComunicadoVersao.comunicado_id == c.id, ComunicadoVersao.numero == (numero or c.versao_atual)
            )
        ).first()
        if v is None:
            raise TransicaoNegada(404, f"Versão {numero} não encontrada.")
        return v

    def _situacao(self, c: Comunicado, v: ComunicadoVersao) -> Situacao:
        return Situacao(
            Alvo.COMUNICADO,
            Estado(c.estado),
            str(v.autor_id),
            c.versao_atual,
            c.versao_aprovada,
            c.validade_fim,
        )

    def versoes(self, comunicado_id: uuid.UUID) -> list[dict]:
        linhas = self.db.execute(
            text(
                "select v.id, v.numero, v.criado_em, v.hash_conteudo, v.titulo, u.nome as autor_nome, v.autor_id "
                "from app.comunicado_versoes v join app.usuarios u on u.id = v.autor_id "
                "where v.comunicado_id = :c order by v.numero"
            ),
            {"c": comunicado_id},
        ).mappings()
        return [dict(r) for r in linhas]

    def detalhe(self, comunicado_id: uuid.UUID, ator: Usuario, agora: datetime) -> dict:
        c = self._obter(comunicado_id)
        v = self.versao(c)
        versoes = self.versoes(c.id)
        return {
            "comunicado": c,
            "versao": v,
            "autor_nome": next(x["autor_nome"] for x in versoes if x["numero"] == v.numero),
            "versoes": versoes,
            "linha_do_tempo": fluxo.linha_do_tempo(self.db, ALVO, versoes),
            "acoes": [
                a.value for a in acoes_possiveis(self._situacao(c, v), str(ator.id), ator.papeis, agora)
            ],
            "frases_longas": dominio.frases_longas(v.texto),
        }

    def listar(self, estado: str | None = None, territorio_id: str | None = None) -> list[dict]:
        linhas = self.db.execute(
            text(
                "select c.id, c.estado, c.nivel, c.territorios, c.validade_inicio, c.validade_fim, c.versao_atual, "
                "c.atualizado_em, c.publicado_em, v.titulo, v.autor_id, u.nome as autor_nome "
                "from app.comunicados c join app.comunicado_versoes v on v.comunicado_id = c.id and v.numero = c.versao_atual "
                "join app.usuarios u on u.id = v.autor_id "
                "where (cast(:e as varchar) is null or c.estado = :e) "
                "and (cast(:t as varchar) is null or :t = any(c.territorios)) order by c.atualizado_em desc"
            ),
            {"e": estado, "t": territorio_id},
        ).mappings()
        return [dict(r) for r in linhas]

    def diferenca(self, comunicado_id: uuid.UUID, a: int, b: int) -> dict:
        c = self._obter(comunicado_id)
        va, vb = _conteudo(self.versao(c, a)), _conteudo(self.versao(c, b))
        campos = {
            "titulo": (va.titulo, vb.titulo),
            "texto": (va.texto, vb.texto),
            "orientacoes": ("\n".join(va.orientacoes), "\n".join(vb.orientacoes)),
        }
        metadados = {
            "nivel": (va.nivel, vb.nivel),
            "territorios": (", ".join(va.territorios), ", ".join(vb.territorios)),
            "publico": (va.publico, vb.publico),
            "validade_inicio": (
                va.validade_inicio.astimezone(UTC).isoformat(),
                vb.validade_inicio.astimezone(UTC).isoformat(),
            ),
            "validade_fim": (
                va.validade_fim.astimezone(UTC).isoformat(),
                vb.validade_fim.astimezone(UTC).isoformat(),
            ),
        }
        return {
            "de": a,
            "para": b,
            "campos": {k: dominio.diferenca(x, y) for k, (x, y) in campos.items()},
            "alterados": [k for k, (x, y) in {**campos, **metadados}.items() if x != y],
            "metadados": {k: {"antes": x, "depois": y} for k, (x, y) in metadados.items() if x != y},
        }

    # ------------------------------------------------------------------ escrita
    def _nova_versao(
        self,
        c: Comunicado,
        numero: int,
        conteudo: dominio.Conteudo,
        evidencias: list[dict],
        autor: Usuario,
        agora: datetime,
    ) -> ComunicadoVersao:
        erros = dominio.problemas(conteudo)
        if erros:
            raise TransicaoNegada(422, " ".join(erros))
        fluxo.validar_territorios(self.db, list(conteudo.territorios))
        v = ComunicadoVersao(
            comunicado_id=c.id,
            numero=numero,
            titulo=conteudo.titulo.strip(),
            texto=conteudo.texto.strip(),
            orientacoes=[o.strip() for o in conteudo.orientacoes if o.strip()],
            evidencias=fluxo.validar_evidencias(self.db, evidencias),
            autor_id=autor.id,
            criado_em=agora,
            territorios=list(conteudo.territorios),
            publico=conteudo.publico,
            nivel=conteudo.nivel,
            validade_inicio=conteudo.validade_inicio,
            validade_fim=conteudo.validade_fim,
            hash_conteudo="",
        )
        v.hash_conteudo = _conteudo(v).hash()
        c.territorios, c.publico, c.nivel = v.territorios, v.publico, v.nivel
        c.validade_inicio, c.validade_fim = v.validade_inicio, v.validade_fim
        c.versao_atual, c.atualizado_em = numero, agora
        self.db.add(v)
        return v

    def criar(
        self,
        conteudo: dominio.Conteudo,
        evidencias: list[dict],
        autor: Usuario,
        ip: str | None,
        agora: datetime,
        avaliacao_id: uuid.UUID | None = None,
    ) -> Comunicado:
        try:
            c = Comunicado(
                id=uuid.uuid4(),
                estado=Estado.RASCUNHO.value,
                territorios=list(conteudo.territorios),
                publico=conteudo.publico,
                nivel=conteudo.nivel,
                validade_inicio=conteudo.validade_inicio,
                validade_fim=conteudo.validade_fim,
                versao_atual=1,
                avaliacao_id=avaliacao_id,
                criado_por=autor.id,
                criado_em=agora,
                atualizado_em=agora,
            )
            self.db.add(c)
            self.db.flush()
            self._nova_versao(c, 1, conteudo, evidencias, autor, agora)
            fluxo.auditar(self.db, "comunicado_criado", autor, ALVO, c.id, ip, versao=1)
            self.db.commit()
            return c
        except Exception:
            self.db.rollback()
            raise

    def editar(
        self,
        comunicado_id: uuid.UUID,
        conteudo: dominio.Conteudo,
        evidencias: list[dict],
        autor: Usuario,
        ip: str | None,
        agora: datetime,
    ) -> Comunicado:
        try:
            c = self._obter(comunicado_id, travar=True)
            atual = self.versao(c)
            novo = aplicar(self._situacao(c, atual), Acao.EDITAR, str(autor.id), autor.papeis, agora)
            estado_anterior = c.estado
            self._nova_versao(c, c.versao_atual + 1, conteudo, evidencias, autor, agora)
            c.estado = novo.value
            if estado_anterior == Estado.PUBLICADO:
                c.publicado_em = c.publicado_por = None  # sai da landing até nova aprovação
            fluxo.auditar(
                self.db,
                "comunicado_editado",
                autor,
                ALVO,
                c.id,
                ip,
                versao=c.versao_atual,
                estado_anterior=estado_anterior,
            )
            self.db.commit()
            return c
        except Exception:
            self.db.rollback()
            raise

    def transicao(
        self,
        comunicado_id: uuid.UUID,
        acao: Acao,
        ator: Usuario,
        ip: str | None,
        agora: datetime,
        justificativa: str | None = None,
    ) -> Comunicado:
        try:
            c = self._obter(comunicado_id, travar=True)
            v = self.versao(c)
            novo = aplicar(self._situacao(c, v), acao, str(ator.id), ator.papeis, agora, justificativa)
            if acao is Acao.PUBLICAR and _conteudo(v).hash() != v.hash_conteudo:
                raise TransicaoNegada(
                    409, "O conteúdo não confere com a versão aprovada. Envie para revisão de novo."
                )
            fluxo.registrar_revisao(self.db, ALVO, v.id, ator, acao, justificativa, agora)
            c.estado = novo.value
            c.atualizado_em = agora
            if acao is Acao.APROVAR:
                c.versao_aprovada = v.numero
            if acao is Acao.PUBLICAR:
                c.publicado_em, c.publicado_por = agora, ator.id
            fluxo.auditar(
                self.db,
                fluxo.acao_auditoria(ALVO, acao),
                ator,
                ALVO,
                c.id,
                ip,
                versao=v.numero,
                hash=v.hash_conteudo,
                justificativa=(justificativa or "").strip() or None,
            )
            self.db.commit()
            return c
        except Exception:
            self.db.rollback()
            raise


def expirar_vencidos(db: Session, agora: datetime) -> int:
    """Encerra os publicados cuja validade terminou (RF-11.6). Roda a cada minuto na API (T7.5)."""
    vencidos = db.execute(
        text(
            "update app.comunicados set estado = 'encerrado', atualizado_em = :a "
            "where estado = 'publicado' and validade_fim <= :a returning id"
        ),
        {"a": agora},
    ).all()
    for (cid,) in vencidos:
        fluxo.auditar(db, "comunicado_expirado", None, ALVO, cid, None)
    db.commit()
    return len(vencidos)
