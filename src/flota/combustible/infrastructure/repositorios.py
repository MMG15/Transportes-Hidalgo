"""Repositorio SQL de cargas de combustible."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select

from flota.combustible.domain.entidades import CargaCombustible
from flota.combustible.domain.repositorios import RepositorioCargas
from flota.combustible.infrastructure.modelos import CargaCombustibleModel
from flota.shared.infrastructure.db import RepositorioSql
from flota.shared.infrastructure.importes import importe_a_columnas, importe_desde_modelo


class RepositorioCargasSql(
    RepositorioSql[CargaCombustible, CargaCombustibleModel], RepositorioCargas
):
    entidad, modelo, orden = (
        CargaCombustible,
        CargaCombustibleModel,
        CargaCombustibleModel.fecha.desc(),
    )

    # El importe es un objeto de valor que ocupa varias columnas.
    def _a_entidad(self, modelo: CargaCombustibleModel) -> CargaCombustible:
        datos = {
            f.name: getattr(modelo, f.name) for f in fields(CargaCombustible) if f.name != "importe"
        }
        return CargaCombustible(**datos, importe=importe_desde_modelo(modelo))

    def _a_modelo(self, carga: CargaCombustible) -> CargaCombustibleModel:
        datos = {f.name: getattr(carga, f.name) for f in fields(carga) if f.name != "importe"}
        return CargaCombustibleModel(**datos, **importe_a_columnas(carga.importe))

    def listar_por_viajes(self, viaje_ids: Sequence[UUID]) -> list[CargaCombustible]:
        if not viaje_ids:
            return []
        stmt = select(CargaCombustibleModel).where(CargaCombustibleModel.viaje_id.in_(viaje_ids))
        return self._todos(stmt.order_by(CargaCombustibleModel.fecha))

    def listar_filtrado(
        self,
        camion_id: UUID | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 100,
        desplazamiento: int = 0,
    ) -> list[CargaCombustible]:
        stmt = select(CargaCombustibleModel)
        if camion_id:
            stmt = stmt.where(CargaCombustibleModel.camion_id == camion_id)
        if desde:
            stmt = stmt.where(CargaCombustibleModel.fecha >= desde)
        if hasta:
            stmt = stmt.where(CargaCombustibleModel.fecha < hasta)
        stmt = stmt.order_by(self.orden).limit(limite).offset(desplazamiento)
        return self._todos(stmt)

    def existe_duplicado(self, carga: CargaCombustible) -> bool:
        m = CargaCombustibleModel
        if carga.referencia_externa:
            condicion = m.referencia_externa == carga.referencia_externa
        else:
            condicion = and_(
                m.camion_id == carga.camion_id, m.fecha == carga.fecha, m.litros == carga.litros
            )
        return self._s.scalars(select(m.id).where(condicion).limit(1)).first() is not None
