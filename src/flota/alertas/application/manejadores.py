"""Manejadores de eventos: conectan lo que pasa en otros módulos con la evaluación de alertas.

`bootstrap.py` llama a `suscribir(...)` al armar el sistema. Cada manejador trabaja con su propia
unidad de trabajo (su propia transacción), después de que la operación original se confirmó.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from flota.alertas.application.casos_de_uso import EvaluarAlertasCarga, EvaluarAlertasViaje
from flota.alertas.application.puertos import UoWAlertas
from flota.combustible.domain.eventos import CargaAnulada, CargaRegistrada
from flota.shared.application.eventos import BusEventos
from flota.viajes.domain.eventos import TramoCerrado, ViajeFinalizado


def suscribir(
    bus: BusEventos,
    crear_uow: Callable[[], UoWAlertas],
    umbral_desvio_pct: Decimal,
    tolerancia_tanque_pct: Decimal,
) -> None:
    def evaluar_viaje(evento: TramoCerrado | ViajeFinalizado) -> None:
        EvaluarAlertasViaje(crear_uow(), umbral_desvio_pct).ejecutar(evento.viaje_id)

    def evaluar_carga(evento: CargaRegistrada) -> None:
        EvaluarAlertasCarga(crear_uow(), tolerancia_tanque_pct).ejecutar(evento.carga_id)
        if evento.viaje_id:  # un ticket que llega tarde cambia el consumo de un tramo cerrado
            EvaluarAlertasViaje(crear_uow(), umbral_desvio_pct).ejecutar(evento.viaje_id)

    bus.suscribir(TramoCerrado, evaluar_viaje)
    bus.suscribir(ViajeFinalizado, evaluar_viaje)

    def reevaluar_viaje(evento: CargaAnulada) -> None:
        if evento.viaje_id:
            EvaluarAlertasViaje(crear_uow(), umbral_desvio_pct).ejecutar(evento.viaje_id)

    bus.suscribir(CargaRegistrada, evaluar_carga)
    bus.suscribir(CargaAnulada, reevaluar_viaje)
