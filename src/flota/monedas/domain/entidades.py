"""Tipo de cambio diario y la regla de conversión de gastos (RF-39, RF-40, RF-41)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from flota.shared.domain.dinero import Dinero, ImporteGasto, Moneda
from flota.shared.domain.errores import DatosInvalidos, ReglaNegocioViolada
from flota.shared.domain.validaciones import positivo, requerido


@dataclass(kw_only=True)
class TipoCambio:
    """Cotización de un día: cuántos pesos argentinos vale 1 unidad de la moneda de origen.

    Ejemplo: 1 CLP = 1,25 ARS  ->  TipoCambio(fecha, CLP, ARS, cotizacion=Decimal("1.25"))
    """

    fecha: date
    cotizacion: Decimal
    moneda_origen: Moneda = Moneda.CLP
    moneda_destino: Moneda = Moneda.ARS
    fuente: str = "manual"
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.moneda_origen = Moneda(self.moneda_origen)
        self.moneda_destino = Moneda(self.moneda_destino)
        if self.moneda_origen == self.moneda_destino:
            raise DatosInvalidos("Las monedas de origen y destino deben ser distintas")
        positivo(self.cotizacion, "cotizacion")
        self.fuente = requerido(self.fuente, "fuente")

    def corregir(self, cotizacion: Decimal, fuente: str) -> None:
        positivo(cotizacion, "cotizacion")
        self.cotizacion = cotizacion
        self.fuente = requerido(fuente, "fuente")


def convertir_a_pesos(
    monto: Dinero, tipo_cambio: TipoCambio | None, fecha_gasto: date
) -> ImporteGasto:
    """Regla única de conversión para todos los gastos (combustible, peajes, viáticos).

    - Gasto en ARS: no se convierte.
    - Gasto en otra moneda: se aplica la cotización vigente a la fecha del gasto. Si no hay
      cotización de ese día se usa la última anterior y el gasto queda marcado para revisar
      (CU-12 E1).
    """
    if monto.moneda == Moneda.ARS:
        return ImporteGasto.en_pesos(monto.monto)
    if tipo_cambio is None:
        raise ReglaNegocioViolada(
            f"No hay ninguna cotización {monto.moneda} → ARS cargada "
            f"hasta el {fecha_gasto:%d/%m/%Y}"
        )
    if tipo_cambio.moneda_origen != monto.moneda or tipo_cambio.fecha > fecha_gasto:
        raise ReglaNegocioViolada("La cotización no corresponde al gasto")
    return ImporteGasto.convertido(
        monto,
        tipo_cambio.cotizacion,
        tipo_cambio_id=tipo_cambio.id,
        revisar_cotizacion=tipo_cambio.fecha != fecha_gasto,
    )
