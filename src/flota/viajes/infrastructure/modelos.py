"""Tablas de viajes."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.infrastructure.db import Base, ConAuditoria


class ViajeModel(ConAuditoria, Base):
    __tablename__ = "viajes"
    __table_args__ = (Index("ix_viajes_camion_fecha", "camion_id", "fecha_salida"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    camion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("camiones.id"))
    chofer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("choferes.id"))
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"))
    origen: Mapped[str] = mapped_column(String(150))
    destino: Mapped[str] = mapped_column(String(150))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fecha_salida: Mapped[datetime] = mapped_column(index=True)
    km_salida: Mapped[Decimal] = mapped_column(Numeric(10, 1))
    fecha_llegada: Mapped[datetime | None]
    km_llegada: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    observaciones: Mapped[str | None] = mapped_column(Text)
