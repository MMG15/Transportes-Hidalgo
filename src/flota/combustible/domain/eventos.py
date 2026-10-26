"""Eventos del módulo de combustible."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from flota.shared.domain.eventos import Evento


@dataclass(frozen=True)
class CargaRegistrada(Evento):
    carga_id: UUID
    viaje_id: UUID | None
