"""Entidad Viaje: la unidad de trazabilidad (todo gasto se asocia a un viaje)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.errores import DatosInvalidos, ReglaNegocioViolada
from flota.shared.domain.validaciones import no_negativo, opcional, positivo, requerido


class EstadoViaje(StrEnum):
    EN_CURSO = "en_curso"
    FINALIZADO = "finalizado"


@dataclass(kw_only=True)
class Viaje:
    camion_id: UUID
    chofer_id: UUID
    cliente_id: UUID
    producto_id: UUID
    origen: str
    destino: str
    cantidad: Decimal  # cantidad transportada, en la unidad del producto
    fecha_salida: datetime
    km_salida: Decimal  # lectura del odómetro al salir
    fecha_llegada: datetime | None = None
    km_llegada: Decimal | None = None
    estado: EstadoViaje = EstadoViaje.EN_CURSO
    observaciones: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.origen = requerido(self.origen, "origen")
        self.destino = requerido(self.destino, "destino")
        self.observaciones = opcional(self.observaciones)
        self.estado = EstadoViaje(self.estado)
        positivo(self.cantidad, "cantidad")
        no_negativo(self.km_salida, "km_salida")

    def finalizar(self, fecha_llegada: datetime, km_llegada: Decimal) -> None:
        if self.estado == EstadoViaje.FINALIZADO:
            raise ReglaNegocioViolada("El viaje ya está finalizado")
        if fecha_llegada < self.fecha_salida:
            raise DatosInvalidos("La fecha de llegada no puede ser anterior a la de salida")
        if km_llegada <= self.km_salida:
            raise DatosInvalidos("El odómetro de llegada debe ser mayor al de salida")
        self.fecha_llegada = fecha_llegada
        self.km_llegada = km_llegada
        self.estado = EstadoViaje.FINALIZADO

    @property
    def km_recorridos(self) -> Decimal | None:
        if self.km_llegada is None:
            return None
        return self.km_llegada - self.km_salida

    def incluye_fecha(self, fecha: datetime) -> bool:
        """True si `fecha` cae dentro del viaje (o después de la salida, si sigue en curso)."""
        if fecha < self.fecha_salida:
            return False
        return self.fecha_llegada is None or fecha <= self.fecha_llegada
