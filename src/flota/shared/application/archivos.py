"""Puerto para guardar archivos (fotos y PDF de comprobantes, RF-07).

Hoy el adaptador guarda en una carpeta del servidor; mañana podría ser un almacenamiento en la
nube sin tocar los casos de uso (sección 14.2 del documento: puerto `AlmacenArchivos`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AlmacenArchivos(ABC):
    @abstractmethod
    def guardar(self, contenido: bytes, extension: str, carpeta: str) -> str:
        """Guarda el archivo y devuelve su CLAVE (para leerlo después)."""

    @abstractmethod
    def leer(self, clave: str) -> bytes: ...
