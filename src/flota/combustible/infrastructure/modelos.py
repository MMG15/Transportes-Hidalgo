"""Tablas de combustible."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.infrastructure.db import Base, ConAuditoria


class CargaCombustibleModel(ConAuditoria, Base):
    __tablename__ = "cargas_combustible"
    __table_args__ = (Index("ix_cargas_camion_fecha", "camion_id", "fecha"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    camion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("camiones.id"))
    viaje_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("viajes.id"), index=True)
    fecha: Mapped[datetime]
    litros: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    precio_litro: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    odometro_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    estacion: Mapped[str | None] = mapped_column(String(120))
    origen: Mapped[str] = mapped_column(String(20))
    referencia_externa: Mapped[str | None] = mapped_column(String(80), unique=True)
