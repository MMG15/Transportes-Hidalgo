"""Comprobante: la foto o PDF de un ticket, tal como llegó (RF-01, RF-02, RF-06, RF-07).

Un comprobante NO es una carga: puede llegar ilegible o incompleto. Cuando sus datos están
completos y validados (por la IA o por una persona, CU-02) se crea el gasto correspondiente
(carga de combustible, peaje o viático) y el comprobante queda PROCESADO, vinculado a ese gasto.

    RECIBIDO ──► PENDIENTE (falta un dato, baja confianza, patente distinta...) ──► PROCESADO
        │                                    │
        └──────────────────────────────────► └──► DESCARTADO (ilegible, ajeno a la empresa)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.errores import DatosInvalidos, ReglaNegocioViolada
from flota.shared.domain.validaciones import requerido


class TipoComprobante(StrEnum):
    COMBUSTIBLE = "combustible"
    PEAJE = "peaje"
    VIATICO = "viatico"


class CanalIngreso(StrEnum):
    PANEL = "panel"  # subido por Administración (RF-02)
    TELEGRAM = "telegram"  # enviado por el chofer (RF-01)


class EstadoComprobante(StrEnum):
    RECIBIDO = "recibido"
    PENDIENTE = "pendiente"  # "Pendiente de validación" (RF-06)
    PROCESADO = "procesado"
    DESCARTADO = "descartado"


# RF-02: imagen o PDF. El límite evita llenar el disco con archivos enormes.
TIPOS_PERMITIDOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}
TAMANIO_MAXIMO = 10 * 1024 * 1024  # 10 MB


def validar_archivo(tipo_mime: str, tamanio: int) -> str:
    """Devuelve la extensión con la que se guarda el archivo."""
    if tipo_mime not in TIPOS_PERMITIDOS:
        raise DatosInvalidos("El comprobante debe ser una foto (JPG, PNG, WEBP) o un PDF")
    if tamanio == 0:
        raise DatosInvalidos("El archivo está vacío")
    if tamanio > TAMANIO_MAXIMO:
        raise DatosInvalidos("El archivo supera los 10 MB")
    return TIPOS_PERMITIDOS[tipo_mime]


@dataclass(kw_only=True)
class Comprobante:
    tipo: TipoComprobante
    canal: CanalIngreso
    archivo: str  # clave en el AlmacenArchivos (RF-07: la imagen original se conserva)
    tipo_mime: str
    recibido_en: datetime
    estado: EstadoComprobante = EstadoComprobante.RECIBIDO
    chofer_id: UUID | None = None  # quién lo envió por Telegram
    camion_id: UUID | None = None  # si se conoce (viaje activo del chofer o patente leída)
    datos_extraidos: dict | None = None  # resultado crudo de la lectura automática (JSON)
    confianza: Decimal | None = None  # 0 a 1, informada por la IA
    problemas: list[str] = field(default_factory=list)  # por qué quedó pendiente
    registro_id: UUID | None = None  # el gasto creado a partir de este comprobante
    motivo_descarte: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.tipo = TipoComprobante(self.tipo)
        self.canal = CanalIngreso(self.canal)
        self.estado = EstadoComprobante(self.estado)

    @property
    def abierto(self) -> bool:
        return self.estado in (EstadoComprobante.RECIBIDO, EstadoComprobante.PENDIENTE)

    @property
    def es_imagen(self) -> bool:
        return self.tipo_mime.startswith("image/")

    def registrar_lectura(self, datos: dict, confianza: Decimal | None) -> None:
        """Guarda lo que leyó la IA (aunque esté incompleto) para mostrarlo al validar."""
        self._exigir_abierto()
        self.datos_extraidos = datos
        self.confianza = confianza

    def marcar_pendiente(self, problemas: list[str]) -> None:
        """RF-06: no se pudo registrar automáticamente; lo revisa Administración (CU-02)."""
        self._exigir_abierto()
        if not problemas:
            raise DatosInvalidos("Hay que indicar por qué queda pendiente")
        self.problemas = list(problemas)
        self.estado = EstadoComprobante.PENDIENTE

    def marcar_procesado(self, registro_id: UUID) -> None:
        self._exigir_abierto()
        self.registro_id = registro_id
        self.problemas = []
        self.estado = EstadoComprobante.PROCESADO

    def descartar(self, motivo: str) -> None:
        """CU-02 E1: ticket inválido o ajeno a la empresa."""
        self._exigir_abierto()
        self.motivo_descarte = requerido(motivo, "motivo")
        self.estado = EstadoComprobante.DESCARTADO

    def _exigir_abierto(self) -> None:
        if not self.abierto:
            raise ReglaNegocioViolada(f"El comprobante ya está {self.estado.value}")
