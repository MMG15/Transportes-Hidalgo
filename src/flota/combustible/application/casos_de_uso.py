"""Registro y consulta de cargas de combustible."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from flota.combustible.application.consumo import CalculadoraConsumo
from flota.combustible.application.puertos import UoWCombustible
from flota.combustible.domain.consumo import ResumenConsumo
from flota.combustible.domain.entidades import CargaCombustible, OrigenDato
from flota.combustible.domain.eventos import CargaRegistrada
from flota.monedas.application.casos_de_uso import importe_en_pesos
from flota.shared.application.comun import obtener_o_fallar
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


# Más del doble del tanque no es un consumo raro: es un error de tipeo o de lectura.
FACTOR_ABSURDO = Decimal("2")


class RegistrarCargaCombustible:
    """CU-02 (carga manual) — RF-02, RF-04, RF-08, RF-18, RF-40: registra una carga.

    - Convierte el importe a ARS con la cotización vigente a la fecha (si es en CLP).
    - Si supera la capacidad del tanque, se registra igual y el módulo de alertas genera la
      alerta (RF-18). Sólo se rechaza si supera el doble del tanque.
    - Publica `CargaRegistrada` para que otros módulos reaccionen.
    """

    def __init__(self, uow: UoWCombustible) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosCarga) -> CargaCombustible:
        monto = datos.monto
        if monto is None and datos.precio_litro is not None:
            monto = datos.precio_litro * datos.litros
        campos = asdict(datos)
        for clave in ("precio_litro", "monto", "moneda"):
            campos.pop(clave)
        carga = CargaCombustible(**campos)

        with self._uow as uow:
            camion = obtener_o_fallar(uow.camiones, carga.camion_id, "camión")
            if carga.litros > camion.capacidad_tanque_litros * FACTOR_ABSURDO:
                raise DatosInvalidos(
                    f"{carga.litros} L es más del doble del tanque del camión {camion.patente} "
                    f"({camion.capacidad_tanque_litros} L): revisá el dato"
                )
            if monto is not None:
                carga.importe = importe_en_pesos(
                    uow, Dinero(monto, datos.moneda), carga.fecha.date()
                )
            if uow.cargas.existe_duplicado(carga):
                raise Duplicado("La carga ya estaba registrada")

            if carga.viaje_id is not None:
                carga.asignar_a_viaje(obtener_o_fallar(uow.viajes, carga.viaje_id, "viaje"))
            elif viaje := uow.viajes.buscar_por_camion_y_fecha(camion.id, carga.fecha):
                carga.asignar_a_viaje(viaje)

            uow.cargas.guardar(carga)
            uow.registrar_evento(CargaRegistrada(carga.id, carga.viaje_id))
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
