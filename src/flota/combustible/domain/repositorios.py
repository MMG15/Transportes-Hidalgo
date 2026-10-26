"""Puertos de persistencia de combustible."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from flota.combustible.domain.entidades import CargaCombustible
from flota.shared.domain.repositorio import Repositorio


class RepositorioCargas(Repositorio[CargaCombustible]):
    @abstractmethod
    def listar_por_viajes(self, viaje_ids: Sequence[UUID]) -> list[CargaCombustible]: ...

    @abstractmethod
    def listar_filtrado(
        self,
        camion_id: UUID | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 100,
        desplazamiento: int = 0,
    ) -> list[CargaCombustible]: ...

    @abstractmethod
    def existe_duplicado(self, carga: CargaCombustible) -> bool:
        """Misma referencia externa, o mismo camión + fecha + litros."""
