"""Configuração do ClimaSense, lida do arquivo .env (T2.1).

Segredos ficam em `SecretStr`: não aparecem em `print`, `repr` nem em logs.
`NEON_URL` (nome usado no ETL anterior) é aceito como sinônimo de `DATABASE_URL`.
"""

from __future__ import annotations

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

    mongo_uri: SecretStr | None = None
    mongo_db_territorio: str = "Recife"
    mongo_db_bronze_vacinacao: str = "vacinacao"

    database_url: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DATABASE_URL", "NEON_URL")
    )

    session_secret: SecretStr | None = None
    sessao_inatividade_min: int = Field(default=60, ge=5, le=24 * 60)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    admin_email: str | None = None
    admin_senha_inicial: SecretStr | None = None

    etl_limite_vacinacao: int = Field(default=5000, ge=1)
    supressao_minima: int = Field(default=5, ge=1)
    map_tiles_url: str = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"

    ana_usuario: str | None = None
    ana_senha: SecretStr | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _lista(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [v.strip() for v in valor.split(",") if v.strip()]
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
    def em_producao(self) -> bool:
        return self.ambiente == "producao"


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
