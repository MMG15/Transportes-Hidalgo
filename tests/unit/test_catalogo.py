"""MOD-01 · Catálogo: reglas de camiones y choferes."""

from decimal import Decimal

import pytest

from flota.catalogo.application.casos_de_uso import (
    ActualizarCamion,
    ActualizarChofer,
    CambiosCamion,
    DatosCamion,
    RegistrarCamion,
)
from flota.catalogo.domain.entidades import Camion, Chofer
from flota.shared.domain.errores import DatosInvalidos, Duplicado
from tests.escenarios import flota_basica
from tests.fakes import UnidadDeTrabajoFake


def nuevo_camion(**cambios) -> Camion:
    datos = dict(
        patente="ab 123-cd",
        marca="Scania",
        modelo="R450",
        capacidad_tanque_litros=Decimal("600"),
        consumo_referencia_l100km=Decimal("40"),
    )
    return Camion(**(datos | cambios))


def test_camion_normaliza_patente():
    assert nuevo_camion().patente == "AB123CD"


def test_camion_rechaza_capacidad_no_positiva():
    with pytest.raises(DatosInvalidos):
        nuevo_camion(capacidad_tanque_litros=Decimal("0"))


def test_camion_rechaza_anio_invalido():
    with pytest.raises(DatosInvalidos):
        nuevo_camion(anio=1800)


def test_km_actual_nunca_retrocede():
    camion = nuevo_camion(km_actual=Decimal("1000"))
    camion.registrar_km(Decimal("900"))  # lectura vieja: se ignora
    assert camion.km_actual == Decimal("1000")
    camion.registrar_km(Decimal("1200"))
    assert camion.km_actual == Decimal("1200")


def test_chofer_valida_dni():
    assert Chofer(nombre="Ana", dni="30.123.456").dni == "30123456"
    with pytest.raises(DatosInvalidos):
        Chofer(nombre="Ana", dni="123")


def test_no_permite_patente_duplicada():
    uow = UnidadDeTrabajoFake()
    flota_basica(uow)
    with pytest.raises(Duplicado):
        RegistrarCamion(uow).ejecutar(
            DatosCamion("AB-123-CD", "Iveco", "Stralis", Decimal("500"), Decimal("35"))
        )


def test_actualizar_camion_y_baja_logica():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    cambios = CambiosCamion("Scania", "R500", Decimal("700"), Decimal("41"), 2020, activo=False)

    camion = ActualizarCamion(uow).ejecutar(flota.camion.id, cambios)

    assert camion.patente == "AB123CD"  # la patente no se edita
    assert (camion.modelo, camion.anio, camion.activo) == ("R500", 2020, False)


def test_actualizar_camion_revalida_los_datos():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    with pytest.raises(DatosInvalidos):
        ActualizarCamion(uow).ejecutar(
            flota.camion.id,
            CambiosCamion("Scania", "R500", Decimal("-1"), Decimal("41"), None, True),
        )


def test_actualizar_chofer():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    chofer = ActualizarChofer(uow).ejecutar(flota.chofer.id, "Juan A. Pérez", activo=False)
    assert chofer.nombre == "Juan A. Pérez" and chofer.activo is False
