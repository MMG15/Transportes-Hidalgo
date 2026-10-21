"""Puertos (interfaces) de persistencia.

El dominio declara QUÉ necesita guardar y buscar; la infraestructura decide CÓMO
(PostgreSQL, memoria para tests, etc.). Esto es la "inversión de dependencias".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from flota.domain.entities import Camion, CargaCombustible, Chofer, Cliente, Producto, Viaje


class Repositorio[E](ABC):
    @abstractmethod
    def guardar(self, entidad: E) -> None:
        """Inserta o actualiza."""

    @abstractmethod
    def obtener(self, id: UUID) -> E | None: ...

    @abstractmethod
    def listar(self, limite: int = 100, desplazamiento: int = 0) -> list[E]: ...


class RepositorioCamiones(Repositorio[Camion]):
    @abstractmethod
    def obtener_por_patente(self, patente: str) -> Camion | None: ...


class RepositorioChoferes(Repositorio[Chofer]):
    @abstractmethod
    def obtener_por_dni(self, dni: str) -> Chofer | None: ...


class RepositorioClientes(Repositorio[Cliente]):
    pass


class RepositorioProductos(Repositorio[Producto]):
    @abstractmethod
    def obtener_por_nombre(self, nombre: str) -> Producto | None: ...


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
