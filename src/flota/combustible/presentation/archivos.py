"""Importación de un archivo subido por HTTP (lo usan la API y el panel web)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

from flota.combustible.application.dto import ResultadoImportacion
from flota.combustible.application.importacion import ImportarCargas
from flota.combustible.application.puertos import UoWCombustible
from flota.combustible.domain.entidades import OrigenDato
from flota.combustible.infrastructure.importacion import lector_para_archivo


def importar_subida(
    uow: UoWCombustible,
    contenido: BinaryIO,
    nombre_archivo: str,
    origen: OrigenDato,
) -> ResultadoImportacion:
    """Lanza ValueError si el formato no es soportado."""
    extension = Path(nombre_archivo).suffix.lower()
    lector = lector_para_archivo(Path(f"archivo{extension}"))
    # Los lectores trabajan con rutas: se guarda en una carpeta temporal que luego se borra.
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / f"importacion{extension}"
        with ruta.open("wb") as destino:
            shutil.copyfileobj(contenido, destino)
        return ImportarCargas(uow, lector, origen).ejecutar(ruta)
