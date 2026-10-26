"""Repositorio SQL del tipo de cambio."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flota.monedas.domain.entidades import TipoCambio
from flota.monedas.domain.repositorios import RepositorioTiposCambio
from flota.monedas.infrastructure.modelos import TipoCambioModel
from flota.shared.domain.dinero import Moneda
from flota.shared.infrastructure.db import RepositorioSql


class RepositorioTiposCambioSql(
    RepositorioSql[TipoCambio, TipoCambioModel], RepositorioTiposCambio
):
    entidad, modelo, orden = TipoCambio, TipoCambioModel, TipoCambioModel.fecha.desc()

    def __init__(self, session: Session, tablas_de_gastos: Sequence[type] = ()) -> None:
        """`tablas_de_gastos`: modelos con columna `tipo_cambio_id` (cargas, peajes, viáticos).

        Los recibe de la raíz de composición: este módulo no importa a los que lo usan.
        """
        super().__init__(session)
        self._tablas_de_gastos = tablas_de_gastos

    def _consulta(self, origen: Moneda, destino: Moneda):
        return select(TipoCambioModel).where(
            TipoCambioModel.moneda_origen == origen, TipoCambioModel.moneda_destino == destino
        )

    def obtener_por_fecha(
        self, fecha: date, origen: Moneda, destino: Moneda = Moneda.ARS
    ) -> TipoCambio | None:
        return self._uno(self._consulta(origen, destino).where(TipoCambioModel.fecha == fecha))

    def vigente_al(
        self, fecha: date, origen: Moneda, destino: Moneda = Moneda.ARS
    ) -> TipoCambio | None:
        return self._uno(
            self._consulta(origen, destino)
            .where(TipoCambioModel.fecha <= fecha)
            .order_by(TipoCambioModel.fecha.desc())
        )

    def contar_usos(self, tipo_cambio_id: UUID) -> int:
        total = 0
        for tabla in self._tablas_de_gastos:
            consulta = select(func.count()).where(tabla.tipo_cambio_id == tipo_cambio_id)
            total += self._s.scalar(consulta) or 0
        return total
