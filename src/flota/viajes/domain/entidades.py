"""Rutas, viajes y tramos: la unidad de trazabilidad (todo gasto se asocia a un viaje).

Un viaje se divide en TRAMOS según el estado de carga del camión. El caso típico:

    salida ──── tramo 1: CARGADO ────► descarga ──── tramo 2: VACÍO ────► llegada

El consumo se calcula y compara por tramo, porque un camión cargado con cal consume
bastante más que vacío (RF-11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.errores import DatosInvalidos, ReglaNegocioViolada
from flota.shared.domain.validaciones import no_negativo, opcional, positivo, requerido


class Pais(StrEnum):
    AR = "AR"
    CL = "CL"


class EstadoCarga(StrEnum):
    CARGADO = "cargado"
    VACIO = "vacio"


class EstadoViaje(StrEnum):
    EN_CURSO = "en_curso"
    FINALIZADO = "finalizado"


class OrigenKm(StrEnum):
    """De dónde salió la lectura del odómetro (CU-03 E2: sin GPS se marca 'manual')."""

    MANUAL = "manual"
    GPS = "gps"


@dataclass(kw_only=True)
class Ruta:
    """Recorrido habitual, con su consumo de referencia para cada estado de carga."""

    origen: str
    destino: str
    pais: Pais = Pais.AR  # país de destino; CL indica viaje internacional
    km_estimados: Decimal | None = None
    ref_l100_cargado: Decimal | None = None  # si no se configura, se usa el histórico
    ref_l100_vacio: Decimal | None = None
    activa: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.origen = requerido(self.origen, "origen")
        self.destino = requerido(self.destino, "destino")
        self.pais = Pais(self.pais)
        for campo in ("km_estimados", "ref_l100_cargado", "ref_l100_vacio"):
            valor = getattr(self, campo)
            if valor is not None:
                positivo(valor, campo)

    @property
    def nombre(self) -> str:
        return f"{self.origen} → {self.destino}"

    def referencia_configurada(self, estado: EstadoCarga) -> Decimal | None:
        if estado == EstadoCarga.CARGADO:
            return self.ref_l100_cargado
        return self.ref_l100_vacio


@dataclass(kw_only=True)
class TramoViaje:
    estado_carga: EstadoCarga
    fecha_inicio: datetime
    km_inicio: Decimal
    fecha_fin: datetime | None = None
    km_fin: Decimal | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.estado_carga = EstadoCarga(self.estado_carga)
        no_negativo(self.km_inicio, "km_inicio")

    @property
    def abierto(self) -> bool:
        return self.fecha_fin is None

    @property
    def km_recorridos(self) -> Decimal | None:
        if self.km_fin is None:
            return None
        return self.km_fin - self.km_inicio

    def cerrar(self, fecha: datetime, km: Decimal) -> None:
        if not self.abierto:
            raise ReglaNegocioViolada("El tramo ya está cerrado")
        if fecha < self.fecha_inicio:
            raise DatosInvalidos("La fecha de cierre del tramo es anterior a su inicio")
        if km <= self.km_inicio:
            raise DatosInvalidos(
                f"El odómetro ({km} km) debe ser mayor al del inicio del tramo "
                f"({self.km_inicio} km)"
            )
        self.fecha_fin = fecha
        self.km_fin = km

    def incluye(self, fecha: datetime) -> bool:
        return fecha >= self.fecha_inicio and (self.fecha_fin is None or fecha <= self.fecha_fin)


@dataclass(kw_only=True)
class Viaje:
    camion_id: UUID
    chofer_id: UUID
    ruta_id: UUID
    fecha_salida: datetime
    km_salida: Decimal  # lectura del odómetro al salir
    cliente_id: UUID | None = None
    producto_id: UUID | None = None
    cantidad: Decimal | None = None  # toneladas (o la unidad del producto) del tramo cargado
    origen_km: OrigenKm = OrigenKm.MANUAL
    tramos: list[TramoViaje] = field(default_factory=list)
    fecha_llegada: datetime | None = None
    km_llegada: Decimal | None = None
    estado: EstadoViaje = EstadoViaje.EN_CURSO
    observaciones: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.observaciones = opcional(self.observaciones)
        self.estado = EstadoViaje(self.estado)
        self.origen_km = OrigenKm(self.origen_km)
        no_negativo(self.km_salida, "km_salida")
        if self.cantidad is not None:
            positivo(self.cantidad, "cantidad")
        if not self.tramos:
            raise DatosInvalidos("El viaje debe tener al menos un tramo")
        if self.lleva_carga and (self.producto_id is None or self.cantidad is None):
            raise DatosInvalidos("Un viaje cargado debe indicar el producto y la cantidad")

    @classmethod
    def iniciar(
        cls,
        *,
        camion_id: UUID,
        chofer_id: UUID,
        ruta_id: UUID,
        fecha_salida: datetime,
        km_salida: Decimal,
        estado_carga: EstadoCarga = EstadoCarga.CARGADO,
        cliente_id: UUID | None = None,
        producto_id: UUID | None = None,
        cantidad: Decimal | None = None,
        origen_km: OrigenKm = OrigenKm.MANUAL,
        observaciones: str | None = None,
    ) -> Viaje:
        """Fábrica: crea el viaje con su primer tramo abierto desde la salida."""
        primer_tramo = TramoViaje(
            estado_carga=estado_carga, fecha_inicio=fecha_salida, km_inicio=km_salida
        )
        return cls(
            camion_id=camion_id,
            chofer_id=chofer_id,
            ruta_id=ruta_id,
            fecha_salida=fecha_salida,
            km_salida=km_salida,
            cliente_id=cliente_id,
            producto_id=producto_id,
            cantidad=cantidad,
            origen_km=origen_km,
            observaciones=observaciones,
            tramos=[primer_tramo],
        )

    # ---------- Consultas ----------
    @property
    def tramo_actual(self) -> TramoViaje:
        return self.tramos[-1]

    @property
    def lleva_carga(self) -> bool:
        return any(t.estado_carga == EstadoCarga.CARGADO for t in self.tramos)

    @property
    def km_recorridos(self) -> Decimal | None:
        if self.km_llegada is None:
            return None
        return self.km_llegada - self.km_salida

    def incluye_fecha(self, fecha: datetime) -> bool:
        """True si `fecha` cae dentro del viaje (o después de la salida, si sigue en curso)."""
        if fecha < self.fecha_salida:
            return False
        return self.fecha_llegada is None or fecha <= self.fecha_llegada

    def tramo_en(self, fecha: datetime) -> TramoViaje:
        """El tramo en curso en esa fecha (antes de la salida: el primero; después: el último)."""
        for tramo in self.tramos:
            if tramo.incluye(fecha):
                return tramo
        return self.tramos[0] if fecha < self.fecha_salida else self.tramos[-1]

    # ---------- Cambios de estado ----------
    def cambiar_estado_carga(
        self, fecha: datetime, km: Decimal, nuevo_estado: EstadoCarga
    ) -> TramoViaje:
        """Cierra el tramo actual y abre otro (p. ej. al descargar: CARGADO -> VACÍO)."""
        self._exigir_en_curso()
        nuevo_estado = EstadoCarga(nuevo_estado)
        if nuevo_estado == self.tramo_actual.estado_carga:
            raise ReglaNegocioViolada(f"El camión ya viaja {nuevo_estado.value}")
        self.tramo_actual.cerrar(fecha, km)
        nuevo = TramoViaje(estado_carga=nuevo_estado, fecha_inicio=fecha, km_inicio=km)
        self.tramos.append(nuevo)
        return nuevo

    def registrar_descarga(self, fecha: datetime, km: Decimal) -> TramoViaje:
        """Fin del tramo cargado: empieza el regreso vacío."""
        return self.cambiar_estado_carga(fecha, km, EstadoCarga.VACIO)

    def finalizar(self, fecha_llegada: datetime, km_llegada: Decimal) -> None:
        self._exigir_en_curso()
        if fecha_llegada < self.fecha_salida:
            raise DatosInvalidos("La fecha de llegada no puede ser anterior a la de salida")
        if km_llegada <= self.km_salida:
            raise DatosInvalidos("El odómetro de llegada debe ser mayor al de salida")
        self.tramo_actual.cerrar(fecha_llegada, km_llegada)
        self.fecha_llegada = fecha_llegada
        self.km_llegada = km_llegada
        self.estado = EstadoViaje.FINALIZADO

    def _exigir_en_curso(self) -> None:
        if self.estado == EstadoViaje.FINALIZADO:
            raise ReglaNegocioViolada("El viaje ya está finalizado")
