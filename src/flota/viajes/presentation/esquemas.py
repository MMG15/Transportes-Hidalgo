"""Esquemas Pydantic de rutas y viajes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from flota.shared.presentation.esquemas import Esquema, Numero
from flota.viajes.domain.entidades import EstadoCarga, EstadoViaje, OrigenKm, Pais


# ---------- Rutas ----------
class RutaCrear(BaseModel):
    origen: str = Field(examples=["Planta Albardón (SJ)"])
    destino: str = Field(examples=["Los Andes (CL)"])
    pais: Pais = Pais.AR
    km_estimados: Decimal | None = Field(default=None, gt=0, examples=[390])
    ref_l100_cargado: Decimal | None = Field(default=None, gt=0, examples=[48])
    ref_l100_vacio: Decimal | None = Field(default=None, gt=0, examples=[34])
    activa: bool = True


class RutaLeer(Esquema):
    id: UUID
    nombre: str
    origen: str
    destino: str
    pais: Pais
    km_estimados: Numero | None
    ref_l100_cargado: Numero | None
    ref_l100_vacio: Numero | None
    activa: bool


# ---------- Viajes ----------
class ViajeCrear(BaseModel):
    camion_id: UUID
    chofer_id: UUID
    ruta_id: UUID
    fecha_salida: datetime
    km_salida: Decimal = Field(ge=0, examples=[125000])
    estado_carga: EstadoCarga = EstadoCarga.CARGADO
    cliente_id: UUID | None = None
    producto_id: UUID | None = None
    cantidad: Decimal | None = Field(default=None, gt=0, examples=[28])
    origen_km: OrigenKm = OrigenKm.MANUAL
    observaciones: str | None = None


class CambioEstadoCarga(BaseModel):
    fecha: datetime
    km: Decimal = Field(gt=0, examples=[125390])
    estado_carga: EstadoCarga = EstadoCarga.VACIO


class ViajeFinalizar(BaseModel):
    fecha_llegada: datetime
    km_llegada: Decimal = Field(gt=0, examples=[125780])


class TramoLeer(Esquema):
    id: UUID
    estado_carga: EstadoCarga
    fecha_inicio: datetime
    km_inicio: Numero
    fecha_fin: datetime | None
    km_fin: Numero | None
    km_recorridos: Numero | None


class ViajeLeer(Esquema):
    id: UUID
    camion_id: UUID
    chofer_id: UUID
    ruta_id: UUID
    cliente_id: UUID | None
    producto_id: UUID | None
    cantidad: Numero | None
    fecha_salida: datetime
    km_salida: Numero
    origen_km: OrigenKm
    fecha_llegada: datetime | None
    km_llegada: Numero | None
    km_recorridos: Numero | None
    estado: EstadoViaje
    observaciones: str | None
    tramos: list[TramoLeer]
