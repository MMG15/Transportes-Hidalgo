"""Unidad de trabajo concreta del sistema.

Vive en la raíz del paquete (junto a `bootstrap.py`) porque es la única pieza que conoce los
repositorios de TODOS los módulos. Cumple los protocolos `UoWCatalogo`, `UoWViajes`,
`UoWCombustible`, ... de cada módulo.
"""

from __future__ import annotations

from typing import Protocol, Self

from sqlalchemy.orm import Session, sessionmaker

from flota.alertas.application.puertos import UoWAlertas
from flota.alertas.infrastructure.repositorios import RepositorioAlertasSql
from flota.catalogo.infrastructure.repositorios import (
    RepositorioCamionesSql,
    RepositorioChoferesSql,
    RepositorioClientesSql,
    RepositorioProductosSql,
)
from flota.combustible.infrastructure.modelos import CargaCombustibleModel
from flota.combustible.infrastructure.repositorios import RepositorioCargasSql
from flota.monedas.infrastructure.repositorios import RepositorioTiposCambioSql
from flota.reportes.application.puertos import UoWReportes
from flota.shared.application.eventos import BusEventos
from flota.shared.application.unidad_de_trabajo import UnidadDeTrabajoBase
from flota.shared.domain.auditoria import SISTEMA, Actor
from flota.shared.infrastructure.auditoria import RepositorioAuditoriaSql
from flota.usuarios.application.puertos import UoWUsuarios
from flota.usuarios.infrastructure.repositorios import RepositorioUsuariosSql
from flota.viajes.infrastructure.repositorios import RepositorioRutasSql, RepositorioViajesSql

# Tablas con importes convertidos (para saber si una cotización ya se usó, RF-41).
TABLAS_DE_GASTOS = (CargaCombustibleModel,)


class UnidadDeTrabajoSistema(UoWReportes, UoWAlertas, UoWUsuarios, Protocol):
    """La suma de lo que piden todos los módulos (la usan la API, el panel y la consola)."""


class UnidadDeTrabajoSql(UnidadDeTrabajoBase):
    """Abre una sesión (transacción) nueva en cada `with`."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        bus: BusEventos | None = None,
        actor: Actor = SISTEMA,
    ) -> None:
        super().__init__(bus, actor)
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self.camiones = RepositorioCamionesSql(self._session)
        self.choferes = RepositorioChoferesSql(self._session)
        self.clientes = RepositorioClientesSql(self._session)
        self.productos = RepositorioProductosSql(self._session)
        self.rutas = RepositorioRutasSql(self._session)
        self.viajes = RepositorioViajesSql(self._session)
        self.cargas = RepositorioCargasSql(self._session)
        self.tipos_cambio = RepositorioTiposCambioSql(self._session, TABLAS_DE_GASTOS)
        self.alertas = RepositorioAlertasSql(self._session)
        self.usuarios = RepositorioUsuariosSql(self._session)
        self.auditoria = RepositorioAuditoriaSql(self._session)
        return super().__enter__()

    def __exit__(self, *args: object) -> None:
        super().__exit__(*args)
        self._session.close()

    def _confirmar(self) -> None:
        self._session.commit()

    def _descartar(self) -> None:
        self._session.rollback()
