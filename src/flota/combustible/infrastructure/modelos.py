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
    odometro_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    estacion: Mapped[str | None] = mapped_column(String(120))
    origen: Mapped[str] = mapped_column(String(20))
    referencia_externa: Mapped[str | None] = mapped_column(String(80), unique=True)
    # Importe (RF-40): el objeto de valor ImporteGasto se guarda "aplanado" en estas columnas.
    monto_original: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    moneda: Mapped[str | None] = mapped_column(String(3))
    cotizacion: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    monto_ars: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    tipo_cambio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tipos_cambio.id", name="fk_cargas_tipo_cambio"), index=True
    )
    revisar_cotizacion: Mapped[bool] = mapped_column(default=False)
    estado_validacion: Mapped[str] = mapped_column(String(15), default="validada")
    comprobante_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comprobantes.id", name="fk_cargas_comprobante"), index=True
    )
    motivo_anulacion: Mapped[str | None] = mapped_column(String(250))
