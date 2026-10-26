"""Lo que los casos de uso de alertas necesitan del exterior."""

from __future__ import annotations

from typing import Protocol

from flota.alertas.domain.repositorios import RepositorioAlertas
from flota.combustible.application.puertos import UoWCombustible


class UoWAlertas(UoWCombustible, Protocol):
    alertas: RepositorioAlertas
