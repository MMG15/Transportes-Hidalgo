"""Puerto de persistencia de la auditoría."""

from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from flota.shared.domain.auditoria import RegistroAuditoria
from flota.shared.domain.repositorio import Repositorio


class RepositorioAuditoria(Repositorio[RegistroAuditoria]):
    @abstractmethod
    def listar_filtrado(
        self,
        tabla: str | None = None,
        registro_id: UUID | None = None,
        usuario_id: UUID | None = None,
        limite: int = 200,
    ) -> list[RegistroAuditoria]:
        """Más recientes primero."""
