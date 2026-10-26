"""Repositorios SQL del catálogo (implementan los puertos del dominio)."""

from __future__ import annotations

from sqlalchemy import select

from flota.catalogo.domain.entidades import Camion, Chofer, Cliente, Producto, normalizar_patente
from flota.catalogo.domain.repositorios import (
    RepositorioCamiones,
    RepositorioChoferes,
    RepositorioClientes,
    RepositorioProductos,
)
from flota.catalogo.infrastructure.modelos import (
    CamionModel,
    ChoferModel,
    ClienteModel,
    ProductoModel,
)
from flota.shared.infrastructure.db import RepositorioSql


class RepositorioCamionesSql(RepositorioSql[Camion, CamionModel], RepositorioCamiones):
    entidad, modelo, orden = Camion, CamionModel, CamionModel.patente.asc()

    def obtener_por_patente(self, patente: str) -> Camion | None:
        patente = normalizar_patente(patente)
        return self._uno(select(CamionModel).where(CamionModel.patente == patente))


class RepositorioChoferesSql(RepositorioSql[Chofer, ChoferModel], RepositorioChoferes):
    entidad, modelo, orden = Chofer, ChoferModel, ChoferModel.nombre.asc()

    def obtener_por_dni(self, dni: str) -> Chofer | None:
        return self._uno(select(ChoferModel).where(ChoferModel.dni == dni))


class RepositorioClientesSql(RepositorioSql[Cliente, ClienteModel], RepositorioClientes):
    entidad, modelo, orden = Cliente, ClienteModel, ClienteModel.razon_social.asc()


class RepositorioProductosSql(RepositorioSql[Producto, ProductoModel], RepositorioProductos):
    entidad, modelo, orden = Producto, ProductoModel, ProductoModel.nombre.asc()

    def obtener_por_nombre(self, nombre: str) -> Producto | None:
        return self._uno(select(ProductoModel).where(ProductoModel.nombre == nombre.strip()))
