"""Lo que los casos de uso de monedas necesitan del exterior."""

from __future__ import annotations

from typing import Protocol

from flota.monedas.domain.repositorios import RepositorioTiposCambio
from flota.shared.application.unidad_de_trabajo import UnidadDeTrabajo


class UoWMonedas(UnidadDeTrabajo, Protocol):
    tipos_cambio: RepositorioTiposCambio
