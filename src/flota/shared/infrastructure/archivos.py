"""Adaptador de AlmacenArchivos sobre una carpeta del disco."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from flota.shared.application.archivos import AlmacenArchivos
from flota.shared.domain.errores import NoEncontrado


class AlmacenEnDisco(AlmacenArchivos):
    """Guarda en `<raiz>/<carpeta>/<año>/<mes>/<uuid>.<ext>`. La clave es la ruta relativa.

    El nombre lo genera el sistema (no el usuario): así nadie puede pisar otro archivo ni
    escribir fuera de la carpeta con nombres como `../../config`.
    """

    def __init__(self, raiz: Path) -> None:
        self._raiz = raiz.resolve()

    def guardar(self, contenido: bytes, extension: str, carpeta: str) -> str:
        hoy = date.today()
        clave = f"{carpeta}/{hoy:%Y}/{hoy:%m}/{uuid4().hex}.{extension.lstrip('.').lower()}"
        destino = self._ruta(clave)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        return clave

    def leer(self, clave: str) -> bytes:
        ruta = self._ruta(clave)
        if not ruta.is_file():
            raise NoEncontrado(f"No se encontró el archivo {clave}")
        return ruta.read_bytes()

    def _ruta(self, clave: str) -> Path:
        ruta = (self._raiz / clave).resolve()
        if not ruta.is_relative_to(self._raiz):  # defensa extra contra "../"
            raise NoEncontrado("Ruta de archivo inválida")
        return ruta
