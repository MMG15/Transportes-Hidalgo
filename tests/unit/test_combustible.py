"""MOD-03 · Combustible: registro de cargas, importación y consumo del viaje."""

from datetime import timedelta
from decimal import Decimal

import pytest

from flota.combustible.application.casos_de_uso import (
    DatosCarga,
    ObtenerConsumoViaje,
    RegistrarCargaCombustible,
)
from flota.combustible.application.dto import ErrorLectura, FilaCarga
from flota.combustible.application.importacion import ImportarCargas
from flota.combustible.application.puertos import LectorCargas
from flota.combustible.domain.consumo import FuenteReferencia
from flota.shared.domain.errores import Duplicado, ReglaNegocioViolada
from tests.escenarios import SALIDA, flota_basica, iniciar_viaje, viaje_ida_y_vuelta
from tests.fakes import UnidadDeTrabajoFake


@pytest.fixture
def uow():
    return UnidadDeTrabajoFake()


def test_carga_se_asigna_automaticamente_al_viaje(uow):
    flota = flota_basica(uow)
    viaje = iniciar_viaje(uow, flota)
    carga = RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(flota.camion.id, SALIDA + timedelta(hours=2), Decimal("150"))
    )
    assert carga.viaje_id == viaje.id


def test_carga_mayor_al_tanque_se_rechaza(uow):
    flota = flota_basica(uow)
    with pytest.raises(ReglaNegocioViolada):
        RegistrarCargaCombustible(uow).ejecutar(DatosCarga(flota.camion.id, SALIDA, Decimal("700")))


def test_carga_duplicada_por_referencia(uow):
    flota = flota_basica(uow)
    registrar = RegistrarCargaCombustible(uow)
    registrar.ejecutar(DatosCarga(flota.camion.id, SALIDA, Decimal("100"), referencia_externa="T1"))
    with pytest.raises(Duplicado):
        registrar.ejecutar(
            DatosCarga(flota.camion.id, SALIDA, Decimal("120"), referencia_externa="T1")
        )


class LectorFijo(LectorCargas):
    def __init__(self, items):
        self.items = items

    def leer(self, ruta):
        yield from self.items


def test_importacion_reporta_errores_y_duplicados(uow):
    flota_basica(uow)
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


def test_consumo_del_viaje_usa_el_historico_de_la_ruta(uow):
    """RF-13: sin referencia configurada, con 3 viajes previos se usa su promedio."""
    flota = flota_basica(uow)  # ruta sin referencias; camión: 40 L/100km
    for dia in range(3):
        viaje_ida_y_vuelta(
            uow, flota, SALIDA + timedelta(days=dia), 1000 + dia * 400, 200, "100", "60"
        )  # 50 L/100km cargado, 30 vacío
    ultimo = viaje_ida_y_vuelta(uow, flota, SALIDA + timedelta(days=5), 3000, 200, "130", "60")

    resumen = ObtenerConsumoViaje(uow, Decimal("15")).ejecutar(ultimo.id)

    ida, vuelta = resumen.tramos
    assert ida.referencia.fuente == FuenteReferencia.HISTORICO
    assert ida.referencia.valor == Decimal("50.00")
    assert ida.consumo_l100km == Decimal("65.00") and ida.alerta  # +30 %
    assert vuelta.referencia.valor == Decimal("30.00") and not vuelta.alerta


def test_primer_viaje_de_la_ruta_usa_la_referencia_del_camion(uow):
    flota = flota_basica(uow)
    viaje = viaje_ida_y_vuelta(uow, flota)
    resumen = ObtenerConsumoViaje(uow, Decimal("15")).ejecutar(viaje.id)
    assert {t.referencia.fuente for t in resumen.tramos} == {FuenteReferencia.CAMION}
