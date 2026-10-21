from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from pathlib import Path

from flota.application.dto import ErrorLectura, FilaCarga
from flota.application.ports import LectorCargas
from flota.infrastructure.importacion.mapeo import procesar_filas


class LectorCsv(LectorCargas):
    """Lee CSV de tarjetas de combustible. Detecta el separador (; , tab) y la codificación."""

    def leer(self, ruta: Path) -> Iterator[FilaCarga | ErrorLectura]:
        contenido = _leer_texto(ruta)
        if not contenido.strip():
            yield ErrorLectura(1, "El archivo está vacío")
            return
        try:
            dialecto = csv.Sniffer().sniff(contenido[:4096], delimiters=";,\t|")
        except csv.Error:
            dialecto = csv.excel  # separador por defecto: coma
        filas = csv.reader(io.StringIO(contenido, newline=""), dialecto)
        encabezado = next(filas)
        yield from procesar_filas(encabezado, enumerate(filas, start=2))


def _leer_texto(ruta: Path) -> str:
    # utf-8-sig quita la marca BOM que agrega Excel; latin-1 es común en sistemas viejos.
    try:
        return ruta.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return ruta.read_text(encoding="latin-1")
