"""Lo que los casos de uso de usuarios necesitan del exterior."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from flota.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from flota.usuarios.domain.repositorios import RepositorioUsuarios


class UoWUsuarios(UnidadDeTrabajo, Protocol):
    usuarios: RepositorioUsuarios


class HasherContrasenas(ABC):
    """Convierte una contraseña en un hash irreversible y verifica contraseñas contra él.

    El dominio no sabe qué algoritmo se usa (hoy Argon2): es un detalle de infraestructura.
    """

    @abstractmethod
    def hash(self, contrasena: str) -> str: ...

    @abstractmethod
    def verificar(self, contrasena: str, hash_guardado: str) -> bool: ...
