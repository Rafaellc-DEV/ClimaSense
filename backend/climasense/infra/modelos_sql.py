"""Modelos SQLAlchemy do esquema `app` (design §5.3). As migrações em `backend/migrations` são a fonte da verdade
do banco; estes modelos espelham as tabelas para uso nos repositórios."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _agora():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(Text)
    papeis: Mapped[list[str]] = mapped_column(ARRAY(String(20)))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    troca_senha_obrigatoria: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = _agora()
    atualizado_em: Mapped[datetime] = _agora()


class Sessao(Base):
    __tablename__ = "sessoes"
    __table_args__ = {"schema": "app"}
    id_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.usuarios.id"))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    criada_em: Mapped[datetime] = _agora()
    ultimo_uso: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogada: Mapped[bool] = mapped_column(Boolean, default=False)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)


class TentativaLogin(Base):
    __tablename__ = "tentativas_login"
    __table_args__ = {"schema": "app"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254))
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sucesso: Mapped[bool] = mapped_column(Boolean)


class Territorio(Base):
    __tablename__ = "territorios"
    __table_args__ = {"schema": "app"}
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10))
    nome_oficial: Mapped[str] = mapped_column(String(120))
    nome_exibicao: Mapped[str] = mapped_column(String(120))
    pai_id: Mapped[str | None] = mapped_column(ForeignKey("app.territorios.id"), nullable=True)
    codigo_oficial: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Fonte(Base):
    __tablename__ = "fontes"
    __table_args__ = {"schema": "app"}
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    orgao: Mapped[str] = mapped_column(String(160))
    url: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(10))
    licenca: Mapped[str | None] = mapped_column(String(120), nullable=True)
    conector: Mapped[str] = mapped_column(String(120))
    limite_desatualizacao_h: Mapped[int] = mapped_column(Integer, default=24)
    min_observacoes: Mapped[int] = mapped_column(Integer, default=30)
    implementada: Mapped[bool] = mapped_column(Boolean, default=False)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)


class EtlExecucao(Base):
    __tablename__ = "etl_execucoes"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fonte_id: Mapped[str] = mapped_column(ForeignKey("app.fontes.id"))
    inicio: Mapped[datetime] = _agora()
    fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(15))
    lidos: Mapped[int] = mapped_column(Integer, default=0)
    gravados: Mapped[int] = mapped_column(Integer, default=0)
    descartados: Mapped[int] = mapped_column(Integer, default=0)
    motivos_descarte: Mapped[dict] = mapped_column(JSONB, default=dict)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    disparado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app.usuarios.id"), nullable=True)


class Avaliacao(Base):
    __tablename__ = "avaliacoes"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    territorio_id: Mapped[str] = mapped_column(ForeignKey("app.territorios.id"))
    periodo_inicio: Mapped[date] = mapped_column(Date)
    periodo_fim: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(15))
    versao_atual: Mapped[int] = mapped_column(Integer, default=1)
    criado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.usuarios.id"))
    criado_em: Mapped[datetime] = _agora()
    atualizado_em: Mapped[datetime] = _agora()


class AvaliacaoVersao(Base):
    __tablename__ = "avaliacao_versoes"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    avaliacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.avaliacoes.id"))
    numero: Mapped[int] = mapped_column(Integer)
    prioridade: Mapped[str] = mapped_column(String(20))
    justificativa: Mapped[str] = mapped_column(Text)
    limitacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidencias: Mapped[list] = mapped_column(JSONB, default=list)
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.usuarios.id"))
    criado_em: Mapped[datetime] = _agora()


class Comunicado(Base):
    __tablename__ = "comunicados"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estado: Mapped[str] = mapped_column(String(15))
    territorios: Mapped[list[str]] = mapped_column(ARRAY(String(80)))
    publico: Mapped[str] = mapped_column(String(40))
    nivel: Mapped[str] = mapped_column(String(15))
    validade_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validade_fim: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    versao_atual: Mapped[int] = mapped_column(Integer, default=1)
    versao_aprovada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publicado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app.usuarios.id"), nullable=True)
    avaliacao_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app.avaliacoes.id"), nullable=True)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app.usuarios.id"), nullable=True)
    criado_em: Mapped[datetime] = _agora()
    atualizado_em: Mapped[datetime] = _agora()


class ComunicadoVersao(Base):
    __tablename__ = "comunicado_versoes"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comunicado_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.comunicados.id"))
    numero: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(120))
    texto: Mapped[str] = mapped_column(String(1200))
    orientacoes: Mapped[list[str]] = mapped_column(ARRAY(String(300)))
    evidencias: Mapped[list] = mapped_column(JSONB, default=list)
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.usuarios.id"))
    criado_em: Mapped[datetime] = _agora()
    hash_conteudo: Mapped[str] = mapped_column(String(64))
    territorios: Mapped[list[str]] = mapped_column(ARRAY(String(80)))
    publico: Mapped[str] = mapped_column(String(40))
    nivel: Mapped[str] = mapped_column(String(15))
    validade_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validade_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Revisao(Base):
    __tablename__ = "revisoes"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alvo: Mapped[str] = mapped_column(String(12))
    versao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    revisor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.usuarios.id"))
    decisao: Mapped[str] = mapped_column(String(10))
    justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    em: Mapped[datetime] = _agora()


class RegistroAuditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = {"schema": "app"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    em: Mapped[datetime] = _agora()
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    acao: Mapped[str] = mapped_column(String(60))
    alvo_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    alvo_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    detalhes: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
