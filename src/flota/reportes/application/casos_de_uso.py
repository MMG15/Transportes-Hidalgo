"""Reportes de consumo por viaje y por camión."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from flota.reportes.application.dto import FilaReporteConsumo, ReporteConsumo, ResumenCamion
from flota.reportes.application.puertos import GeneradorReporte, UoWReportes
from flota.combustible.domain.consumo import DOS_DECIMALES, UN_DECIMAL, calcular_consumo


class GenerarReporteConsumo:
    def __init__(self, uow: UoWReportes, umbral_desvio_pct: Decimal) -> None:
        self._uow = uow
        self._umbral = umbral_desvio_pct

    def ejecutar(self, desde: date, hasta: date, camion_id: UUID | None = None) -> ReporteConsumo:
        inicio = datetime.combine(desde, time.min)
        fin = datetime.combine(hasta + timedelta(days=1), time.min)
        filas: list[FilaReporteConsumo] = []

        with self._uow as uow:
            viajes = uow.viajes.listar_por_periodo(inicio, fin, camion_id)
            cargas_por_viaje = defaultdict(list)
            for carga in uow.cargas.listar_por_viajes([v.id for v in viajes]):
                cargas_por_viaje[carga.viaje_id].append(carga)

            # Caché simple para no consultar el mismo camión/chofer/etc. una vez por viaje.
            cache: dict[UUID, object] = {}

            def buscar(repo, id: UUID):
                if id not in cache:
                    cache[id] = repo.obtener(id)
                return cache[id]

            for viaje in viajes:
                camion = buscar(uow.camiones, viaje.camion_id)
                chofer = buscar(uow.choferes, viaje.chofer_id)
                cliente = buscar(uow.clientes, viaje.cliente_id)
                producto = buscar(uow.productos, viaje.producto_id)
                consumo = calcular_consumo(viaje, camion, cargas_por_viaje[viaje.id], self._umbral)
                filas.append(
                    FilaReporteConsumo(
                        viaje_id=viaje.id,
                        fecha_salida=viaje.fecha_salida,
                        fecha_llegada=viaje.fecha_llegada,
                        estado=str(viaje.estado),
                        patente=camion.patente,
                        chofer=chofer.nombre,
                        cliente=cliente.razon_social,
                        producto=producto.nombre,
                        unidad=producto.unidad,
                        origen=viaje.origen,
                        destino=viaje.destino,
                        cantidad=viaje.cantidad,
                        km_recorridos=consumo.km_recorridos,
                        litros=consumo.litros,
                        costo=consumo.costo,
                        consumo_l100km=consumo.consumo_l100km,
                        consumo_referencia_l100km=consumo.consumo_referencia_l100km,
                        desvio_pct=consumo.desvio_pct,
                        litros_por_unidad=consumo.litros_por_unidad,
                        alerta=consumo.alerta,
                    )
                )

        return ReporteConsumo(desde, hasta, filas, _resumir_por_camion(filas))


def _resumir_por_camion(filas: list[FilaReporteConsumo]) -> list[ResumenCamion]:
    grupos: dict[str, list[FilaReporteConsumo]] = defaultdict(list)
    for fila in filas:
        grupos[fila.patente].append(fila)

    resumen = []
    for patente, grupo in sorted(grupos.items()):
        # El promedio sólo considera viajes con km y litros (finalizados y con cargas).
        completos = [f for f in grupo if f.km_recorridos and f.litros]
        km = sum((f.km_recorridos for f in completos), Decimal("0"))
        litros_completos = sum((f.litros for f in completos), Decimal("0"))
        referencia = grupo[0].consumo_referencia_l100km
        promedio = desvio = None
        if km:
            promedio = (litros_completos / km * 100).quantize(DOS_DECIMALES)
            desvio = ((promedio - referencia) / referencia * 100).quantize(UN_DECIMAL)
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


class ExportarReporteConsumo:
    def __init__(self, generar: GenerarReporteConsumo, generador: GeneradorReporte) -> None:
        self._generar = generar
        self._generador = generador

    def ejecutar(
        self,
        desde: date,
        hasta: date,
        destino: Path | BinaryIO,
        camion_id: UUID | None = None,
    ) -> ReporteConsumo:
        reporte = self._generar.ejecutar(desde, hasta, camion_id)
        self._generador.generar(reporte, destino)
        return reporte
