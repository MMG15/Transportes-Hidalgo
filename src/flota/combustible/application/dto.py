"""Objetos de transferencia de datos (DTO) de la importación de cargas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


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
    importe: Decimal | None = None  # total del ticket (si no viene, se usa precio x litros)
    moneda: str = "ARS"


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
