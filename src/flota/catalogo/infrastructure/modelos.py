"""Tablas del catálogo."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.infrastructure.db import Base, ConAuditoria


class CamionModel(ConAuditoria, Base):
    __tablename__ = "camiones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    patente: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    marca: Mapped[str] = mapped_column(String(60))
    modelo: Mapped[str] = mapped_column(String(60))
    capacidad_tanque_litros: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    consumo_referencia_l100km: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    activo: Mapped[bool] = mapped_column(default=True)


class ChoferModel(ConAuditoria, Base):
    __tablename__ = "choferes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    dni: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    activo: Mapped[bool] = mapped_column(default=True)


class ClienteModel(ConAuditoria, Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(150))
    cuit: Mapped[str | None] = mapped_column(String(15))
    localidad: Mapped[str | None] = mapped_column(String(100))


class ProductoModel(ConAuditoria, Base):
    __tablename__ = "productos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    unidad: Mapped[str] = mapped_column(String(10))
