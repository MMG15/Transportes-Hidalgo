"""Eventos de comprobantes: el procesamiento con IA (Sesión 8) escucha `ComprobanteRecibido`."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from flota.shared.domain.eventos import Evento


@dataclass(frozen=True)
class ComprobanteRecibido(Evento):
    comprobante_id: UUID


@dataclass(frozen=True)
class ComprobantePendiente(Evento):
    """Quedó pendiente de validación: hay que avisarle al chofer o a Administración."""

    comprobante_id: UUID
