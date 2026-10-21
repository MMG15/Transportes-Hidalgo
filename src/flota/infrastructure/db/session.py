from __future__ import annotations

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from flota.infrastructure.config import get_settings


def crear_engine(url: URL | str | None = None) -> Engine:
    # pool_pre_ping verifica que la conexión siga viva antes de usarla.
    return create_engine(url or get_settings().url_db(), pool_pre_ping=True)


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False: los datos leídos siguen disponibles después del commit.
    return sessionmaker(engine, expire_on_commit=False)
