"""Puerto de persistencia de comprobantes."""

from __future__ import annotations

from abc import abstractmethod

from flota.comprobantes.domain.entidades import Comprobante, EstadoComprobante, TipoComprobante
from flota.shared.domain.repositorio import Repositorio


class RepositorioComprobantes(Repositorio[Comprobante]):
    @abstractmethod
    def listar_por_estado(
        self,
        estados: list[EstadoComprobante],
        tipo: TipoComprobante | None = None,
        limite: int = 200,
    ) -> list[Comprobante]:
        """Más antiguos primero (se atienden por orden de llegada)."""

    @abstractmethod
    def contar_por_estado(self, estado: EstadoComprobante) -> int: ...
