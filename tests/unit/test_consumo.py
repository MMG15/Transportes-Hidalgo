"""Reglas de consumo (RF-10, RF-11, RF-13, RF-16): dominio puro, sin base de datos."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from flota.catalogo.domain.entidades import Camion
from flota.combustible.domain.consumo import (
    FuenteReferencia,
    PromedioHistorico,
    calcular_consumo,
    elegir_referencia,
    promedio_historico,
)
from flota.combustible.domain.entidades import CargaCombustible
from flota.shared.domain.errores import ReglaNegocioViolada
from flota.viajes.domain.entidades import EstadoCarga, Ruta, Viaje
from tests.escenarios import SALIDA

CARGADO, VACIO = EstadoCarga.CARGADO, EstadoCarga.VACIO


def camion() -> Camion:
    return Camion(
        patente="AB123CD",
        marca="Scania",
        modelo="R450",
        capacidad_tanque_litros=Decimal("600"),
        consumo_referencia_l100km=Decimal("40"),
    )


def ruta(cargado=None, vacio=None) -> Ruta:
    return Ruta(
        origen="Albardón", destino="Mendoza", ref_l100_cargado=cargado, ref_l100_vacio=vacio
    )


def viaje_ida_y_vuelta(c: Camion, r: Ruta) -> Viaje:
    """200 km cargado + 200 km vacío."""
    viaje = Viaje.iniciar(
        camion_id=c.id,
        chofer_id=uuid4(),
        ruta_id=r.id,
        fecha_salida=SALIDA,
        km_salida=Decimal("1000"),
        producto_id=uuid4(),
        cantidad=Decimal("28"),
    )
    viaje.registrar_descarga(SALIDA + timedelta(hours=5), Decimal("1200"))
    viaje.finalizar(SALIDA + timedelta(hours=10), Decimal("1400"))
    return viaje


def carga(viaje: Viaje, horas: int, litros: str, precio: str | None = None) -> CargaCombustible:
    return CargaCombustible(
        camion_id=viaje.camion_id,
        fecha=SALIDA + timedelta(hours=horas),
        litros=Decimal(litros),
        precio_litro=Decimal(precio) if precio else None,
        viaje_id=viaje.id,
    )


def test_consumo_por_tramo_contra_la_referencia_de_la_ruta():
    c, r = camion(), ruta(cargado=Decimal("42"), vacio=Decimal("31"))
    viaje = viaje_ida_y_vuelta(c, r)
    cargas = [carga(viaje, 2, "84"), carga(viaje, 7, "80")]  # 42 y 40 L/100km

    resumen = calcular_consumo(viaje, c, cargas, Decimal("15"), ruta=r)

    ida, vuelta = resumen.tramos
    assert (ida.consumo_l100km, ida.referencia.valor, ida.alerta) == (
        Decimal("42.00"), Decimal("42"), False,
    )  # fmt: skip
    # Vacío: 40 contra 31 de referencia -> +29 % -> alerta
    assert vuelta.consumo_l100km == Decimal("40.00")
    assert vuelta.desvio_pct == Decimal("29.0") and vuelta.alerta
    assert ida.referencia.fuente == FuenteReferencia.RUTA
    assert resumen.alerta  # basta con un tramo fuera de rango


def test_totales_del_viaje():
    c, r = camion(), ruta(cargado=Decimal("50"), vacio=Decimal("30"))
    viaje = viaje_ida_y_vuelta(c, r)
    cargas = [carga(viaje, 2, "100", "1000"), carga(viaje, 7, "60")]

    resumen = calcular_consumo(viaje, c, cargas, ruta=r)

    assert resumen.litros == Decimal("160")
    assert resumen.consumo_l100km == Decimal("40.00")  # 160 L / 400 km
    assert resumen.consumo_referencia_l100km == Decimal("40.00")  # (50*200 + 30*200) / 400
    assert resumen.desvio_pct == Decimal("0.0")
    assert resumen.costo == Decimal("100000.00")  # sólo la carga con precio
    assert resumen.litros_por_unidad == Decimal("5.71")  # 160 L / 28 tn


def test_cargas_de_otro_viaje_no_se_suman():
    c, r = camion(), ruta()
    viaje = viaje_ida_y_vuelta(c, r)
    ajena = carga(viaje, 2, "999")
    ajena.viaje_id = uuid4()
    assert calcular_consumo(viaje, c, [ajena], ruta=r).litros == Decimal("0")


def test_viaje_en_curso_no_tiene_consumo_del_tramo_abierto():
    c, r = camion(), ruta()
    viaje = Viaje.iniciar(
        camion_id=c.id,
        chofer_id=uuid4(),
        ruta_id=r.id,
        fecha_salida=SALIDA,
        km_salida=Decimal("1000"),
        producto_id=uuid4(),
        cantidad=Decimal("28"),
    )
    resumen = calcular_consumo(viaje, c, [carga(viaje, 1, "50")], ruta=r)
    assert resumen.consumo_l100km is None
    assert resumen.tramos[0].consumo_l100km is None
    assert resumen.alerta is False


def test_el_camion_debe_ser_el_del_viaje():
    c, r = camion(), ruta()
    with pytest.raises(ReglaNegocioViolada):
        calcular_consumo(viaje_ida_y_vuelta(c, r), camion(), [], ruta=r)


# ---------- Elección de la referencia ----------
def test_referencia_configurada_tiene_prioridad():
    historico = PromedioHistorico(CARGADO, viajes=10, km=Decimal(1000), litros=Decimal(450))
    referencia = elegir_referencia(CARGADO, ruta(cargado=Decimal("42")), historico, camion())
    assert (referencia.valor, referencia.fuente) == (Decimal("42"), FuenteReferencia.RUTA)


def test_sin_configurar_usa_el_historico_si_hay_suficientes_viajes():
    historico = PromedioHistorico(CARGADO, viajes=3, km=Decimal(1000), litros=Decimal(450))
    referencia = elegir_referencia(CARGADO, ruta(), historico, camion())
    assert (referencia.valor, referencia.fuente) == (Decimal("45.00"), FuenteReferencia.HISTORICO)


def test_con_poco_historial_usa_el_camion():
    historico = PromedioHistorico(CARGADO, viajes=2, km=Decimal(1000), litros=Decimal(450))
    referencia = elegir_referencia(CARGADO, ruta(), historico, camion())
    assert (referencia.valor, referencia.fuente) == (Decimal("40"), FuenteReferencia.CAMION)


def test_promedio_historico_por_estado_de_carga():
    c, r = camion(), ruta()
    v1, v2 = viaje_ida_y_vuelta(c, r), viaje_ida_y_vuelta(c, r)
    datos = [
        (v1, [carga(v1, 2, "90"), carga(v1, 7, "60")]),
        (v2, [carga(v2, 2, "110"), carga(v2, 7, "62")]),
    ]
    cargado = promedio_historico(datos, CARGADO)
    vacio = promedio_historico(datos, VACIO)
    assert (cargado.viajes, cargado.l100km) == (2, Decimal("50.00"))  # 200 L / 400 km
    assert (vacio.viajes, vacio.l100km) == (2, Decimal("30.50"))  # 122 L / 400 km


def test_la_referencia_del_camion_informa_el_desvio_pero_no_alerta():
    """Sin referencia de la ruta, cargado contra la referencia general daría falsas alarmas."""
    c, r = camion(), ruta()  # ruta sin referencias ni historial -> camión (40)
    viaje = viaje_ida_y_vuelta(c, r)
    resumen = calcular_consumo(viaje, c, [carga(viaje, 2, "100")], ruta=r)

    ida = resumen.tramos[0]
    assert ida.referencia.fuente == FuenteReferencia.CAMION
    assert ida.desvio_pct == Decimal("25.0")
    assert ida.alerta is False and resumen.alerta is False
