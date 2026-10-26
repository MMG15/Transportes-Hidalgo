"""Objetos de valor para importes en distintas monedas (RF-40, RF-41).

Un OBJETO DE VALOR no tiene identidad: dos `Dinero(100, ARS)` son iguales e intercambiables.
Es inmutable (`frozen=True`): las operaciones devuelven un objeto nuevo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from flota.shared.domain.errores import DatosInvalidos, ReglaNegocioViolada

CENTAVOS = Decimal("0.01")


class Moneda(StrEnum):
    ARS = "ARS"  # peso argentino
    CLP = "CLP"  # peso chileno


@dataclass(frozen=True)
class Dinero:
    monto: Decimal
    moneda: Moneda = Moneda.ARS

    def __post_init__(self) -> None:
        # En una dataclass congelada no se puede hacer self.x = ...: se usa object.__setattr__.
        object.__setattr__(self, "moneda", Moneda(self.moneda))
        object.__setattr__(self, "monto", Decimal(self.monto))

    def __add__(self, otro: Dinero) -> Dinero:
        self._misma_moneda(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def __sub__(self, otro: Dinero) -> Dinero:
        self._misma_moneda(otro)
        return Dinero(self.monto - otro.monto, self.moneda)

    def __mul__(self, factor: Decimal | int) -> Dinero:
        return Dinero(self.monto * Decimal(factor), self.moneda)

    def __lt__(self, otro: Dinero) -> bool:
        self._misma_moneda(otro)
        return self.monto < otro.monto

    def redondeado(self) -> Dinero:
        return Dinero(self.monto.quantize(CENTAVOS, rounding=ROUND_HALF_UP), self.moneda)

    def _misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise ReglaNegocioViolada(
                f"No se pueden operar {self.moneda} y {otro.moneda} sin convertir antes"
            )

    def __str__(self) -> str:
        return f"{self.moneda} {self.monto:,.2f}"


@dataclass(frozen=True)
class ImporteGasto:
    """Lo que cada gasto (combustible, peaje, viático) guarda de su importe (RF-40):
    monto original, moneda, cotización aplicada y monto convertido a ARS.

    La cotización queda FIJA en el gasto: actualizar la tabla de tipos de cambio después no
    cambia los gastos ya registrados (RF-41).
    """

    original: Dinero
    cotizacion: Decimal  # pesos argentinos por unidad de la moneda original (ARS -> 1)
    monto_ars: Decimal
    tipo_cambio_id: UUID | None = None
    revisar_cotizacion: bool = False  # se usó la última cotización disponible, no la del día

    def __post_init__(self) -> None:
        if self.original.monto < 0:
            raise DatosInvalidos("El importe no puede ser negativo")
        if self.cotizacion <= 0:
            raise DatosInvalidos("La cotización debe ser mayor a cero")

    @classmethod
    def en_pesos(cls, monto: Decimal) -> ImporteGasto:
        """Gasto en ARS: no necesita conversión."""
        original = Dinero(monto, Moneda.ARS).redondeado()
        return cls(original=original, cotizacion=Decimal("1"), monto_ars=original.monto)

    @classmethod
    def convertido(
        cls,
        original: Dinero,
        cotizacion: Decimal,
        tipo_cambio_id: UUID | None = None,
        revisar_cotizacion: bool = False,
    ) -> ImporteGasto:
        monto_ars = (original.monto * cotizacion).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
        return cls(
            original=original.redondeado(),
            cotizacion=cotizacion,
            monto_ars=monto_ars,
            tipo_cambio_id=tipo_cambio_id,
            revisar_cotizacion=revisar_cotizacion,
        )

    @property
    def ars(self) -> Dinero:
        return Dinero(self.monto_ars, Moneda.ARS)
