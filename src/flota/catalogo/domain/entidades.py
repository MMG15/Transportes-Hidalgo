"""Entidades del catálogo: camiones, choferes, clientes y productos.

Son clases Python puras (dataclasses). No saben nada de bases de datos, web ni Excel,
por eso se pueden testear y reutilizar sin infraestructura.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from flota.shared.domain.errores import DatosInvalidos
from flota.shared.domain.validaciones import opcional, positivo, requerido


def normalizar_patente(patente: str) -> str:
    """'ab 123-cd' -> 'AB123CD'. Se usa tanto al guardar como al buscar."""
    return patente.strip().upper().replace(" ", "").replace("-", "")


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
        self.patente = normalizar_patente(requerido(self.patente, "patente"))
        self.marca = requerido(self.marca, "marca")
        self.modelo = requerido(self.modelo, "modelo")
        positivo(self.capacidad_tanque_litros, "capacidad_tanque_litros")
        positivo(self.consumo_referencia_l100km, "consumo_referencia_l100km")


@dataclass(kw_only=True)
class Chofer:
    nombre: str
    dni: str
    activo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.nombre = requerido(self.nombre, "nombre")
        self.dni = "".join(c for c in requerido(self.dni, "dni") if c.isdigit())
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
        self.razon_social = requerido(self.razon_social, "razon_social")
        self.cuit = opcional(self.cuit)
        self.localidad = opcional(self.localidad)


@dataclass(kw_only=True)
class Producto:
    """Cal viva, cal hidratada u otro producto transportado."""

    nombre: str
    unidad: str = "tn"
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.nombre = requerido(self.nombre, "nombre")
        self.unidad = requerido(self.unidad, "unidad")
