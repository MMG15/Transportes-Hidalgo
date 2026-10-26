"""Lo que los casos de uso del catálogo necesitan del exterior."""

from __future__ import annotations

from typing import Protocol

from flota.catalogo.domain.repositorios import (
    RepositorioCamiones,
    RepositorioChoferes,
    RepositorioClientes,
    RepositorioProductos,
)
from flota.shared.application.unidad_de_trabajo import UnidadDeTrabajo


class UoWCatalogo(UnidadDeTrabajo, Protocol):
    camiones: RepositorioCamiones
    choferes: RepositorioChoferes
    clientes: RepositorioClientes
    productos: RepositorioProductos
