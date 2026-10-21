from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from flota.domain.consumo import calcular_consumo
from flota.domain.entities import Camion, CargaCombustible, EstadoViaje, Viaje
from flota.domain.exceptions import DatosInvalidos, ReglaNegocioViolada

SALIDA = datetime(2026, 10, 1, 8, 0)


def nuevo_camion(**cambios) -> Camion:
    datos = dict(
        patente="ab 123-cd",
        marca="Scania",
        modelo="R450",
        capacidad_tanque_litros=Decimal("600"),
        consumo_referencia_l100km=Decimal("40"),
    )
    return Camion(**(datos | cambios))


def nuevo_viaje(camion: Camion, **cambios) -> Viaje:
    datos = dict(
        camion_id=camion.id,
        chofer_id=uuid4(),
        cliente_id=uuid4(),
        producto_id=uuid4(),
        origen="Planta",
        destino="Campo",
        cantidad=Decimal("25"),
        fecha_salida=SALIDA,
        km_salida=Decimal("1000"),
    )
    return Viaje(**(datos | cambios))


def test_camion_normaliza_patente():
    assert nuevo_camion().patente == "AB123CD"


def test_camion_rechaza_capacidad_no_positiva():
    with pytest.raises(DatosInvalidos):
        nuevo_camion(capacidad_tanque_litros=Decimal("0"))


def test_finalizar_viaje_calcula_km():
    viaje = nuevo_viaje(nuevo_camion())
    viaje.finalizar(SALIDA + timedelta(hours=5), Decimal("1400"))
    assert viaje.estado == EstadoViaje.FINALIZADO
    assert viaje.km_recorridos == Decimal("400")


def test_no_se_puede_finalizar_dos_veces():
    viaje = nuevo_viaje(nuevo_camion())
    viaje.finalizar(SALIDA + timedelta(hours=5), Decimal("1400"))
    with pytest.raises(ReglaNegocioViolada):
        viaje.finalizar(SALIDA + timedelta(hours=6), Decimal("1500"))


def test_odometro_de_llegada_debe_ser_mayor():
    viaje = nuevo_viaje(nuevo_camion())
    with pytest.raises(DatosInvalidos):
        viaje.finalizar(SALIDA + timedelta(hours=5), Decimal("900"))


def test_calculo_de_consumo_y_alerta():
    camion = nuevo_camion()
    viaje = nuevo_viaje(camion)
    viaje.finalizar(SALIDA + timedelta(hours=5), Decimal("1400"))  # 400 km
    cargas = [
        CargaCombustible(
            camion_id=camion.id,
            fecha=SALIDA,
            litros=Decimal("100"),
            precio_litro=Decimal("1000"),
            viaje_id=viaje.id,
        ),
        CargaCombustible(
            camion_id=camion.id, fecha=SALIDA, litros=Decimal("100"), viaje_id=viaje.id
        ),
        # De otro viaje: no debe sumarse
        CargaCombustible(
            camion_id=camion.id, fecha=SALIDA, litros=Decimal("999"), viaje_id=uuid4()
        ),
    ]

    resumen = calcular_consumo(viaje, camion, cargas, umbral_desvio_pct=Decimal("15"))

    assert resumen.litros == Decimal("200")
    assert resumen.consumo_l100km == Decimal("50.00")  # 200 L / 400 km * 100
    assert resumen.desvio_pct == Decimal("25.0")  # (50 - 40) / 40
    assert resumen.alerta is True
    assert resumen.costo == Decimal("100000.00")
    assert resumen.litros_por_unidad == Decimal("8.00")  # 200 L / 25 tn


def test_viaje_en_curso_no_tiene_consumo():
    camion = nuevo_camion()
    viaje = nuevo_viaje(camion)
    carga = CargaCombustible(
        camion_id=camion.id, fecha=SALIDA, litros=Decimal("50"), viaje_id=viaje.id
    )
    resumen = calcular_consumo(viaje, camion, [carga])
    assert resumen.consumo_l100km is None
    assert resumen.alerta is False


def test_carga_no_se_asigna_a_viaje_de_otro_camion():
    viaje = nuevo_viaje(nuevo_camion())
    carga = CargaCombustible(camion_id=uuid4(), fecha=SALIDA, litros=Decimal("50"))
    with pytest.raises(ReglaNegocioViolada):
        carga.asignar_a_viaje(viaje)
