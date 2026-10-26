"""Servicio de dominio: cálculo del consumo de combustible de un viaje, por tramo.

Es lógica de negocio que involucra varias entidades (viaje, ruta, camión, cargas),
por eso vive en funciones aparte y no dentro de una sola entidad.

Reglas (RF-10, RF-11, RF-13, RF-16):
- L/100 km = litros ÷ km × 100, por tramo (cargado / vacío) y para el viaje completo.
- Cada carga se asigna al tramo en curso en la fecha de la carga.
- La referencia de cada tramo se elige en este orden:
    1. la configurada en la ruta para ese estado de carga,
    2. el promedio histórico de la ruta para ese estado (si hay viajes suficientes),
    3. la referencia general del camión (respaldo).
- Hay alerta si el consumo de un tramo supera la referencia en más del umbral (15 % por
  defecto), SÓLO si la referencia es de la ruta (configurada o histórica). La referencia del
  camión es una sola para cargado y vacío: compararla daría falsas alarmas en cada tramo
  cargado. Con ella se informa el desvío, pero no se alerta.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from flota.catalogo.domain.entidades import Camion
from flota.combustible.domain.entidades import CargaCombustible
from flota.shared.domain.errores import ReglaNegocioViolada
from flota.viajes.domain.entidades import EstadoCarga, Ruta, Viaje

DOS_DECIMALES = Decimal("0.01")
UN_DECIMAL = Decimal("0.1")
VIAJES_MINIMOS_HISTORICO = 3


class FuenteReferencia(StrEnum):
    RUTA = "ruta"  # configurada por el Resp. de Sistemas
    HISTORICO = "historico"  # promedio de los viajes anteriores en la ruta
    CAMION = "camion"  # respaldo: referencia general del camión


@dataclass(frozen=True)
class Referencia:
    valor: Decimal
    fuente: FuenteReferencia


@dataclass(frozen=True)
class PromedioHistorico:
    """Promedio de consumo de una ruta para un estado de carga (RF-13)."""

    estado_carga: EstadoCarga
    viajes: int
    km: Decimal
    litros: Decimal

    @property
    def l100km(self) -> Decimal | None:
        return l100km(self.litros, self.km)


@dataclass(frozen=True)
class ConsumoTramo:
    tramo_id: UUID
    estado_carga: EstadoCarga
    km_recorridos: Decimal | None
    litros: Decimal
    consumo_l100km: Decimal | None
    referencia: Referencia
    desvio_pct: Decimal | None
    alerta: bool


@dataclass(frozen=True)
class ResumenConsumo:
    viaje_id: UUID
    camion_id: UUID
    km_recorridos: Decimal | None
    litros: Decimal
    costo: Decimal | None
    consumo_l100km: Decimal | None
    consumo_referencia_l100km: Decimal  # promedio de las referencias, ponderado por km
    desvio_pct: Decimal | None  # positivo = consumió más de lo esperado
    litros_por_unidad: Decimal | None  # p. ej. litros por tonelada transportada
    alerta: bool
    tramos: tuple[ConsumoTramo, ...]

    def tramo(self, estado: EstadoCarga) -> ConsumoTramo | None:
        """El primer tramo con ese estado de carga (útil para mostrar cargado / vacío)."""
        return next((t for t in self.tramos if t.estado_carga == estado), None)


# ---------- Funciones puras ----------
def l100km(litros: Decimal, km: Decimal | None) -> Decimal | None:
    if not km or not litros:
        return None
    return (litros / km * 100).quantize(DOS_DECIMALES)


def desvio_pct(consumo: Decimal | None, referencia: Decimal) -> Decimal | None:
    if consumo is None:
        return None
    return ((consumo - referencia) / referencia * 100).quantize(UN_DECIMAL)


def elegir_referencia(
    estado: EstadoCarga,
    ruta: Ruta | None,
    historico: PromedioHistorico | None,
    camion: Camion,
) -> Referencia:
    if ruta and (configurada := ruta.referencia_configurada(estado)):
        return Referencia(configurada, FuenteReferencia.RUTA)
    if historico and historico.viajes >= VIAJES_MINIMOS_HISTORICO and historico.l100km:
        return Referencia(historico.l100km, FuenteReferencia.HISTORICO)
    return Referencia(camion.consumo_referencia_l100km, FuenteReferencia.CAMION)


def litros_por_tramo(viaje: Viaje, cargas: Iterable[CargaCombustible]) -> dict[UUID, Decimal]:
    """Suma los litros de las cargas del viaje en el tramo en curso al momento de cada carga."""
    totales = {t.id: Decimal("0") for t in viaje.tramos}
    for carga in cargas:
        if carga.viaje_id == viaje.id and carga.cuenta_para_consumo:
            totales[viaje.tramo_en(carga.fecha).id] += carga.litros
    return totales


def promedio_historico(
    viajes_con_cargas: Iterable[tuple[Viaje, list[CargaCombustible]]], estado: EstadoCarga
) -> PromedioHistorico:
    """RF-13: promedio de la ruta para un estado, sumando km y litros de viajes cerrados."""
    viajes = 0
    km = litros = Decimal("0")
    for viaje, cargas in viajes_con_cargas:
        por_tramo = litros_por_tramo(viaje, cargas)
        tramos = [
            t
            for t in viaje.tramos
            if t.estado_carga == estado and t.km_recorridos and por_tramo[t.id]
        ]
        if tramos:
            viajes += 1
            km += sum((t.km_recorridos for t in tramos), Decimal("0"))
            litros += sum((por_tramo[t.id] for t in tramos), Decimal("0"))
    return PromedioHistorico(estado, viajes, km, litros)


def calcular_consumo(
    viaje: Viaje,
    camion: Camion,
    cargas: Iterable[CargaCombustible],
    umbral_desvio_pct: Decimal = Decimal("15"),
    ruta: Ruta | None = None,
    historicos: Mapping[EstadoCarga, PromedioHistorico] | None = None,
) -> ResumenConsumo:
    if camion.id != viaje.camion_id:
        raise ReglaNegocioViolada("El camión no corresponde al viaje")
    historicos = historicos or {}

    propias = [c for c in cargas if c.viaje_id == viaje.id and c.cuenta_para_consumo]
    por_tramo = litros_por_tramo(viaje, propias)

    tramos: list[ConsumoTramo] = []
    for tramo in viaje.tramos:
        referencia = elegir_referencia(
            tramo.estado_carga, ruta, historicos.get(tramo.estado_carga), camion
        )
        consumo = l100km(por_tramo[tramo.id], tramo.km_recorridos)
        desvio = desvio_pct(consumo, referencia.valor)
        tramos.append(
            ConsumoTramo(
                tramo_id=tramo.id,
                estado_carga=tramo.estado_carga,
                km_recorridos=tramo.km_recorridos,
                litros=por_tramo[tramo.id],
                consumo_l100km=consumo,
                referencia=referencia,
                desvio_pct=desvio,
                alerta=(
                    desvio is not None
                    and desvio > umbral_desvio_pct
                    and referencia.fuente != FuenteReferencia.CAMION
                ),
            )
        )

    litros = sum((c.litros for c in propias), Decimal("0"))
    importes = [c.costo_ars for c in propias if c.costo_ars is not None]
    km = viaje.km_recorridos
    consumo_total = l100km(litros, km)
    referencia_total = _referencia_ponderada(tramos)
    desvio_total = desvio_pct(consumo_total, referencia_total)
    return ResumenConsumo(
        viaje_id=viaje.id,
        camion_id=camion.id,
        km_recorridos=km,
        litros=litros,
        costo=sum(importes, Decimal("0")) if importes else None,
        consumo_l100km=consumo_total,
        consumo_referencia_l100km=referencia_total,
        desvio_pct=desvio_total,
        litros_por_unidad=(
            (litros / viaje.cantidad).quantize(DOS_DECIMALES) if litros and viaje.cantidad else None
        ),
        alerta=any(t.alerta for t in tramos),
        tramos=tuple(tramos),
    )


def _referencia_ponderada(tramos: list[ConsumoTramo]) -> Decimal:
    """Referencia del viaje completo: promedio de las de cada tramo, pesado por sus km."""
    con_km = [t for t in tramos if t.km_recorridos]
    if not con_km:
        return tramos[0].referencia.valor
    km = sum((t.km_recorridos for t in con_km), Decimal("0"))
    ponderada = sum((t.referencia.valor * t.km_recorridos for t in con_km), Decimal("0")) / km
    return ponderada.quantize(DOS_DECIMALES)
