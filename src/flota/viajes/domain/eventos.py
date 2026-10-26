"""Eventos del módulo de viajes: los escucha, por ejemplo, el módulo de alertas."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from flota.shared.domain.eventos import Evento


@dataclass(frozen=True)
class TramoCerrado(Evento):
    """Se cerró un tramo (descarga): ya se puede evaluar su consumo."""

    viaje_id: UUID


@dataclass(frozen=True)
class ViajeFinalizado(Evento):
    viaje_id: UUID
