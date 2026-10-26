"""Eventos del módulo de alertas (los usará la notificación por Telegram / correo, RF-19)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from flota.shared.domain.eventos import Evento


@dataclass(frozen=True)
class AlertaGenerada(Evento):
    alerta_id: UUID


@dataclass(frozen=True)
class AlertaEscalada(Evento):
    """Desvío confirmado: hay que avisar a Gerencia (CU-06 paso 5)."""

    alerta_id: UUID
