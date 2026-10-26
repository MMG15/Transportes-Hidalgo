"""Tablas de rutas, viajes y tramos."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flota.shared.infrastructure.db import Base, ConAuditoria


class RutaModel(ConAuditoria, Base):
    __tablename__ = "rutas"
    __table_args__ = (UniqueConstraint("origen", "destino", name="uq_rutas_origen_destino"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    origen: Mapped[str] = mapped_column(String(150))
    destino: Mapped[str] = mapped_column(String(150))
    pais: Mapped[str] = mapped_column(String(2))
    km_estimados: Mapped[Decimal | None] = mapped_column(Numeric(8, 1))
    ref_l100_cargado: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    ref_l100_vacio: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    activa: Mapped[bool] = mapped_column(default=True)


class ViajeModel(ConAuditoria, Base):
    __tablename__ = "viajes"
    __table_args__ = (Index("ix_viajes_camion_fecha", "camion_id", "fecha_salida"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    camion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("camiones.id"))
    chofer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("choferes.id"))
    ruta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rutas.id", name="fk_viajes_ruta_id_rutas"), index=True
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clientes.id"))
    producto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    fecha_salida: Mapped[datetime] = mapped_column(index=True)
    km_salida: Mapped[Decimal] = mapped_column(Numeric(10, 1))
    origen_km: Mapped[str] = mapped_column(String(10), default="manual")
    fecha_llegada: Mapped[datetime | None]
    km_llegada: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    observaciones: Mapped[str | None] = mapped_column(Text)

    # cascade "delete-orphan": un tramo que se saca de la lista se borra de la base.
    # lazy="selectin": los tramos se leen en una sola consulta extra para todos los viajes.
    tramos: Mapped[list[TramoViajeModel]] = relationship(
        cascade="all, delete-orphan", order_by="TramoViajeModel.orden", lazy="selectin"
    )


class TramoViajeModel(Base):
    __tablename__ = "tramos_viaje"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    viaje_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("viajes.id", ondelete="CASCADE"), index=True
    )
    orden: Mapped[int]
    estado_carga: Mapped[str] = mapped_column(String(10))
    fecha_inicio: Mapped[datetime]
    km_inicio: Mapped[Decimal] = mapped_column(Numeric(10, 1))
    fecha_fin: Mapped[datetime | None]
    km_fin: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
