"""Configuração do ClimaSense, lida do arquivo .env (T2.1).

Segredos ficam em `SecretStr`: não aparecem em `print`, `repr` nem em logs.
`NEON_URL` (nome usado no ETL anterior) é aceito como sinônimo de `DATABASE_URL`.
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]


class ConfiguracaoAusente(RuntimeError):
    """Uma variável obrigatória para esta operação não está no .env."""


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(RAIZ_REPOSITORIO / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ambiente: Literal["desenvolvimento", "teste", "producao"] = "desenvolvimento"
    # Prévia de pesquisa: desligada por padrão, nunca habilitada em produção.
    ml_previa_experimental_local: bool = False

    mongo_uri: SecretStr | None = None
    mongo_db_territorio: str = "Recife"

    database_url: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DATABASE_URL", "NEON_URL")
    )

    # URL do dono do banco (RNF-01, ADR 0014): só Alembic, ETL e comandos administrativos. A API usa `database_url`
    # (papel `climasense_app`, sem poder de dono). Ausente: cai em `database_url` (desenvolvimento e testes).
    database_url_migracoes: SecretStr | None = None

    session_secret: SecretStr | None = None
    sessao_inatividade_min: int = Field(default=60, ge=5, le=24 * 60)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # Proxies reversos em que se confia para ler X-Forwarded-For (IPs ou CIDRs, separados por vírgula).
    # Vazio (padrão) = ninguém: o IP do cliente é sempre o do soquete (RNF-01, T0.4).
    proxies_confiaveis: Annotated[list[str], NoDecode] = []

    # Chaves de funcionalidade fora do escopo do PRD v2 (ADR 0011, RNF-02). Desligada = rota não registrada (404).
    func_landing_publica: bool = False  # /publico/* (inclui /publico/territorios/busca)
    func_comunicados: bool = False  # /comunicados/*
    func_avaliacoes: bool = False  # /avaliacoes/*
    func_mapa_portatil: bool = False  # /territorios/mapa-portatil
    func_estatisticas_series: bool = False  # /series/estatisticas

    admin_email: str | None = None
    admin_senha_inicial: SecretStr | None = None

    supressao_minima: int = Field(default=5, ge=1)

    # Prazo de guarda (RNF-03, ADR 0015): `python -m climasense.admin limpar-retencao`.
    retencao_tentativas_login_dias: int = Field(default=90, ge=1)
    retencao_sessoes_dias: int = Field(default=30, ge=1)
    map_tiles_url: str = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"

    ana_usuario: str | None = None
    ana_senha: SecretStr | None = None

    @field_validator("cors_origins", "proxies_confiaveis", mode="before")
    @classmethod
    def _lista(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [v.strip() for v in valor.split(",") if v.strip()]
        return valor

    @field_validator("proxies_confiaveis")
    @classmethod
    def _proxies_validos(cls, valor: list[str]) -> list[str]:
        for item in valor:
            try:
                ipaddress.ip_network(item, strict=False)
            except ValueError:
                raise ValueError(f"PROXIES_CONFIAVEIS: '{item}' não é um IP nem uma faixa CIDR.") from None
        return valor

    @field_validator(
        "mongo_uri", "database_url", "session_secret", "admin_senha_inicial", "ana_senha", mode="before"
    )
    @classmethod
    def _vazio_e_nulo(cls, valor: object) -> object:
        return None if isinstance(valor, str) and not valor.strip() else valor

    # --- acesso obrigatório: mensagem clara, sem jamais mostrar o valor ---------------------------
    def exigir(self, campo: str) -> str:
        valor = getattr(self, campo)
        if valor is None:
            raise ConfiguracaoAusente(f"Configure {campo.upper()} no arquivo .env.")
        return valor.get_secret_value() if isinstance(valor, SecretStr) else str(valor)

    @property
    def redes_proxy(self) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        return [ipaddress.ip_network(p, strict=False) for p in self.proxies_confiaveis]

    @property
    def em_producao(self) -> bool:
        return self.ambiente == "producao"


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
