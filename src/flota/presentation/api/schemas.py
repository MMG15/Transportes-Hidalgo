"""Esquemas Pydantic: validan lo que entra por HTTP y definen lo que sale en JSON."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from flota.domain.entities import EstadoViaje, OrigenDato

# Los Decimal se envían como número en el JSON (por defecto Pydantic los manda como texto).
Numero = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Esquema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Catálogo ----------
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


# ---------- Viajes ----------
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


class ConsumoLeer(Esquema):
    viaje_id: UUID
    camion_id: UUID
    km_recorridos: Numero | None
    litros: Numero
    costo: Numero | None
    consumo_l100km: Numero | None
    consumo_referencia_l100km: Numero
    desvio_pct: Numero | None
    litros_por_unidad: Numero | None
    alerta: bool


# ---------- Combustible ----------
class CargaCrear(BaseModel):
    camion_id: UUID
    fecha: datetime
    litros: Decimal = Field(gt=0, examples=[350])
    precio_litro: Decimal | None = Field(default=None, ge=0, examples=[1450])
    odometro_km: Decimal | None = Field(default=None, ge=0)
    estacion: str | None = None
    referencia_externa: str | None = Field(default=None, examples=["T-000123"])
    viaje_id: UUID | None = None


class CargaLeer(Esquema):
    id: UUID
    camion_id: UUID
    viaje_id: UUID | None
    fecha: datetime
    litros: Numero
    precio_litro: Numero | None
    importe: Numero | None
    odometro_km: Numero | None
    estacion: str | None
    origen: OrigenDato
    referencia_externa: str | None


class ResultadoImportacionLeer(Esquema):
    procesadas: int
    importadas: int
    duplicadas: int
    errores: list[str]


# ---------- Reportes ----------
class FilaReporteLeer(Esquema):
    viaje_id: UUID
    fecha_salida: datetime
    fecha_llegada: datetime | None
    estado: str
    patente: str
    chofer: str
    cliente: str
    producto: str
    unidad: str
    origen: str
    destino: str
    cantidad: Numero
    km_recorridos: Numero | None
    litros: Numero
    costo: Numero | None
    consumo_l100km: Numero | None
    consumo_referencia_l100km: Numero
    desvio_pct: Numero | None
    litros_por_unidad: Numero | None
    alerta: bool


class ResumenCamionLeer(Esquema):
    patente: str
    viajes: int
    km_recorridos: Numero
    litros: Numero
    costo: Numero
    consumo_promedio_l100km: Numero | None
    consumo_referencia_l100km: Numero
    desvio_pct: Numero | None
    viajes_con_alerta: int


class ReporteLeer(Esquema):
    filas: list[FilaReporteLeer]
    resumen_por_camion: list[ResumenCamionLeer]
