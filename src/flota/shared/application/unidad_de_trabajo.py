"""Unidad de trabajo: agrupa los repositorios en una única transacción.

Uso:
    with uow:
        uow.camiones.guardar(camion)
        uow.registrar_evento(CamionRegistrado(...))   # opcional
        uow.commit()   # confirma y DESPUÉS publica los eventos registrados
    # si no se llamó a commit(), al salir del `with` se descarta todo (y los eventos también)

Cada módulo declara la unidad de trabajo que necesita como un `Protocol` que hereda de
`UnidadDeTrabajo` y agrega sólo SUS repositorios (ver `catalogo/application/puertos.py`).
Una única clase concreta (`flota.unidad_de_trabajo.UnidadDeTrabajoSql`) los cumple a todos.
"""

from __future__ import annotations

from typing import Protocol, Self

from flota.shared.application.eventos import BusEventos
from flota.shared.domain.eventos import Evento


class UnidadDeTrabajo(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(self, *args: object) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def registrar_evento(self, evento: Evento) -> None: ...


class UnidadDeTrabajoBase:
    """Comportamiento común: transacción + eventos que se publican sólo si se confirma."""

    def __init__(self, bus: BusEventos | None = None) -> None:
        self.bus = bus
        self._eventos: list[Evento] = []

    def __enter__(self) -> Self:
        self._eventos = []
        return self

    def __exit__(self, *args: object) -> None:
        self.rollback()

    def registrar_evento(self, evento: Evento) -> None:
        self._eventos.append(evento)

    def commit(self) -> None:
        self._confirmar()
        pendientes, self._eventos = self._eventos, []
        if self.bus:
            for evento in pendientes:
                self.bus.publicar(evento)

    def rollback(self) -> None:
        self._eventos = []
        self._descartar()

    # Lo implementa cada unidad de trabajo concreta (SQL, memoria).
    def _confirmar(self) -> None:
        raise NotImplementedError

    def _descartar(self) -> None:
        raise NotImplementedError
