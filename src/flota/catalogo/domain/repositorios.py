"""Puertos de persistencia del catálogo."""

from __future__ import annotations

from abc import abstractmethod

from flota.catalogo.domain.entidades import Camion, Chofer, Cliente, Producto
from flota.shared.domain.repositorio import Repositorio


class RepositorioCamiones(Repositorio[Camion]):
    @abstractmethod
    def obtener_por_patente(self, patente: str) -> Camion | None: ...


class RepositorioChoferes(Repositorio[Chofer]):
    @abstractmethod
    def obtener_por_dni(self, dni: str) -> Chofer | None: ...


class RepositorioClientes(Repositorio[Cliente]):
    pass


class RepositorioProductos(Repositorio[Producto]):
    @abstractmethod
    def obtener_por_nombre(self, nombre: str) -> Producto | None: ...
