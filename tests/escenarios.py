"""Datos de prueba reutilizables (patrón "Object Mother": fábricas de objetos para los tests)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from flota.catalogo.application.casos_de_uso import (
    DatosCamion,
    DatosChofer,
    DatosCliente,
    DatosProducto,
    RegistrarCamion,
    RegistrarChofer,
    RegistrarCliente,
    RegistrarProducto,
)
from flota.catalogo.domain.entidades import Camion, Chofer, Cliente, Producto
from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.viajes.application.casos_de_uso import (
    CambiarEstadoCarga,
    DatosInicioViaje,
    DatosRuta,
    FinalizarViaje,
    IniciarViaje,
    RegistrarRuta,
)
from flota.viajes.domain.entidades import EstadoCarga, Pais, Ruta, Viaje

SALIDA = datetime(2026, 10, 1, 8, 0)


@dataclass
class Flota:
    camion: Camion
    chofer: Chofer
    cliente: Cliente
    producto: Producto
    ruta: Ruta


def flota_basica(
    uow, ref_cargado: Decimal | None = None, ref_vacio: Decimal | None = None
) -> Flota:
    """Un camión (ref. 40 L/100km), un chofer, un cliente, cal viva y la ruta Albardón → Mendoza."""
    return Flota(
        camion=RegistrarCamion(uow).ejecutar(
            DatosCamion("AB123CD", "Scania", "R450", Decimal("600"), Decimal("40"))
        ),
        chofer=RegistrarChofer(uow).ejecutar(DatosChofer("Juan Pérez", "30.123.456")),
        cliente=RegistrarCliente(uow).ejecutar(DatosCliente("Cliente SA")),
        producto=RegistrarProducto(uow).ejecutar(DatosProducto("Cal viva")),
        ruta=RegistrarRuta(uow).ejecutar(
            DatosRuta("Albardón", "Mendoza", Pais.AR, Decimal("170"), ref_cargado, ref_vacio)
        ),
    )


def iniciar_viaje(uow, flota: Flota, salida: datetime = SALIDA, km: str = "1000") -> Viaje:
    return IniciarViaje(uow).ejecutar(
        DatosInicioViaje(
            flota.camion.id,
            flota.chofer.id,
            flota.ruta.id,
            salida,
            Decimal(km),
            cliente_id=flota.cliente.id,
            producto_id=flota.producto.id,
            cantidad=Decimal("28"),
        )
    )


def viaje_ida_y_vuelta(
    uow,
    flota: Flota,
    salida: datetime = SALIDA,
    km_salida: int = 1000,
    km_tramo: int = 200,
    litros_ida: str = "80",
    litros_vuelta: str = "60",
) -> Viaje:
    """Viaje completo: ida cargado (carga a las 2 h) y regreso vacío (carga a las 7 h)."""
    viaje = iniciar_viaje(uow, flota, salida, str(km_salida))
    registrar = RegistrarCargaCombustible(uow)
    registrar.ejecutar(
        DatosCarga(flota.camion.id, salida + timedelta(hours=2), Decimal(litros_ida))
    )
    CambiarEstadoCarga(uow).ejecutar(
        viaje.id,
        salida + timedelta(hours=5),
        Decimal(km_salida + km_tramo),
        EstadoCarga.VACIO,
    )
    registrar.ejecutar(
        DatosCarga(flota.camion.id, salida + timedelta(hours=7), Decimal(litros_vuelta))
    )
    return FinalizarViaje(uow).ejecutar(
        viaje.id, salida + timedelta(hours=10), Decimal(km_salida + 2 * km_tramo)
    )
