"""Puertos de persistencia de viajes."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from uuid import UUID

from flota.shared.domain.repositorio import Repositorio
from flota.viajes.domain.entidades import Viaje


class RepositorioViajes(Repositorio[Viaje]):
    @abstractmethod
    def listar_por_periodo(
        self, desde: datetime, hasta: datetime, camion_id: UUID | None = None
    ) -> list[Viaje]:
        """Viajes con fecha de salida en [desde, hasta)."""

    @abstractmethod
    def buscar_en_curso(self, camion_id: UUID) -> Viaje | None: ...

    @abstractmethod
    def buscar_por_camion_y_fecha(self, camion_id: UUID, fecha: datetime) -> Viaje | None:
        """El viaje del camión que estaba en marcha en esa fecha, si hay alguno."""
