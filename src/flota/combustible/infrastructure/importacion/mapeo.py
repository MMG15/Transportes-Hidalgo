"""Lógica común a todos los lectores: reconocer columnas y convertir valores.

Los archivos de distintas tarjetas de combustible usan nombres de columna distintos
("Dominio", "Patente", "Vehículo"...). Los ALIAS permiten aceptarlos a todos.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flota.combustible.application.dto import ErrorLectura, FilaCarga

ALIAS: dict[str, set[str]] = {
    "fecha": {"fecha", "fecha_carga", "fecha_hora", "fecha_y_hora", "date"},
    "patente": {"patente", "dominio", "vehiculo", "camion", "matricula"},
    "litros": {"litros", "lts", "cantidad_litros", "volumen", "cantidad"},
    "precio_litro": {"precio_litro", "precio", "precio_unitario", "precio_por_litro", "pu"},
    "odometro_km": {"odometro_km", "odometro", "km", "kilometraje", "kms"},
    "estacion": {"estacion", "estacion_servicio", "establecimiento", "lugar", "comercio"},
    "importe": {"importe", "monto", "total", "importe_total", "monto_total"},
    "moneda": {"moneda", "divisa"},
    "referencia": {
        "referencia",
        "ticket",
        "nro_ticket",
        "comprobante",
        "nro_comprobante",
        "id_transaccion",
        "transaccion",
        "remito",
    },
}
OBLIGATORIAS = ("fecha", "patente", "litros")
MONEDAS = {"ARS", "CLP"}
_CANONICA = {alias: canonica for canonica, aliases in ALIAS.items() for alias in aliases}

_FORMATOS_FECHA = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%y %H:%M",
    "%d/%m/%y",
)
_MILES_CON_PUNTO = re.compile(r"^-?\d{1,3}(\.\d{3})+$")


def normalizar_encabezado(texto: object) -> str:
    """'Odómetro (km)' -> 'odometro_km'"""
    if texto is None:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower()).strip("_")


def a_decimal(valor: object) -> Decimal | None:
    """Acepta números y textos en formato argentino ('1.234,56') o inglés ('1,234.56')."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int | float):
        return Decimal(str(valor))
    texto = str(valor).strip().replace("$", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    elif _MILES_CON_PUNTO.match(texto):
        texto = texto.replace(".", "")
    try:
        return Decimal(texto)
    except InvalidOperation as error:
        raise ValueError(f"'{valor}' no es un número válido") from error


def a_fecha(valor: object) -> datetime | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, datetime.min.time())
    texto = str(valor).strip()
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(texto)
    except ValueError as error:
        raise ValueError(f"'{valor}' no es una fecha válida") from error


def _texto(valor: object) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)  # nro. de ticket leído como 1234.0
    return str(valor).strip() or None


def procesar_filas(
    encabezado: Sequence[object], filas: Iterable[tuple[int, Sequence[object]]]
) -> Iterator[FilaCarga | ErrorLectura]:
    """Convierte filas crudas (número de fila, valores) en FilaCarga o ErrorLectura."""
    indices: dict[str, int] = {}
    for i, nombre in enumerate(encabezado):
        canonica = _CANONICA.get(normalizar_encabezado(nombre))
        if canonica and canonica not in indices:
            indices[canonica] = i

    faltantes = [c for c in OBLIGATORIAS if c not in indices]
    if faltantes:
        yield ErrorLectura(1, f"Faltan las columnas obligatorias: {', '.join(faltantes)}")
        return

    for numero, valores in filas:
        if all(v is None or str(v).strip() == "" for v in valores):
            continue  # fila vacía

        def valor(campo: str, valores=valores) -> object:
            i = indices.get(campo)
            return valores[i] if i is not None and i < len(valores) else None

        try:
            fecha = a_fecha(valor("fecha"))
            patente = _texto(valor("patente"))
            litros = a_decimal(valor("litros"))
            if fecha is None or patente is None or litros is None:
                raise ValueError("fecha, patente y litros son obligatorios")
            moneda = (_texto(valor("moneda")) or "ARS").upper()
            if moneda not in MONEDAS:
                raise ValueError(f"moneda '{moneda}' no soportada (use ARS o CLP)")
            yield FilaCarga(
                numero_fila=numero,
                fecha=fecha,
                patente=patente,
                litros=litros,
                precio_litro=a_decimal(valor("precio_litro")),
                odometro_km=a_decimal(valor("odometro_km")),
                estacion=_texto(valor("estacion")),
                referencia=_texto(valor("referencia")),
                importe=a_decimal(valor("importe")),
                moneda=moneda,
            )
        except ValueError as error:
            yield ErrorLectura(numero, str(error))
