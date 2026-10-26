"""Puertos de persistencia de viajes y rutas."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from uuid import UUID

from flota.shared.domain.repositorio import Repositorio
from flota.viajes.domain.entidades import Ruta, Viaje


class RepositorioRutas(Repositorio[Ruta]):
    @abstractmethod
    def obtener_por_origen_destino(self, origen: str, destino: str) -> Ruta | None: ...


class RepositorioViajes(Repositorio[Viaje]):
    """El viaje es un agregado: el repositorio guarda y devuelve el viaje con sus tramos."""

    @abstractmethod
    def listar_por_periodo(
        self,
        desde: datetime,
        hasta: datetime,
        camion_id: UUID | None = None,
        chofer_id: UUID | None = None,
        ruta_id: UUID | None = None,
    ) -> list[Viaje]:
        """Viajes con fecha de salida en [desde, hasta)."""

    @abstractmethod
    def buscar_en_curso(self, camion_id: UUID) -> Viaje | None: ...

    @abstractmethod
    def buscar_por_camion_y_fecha(self, camion_id: UUID, fecha: datetime) -> Viaje | None:
        """El viaje del camión que estaba en marcha en esa fecha, si hay alguno."""

    @abstractmethod
    def listar_finalizados_por_ruta(
        self, ruta_id: UUID, antes_de: datetime | None = None, limite: int = 20
    ) -> list[Viaje]:
        """Los últimos viajes cerrados de la ruta (para el promedio histórico, RF-13)."""
