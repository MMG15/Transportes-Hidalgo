"""Repositorio SQL de alertas."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from flota.alertas.domain.entidades import Alerta, EstadoAlerta, TipoAlerta
from flota.alertas.domain.repositorios import RepositorioAlertas
from flota.alertas.infrastructure.modelos import AlertaModel
from flota.shared.infrastructure.db import RepositorioSql

ESTADOS_ABIERTOS = (EstadoAlerta.ABIERTA, EstadoAlerta.EN_ANALISIS)


class RepositorioAlertasSql(RepositorioSql[Alerta, AlertaModel], RepositorioAlertas):
    entidad, modelo, orden = Alerta, AlertaModel, AlertaModel.creada_en.desc()

    def buscar_por_origen(
        self, tipo: TipoAlerta, origen_tabla: str, origen_id: UUID
    ) -> Alerta | None:
        return self._uno(
            select(AlertaModel).where(
                AlertaModel.tipo == tipo,
                AlertaModel.origen_tabla == origen_tabla,
                AlertaModel.origen_id == origen_id,
            )
        )

    def listar_por_estado(
        self, estados: list[EstadoAlerta] | None = None, limite: int = 200
    ) -> list[Alerta]:
        stmt = select(AlertaModel)
        if estados:
            stmt = stmt.where(AlertaModel.estado.in_(estados))
        return self._todos(stmt.order_by(self.orden).limit(limite))

    def contar_abiertas(self) -> int:
        consulta = select(func.count()).where(AlertaModel.estado.in_(ESTADOS_ABIERTOS))
        return self._s.scalar(consulta) or 0
