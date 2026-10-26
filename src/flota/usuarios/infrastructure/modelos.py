"""Tabla de usuarios."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.infrastructure.db import Base, ConAuditoria


class UsuarioModel(ConAuditoria, Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    rol: Mapped[str] = mapped_column(String(10))
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(default=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(40))
    ultimo_acceso: Mapped[datetime | None]
