"""Puertos de la capa de aplicación: lo que los casos de uso necesitan del mundo exterior."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, Self

from flota.application.dto import ErrorLectura, FilaCarga, ReporteConsumo
from flota.domain.repositories import (
    RepositorioCamiones,
    RepositorioCargas,
    RepositorioChoferes,
    RepositorioClientes,
    RepositorioProductos,
    RepositorioViajes,
)


class UnidadDeTrabajo(ABC):
    """Agrupa los repositorios en una única transacción.

    Uso:
        with uow:
            uow.camiones.guardar(camion)
            uow.commit()   # si no se llama, al salir del `with` se descarta todo
    """

    camiones: RepositorioCamiones
    choferes: RepositorioChoferes
    clientes: RepositorioClientes
    productos: RepositorioProductos
    viajes: RepositorioViajes
    cargas: RepositorioCargas

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.rollback()

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...


class LectorCargas(ABC):
    """Lee cargas de combustible desde un archivo externo."""

    @abstractmethod
    def leer(self, ruta: Path) -> Iterator[FilaCarga | ErrorLectura]: ...


class GeneradorReporte(ABC):
    """Escribe un reporte de consumo en algún formato (Excel, PDF, ...)."""

    @abstractmethod
    def generar(self, reporte: ReporteConsumo, destino: Path | BinaryIO) -> None: ...
