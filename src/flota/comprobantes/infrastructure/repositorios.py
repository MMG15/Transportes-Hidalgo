"""Repositorio SQL de comprobantes."""

from __future__ import annotations

from sqlalchemy import func, select

from flota.comprobantes.domain.entidades import Comprobante, EstadoComprobante, TipoComprobante
from flota.comprobantes.domain.repositorios import RepositorioComprobantes
from flota.comprobantes.infrastructure.modelos import ComprobanteModel
from flota.shared.infrastructure.db import RepositorioSql


class RepositorioComprobantesSql(
    RepositorioSql[Comprobante, ComprobanteModel], RepositorioComprobantes
):
    entidad, modelo, orden = Comprobante, ComprobanteModel, ComprobanteModel.recibido_en.desc()

    def listar_por_estado(
        self,
        estados: list[EstadoComprobante],
        tipo: TipoComprobante | None = None,
        limite: int = 200,
    ) -> list[Comprobante]:
        stmt = select(ComprobanteModel).where(ComprobanteModel.estado.in_(estados))
        if tipo:
            stmt = stmt.where(ComprobanteModel.tipo == tipo)
        return self._todos(stmt.order_by(ComprobanteModel.recibido_en).limit(limite))

    def contar_por_estado(self, estado: EstadoComprobante) -> int:
        consulta = select(func.count()).where(ComprobanteModel.estado == estado)
        return self._s.scalar(consulta) or 0
