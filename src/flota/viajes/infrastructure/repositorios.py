"""Repositorios SQL de rutas y viajes."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select

from flota.shared.infrastructure.db import RepositorioSql
from flota.viajes.domain.entidades import EstadoViaje, Ruta, TramoViaje, Viaje
from flota.viajes.domain.repositorios import RepositorioRutas, RepositorioViajes
from flota.viajes.infrastructure.modelos import RutaModel, TramoViajeModel, ViajeModel


class RepositorioRutasSql(RepositorioSql[Ruta, RutaModel], RepositorioRutas):
    entidad, modelo, orden = Ruta, RutaModel, RutaModel.origen.asc()

    def obtener_por_origen_destino(self, origen: str, destino: str) -> Ruta | None:
        return self._uno(
            select(RutaModel).where(
                RutaModel.origen == origen.strip(), RutaModel.destino == destino.strip()
            )
        )


class RepositorioViajesSql(RepositorioSql[Viaje, ViajeModel], RepositorioViajes):
    entidad, modelo, orden = Viaje, ViajeModel, ViajeModel.fecha_salida.desc()

    # El viaje tiene una lista de tramos: la conversión genérica no alcanza.
    def _a_entidad(self, modelo: ViajeModel) -> Viaje:
        datos = {f.name: getattr(modelo, f.name) for f in fields(Viaje) if f.name != "tramos"}
        tramos = [
            TramoViaje(
                id=t.id,
                estado_carga=t.estado_carga,
                fecha_inicio=t.fecha_inicio,
                km_inicio=t.km_inicio,
                fecha_fin=t.fecha_fin,
                km_fin=t.km_fin,
            )
            for t in modelo.tramos
        ]
        return Viaje(**datos, tramos=tramos)

    def _a_modelo(self, viaje: Viaje) -> ViajeModel:
        datos = {f.name: getattr(viaje, f.name) for f in fields(viaje) if f.name != "tramos"}
        tramos = [
            TramoViajeModel(
                id=t.id,
                viaje_id=viaje.id,
                orden=orden,
                estado_carga=t.estado_carga,
                fecha_inicio=t.fecha_inicio,
                km_inicio=t.km_inicio,
                fecha_fin=t.fecha_fin,
                km_fin=t.km_fin,
            )
            for orden, t in enumerate(viaje.tramos)
        ]
        return ViajeModel(**datos, tramos=tramos)

    def listar_por_periodo(
        self,
        desde: datetime,
        hasta: datetime,
        camion_id: UUID | None = None,
        chofer_id: UUID | None = None,
        ruta_id: UUID | None = None,
    ) -> list[Viaje]:
        stmt = select(ViajeModel).where(
            ViajeModel.fecha_salida >= desde, ViajeModel.fecha_salida < hasta
        )
        if camion_id:
            stmt = stmt.where(ViajeModel.camion_id == camion_id)
        if chofer_id:
            stmt = stmt.where(ViajeModel.chofer_id == chofer_id)
        if ruta_id:
            stmt = stmt.where(ViajeModel.ruta_id == ruta_id)
        return self._todos(stmt.order_by(ViajeModel.fecha_salida))

    def buscar_en_curso(self, camion_id: UUID) -> Viaje | None:
        return self._uno(
            select(ViajeModel).where(
                ViajeModel.camion_id == camion_id, ViajeModel.estado == EstadoViaje.EN_CURSO
            )
        )

    def buscar_por_camion_y_fecha(self, camion_id: UUID, fecha: datetime) -> Viaje | None:
        stmt = (
            select(ViajeModel)
            .where(
                ViajeModel.camion_id == camion_id,
                ViajeModel.fecha_salida <= fecha,
                or_(ViajeModel.fecha_llegada.is_(None), ViajeModel.fecha_llegada >= fecha),
            )
            .order_by(ViajeModel.fecha_salida.desc())
        )
        return self._uno(stmt)

    def listar_finalizados_por_ruta(
        self, ruta_id: UUID, antes_de: datetime | None = None, limite: int = 20
    ) -> list[Viaje]:
        stmt = select(ViajeModel).where(
            ViajeModel.ruta_id == ruta_id, ViajeModel.estado == EstadoViaje.FINALIZADO
        )
        if antes_de:
            stmt = stmt.where(ViajeModel.fecha_salida < antes_de)
        return self._todos(stmt.order_by(ViajeModel.fecha_salida.desc()).limit(limite))
