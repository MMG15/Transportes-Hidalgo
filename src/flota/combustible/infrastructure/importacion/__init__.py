"""Lectores de archivos de cargas de combustible."""

from pathlib import Path

from flota.combustible.application.puertos import LectorCargas
from flota.combustible.infrastructure.importacion.lector_csv import LectorCsv
from flota.combustible.infrastructure.importacion.lector_excel import LectorExcel

EXTENSIONES_SOPORTADAS = {".xlsx", ".xlsm", ".csv", ".txt"}


def lector_para_archivo(ruta: Path) -> LectorCargas:
    """Elige el lector según la extensión del archivo."""
    extension = ruta.suffix.lower()
    if extension in {".xlsx", ".xlsm"}:
        return LectorExcel()
    if extension in {".csv", ".txt"}:
        return LectorCsv()
    raise ValueError(f"Formato no soportado: {extension}. Use .xlsx o .csv")


__all__ = ["EXTENSIONES_SOPORTADAS", "LectorCsv", "LectorExcel", "lector_para_archivo"]
