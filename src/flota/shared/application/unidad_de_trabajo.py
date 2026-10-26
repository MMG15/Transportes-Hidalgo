"""Unidad de trabajo: agrupa los repositorios en una única transacción.

Uso:
    with uow:
        uow.camiones.guardar(camion)
        uow.commit()   # si no se llama, al salir del `with` se descarta todo

Cada módulo declara la unidad de trabajo que necesita como un `Protocol` que hereda de
`UnidadDeTrabajo` y agrega sólo SUS repositorios (ver `catalogo/application/puertos.py`).
Una única clase concreta (`flota.unidad_de_trabajo.UnidadDeTrabajoSql`) los cumple a todos.
"""

from __future__ import annotations

from typing import Protocol, Self


class UnidadDeTrabajo(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(self, *args: object) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class UnidadDeTrabajoBase:
    """Comportamiento común: al salir del `with` se descarta lo que no se confirmó."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.rollback()

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError
