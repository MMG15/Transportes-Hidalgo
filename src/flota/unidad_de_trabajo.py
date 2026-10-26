"""Unidad de trabajo concreta del sistema.

Vive en la raíz del paquete (junto a `bootstrap.py`) porque es la única pieza que conoce los
repositorios de TODOS los módulos. Cumple los protocolos `UoWCatalogo`, `UoWViajes`,
`UoWCombustible`, ... de cada módulo.
"""

from __future__ import annotations

from typing import Protocol, Self

from sqlalchemy.orm import Session, sessionmaker

from flota.catalogo.infrastructure.repositorios import (
    RepositorioCamionesSql,
    RepositorioChoferesSql,
    RepositorioClientesSql,
    RepositorioProductosSql,
)
from flota.combustible.infrastructure.repositorios import RepositorioCargasSql
from flota.reportes.application.puertos import UoWReportes
from flota.shared.application.unidad_de_trabajo import UnidadDeTrabajoBase
from flota.viajes.infrastructure.repositorios import RepositorioViajesSql


class UnidadDeTrabajoSistema(UoWReportes, Protocol):
    """La suma de lo que piden todos los módulos (la usan la API, el panel y la consola)."""


class UnidadDeTrabajoSql(UnidadDeTrabajoBase):
    """Abre una sesión (transacción) nueva en cada `with`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self.camiones = RepositorioCamionesSql(self._session)
        self.choferes = RepositorioChoferesSql(self._session)
        self.clientes = RepositorioClientesSql(self._session)
        self.productos = RepositorioProductosSql(self._session)
        self.viajes = RepositorioViajesSql(self._session)
        self.cargas = RepositorioCargasSql(self._session)
        return super().__enter__()

    def __exit__(self, *args: object) -> None:
        super().__exit__(*args)
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
