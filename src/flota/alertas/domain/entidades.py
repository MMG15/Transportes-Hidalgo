"""Alerta: una anomalía detectada que alguien tiene que analizar y resolver (RF-16 a RF-20).

Ciclo de vida (CU-06):

    ABIERTA ──► EN_ANÁLISIS ──► JUSTIFICADA         (era explicable: se cierra)
       │              │
       └──────────────┴──────► DESVÍO CONFIRMADO    (se escala a Gerencia)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.errores import DatosInvalidos, ReglaNegocioViolada
from flota.shared.domain.validaciones import requerido


class TipoAlerta(StrEnum):
    DESVIO_CONSUMO = "desvio_consumo"  # RF-16
    UBICACION = "ubicacion"  # RF-17
    CAPACIDAD_TANQUE = "capacidad_tanque"  # RF-18
    MANTENIMIENTO = "mantenimiento"  # RF-23
    NEUMATICO = "neumatico"  # RF-29
    STOCK_MINIMO = "stock_minimo"  # RF-32
    PEAJE = "peaje"  # RF-42


class EstadoAlerta(StrEnum):
    ABIERTA = "abierta"
    EN_ANALISIS = "en_analisis"
    JUSTIFICADA = "justificada"
    CONFIRMADA = "confirmada"  # desvío confirmado


NOMBRES_TIPO = {
    TipoAlerta.DESVIO_CONSUMO: "Desvío de consumo",
    TipoAlerta.UBICACION: "Ubicación no coincide",
    TipoAlerta.CAPACIDAD_TANQUE: "Supera el tanque",
    TipoAlerta.MANTENIMIENTO: "Mantenimiento próximo",
    TipoAlerta.NEUMATICO: "Neumático",
    TipoAlerta.STOCK_MINIMO: "Stock mínimo",
    TipoAlerta.PEAJE: "Diferencia de peaje",
}


@dataclass(kw_only=True)
class Alerta:
    tipo: TipoAlerta
    origen_tabla: str  # qué registro la generó: tabla + id (una única tabla para todos los tipos)
    origen_id: UUID
    descripcion: str
    creada_en: datetime
    valor_detectado: Decimal | None = None
    valor_referencia: Decimal | None = None
    camion_id: UUID | None = None
    viaje_id: UUID | None = None
    estado: EstadoAlerta = EstadoAlerta.ABIERTA
    comentario: str | None = None
    usuario_id: UUID | None = None  # quién la resolvió (None = el sistema)
    resuelta_en: datetime | None = None
    escalada: bool = False  # se escaló a Gerencia (desvío confirmado)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.tipo = TipoAlerta(self.tipo)
        self.estado = EstadoAlerta(self.estado)
        self.descripcion = requerido(self.descripcion, "descripcion")

    @property
    def abierta(self) -> bool:
        return self.estado in (EstadoAlerta.ABIERTA, EstadoAlerta.EN_ANALISIS)

    @property
    def nombre_tipo(self) -> str:
        return NOMBRES_TIPO[self.tipo]

    def actualizar(
        self, descripcion: str, detectado: Decimal | None, referencia: Decimal | None
    ) -> None:
        """Al recalcular (p. ej. llegó un ticket tarde) se actualizan los valores."""
        self._exigir_abierta()
        self.descripcion = requerido(descripcion, "descripcion")
        self.valor_detectado = detectado
        self.valor_referencia = referencia

    def poner_en_analisis(self, comentario: str, fecha: datetime, usuario_id: UUID | None) -> None:
        """CU-06 E1: falta información; queda en análisis."""
        if self.estado != EstadoAlerta.ABIERTA:
            raise ReglaNegocioViolada("Sólo una alerta abierta puede pasar a análisis")
        self.comentario = requerido(comentario, "comentario")
        self.estado = EstadoAlerta.EN_ANALISIS
        self.usuario_id = usuario_id

    def justificar(self, comentario: str, fecha: datetime, usuario_id: UUID | None) -> None:
        """CU-06 paso 4 — RF-20: el desvío tiene explicación; se cierra."""
        self._cerrar(EstadoAlerta.JUSTIFICADA, comentario, fecha, usuario_id)

    def confirmar_desvio(self, comentario: str, fecha: datetime, usuario_id: UUID | None) -> None:
        """CU-06 pasos 4 y 5 — RF-20: desvío confirmado; se escala a Gerencia."""
        self._cerrar(EstadoAlerta.CONFIRMADA, comentario, fecha, usuario_id)
        self.escalada = True

    def normalizar(self, fecha: datetime) -> None:
        """El sistema la cierra porque, al recalcular, el valor volvió a la normalidad."""
        self._cerrar(
            EstadoAlerta.JUSTIFICADA,
            "Se normalizó al recalcular (cerrada por el sistema)",
            fecha,
            None,
        )

    def _cerrar(
        self, estado: EstadoAlerta, comentario: str, fecha: datetime, usuario_id: UUID | None
    ) -> None:
        self._exigir_abierta()
        if not comentario or not comentario.strip():
            raise DatosInvalidos("Para resolver una alerta hay que dejar un comentario")
        self.estado = estado
        self.comentario = comentario.strip()
        self.resuelta_en = fecha
        self.usuario_id = usuario_id

    def _exigir_abierta(self) -> None:
        if not self.abierta:
            raise ReglaNegocioViolada("La alerta ya está resuelta")
