"""Unidad de trabajo: agrupa los repositorios en una única transacción.

Uso:
    with uow:
        uow.camiones.guardar(camion)
        uow.auditar("camiones", camion.id, AccionAuditoria.ALTA, despues=camion)   # opcional
        uow.registrar_evento(CamionRegistrado(...))                               # opcional
        uow.commit()   # confirma y DESPUÉS publica los eventos registrados
    # si no se llamó a commit(), al salir del `with` se descarta todo (y los eventos también)

Cada módulo declara la unidad de trabajo que necesita como un `Protocol` que hereda de
`UnidadDeTrabajo` y agrega sólo SUS repositorios (ver `catalogo/application/puertos.py`).
Una única clase concreta (`flota.unidad_de_trabajo.UnidadDeTrabajoSql`) los cumple a todos.

`actor` es el usuario que está operando: lo fija la capa de presentación (panel, API, bot) al
identificarlo, y la auditoría lo usa para registrar quién hizo cada cambio (RF-55).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Self
from uuid import UUID

from flota.shared.application.eventos import BusEventos
from flota.shared.domain.auditoria import (
    SISTEMA,
    AccionAuditoria,
    Actor,
    RegistroAuditoria,
    instantanea,
)
from flota.shared.domain.eventos import Evento
from flota.shared.domain.repositorio_auditoria import RepositorioAuditoria


class UnidadDeTrabajo(Protocol):
    actor: Actor
    auditoria: RepositorioAuditoria

    def __enter__(self) -> Self: ...

    def __exit__(self, *args: object) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def registrar_evento(self, evento: Evento) -> None: ...

    def auditar(
        self,
        tabla: str,
        registro_id: UUID,
        accion: AccionAuditoria,
        antes: object = None,
        despues: object = None,
    ) -> None: ...


class UnidadDeTrabajoBase:
    """Comportamiento común: transacción, auditoría y eventos (publicados tras el commit)."""

    auditoria: RepositorioAuditoria

    def __init__(self, bus: BusEventos | None = None, actor: Actor = SISTEMA) -> None:
        self.bus = bus
        self.actor = actor
        self._eventos: list[Evento] = []

    def __enter__(self) -> Self:
        self._eventos = []
        return self

    def __exit__(self, *args: object) -> None:
        self.rollback()

    def registrar_evento(self, evento: Evento) -> None:
        self._eventos.append(evento)

    def auditar(
        self,
        tabla: str,
        registro_id: UUID,
        accion: AccionAuditoria,
        antes: object = None,
        despues: object = None,
    ) -> None:
        """RF-55: guarda el cambio en la misma transacción que el cambio en sí."""
        self.auditoria.guardar(
            RegistroAuditoria(
                fecha=datetime.now(),
                tabla=tabla,
                registro_id=registro_id,
                accion=accion,
                usuario_id=self.actor.usuario_id,
                usuario_nombre=self.actor.nombre,
                valor_anterior=instantanea(antes),
                valor_nuevo=instantanea(despues),
            )
        )

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
