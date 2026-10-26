"""Esquemas Pydantic de viajes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from flota.shared.presentation.esquemas import Esquema, Numero
from flota.viajes.domain.entidades import EstadoViaje


class ViajeCrear(BaseModel):
    camion_id: UUID
    chofer_id: UUID
    cliente_id: UUID
    producto_id: UUID
    origen: str = Field(examples=["Planta Olavarría"])
    destino: str = Field(examples=["Campo La Esperanza"])
    cantidad: Decimal = Field(gt=0, examples=[28])
    fecha_salida: datetime
    km_salida: Decimal = Field(ge=0, examples=[125000])
    observaciones: str | None = None


class ViajeFinalizar(BaseModel):
    fecha_llegada: datetime
    km_llegada: Decimal = Field(gt=0, examples=[125420])


class ViajeLeer(Esquema):
    id: UUID
    camion_id: UUID
    chofer_id: UUID
    cliente_id: UUID
    producto_id: UUID
    origen: str
    destino: str
    cantidad: Numero
    fecha_salida: datetime
    km_salida: Numero
    fecha_llegada: datetime | None
    km_llegada: Numero | None
    km_recorridos: Numero | None
    estado: EstadoViaje
    observaciones: str | None
