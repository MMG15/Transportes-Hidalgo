"""Filtros de Jinja2 para mostrar datos en formato argentino."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

VACIO = "—"


def numero(valor: Decimal | float | int | None, decimales: int = 2) -> str:
    """1234.5 -> '1.234,50'"""
    if valor is None:
        return VACIO
    texto = f"{valor:,.{decimales}f}"  # formato inglés: 1,234.50
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def moneda(valor: Decimal | float | None) -> str:
    return VACIO if valor is None else f"$ {numero(valor)}"


def fecha(valor: datetime | date | None, con_hora: bool = True) -> str:
    if valor is None:
        return VACIO
    if isinstance(valor, datetime) and con_hora:
        return f"{valor:%d/%m/%Y %H:%M}"
    return f"{valor:%d/%m/%Y}"


def fecha_input(valor: datetime | date | None) -> str:
    """Formato que esperan los <input type="datetime-local"> / "date"."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return f"{valor:%Y-%m-%dT%H:%M}"
    return f"{valor:%Y-%m-%d}"


FILTROS = {"numero": numero, "moneda": moneda, "fecha": fecha, "fecha_input": fecha_input}
