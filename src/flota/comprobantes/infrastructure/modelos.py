"""Tabla de comprobantes."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.infrastructure.auditoria import JsonFlexible
from flota.shared.infrastructure.db import Base


class ComprobanteModel(Base):
    __tablename__ = "comprobantes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(15))
    canal: Mapped[str] = mapped_column(String(15))
    archivo: Mapped[str] = mapped_column(String(255))
    tipo_mime: Mapped[str] = mapped_column(String(50))
    recibido_en: Mapped[datetime] = mapped_column(index=True)
    estado: Mapped[str] = mapped_column(String(15), index=True)
    chofer_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    camion_id: Mapped[uuid.UUID | None]
    datos_extraidos: Mapped[dict | None] = mapped_column(JsonFlexible)  # RF-03: JSON de la IA
    confianza: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    problemas: Mapped[list] = mapped_column(JsonFlexible, default=list)
    registro_id: Mapped[uuid.UUID | None]
    motivo_descarte: Mapped[str | None] = mapped_column(String(250))
