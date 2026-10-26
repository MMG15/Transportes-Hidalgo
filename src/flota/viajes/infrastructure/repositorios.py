"""Repositorio SQL de viajes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select

from flota.shared.infrastructure.db import RepositorioSql
from flota.viajes.domain.entidades import EstadoViaje, Viaje
from flota.viajes.domain.repositorios import RepositorioViajes
from flota.viajes.infrastructure.modelos import ViajeModel


class RepositorioViajesSql(RepositorioSql[Viaje, ViajeModel], RepositorioViajes):
    entidad, modelo, orden = Viaje, ViajeModel, ViajeModel.fecha_salida.desc()

    def listar_por_periodo(
        self, desde: datetime, hasta: datetime, camion_id: UUID | None = None
    ) -> list[Viaje]:
        stmt = select(ViajeModel).where(
            ViajeModel.fecha_salida >= desde, ViajeModel.fecha_salida < hasta
        )
        if camion_id:
            stmt = stmt.where(ViajeModel.camion_id == camion_id)
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
