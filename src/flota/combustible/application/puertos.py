"""Lo que los casos de uso de combustible necesitan del exterior."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from flota.combustible.application.dto import ErrorLectura, FilaCarga
from flota.combustible.domain.repositorios import RepositorioCargas
from flota.viajes.application.puertos import UoWViajes


class UoWCombustible(UoWViajes, Protocol):
    cargas: RepositorioCargas


class LectorCargas(ABC):
    """Lee cargas de combustible desde un archivo externo."""

    @abstractmethod
    def leer(self, ruta: Path) -> Iterator[FilaCarga | ErrorLectura]: ...
