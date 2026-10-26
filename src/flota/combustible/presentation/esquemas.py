"""Esquemas Pydantic de combustible."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from flota.combustible.domain.consumo import FuenteReferencia
from flota.combustible.domain.entidades import OrigenDato
from flota.shared.domain.dinero import Moneda
from flota.shared.presentation.esquemas import Esquema, Numero
from flota.viajes.domain.entidades import EstadoCarga


class CargaCrear(BaseModel):
    camion_id: UUID
    fecha: datetime
    litros: Decimal = Field(gt=0, examples=[350])
    monto: Decimal | None = Field(default=None, ge=0, description="Importe total del ticket")
    precio_litro: Decimal | None = Field(
        default=None, ge=0, examples=[1450], description="Se usa si no se informa el monto"
    )
    moneda: Moneda = Moneda.ARS
    odometro_km: Decimal | None = Field(default=None, ge=0)
    estacion: str | None = None
    referencia_externa: str | None = Field(default=None, examples=["T-000123"])
    viaje_id: UUID | None = None


class DineroLeer(Esquema):
    monto: Numero
    moneda: Moneda


class ImporteLeer(Esquema):
    original: DineroLeer
    cotizacion: Numero
    monto_ars: Numero
    revisar_cotizacion: bool


class CargaLeer(Esquema):
    id: UUID
    camion_id: UUID
    viaje_id: UUID | None
    fecha: datetime
    litros: Numero
    importe: ImporteLeer | None
    precio_litro: Numero | None
    costo_ars: Numero | None
    odometro_km: Numero | None
    estacion: str | None
    origen: OrigenDato
    referencia_externa: str | None


class ResultadoImportacionLeer(Esquema):
    procesadas: int
    importadas: int
    duplicadas: int
    errores: list[str]


class ReferenciaLeer(Esquema):
    valor: Numero
    fuente: FuenteReferencia


class ConsumoTramoLeer(Esquema):
    tramo_id: UUID
    estado_carga: EstadoCarga
    km_recorridos: Numero | None
    litros: Numero
    consumo_l100km: Numero | None
    referencia: ReferenciaLeer
    desvio_pct: Numero | None
    alerta: bool


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
    tramos: list[ConsumoTramoLeer]
