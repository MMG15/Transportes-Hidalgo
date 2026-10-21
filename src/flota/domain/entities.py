"""Entidades del dominio: los conceptos centrales del negocio.

Son clases Python puras (dataclasses). No saben nada de bases de datos, web ni Excel,
por eso se pueden testear y reutilizar sin infraestructura.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.domain.exceptions import DatosInvalidos, ReglaNegocioViolada


class OrigenDato(StrEnum):
    """De dónde proviene un registro de combustible."""

    MANUAL = "manual"
    EXCEL = "excel"
    TARJETA = "tarjeta"
    GPS = "gps"


class EstadoViaje(StrEnum):
    EN_CURSO = "en_curso"
    FINALIZADO = "finalizado"


def normalizar_patente(patente: str) -> str:
    """'ab 123-cd' -> 'AB123CD'. Se usa tanto al guardar como al buscar."""
    return patente.strip().upper().replace(" ", "").replace("-", "")


def _requerido(valor: str | None, campo: str) -> str:
    if valor is None or not str(valor).strip():
        raise DatosInvalidos(f"El campo '{campo}' es obligatorio")
    return str(valor).strip()


def _opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    return str(valor).strip() or None


def _positivo(valor: Decimal | None, campo: str) -> Decimal:
    if valor is None or valor <= 0:
        raise DatosInvalidos(f"El campo '{campo}' debe ser mayor a cero")
    return valor


def _no_negativo(valor: Decimal | None, campo: str) -> Decimal | None:
    if valor is not None and valor < 0:
        raise DatosInvalidos(f"El campo '{campo}' no puede ser negativo")
    return valor


@dataclass(kw_only=True)
class Camion:
    patente: str
    marca: str
    modelo: str
    capacidad_tanque_litros: Decimal
    consumo_referencia_l100km: Decimal  # consumo esperado según fabricante / histórico
    activo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.patente = normalizar_patente(_requerido(self.patente, "patente"))
        self.marca = _requerido(self.marca, "marca")
        self.modelo = _requerido(self.modelo, "modelo")
        _positivo(self.capacidad_tanque_litros, "capacidad_tanque_litros")
        _positivo(self.consumo_referencia_l100km, "consumo_referencia_l100km")


@dataclass(kw_only=True)
class Chofer:
    nombre: str
    dni: str
    activo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.nombre = _requerido(self.nombre, "nombre")
        self.dni = "".join(c for c in _requerido(self.dni, "dni") if c.isdigit())
        if not 7 <= len(self.dni) <= 9:
            raise DatosInvalidos("El DNI debe tener entre 7 y 9 dígitos")


@dataclass(kw_only=True)
class Cliente:
    """El productor (u otro cliente) que recibe la mercadería."""

    razon_social: str
    cuit: str | None = None
    localidad: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.razon_social = _requerido(self.razon_social, "razon_social")
        self.cuit = _opcional(self.cuit)
        self.localidad = _opcional(self.localidad)


@dataclass(kw_only=True)
class Producto:
    """Cal viva, cal hidratada u otro producto transportado."""

    nombre: str
    unidad: str = "tn"
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.nombre = _requerido(self.nombre, "nombre")
        self.unidad = _requerido(self.unidad, "unidad")


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
        self.origen = _requerido(self.origen, "origen")
        self.destino = _requerido(self.destino, "destino")
        self.observaciones = _opcional(self.observaciones)
        self.estado = EstadoViaje(self.estado)
        _positivo(self.cantidad, "cantidad")
        _no_negativo(self.km_salida, "km_salida")

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
        _positivo(self.litros, "litros")
        _no_negativo(self.precio_litro, "precio_litro")
        _no_negativo(self.odometro_km, "odometro_km")
        self.estacion = _opcional(self.estacion)
        self.referencia_externa = _opcional(self.referencia_externa)
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
