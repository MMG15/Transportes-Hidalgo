"""Entidad CargaCombustible."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.dinero import CENTAVOS, ImporteGasto, Moneda
from flota.shared.domain.errores import ReglaNegocioViolada
from flota.shared.domain.validaciones import no_negativo, opcional, positivo, requerido
from flota.viajes.domain.entidades import Viaje


class OrigenDato(StrEnum):
    """De dónde proviene un registro de combustible."""

    MANUAL = "manual"  # tipeada en el panel o la API
    EXCEL = "excel"
    TARJETA = "tarjeta"  # archivo del proveedor de la tarjeta de combustible
    TICKET = "ticket"  # foto o PDF del ticket subido al panel (RF-02)
    TELEGRAM = "telegram"  # foto enviada por el chofer (RF-01)
    GPS = "gps"


class EstadoValidacion(StrEnum):
    VALIDADA = "validada"  # la cargó o la revisó una persona
    VALIDADA_IA = "validada_ia"  # la leyó la IA con buena confianza (CU-01)
    ANULADA = "anulada"  # CU-02 E1: no corresponde; no cuenta para el consumo


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
    estado_validacion: EstadoValidacion = EstadoValidacion.VALIDADA
    comprobante_id: UUID | None = None  # foto / PDF del ticket (RF-07)
    motivo_anulacion: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        positivo(self.litros, "litros")
        no_negativo(self.odometro_km, "odometro_km")
        self.estacion = opcional(self.estacion)
        self.referencia_externa = opcional(self.referencia_externa)
        self.origen = OrigenDato(self.origen)
        self.estado_validacion = EstadoValidacion(self.estado_validacion)

    @property
    def cuenta_para_consumo(self) -> bool:
        """Una carga anulada no entra en el cálculo de L/100 km."""
        return self.estado_validacion != EstadoValidacion.ANULADA

    def anular(self, motivo: str) -> None:
        """CU-02 E1: la carga no corresponde (ticket ajeno, duplicado no detectado, error)."""
        if self.estado_validacion == EstadoValidacion.ANULADA:
            raise ReglaNegocioViolada("La carga ya está anulada")
        self.motivo_anulacion = requerido(motivo, "motivo")
        self.estado_validacion = EstadoValidacion.ANULADA

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
