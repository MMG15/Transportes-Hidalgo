"""Registro y consulta de cargas de combustible."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from flota.application.ports import UnidadDeTrabajo
from flota.application.use_cases._comun import obtener_o_fallar
from flota.domain.entities import CargaCombustible, OrigenDato
from flota.domain.exceptions import Duplicado, ReglaNegocioViolada


@dataclass(frozen=True)
class DatosCarga:
    camion_id: UUID
    fecha: datetime
    litros: Decimal
    precio_litro: Decimal | None = None
    odometro_km: Decimal | None = None
    estacion: str | None = None
    origen: OrigenDato = OrigenDato.MANUAL
    referencia_externa: str | None = None
    viaje_id: UUID | None = None  # si no se indica, se asigna automáticamente


class RegistrarCargaCombustible:
    def __init__(self, uow: UnidadDeTrabajo, tolerancia_tanque_pct: Decimal = Decimal("5")) -> None:
        self._uow = uow
        self._tolerancia = tolerancia_tanque_pct

    def ejecutar(self, datos: DatosCarga) -> CargaCombustible:
        carga = CargaCombustible(**asdict(datos))
        with self._uow as uow:
            camion = obtener_o_fallar(uow.camiones, carga.camion_id, "camión")
            maximo = camion.capacidad_tanque_litros * (1 + self._tolerancia / 100)
            if carga.litros > maximo:
                raise ReglaNegocioViolada(
                    f"La carga de {carga.litros} L supera la capacidad del tanque del camión "
                    f"{camion.patente} ({camion.capacidad_tanque_litros} L)"
                )
            if uow.cargas.existe_duplicado(carga):
                raise Duplicado("La carga ya estaba registrada")

            if carga.viaje_id is not None:
                carga.asignar_a_viaje(obtener_o_fallar(uow.viajes, carga.viaje_id, "viaje"))
            elif viaje := uow.viajes.buscar_por_camion_y_fecha(camion.id, carga.fecha):
                carga.asignar_a_viaje(viaje)

            uow.cargas.guardar(carga)
            uow.commit()
        return carga


class ConsultasCargas:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
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
