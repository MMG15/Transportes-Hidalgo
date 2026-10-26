"""Tabla única de alertas (todos los tipos): el registro de origen se identifica con tabla + id."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.infrastructure.db import Base


class AlertaModel(Base):
    __tablename__ = "alertas"
    __table_args__ = (Index("ix_alertas_origen", "tipo", "origen_tabla", "origen_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))
    origen_tabla: Mapped[str] = mapped_column(String(40))
    origen_id: Mapped[uuid.UUID]
    descripcion: Mapped[str] = mapped_column(Text)
    creada_en: Mapped[datetime] = mapped_column(index=True)
    valor_detectado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    valor_referencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    # Sin claves foráneas a propósito: una alerta puede venir de cualquier módulo.
    camion_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    viaje_id: Mapped[uuid.UUID | None]
    estado: Mapped[str] = mapped_column(String(20), index=True)
    comentario: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[uuid.UUID | None]
    resuelta_en: Mapped[datetime | None]
    escalada: Mapped[bool] = mapped_column(default=False)
