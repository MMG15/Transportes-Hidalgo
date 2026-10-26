"""Conversión del objeto de valor ImporteGasto a columnas y de vuelta.

Todas las tablas de gastos (combustible, peajes, viáticos) usan las mismas columnas:
monto_original, moneda, cotizacion, monto_ars, tipo_cambio_id, revisar_cotizacion.
"""

from __future__ import annotations

from flota.shared.domain.dinero import Dinero, ImporteGasto

COLUMNAS_IMPORTE = (
    "monto_original",
    "moneda",
    "cotizacion",
    "monto_ars",
    "tipo_cambio_id",
    "revisar_cotizacion",
)


def importe_a_columnas(importe: ImporteGasto | None) -> dict[str, object]:
    if importe is None:
        return dict.fromkeys(COLUMNAS_IMPORTE) | {"revisar_cotizacion": False}
    return {
        "monto_original": importe.original.monto,
        "moneda": importe.original.moneda.value,
        "cotizacion": importe.cotizacion,
        "monto_ars": importe.monto_ars,
        "tipo_cambio_id": importe.tipo_cambio_id,
        "revisar_cotizacion": importe.revisar_cotizacion,
    }


def importe_desde_modelo(modelo: object) -> ImporteGasto | None:
    if getattr(modelo, "monto_original", None) is None:
        return None
    return ImporteGasto(
        original=Dinero(modelo.monto_original, modelo.moneda),
        cotizacion=modelo.cotizacion,
        monto_ars=modelo.monto_ars,
        tipo_cambio_id=modelo.tipo_cambio_id,
        revisar_cotizacion=modelo.revisar_cotizacion,
    )
