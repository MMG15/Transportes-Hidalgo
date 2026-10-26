"""Servicio de dominio: cálculo del consumo de combustible de un viaje.

Es lógica de negocio que involucra varias entidades (viaje, camión, cargas),
por eso vive en una función aparte y no dentro de una sola entidad.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from flota.catalogo.domain.entidades import Camion
from flota.combustible.domain.entidades import CargaCombustible
from flota.shared.domain.errores import ReglaNegocioViolada
from flota.viajes.domain.entidades import Viaje

DOS_DECIMALES = Decimal("0.01")
UN_DECIMAL = Decimal("0.1")


@dataclass(frozen=True)
class ResumenConsumo:
    viaje_id: UUID
    camion_id: UUID
    km_recorridos: Decimal | None
    litros: Decimal
    costo: Decimal | None
    consumo_l100km: Decimal | None
    consumo_referencia_l100km: Decimal
    desvio_pct: Decimal | None  # positivo = consumió más de lo esperado
    litros_por_unidad: Decimal | None  # p. ej. litros por tonelada transportada
    alerta: bool


def calcular_consumo(
    viaje: Viaje,
    camion: Camion,
    cargas: Iterable[CargaCombustible],
    umbral_desvio_pct: Decimal = Decimal("15"),
) -> ResumenConsumo:
    if camion.id != viaje.camion_id:
        raise ReglaNegocioViolada("El camión no corresponde al viaje")

    propias = [c for c in cargas if c.viaje_id == viaje.id]
    litros = sum((c.litros for c in propias), Decimal("0"))
    importes = [c.importe for c in propias if c.importe is not None]
    costo = sum(importes, Decimal("0")) if importes else None

    km = viaje.km_recorridos
    referencia = camion.consumo_referencia_l100km
    consumo = desvio = None
    if km and litros:
        consumo = (litros / km * 100).quantize(DOS_DECIMALES)
        desvio = ((consumo - referencia) / referencia * 100).quantize(UN_DECIMAL)

    return ResumenConsumo(
        viaje_id=viaje.id,
        camion_id=camion.id,
        km_recorridos=km,
        litros=litros,
        costo=costo,
        consumo_l100km=consumo,
        consumo_referencia_l100km=referencia,
        desvio_pct=desvio,
        litros_por_unidad=(litros / viaje.cantidad).quantize(DOS_DECIMALES) if litros else None,
        alerta=desvio is not None and desvio > umbral_desvio_pct,
    )
