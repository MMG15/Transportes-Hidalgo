"""Tabla de tipos de cambio."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.infrastructure.db import Base, ConAuditoria


class TipoCambioModel(ConAuditoria, Base):
    __tablename__ = "tipos_cambio"
    __table_args__ = (
        UniqueConstraint("fecha", "moneda_origen", "moneda_destino", name="uq_tipos_cambio_dia"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(index=True)
    moneda_origen: Mapped[str] = mapped_column(String(3))
    moneda_destino: Mapped[str] = mapped_column(String(3))
    cotizacion: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    fuente: Mapped[str] = mapped_column(String(60))
