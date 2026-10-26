"""Bus de eventos en memoria: reparte cada evento a los manejadores suscriptos a su tipo.

Los manejadores se ejecutan DESPUÉS del commit de la operación que publicó el evento, en su propia
transacción. Si un manejador falla, se registra el error y la operación original igual queda
guardada (por ejemplo: el viaje se finaliza aunque falle el cálculo de alertas).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable

from flota.shared.domain.eventos import Evento

log = logging.getLogger(__name__)

type Manejador = Callable[[Evento], None]


class BusEventos:
    def __init__(self) -> None:
        self._manejadores: dict[type[Evento], list[Manejador]] = defaultdict(list)

    def suscribir(self, tipo: type[Evento], manejador: Manejador) -> None:
        self._manejadores[tipo].append(manejador)

    def publicar(self, evento: Evento) -> None:
        for manejador in self._manejadores[type(evento)]:
            try:
                manejador(evento)
            except Exception:
                log.exception("Falló el manejador %s del evento %s", manejador, evento)
