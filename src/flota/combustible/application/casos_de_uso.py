"""Registro y consulta de cargas de combustible."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from flota.combustible.application.consumo import CalculadoraConsumo
from flota.combustible.application.puertos import UoWCombustible
from flota.combustible.domain.consumo import ResumenConsumo
from flota.combustible.domain.entidades import CargaCombustible, EstadoValidacion, OrigenDato
from flota.combustible.domain.eventos import CargaAnulada, CargaRegistrada
from flota.monedas.application.casos_de_uso import importe_en_pesos
from flota.shared.application.comun import obtener_o_fallar
from flota.shared.domain.auditoria import AccionAuditoria
from flota.shared.domain.dinero import Dinero, Moneda
from flota.shared.domain.errores import DatosInvalidos, Duplicado


@dataclass(frozen=True)
class DatosCarga:
    camion_id: UUID
    fecha: datetime
    litros: Decimal
    precio_litro: Decimal | None = None  # se usa si no se informa el monto total
    odometro_km: Decimal | None = None
    estacion: str | None = None
    origen: OrigenDato = OrigenDato.MANUAL
    referencia_externa: str | None = None
    viaje_id: UUID | None = None  # si no se indica, se asigna automáticamente
    monto: Decimal | None = None  # importe total del ticket
    moneda: Moneda = Moneda.ARS
    estado_validacion: EstadoValidacion = EstadoValidacion.VALIDADA
    comprobante_id: UUID | None = None


# Más del doble del tanque no es un consumo raro: es un error de tipeo o de lectura.
FACTOR_ABSURDO = Decimal("2")
# Margen para relojes desfasados al controlar que la fecha no sea futura (RF-04).
MARGEN_FUTURO = timedelta(hours=1)

type Reloj = Callable[[], datetime]


class RegistrarCargaCombustible:
    """CU-02 (carga manual) — RF-02, RF-04, RF-08, RF-18, RF-40: registra una carga.

    - Convierte el importe a ARS con la cotización vigente a la fecha (si es en CLP).
    - Si supera la capacidad del tanque, se registra igual y el módulo de alertas genera la
      alerta (RF-18). Sólo se rechaza si supera el doble del tanque.
    - Publica `CargaRegistrada` para que otros módulos reaccionen.
    """

    def __init__(self, uow: UoWCombustible, reloj: Reloj = datetime.now) -> None:
        self._uow = uow
        self._ahora = reloj

    def ejecutar(self, datos: DatosCarga) -> CargaCombustible:
        with self._uow as uow:
            carga = self.registrar_en(uow, datos)
            uow.commit()
        return carga

    def registrar_en(self, uow: UoWCombustible, datos: DatosCarga) -> CargaCombustible:
        """Registra la carga dentro de una transacción YA ABIERTA, sin confirmarla.

        Lo usan otros casos de uso que tienen que hacer más cosas en la misma transacción
        (p. ej. validar un comprobante: carga + comprobante procesado, todo o nada).
        """
        if datos.fecha > self._ahora() + MARGEN_FUTURO:
            raise DatosInvalidos("La fecha de la carga no puede ser futura")
        monto = datos.monto
        if monto is None and datos.precio_litro is not None:
            monto = datos.precio_litro * datos.litros
        campos = asdict(datos)
        for clave in ("precio_litro", "monto", "moneda"):
            campos.pop(clave)
        carga = CargaCombustible(**campos)

        camion = obtener_o_fallar(uow.camiones, carga.camion_id, "camión")
        if carga.litros > camion.capacidad_tanque_litros * FACTOR_ABSURDO:
            raise DatosInvalidos(
                f"{carga.litros} L es más del doble del tanque del camión {camion.patente} "
                f"({camion.capacidad_tanque_litros} L): revisá el dato"
            )
        if monto is not None:
            carga.importe = importe_en_pesos(uow, Dinero(monto, datos.moneda), carga.fecha.date())
        if uow.cargas.existe_duplicado(carga):
            raise Duplicado("La carga ya estaba registrada")

        if carga.viaje_id is not None:
            carga.asignar_a_viaje(obtener_o_fallar(uow.viajes, carga.viaje_id, "viaje"))
        elif viaje := uow.viajes.buscar_por_camion_y_fecha(camion.id, carga.fecha):
            carga.asignar_a_viaje(viaje)

        uow.cargas.guardar(carga)
        uow.auditar("cargas_combustible", carga.id, AccionAuditoria.ALTA, despues=carga)
        uow.registrar_evento(CargaRegistrada(carga.id, carga.viaje_id))
        return carga


class AnularCarga:
    """CU-02 E1 — RF-55: anula una carga registrada (queda en la base y en la auditoría,
    pero no cuenta para el consumo). Publica `CargaAnulada` para recalcular las alertas."""

    def __init__(self, uow: UoWCombustible) -> None:
        self._uow = uow

    def ejecutar(self, carga_id: UUID, motivo: str) -> CargaCombustible:
        with self._uow as uow:
            carga = obtener_o_fallar(uow.cargas, carga_id, "carga")
            antes = replace(carga)
            carga.anular(motivo)
            uow.cargas.guardar(carga)
            uow.auditar("cargas_combustible", carga.id, AccionAuditoria.BAJA, antes, carga)
            uow.registrar_evento(CargaAnulada(carga.id, carga.viaje_id))
            uow.commit()
        return carga


class ConsultasCargas:
    def __init__(self, uow: UoWCombustible) -> None:
        self._uow = uow

    def listar(
        self,
        camion_id: UUID | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 100,
        desplazamiento: int = 0,
    ) -> list[CargaCombustible]:
        with self._uow as uow:
            return uow.cargas.listar_filtrado(camion_id, desde, hasta, limite, desplazamiento)


class ObtenerConsumoViaje:
    """CU-05 — RF-10, RF-11, RF-13: consumo del viaje por tramo, contra la referencia de la ruta."""

    def __init__(self, uow: UoWCombustible, umbral_desvio_pct: Decimal) -> None:
        self._uow = uow
        self._umbral = umbral_desvio_pct

    def ejecutar(self, viaje_id: UUID) -> ResumenConsumo:
        with self._uow as uow:
            viaje = obtener_o_fallar(uow.viajes, viaje_id, "viaje")
            return CalculadoraConsumo(uow, self._umbral).calcular(viaje)
