from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

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
from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.combustible.application.dto import ErrorLectura, FilaCarga
from flota.combustible.application.importacion import ImportarCargas
from flota.combustible.application.puertos import LectorCargas
from flota.reportes.application.casos_de_uso import GenerarReporteConsumo
from flota.shared.domain.errores import Duplicado, ReglaNegocioViolada
from flota.viajes.application.casos_de_uso import DatosInicioViaje, FinalizarViaje, IniciarViaje
from tests.fakes import UnidadDeTrabajoFake

SALIDA = datetime(2026, 10, 1, 8, 0)


@pytest.fixture
def uow():
    return UnidadDeTrabajoFake()


@pytest.fixture
def escenario(uow):
    camion = RegistrarCamion(uow).ejecutar(
        DatosCamion("AB123CD", "Scania", "R450", Decimal("600"), Decimal("40"))
    )
    chofer = RegistrarChofer(uow).ejecutar(DatosChofer("Juan Pérez", "30.123.456"))
    cliente = RegistrarCliente(uow).ejecutar(DatosCliente("Productor SA"))
    producto = RegistrarProducto(uow).ejecutar(DatosProducto("Cal viva"))
    viaje = IniciarViaje(uow).ejecutar(
        DatosInicioViaje(
            camion.id,
            chofer.id,
            cliente.id,
            producto.id,
            "Planta",
            "Campo",
            Decimal("28"),
            SALIDA,
            Decimal("1000"),
        )
    )
    return camion, viaje


def test_no_permite_patente_duplicada(uow, escenario):
    with pytest.raises(Duplicado):
        RegistrarCamion(uow).ejecutar(
            DatosCamion("AB-123-CD", "Iveco", "Stralis", Decimal("500"), Decimal("35"))
        )


def test_no_permite_dos_viajes_en_curso(uow, escenario):
    camion, viaje = escenario
    with pytest.raises(ReglaNegocioViolada):
        IniciarViaje(uow).ejecutar(
            DatosInicioViaje(
                camion.id,
                viaje.chofer_id,
                viaje.cliente_id,
                viaje.producto_id,
                "A",
                "B",
                Decimal("10"),
                SALIDA + timedelta(hours=1),
                Decimal("1000"),
            )
        )


def test_carga_se_asigna_automaticamente_al_viaje(uow, escenario):
    camion, viaje = escenario
    carga = RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(camion.id, SALIDA + timedelta(hours=2), Decimal("150"))
    )
    assert carga.viaje_id == viaje.id


def test_carga_mayor_al_tanque_se_rechaza(uow, escenario):
    camion, _ = escenario
    with pytest.raises(ReglaNegocioViolada):
        RegistrarCargaCombustible(uow).ejecutar(DatosCarga(camion.id, SALIDA, Decimal("700")))


def test_carga_duplicada_por_referencia(uow, escenario):
    camion, _ = escenario
    registrar = RegistrarCargaCombustible(uow)
    registrar.ejecutar(DatosCarga(camion.id, SALIDA, Decimal("100"), referencia_externa="T1"))
    with pytest.raises(Duplicado):
        registrar.ejecutar(DatosCarga(camion.id, SALIDA, Decimal("120"), referencia_externa="T1"))


class LectorFijo(LectorCargas):
    def __init__(self, items):
        self.items = items

    def leer(self, ruta):
        yield from self.items


def test_importacion_reporta_errores_y_duplicados(uow, escenario):
    filas = [
        FilaCarga(2, SALIDA + timedelta(hours=1), "ab123cd", Decimal("100"), referencia="X1"),
        FilaCarga(3, SALIDA + timedelta(hours=2), "AB123CD", Decimal("50"), referencia="X1"),
        FilaCarga(4, SALIDA, "ZZ999ZZ", Decimal("50")),
        ErrorLectura(5, "fecha inválida"),
    ]
    resultado = ImportarCargas(uow, LectorFijo(filas)).ejecutar(ruta=None)

    assert resultado.procesadas == 4
    assert resultado.importadas == 1
    assert resultado.duplicadas == 1
    assert len(resultado.errores) == 2
    assert "ZZ999ZZ" in resultado.errores[0]


def test_reporte_de_consumo(uow, escenario):
    camion, viaje = escenario
    RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(camion.id, SALIDA + timedelta(hours=1), Decimal("160"), Decimal("1000"))
    )
    FinalizarViaje(uow).ejecutar(viaje.id, SALIDA + timedelta(hours=8), Decimal("1400"))

    reporte = GenerarReporteConsumo(uow, Decimal("15")).ejecutar(
        date(2026, 10, 1), date(2026, 10, 1)
    )

    assert len(reporte.filas) == 1
    fila = reporte.filas[0]
    assert fila.patente == "AB123CD"
    assert fila.consumo_l100km == Decimal("40.00")
    assert fila.alerta is False
    assert reporte.resumen_por_camion[0].consumo_promedio_l100km == Decimal("40.00")
