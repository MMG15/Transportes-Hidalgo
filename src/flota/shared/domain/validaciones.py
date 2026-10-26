"""Validaciones reutilizables por las entidades de todos los módulos."""

from __future__ import annotations

from decimal import Decimal

from flota.shared.domain.errores import DatosInvalidos


def requerido(valor: str | None, campo: str) -> str:
    if valor is None or not str(valor).strip():
        raise DatosInvalidos(f"El campo '{campo}' es obligatorio")
    return str(valor).strip()


def opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    return str(valor).strip() or None


def positivo(valor: Decimal | None, campo: str) -> Decimal:
    if valor is None or valor <= 0:
        raise DatosInvalidos(f"El campo '{campo}' debe ser mayor a cero")
    return valor


def no_negativo(valor: Decimal | None, campo: str) -> Decimal | None:
    if valor is not None and valor < 0:
        raise DatosInvalidos(f"El campo '{campo}' no puede ser negativo")
    return valor
