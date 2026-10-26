"""Eventos de dominio: "algo pasó" en el negocio (un viaje se finalizó, se registró una carga).

Un módulo PUBLICA el evento sin saber quién lo escucha; otros módulos se SUSCRIBEN y reaccionan.
Así `viajes` no necesita importar `alertas` (que a su vez depende de `viajes`): se evita una
dependencia circular y cada módulo queda independiente (patrón Observador).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evento:
    """Base de todos los eventos. Son inmutables: describen algo que ya ocurrió."""
