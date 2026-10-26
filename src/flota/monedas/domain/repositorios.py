"""Puertos de persistencia del tipo de cambio."""

from __future__ import annotations

from abc import abstractmethod
from datetime import date
from uuid import UUID

from flota.monedas.domain.entidades import TipoCambio
from flota.shared.domain.dinero import Moneda
from flota.shared.domain.repositorio import Repositorio


class RepositorioTiposCambio(Repositorio[TipoCambio]):
    @abstractmethod
    def obtener_por_fecha(
        self, fecha: date, origen: Moneda, destino: Moneda = Moneda.ARS
    ) -> TipoCambio | None: ...

    @abstractmethod
    def vigente_al(
        self, fecha: date, origen: Moneda, destino: Moneda = Moneda.ARS
    ) -> TipoCambio | None:
        """La cotización de esa fecha o, si no hay, la última anterior."""

    @abstractmethod
    def contar_usos(self, tipo_cambio_id: UUID) -> int:
        """Cuántos gastos (de cualquier módulo) se convirtieron con esta cotización."""
