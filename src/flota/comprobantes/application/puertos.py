"""Lo que los casos de uso de comprobantes necesitan del exterior."""

from __future__ import annotations

from typing import Protocol

from flota.combustible.application.puertos import UoWCombustible
from flota.comprobantes.domain.repositorios import RepositorioComprobantes


class UoWComprobantes(UoWCombustible, Protocol):
    comprobantes: RepositorioComprobantes
