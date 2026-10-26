"""Auditoría (RF-55): quién cambió qué, cuándo, y cómo estaba antes y después.

La unidad de trabajo conoce al ACTOR (el usuario que está operando) y los casos de uso llaman a
`uow.auditar(...)`. Así ningún caso de uso tiene que recibir el usuario como parámetro.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from uuid import UUID, uuid4


class AccionAuditoria(StrEnum):
    ALTA = "alta"
    MODIFICACION = "modificacion"
    BAJA = "baja"


@dataclass(frozen=True)
class Actor:
    """Quién está operando: un usuario del panel, un chofer por Telegram o el sistema."""

    usuario_id: UUID | None
    nombre: str


SISTEMA = Actor(None, "sistema")


@dataclass(kw_only=True)
class RegistroAuditoria:
    fecha: datetime
    tabla: str
    registro_id: UUID
    accion: AccionAuditoria
    usuario_id: UUID | None
    usuario_nombre: str
    valor_anterior: dict | None = None
    valor_nuevo: dict | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.accion = AccionAuditoria(self.accion)

    @property
    def campos_cambiados(self) -> list[str]:
        antes, despues = self.valor_anterior or {}, self.valor_nuevo or {}
        return sorted(k for k in antes.keys() | despues.keys() if antes.get(k) != despues.get(k))


def instantanea(objeto: object) -> dict | None:
    """Copia de una entidad como diccionario guardable en JSON (para valor anterior / nuevo)."""
    if objeto is None:
        return None
    if isinstance(objeto, dict):
        return _a_json(objeto)
    return _a_json(asdict(objeto) if is_dataclass(objeto) else dict(vars(objeto)))


def _a_json(valor: object) -> object:
    match valor:
        case dict():
            return {str(k): _a_json(v) for k, v in valor.items() if not str(k).startswith("_")}
        case list() | tuple():
            return [_a_json(v) for v in valor]
        case Enum():
            return valor.value
        case Decimal() | UUID():
            return str(valor)
        case datetime() | date():
            return valor.isoformat()
        case _:
            return valor
