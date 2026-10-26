"""Lo que los casos de uso de viajes necesitan del exterior."""

from __future__ import annotations

from typing import Protocol

from flota.catalogo.application.puertos import UoWCatalogo
from flota.viajes.domain.repositorios import RepositorioRutas, RepositorioViajes


class UoWViajes(UoWCatalogo, Protocol):
    rutas: RepositorioRutas
    viajes: RepositorioViajes
