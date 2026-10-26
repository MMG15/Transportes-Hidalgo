"""Esquemas Pydantic de tipos de cambio."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from flota.shared.domain.dinero import Moneda
from flota.shared.presentation.esquemas import Esquema, Numero


class CotizacionCrear(BaseModel):
    fecha: date
    cotizacion: Decimal = Field(gt=0, description="Pesos argentinos por 1 unidad de origen")
    moneda_origen: Moneda = Moneda.CLP
    fuente: str = "manual"


class CotizacionCorregir(BaseModel):
    cotizacion: Decimal = Field(gt=0)
    fuente: str = "corrección manual"
    confirmar: bool = Field(
        default=False, description="Obligatorio si la cotización ya se usó en algún gasto"
    )


class TipoCambioLeer(Esquema):
    id: UUID
    fecha: date
    moneda_origen: Moneda
    moneda_destino: Moneda
    cotizacion: Numero
    fuente: str
