"""Configuración leída de variables de entorno / archivo .env (pydantic-settings)."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_PROYECTO / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "flota"

    umbral_desvio_pct: Decimal = Decimal("15")
    tolerancia_tanque_pct: Decimal = Decimal("5")

    def url_db(self, database: str | None = None) -> URL | str:
        """URL de conexión. `URL.create` escapa caracteres especiales de la contraseña."""
        if self.database_url and database is None:
            return self.database_url
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=database or self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
