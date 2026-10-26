"""Puerto genérico de persistencia.

Cada módulo declara QUÉ necesita guardar y buscar heredando de `Repositorio[E]`;
la infraestructura decide CÓMO (PostgreSQL, memoria para tests, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class Repositorio[E](ABC):
    @abstractmethod
    def guardar(self, entidad: E) -> None:
        """Inserta o actualiza."""

    @abstractmethod
    def obtener(self, id: UUID) -> E | None: ...

    @abstractmethod
    def listar(self, limite: int = 100, desplazamiento: int = 0) -> list[E]: ...
