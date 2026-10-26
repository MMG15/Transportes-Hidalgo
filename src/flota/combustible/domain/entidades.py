"""Entidad CargaCombustible."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.errores import ReglaNegocioViolada
from flota.shared.domain.validaciones import no_negativo, opcional, positivo
from flota.viajes.domain.entidades import Viaje


class OrigenDato(StrEnum):
    """De dónde proviene un registro de combustible."""

    MANUAL = "manual"
    EXCEL = "excel"
    TARJETA = "tarjeta"
    GPS = "gps"


@dataclass(kw_only=True)
class CargaCombustible:
    camion_id: UUID
    fecha: datetime
    litros: Decimal
    precio_litro: Decimal | None = None
    odometro_km: Decimal | None = None
    estacion: str | None = None
    origen: OrigenDato = OrigenDato.MANUAL
    referencia_externa: str | None = None  # nro. de ticket o id de transacción de la tarjeta
    viaje_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        positivo(self.litros, "litros")
        no_negativo(self.precio_litro, "precio_litro")
        no_negativo(self.odometro_km, "odometro_km")
        self.estacion = opcional(self.estacion)
        self.referencia_externa = opcional(self.referencia_externa)
        self.origen = OrigenDato(self.origen)

    @property
    def importe(self) -> Decimal | None:
        if self.precio_litro is None:
            return None
        return (self.litros * self.precio_litro).quantize(Decimal("0.01"))

    def asignar_a_viaje(self, viaje: Viaje) -> None:
        if viaje.camion_id != self.camion_id:
            raise ReglaNegocioViolada("La carga y el viaje corresponden a camiones distintos")
        self.viaje_id = viaje.id
