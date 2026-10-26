"""Puertos de persistencia de alertas."""

from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from flota.alertas.domain.entidades import Alerta, EstadoAlerta, TipoAlerta
from flota.shared.domain.repositorio import Repositorio


class RepositorioAlertas(Repositorio[Alerta]):
    @abstractmethod
    def buscar_por_origen(
        self, tipo: TipoAlerta, origen_tabla: str, origen_id: UUID
    ) -> Alerta | None:
        """La alerta de ese tipo generada por ese registro (hay a lo sumo una)."""

    @abstractmethod
    def listar_por_estado(
        self, estados: list[EstadoAlerta] | None = None, limite: int = 200
    ) -> list[Alerta]:
        """Más recientes primero."""

    @abstractmethod
    def contar_abiertas(self) -> int: ...
