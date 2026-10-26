"""Esquemas Pydantic del catálogo: validan lo que entra por HTTP y definen lo que sale en JSON."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from flota.shared.presentation.esquemas import Esquema, Numero


class CamionCrear(BaseModel):
    patente: str = Field(min_length=6, max_length=15, examples=["AB123CD"])
    marca: str = Field(examples=["Scania"])
    modelo: str = Field(examples=["R450"])
    capacidad_tanque_litros: Decimal = Field(gt=0, examples=[600])
    consumo_referencia_l100km: Decimal = Field(gt=0, examples=[38])


class CamionLeer(Esquema):
    id: UUID
    patente: str
    marca: str
    modelo: str
    capacidad_tanque_litros: Numero
    consumo_referencia_l100km: Numero
    activo: bool


class ChoferCrear(BaseModel):
    nombre: str = Field(examples=["Juan Pérez"])
    dni: str = Field(examples=["30123456"])


class ChoferLeer(Esquema):
    id: UUID
    nombre: str
    dni: str
    activo: bool


class ClienteCrear(BaseModel):
    razon_social: str = Field(examples=["Agropecuaria San José S.A."])
    cuit: str | None = Field(default=None, examples=["30-71234567-8"])
    localidad: str | None = Field(default=None, examples=["Pergamino"])


class ClienteLeer(Esquema):
    id: UUID
    razon_social: str
    cuit: str | None
    localidad: str | None


class ProductoCrear(BaseModel):
    nombre: str = Field(examples=["Cal viva"])
    unidad: str = Field(default="tn", examples=["tn"])


class ProductoLeer(Esquema):
    id: UUID
    nombre: str
    unidad: str
