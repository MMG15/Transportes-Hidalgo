"""Objetos de transferencia de datos (DTO) que cruzan los límites de la capa de aplicación."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class FilaCarga:
    """Una fila leída de un archivo externo (Excel, CSV de tarjeta, ...)."""

    numero_fila: int
    fecha: datetime
    patente: str
    litros: Decimal
    precio_litro: Decimal | None = None
    odometro_km: Decimal | None = None
    estacion: str | None = None
    referencia: str | None = None


@dataclass(frozen=True)
class ErrorLectura:
    numero_fila: int
    mensaje: str


@dataclass
class ResultadoImportacion:
    procesadas: int = 0
    importadas: int = 0
    duplicadas: int = 0
    errores: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FilaReporteConsumo:
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
    cantidad: Decimal
    km_recorridos: Decimal | None
    litros: Decimal
    costo: Decimal | None
    consumo_l100km: Decimal | None
    consumo_referencia_l100km: Decimal
    desvio_pct: Decimal | None
    litros_por_unidad: Decimal | None
    alerta: bool


@dataclass(frozen=True)
class ResumenCamion:
    patente: str
    viajes: int
    km_recorridos: Decimal
    litros: Decimal
    costo: Decimal
    consumo_promedio_l100km: Decimal | None
    consumo_referencia_l100km: Decimal
    desvio_pct: Decimal | None
    viajes_con_alerta: int


@dataclass(frozen=True)
class ReporteConsumo:
    desde: date
    hasta: date
    filas: list[FilaReporteConsumo]
    resumen_por_camion: list[ResumenCamion]
