"""Servicio de aplicación: arma el contexto (ruta, histórico, cargas) y calcula el consumo.

El dominio (`combustible/domain/consumo.py`) sabe CALCULAR; este servicio sabe BUSCAR lo que
el cálculo necesita en los repositorios. Debe usarse dentro de un `with uow:` abierto.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from flota.combustible.application.puertos import UoWCombustible
from flota.combustible.domain.consumo import (
    PromedioHistorico,
    ResumenConsumo,
    calcular_consumo,
    promedio_historico,
)
from flota.combustible.domain.entidades import CargaCombustible
from flota.shared.application.comun import obtener_o_fallar
from flota.viajes.domain.entidades import EstadoCarga, Viaje

VIAJES_PARA_HISTORICO = 20


class CalculadoraConsumo:
    """Calcula el consumo de uno o muchos viajes reutilizando las consultas por ruta."""

    def __init__(
        self, uow: UoWCombustible, umbral_desvio_pct: Decimal, limite: int = VIAJES_PARA_HISTORICO
    ) -> None:
        self._uow = uow
        self._umbral = umbral_desvio_pct
        self._limite = limite
        # Caché por ruta: viajes finalizados (más nuevos primero) con sus cargas.
        self._historial: dict[UUID, list[tuple[Viaje, list[CargaCombustible]]]] = {}

    def calcular(
        self, viaje: Viaje, cargas: list[CargaCombustible] | None = None
    ) -> ResumenConsumo:
        camion = obtener_o_fallar(self._uow.camiones, viaje.camion_id, "camión")
        ruta = self._uow.rutas.obtener(viaje.ruta_id)
        if cargas is None:
            cargas = self._uow.cargas.listar_por_viajes([viaje.id])
        return calcular_consumo(
            viaje,
            camion,
            cargas,
            self._umbral,
            ruta=ruta,
            historicos=self.historicos(viaje.ruta_id, antes_de=viaje.fecha_salida),
        )

    def historicos(
        self, ruta_id: UUID, antes_de: datetime | None = None
    ) -> dict[EstadoCarga, PromedioHistorico]:
        """RF-13: promedio de los últimos viajes cerrados de la ruta, anteriores a `antes_de`."""
        anteriores = [
            (v, c)
            for v, c in self._historial_de(ruta_id)
            if antes_de is None or v.fecha_salida < antes_de
        ][: self._limite]
        return {estado: promedio_historico(anteriores, estado) for estado in EstadoCarga}

    def _historial_de(self, ruta_id: UUID) -> list[tuple[Viaje, list[CargaCombustible]]]:
        if ruta_id not in self._historial:
            # Se trae un margen mayor al límite para poder filtrar "anteriores a" cada viaje.
            viajes = self._uow.viajes.listar_finalizados_por_ruta(ruta_id, limite=self._limite * 5)
            cargas_por_viaje: dict[UUID, list[CargaCombustible]] = defaultdict(list)
            for carga in self._uow.cargas.listar_por_viajes([v.id for v in viajes]):
                cargas_por_viaje[carga.viaje_id].append(carga)
            self._historial[ruta_id] = [(v, cargas_por_viaje[v.id]) for v in viajes]
        return self._historial[ruta_id]
