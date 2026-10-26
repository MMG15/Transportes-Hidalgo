"""Base de los modelos ORM, motor de base de datos y repositorio SQL genérico.

Los modelos ORM (tablas) son distintos de las entidades del dominio a propósito:
la base de datos puede cambiar sin tocar las reglas del negocio.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import URL, Engine, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from flota.shared.infrastructure.config import get_settings


class Base(DeclarativeBase):
    pass


class ConAuditoria:
    """Mixin: agrega la fecha de creación a todas las tablas."""

    creado_en: Mapped[datetime] = mapped_column(default=datetime.now)


def crear_engine(url: URL | str | None = None) -> Engine:
    # pool_pre_ping verifica que la conexión siga viva antes de usarla.
    return create_engine(url or get_settings().url_db(), pool_pre_ping=True)


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False: los datos leídos siguen disponibles después del commit.
    return sessionmaker(engine, expire_on_commit=False)


class RepositorioSql[E, M]:
    """Implementación genérica: guardar/obtener/listar + conversión entidad <-> modelo.

    La conversión por defecto funciona cuando la entidad y el modelo usan los mismos nombres
    de campo; si no, la subclase redefine `_a_entidad` / `_a_modelo`.
    """

    entidad: ClassVar[type]
    modelo: ClassVar[type]
    # Debe ser una expresión (.asc() / .desc()), no la columna sola: una columna es un
    # descriptor y, leída como self.orden, SQLAlchemy intentaría resolverla sobre el repositorio.
    orden: ClassVar[Any]

    def __init__(self, session: Session) -> None:
        self._s = session

    def guardar(self, entidad: E) -> None:
        self._s.merge(self._a_modelo(entidad))  # merge = INSERT o UPDATE según exista
        self._s.flush()

    def obtener(self, id: UUID) -> E | None:
        modelo = self._s.get(self.modelo, id)
        return self._a_entidad(modelo) if modelo else None

    def listar(self, limite: int = 100, desplazamiento: int = 0) -> list[E]:
        stmt = select(self.modelo).order_by(self.orden).limit(limite).offset(desplazamiento)
        return self._todos(stmt)

    def _todos(self, stmt) -> list[E]:
        return [self._a_entidad(m) for m in self._s.scalars(stmt)]

    def _uno(self, stmt) -> E | None:
        modelo = self._s.scalars(stmt.limit(1)).first()
        return self._a_entidad(modelo) if modelo else None

    def _a_entidad(self, modelo: M) -> E:
        return self.entidad(**{f.name: getattr(modelo, f.name) for f in fields(self.entidad)})

    def _a_modelo(self, entidad: E) -> M:
        return self.modelo(**{f.name: getattr(entidad, f.name) for f in fields(entidad)})
