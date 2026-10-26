"""Entidad CargaCombustible."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.dinero import CENTAVOS, ImporteGasto, Moneda
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
    importe: ImporteGasto | None = None  # monto original, moneda, cotización y monto en ARS
    odometro_km: Decimal | None = None
    estacion: str | None = None
    origen: OrigenDato = OrigenDato.MANUAL
    referencia_externa: str | None = None  # nro. de ticket o id de transacción de la tarjeta
    viaje_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        positivo(self.litros, "litros")
        no_negativo(self.odometro_km, "odometro_km")
        self.estacion = opcional(self.estacion)
        self.referencia_externa = opcional(self.referencia_externa)
        self.origen = OrigenDato(self.origen)

    @property
    def cuenta_para_consumo(self) -> bool:
        """Si la carga entra en el cálculo de L/100 km. (Con la validación de tickets, las
        cargas pendientes o anuladas quedarán afuera.)"""
        return True

    @property
    def moneda(self) -> Moneda | None:
        return self.importe.original.moneda if self.importe else None

    @property
    def costo_ars(self) -> Decimal | None:
        """Lo que costó la carga en pesos argentinos (con la cotización fija del gasto)."""
        return self.importe.monto_ars if self.importe else None

    @property
    def precio_litro(self) -> Decimal | None:
        """Precio por litro en la moneda original del ticket."""
        if self.importe is None:
            return None
        return (self.importe.original.monto / self.litros).quantize(CENTAVOS)

    def supera_tanque(self, capacidad: Decimal, tolerancia_pct: Decimal) -> bool:
        """RF-18: más litros que la capacidad del tanque (más una tolerancia)."""
        return self.litros > capacidad * (1 + tolerancia_pct / 100)

    def asignar_a_viaje(self, viaje: Viaje) -> None:
        if viaje.camion_id != self.camion_id:
            raise ReglaNegocioViolada("La carga y el viaje corresponden a camiones distintos")
        self.viaje_id = viaje.id
