"""Ciclo de vida de un viaje."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from flota.shared.application.comun import obtener_o_fallar
from flota.shared.domain.errores import ReglaNegocioViolada
from flota.viajes.application.puertos import UoWViajes
from flota.viajes.domain.entidades import Viaje


@dataclass(frozen=True)
class DatosInicioViaje:
    camion_id: UUID
    chofer_id: UUID
    cliente_id: UUID
    producto_id: UUID
    origen: str
    destino: str
    cantidad: Decimal
    fecha_salida: datetime
    km_salida: Decimal
    observaciones: str | None = None


class IniciarViaje:
    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosInicioViaje) -> Viaje:
        viaje = Viaje(**asdict(datos))
        with self._uow as uow:
            camion = obtener_o_fallar(uow.camiones, datos.camion_id, "camión")
            chofer = obtener_o_fallar(uow.choferes, datos.chofer_id, "chofer")
            obtener_o_fallar(uow.clientes, datos.cliente_id, "cliente")
            obtener_o_fallar(uow.productos, datos.producto_id, "producto")
            if not camion.activo:
                raise ReglaNegocioViolada(f"El camión {camion.patente} está inactivo")
            if not chofer.activo:
                raise ReglaNegocioViolada(f"El chofer {chofer.nombre} está inactivo")
            if uow.viajes.buscar_en_curso(camion.id):
                raise ReglaNegocioViolada(f"El camión {camion.patente} ya tiene un viaje en curso")
            uow.viajes.guardar(viaje)
            uow.commit()
        return viaje


class FinalizarViaje:
    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def ejecutar(self, viaje_id: UUID, fecha_llegada: datetime, km_llegada: Decimal) -> Viaje:
        with self._uow as uow:
            viaje = obtener_o_fallar(uow.viajes, viaje_id, "viaje")
            viaje.finalizar(fecha_llegada, km_llegada)
            uow.viajes.guardar(viaje)
            uow.commit()
        return viaje


class ConsultasViajes:
    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def obtener(self, viaje_id: UUID) -> Viaje:
        with self._uow as uow:
            return obtener_o_fallar(uow.viajes, viaje_id, "viaje")

    def listar(
        self, desde: datetime, hasta: datetime, camion_id: UUID | None = None
    ) -> list[Viaje]:
        with self._uow as uow:
            return uow.viajes.listar_por_periodo(desde, hasta, camion_id)
