"""Reportes de consumo por viaje, camión, chofer y ruta (CU-05, RF-12, RF-52)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from flota.combustible.application.consumo import CalculadoraConsumo
from flota.combustible.domain.consumo import DOS_DECIMALES, UN_DECIMAL, ResumenConsumo, l100km
from flota.reportes.application.dto import (
    FiltroReporte,
    FilaReporteConsumo,
    ReporteConsumo,
    ResumenCamion,
    ResumenGrupo,
)
from flota.reportes.application.puertos import GeneradorReporte, UoWReportes
from flota.viajes.domain.entidades import EstadoCarga

SIN_DATO = "—"


class GenerarReporteConsumo:
    """CU-05 — RF-10 a RF-13, RF-52: consumo por viaje y resúmenes por camión, chofer y ruta."""

    def __init__(self, uow: UoWReportes, umbral_desvio_pct: Decimal) -> None:
        self._uow = uow
        self._umbral = umbral_desvio_pct

    def ejecutar(
        self, desde: date, hasta: date, camion_id: UUID | None = None, **filtros
    ) -> ReporteConsumo:
        return self.con_filtro(FiltroReporte(desde, hasta, camion_id, **filtros))

    def con_filtro(self, filtro: FiltroReporte) -> ReporteConsumo:
        inicio = datetime.combine(filtro.desde, time.min)
        fin = datetime.combine(filtro.hasta + timedelta(days=1), time.min)
        filas: list[FilaReporteConsumo] = []

        with self._uow as uow:
            viajes = uow.viajes.listar_por_periodo(
                inicio, fin, filtro.camion_id, filtro.chofer_id, filtro.ruta_id
            )
            cargas_por_viaje = defaultdict(list)
            for carga in uow.cargas.listar_por_viajes([v.id for v in viajes]):
                cargas_por_viaje[carga.viaje_id].append(carga)

            calculadora = CalculadoraConsumo(uow, self._umbral)
            # Caché simple para no consultar el mismo camión/chofer/etc. una vez por viaje.
            cache: dict[UUID, object] = {}

            def buscar(repo, id: UUID | None):
                if id is None:
                    return None
                if id not in cache:
                    cache[id] = repo.obtener(id)
                return cache[id]

            for viaje in viajes:
                ruta = buscar(uow.rutas, viaje.ruta_id)
                if filtro.pais and ruta.pais != filtro.pais:
                    continue
                camion = buscar(uow.camiones, viaje.camion_id)
                chofer = buscar(uow.choferes, viaje.chofer_id)
                cliente = buscar(uow.clientes, viaje.cliente_id)
                producto = buscar(uow.productos, viaje.producto_id)
                consumo = calculadora.calcular(viaje, cargas_por_viaje[viaje.id])
                filas.append(
                    _fila(viaje, camion, chofer, ruta, cliente, producto, consumo)
                )

        return ReporteConsumo(
            filtro.desde,
            filtro.hasta,
            filas,
            _resumir_por_camion(filas),
            _resumir_por(filas, lambda f: f.chofer),
            _resumir_por(filas, lambda f: f.ruta),
        )


def _fila(viaje, camion, chofer, ruta, cliente, producto, consumo: ResumenConsumo):
    cargado = consumo.tramo(EstadoCarga.CARGADO)
    vacio = consumo.tramo(EstadoCarga.VACIO)
    fuentes = sorted({t.referencia.fuente.value for t in consumo.tramos})
    return FilaReporteConsumo(
        viaje_id=viaje.id,
        fecha_salida=viaje.fecha_salida,
        fecha_llegada=viaje.fecha_llegada,
        estado=str(viaje.estado),
        patente=camion.patente,
        chofer=chofer.nombre,
        ruta=ruta.nombre,
        pais=str(ruta.pais),
        origen=ruta.origen,
        destino=ruta.destino,
        cliente=cliente.razon_social if cliente else SIN_DATO,
        producto=producto.nombre if producto else SIN_DATO,
        unidad=producto.unidad if producto else "",
        cantidad=viaje.cantidad,
        km_recorridos=consumo.km_recorridos,
        litros=consumo.litros,
        costo=consumo.costo,
        consumo_l100km=consumo.consumo_l100km,
        consumo_referencia_l100km=consumo.consumo_referencia_l100km,
        desvio_pct=consumo.desvio_pct,
        litros_por_unidad=consumo.litros_por_unidad,
        alerta=consumo.alerta,
        consumo_cargado_l100km=cargado.consumo_l100km if cargado else None,
        referencia_cargado_l100km=cargado.referencia.valor if cargado else None,
        consumo_vacio_l100km=vacio.consumo_l100km if vacio else None,
        referencia_vacio_l100km=vacio.referencia.valor if vacio else None,
        fuente_referencia=", ".join(fuentes),
    )


def _completas(filas: list[FilaReporteConsumo]) -> list[FilaReporteConsumo]:
    """Sólo los viajes con km y litros (finalizados y con cargas) entran en los promedios."""
    return [f for f in filas if f.km_recorridos and f.litros]


def _resumir_por_camion(filas: list[FilaReporteConsumo]) -> list[ResumenCamion]:
    grupos: dict[str, list[FilaReporteConsumo]] = defaultdict(list)
    for fila in filas:
        grupos[fila.patente].append(fila)

    resumen = []
    for patente, grupo in sorted(grupos.items()):
        completas = _completas(grupo)
        km = sum((f.km_recorridos for f in completas), Decimal("0"))
        litros_completos = sum((f.litros for f in completas), Decimal("0"))
        # La referencia del camión es el promedio de las referencias de sus viajes, por km.
        referencia = (
            (sum((f.consumo_referencia_l100km * f.km_recorridos for f in completas), Decimal(0)) / km)
            .quantize(DOS_DECIMALES)
            if km
            else grupo[0].consumo_referencia_l100km
        )
        promedio = l100km(litros_completos, km)
        desvio = (
            ((promedio - referencia) / referencia * 100).quantize(UN_DECIMAL) if promedio else None
        )
        resumen.append(
            ResumenCamion(
                patente=patente,
                viajes=len(grupo),
                km_recorridos=km,
                litros=sum((f.litros for f in grupo), Decimal("0")),
                costo=sum((f.costo for f in grupo if f.costo is not None), Decimal("0")),
                consumo_promedio_l100km=promedio,
                consumo_referencia_l100km=referencia,
                desvio_pct=desvio,
                viajes_con_alerta=sum(1 for f in grupo if f.alerta),
            )
        )
    return resumen


def _resumir_por(
    filas: list[FilaReporteConsumo], clave: Callable[[FilaReporteConsumo], str]
) -> list[ResumenGrupo]:
    grupos: dict[str, list[FilaReporteConsumo]] = defaultdict(list)
    for fila in filas:
        grupos[clave(fila)].append(fila)

    resumen = []
    for nombre, grupo in sorted(grupos.items()):
        completas = _completas(grupo)
        km = sum((f.km_recorridos for f in completas), Decimal("0"))
        litros = sum((f.litros for f in completas), Decimal("0"))
        resumen.append(
            ResumenGrupo(
                nombre=nombre,
                viajes=len(grupo),
                km_recorridos=km,
                litros=sum((f.litros for f in grupo), Decimal("0")),
                costo=sum((f.costo for f in grupo if f.costo is not None), Decimal("0")),
                consumo_promedio_l100km=l100km(litros, km),
                viajes_con_alerta=sum(1 for f in grupo if f.alerta),
                consumo_cargado_l100km=_promedio(f.consumo_cargado_l100km for f in grupo),
                consumo_vacio_l100km=_promedio(f.consumo_vacio_l100km for f in grupo),
            )
        )
    return resumen


def _promedio(valores) -> Decimal | None:
    lista = [v for v in valores if v is not None]
    if not lista:
        return None
    return (sum(lista, Decimal("0")) / len(lista)).quantize(DOS_DECIMALES)


class ExportarReporteConsumo:
    """CU-05 — RF-51: exporta el reporte con el generador elegido (Excel; PDF más adelante)."""

    def __init__(self, generar: GenerarReporteConsumo, generador: GeneradorReporte) -> None:
        self._generar = generar
        self._generador = generador

    def ejecutar(
        self,
        desde: date,
        hasta: date,
        destino: Path | BinaryIO,
        camion_id: UUID | None = None,
        **filtros,
    ) -> ReporteConsumo:
        reporte = self._generar.ejecutar(desde, hasta, camion_id, **filtros)
        self._generador.generar(reporte, destino)
        return reporte
