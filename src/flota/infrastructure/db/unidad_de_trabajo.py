from __future__ import annotations

from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from flota.application.ports import UnidadDeTrabajo
from flota.infrastructure.db.repositorios import (
    RepositorioCamionesSql,
    RepositorioCargasSql,
    RepositorioChoferesSql,
    RepositorioClientesSql,
    RepositorioProductosSql,
    RepositorioViajesSql,
)


class UnidadDeTrabajoSql(UnidadDeTrabajo):
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
