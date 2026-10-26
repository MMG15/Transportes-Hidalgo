"""Puerto de persistencia de usuarios."""

from __future__ import annotations

from abc import abstractmethod

from flota.shared.domain.repositorio import Repositorio
from flota.usuarios.domain.entidades import Usuario


class RepositorioUsuarios(Repositorio[Usuario]):
    @abstractmethod
    def obtener_por_email(self, email: str) -> Usuario | None: ...
