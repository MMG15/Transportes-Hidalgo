"""Modelos ORM (tablas). Son distintos de las entidades del dominio a propósito:
la base de datos puede cambiar sin tocar las reglas del negocio."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class _ConAuditoria:
    creado_en: Mapped[datetime] = mapped_column(default=datetime.now)


class CamionModel(_ConAuditoria, Base):
    __tablename__ = "camiones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    patente: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    marca: Mapped[str] = mapped_column(String(60))
    modelo: Mapped[str] = mapped_column(String(60))
    capacidad_tanque_litros: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    consumo_referencia_l100km: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    activo: Mapped[bool] = mapped_column(default=True)


class ChoferModel(_ConAuditoria, Base):
    __tablename__ = "choferes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    dni: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    activo: Mapped[bool] = mapped_column(default=True)


class ClienteModel(_ConAuditoria, Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(150))
    cuit: Mapped[str | None] = mapped_column(String(15))
    localidad: Mapped[str | None] = mapped_column(String(100))


class ProductoModel(_ConAuditoria, Base):
    __tablename__ = "productos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    unidad: Mapped[str] = mapped_column(String(10))


class ViajeModel(_ConAuditoria, Base):
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


class CargaCombustibleModel(_ConAuditoria, Base):
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
