"""Adaptadores de repositorio sobre SQLAlchemy (implementan los puertos del dominio)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from flota.domain.entities import (
    Camion,
    CargaCombustible,
    Chofer,
    Cliente,
    EstadoViaje,
    Producto,
    Viaje,
    normalizar_patente,
)
from flota.domain.repositories import (
    RepositorioCamiones,
    RepositorioCargas,
    RepositorioChoferes,
    RepositorioClientes,
    RepositorioProductos,
    RepositorioViajes,
)
from flota.infrastructure.db.models import (
    CamionModel,
    CargaCombustibleModel,
    ChoferModel,
    ClienteModel,
    ProductoModel,
    ViajeModel,
)


class _RepositorioSql[E, M]:
    """Implementación genérica: guardar/obtener/listar + conversión entidad <-> modelo.

    La conversión funciona porque las entidades y los modelos usan los mismos nombres de campo.
    """

    entidad: ClassVar[type]
    modelo: ClassVar[type]
    # Debe ser una expresión (.asc() / .desc()), no la columna sola: una columna es un
    # descriptor y, leída como self.orden, SQLAlchemy intentaría resolverla sobre el repositorio.
    orden: ClassVar[Any]

    def __init__(self, session: Session) -> None:
        self._s = session

    def guardar(self, entidad: E) -> None:
        self._s.merge(self._a_modelo(entidad))  # merge = INSERT o UPDATE según exista
        self._s.flush()

    def obtener(self, id: UUID) -> E | None:
        modelo = self._s.get(self.modelo, id)
        return self._a_entidad(modelo) if modelo else None

    def listar(self, limite: int = 100, desplazamiento: int = 0) -> list[E]:
        stmt = select(self.modelo).order_by(self.orden).limit(limite).offset(desplazamiento)
        return self._todos(stmt)

    def _todos(self, stmt) -> list[E]:
        return [self._a_entidad(m) for m in self._s.scalars(stmt)]

    def _uno(self, stmt) -> E | None:
        modelo = self._s.scalars(stmt.limit(1)).first()
        return self._a_entidad(modelo) if modelo else None

    def _a_entidad(self, modelo: M) -> E:
        return self.entidad(**{f.name: getattr(modelo, f.name) for f in fields(self.entidad)})

    def _a_modelo(self, entidad: E) -> M:
        return self.modelo(**{f.name: getattr(entidad, f.name) for f in fields(entidad)})


class RepositorioCamionesSql(_RepositorioSql[Camion, CamionModel], RepositorioCamiones):
    entidad, modelo, orden = Camion, CamionModel, CamionModel.patente.asc()

    def obtener_por_patente(self, patente: str) -> Camion | None:
        patente = normalizar_patente(patente)
        return self._uno(select(CamionModel).where(CamionModel.patente == patente))


class RepositorioChoferesSql(_RepositorioSql[Chofer, ChoferModel], RepositorioChoferes):
    entidad, modelo, orden = Chofer, ChoferModel, ChoferModel.nombre.asc()

    def obtener_por_dni(self, dni: str) -> Chofer | None:
        return self._uno(select(ChoferModel).where(ChoferModel.dni == dni))


class RepositorioClientesSql(_RepositorioSql[Cliente, ClienteModel], RepositorioClientes):
    entidad, modelo, orden = Cliente, ClienteModel, ClienteModel.razon_social.asc()


class RepositorioProductosSql(_RepositorioSql[Producto, ProductoModel], RepositorioProductos):
    entidad, modelo, orden = Producto, ProductoModel, ProductoModel.nombre.asc()

    def obtener_por_nombre(self, nombre: str) -> Producto | None:
        return self._uno(select(ProductoModel).where(ProductoModel.nombre == nombre.strip()))


class RepositorioViajesSql(_RepositorioSql[Viaje, ViajeModel], RepositorioViajes):
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


class RepositorioCargasSql(
    _RepositorioSql[CargaCombustible, CargaCombustibleModel], RepositorioCargas
):
    entidad, modelo, orden = (
        CargaCombustible,
        CargaCombustibleModel,
        CargaCombustibleModel.fecha.desc(),
    )

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
