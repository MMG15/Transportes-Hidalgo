"""MOD-10 · Monedas: objeto de valor Dinero, conversión y tipo de cambio (RF-39 a RF-41)."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.monedas.application.casos_de_uso import CargarCotizacion, CorregirCotizacion
from flota.monedas.domain.entidades import TipoCambio, convertir_a_pesos
from flota.shared.domain.dinero import Dinero, ImporteGasto, Moneda
from flota.shared.domain.errores import DatosInvalidos, Duplicado, ReglaNegocioViolada
from tests.escenarios import flota_basica
from tests.fakes import UnidadDeTrabajoFake

ARS, CLP = Moneda.ARS, Moneda.CLP
HOY = date(2026, 10, 20)


# ---------- Dinero (objeto de valor) ----------
def test_dinero_se_suma_en_la_misma_moneda():
    assert Dinero(Decimal("10"), CLP) + Dinero(Decimal("5"), CLP) == Dinero(Decimal("15"), CLP)


def test_no_se_mezclan_monedas():
    with pytest.raises(ReglaNegocioViolada):
        Dinero(Decimal("10"), ARS) + Dinero(Decimal("5"), CLP)


def test_dinero_es_inmutable_y_comparable_por_valor():
    a = Dinero(Decimal("1.5"), "CLP")  # acepta el texto y lo convierte a Moneda
    assert a == Dinero(Decimal("1.50"), CLP)
    assert a * 2 == Dinero(Decimal("3"), CLP)
    with pytest.raises(AttributeError):
        a.monto = Decimal("2")  # type: ignore[misc]


def test_importe_en_pesos_no_se_convierte():
    importe = ImporteGasto.en_pesos(Decimal("1234.567"))
    assert importe.monto_ars == Decimal("1234.57")
    assert importe.cotizacion == Decimal("1")


# ---------- Regla de conversión ----------
def tipo(fecha: date = HOY, cotizacion: str = "1.25") -> TipoCambio:
    return TipoCambio(fecha=fecha, cotizacion=Decimal(cotizacion))


def test_convierte_clp_con_la_cotizacion_del_dia():
    importe = convertir_a_pesos(Dinero(Decimal("1000"), CLP), tipo(), HOY)
    assert (importe.monto_ars, importe.revisar_cotizacion) == (Decimal("1250.00"), False)


def test_con_cotizacion_anterior_queda_para_revisar():
    importe = convertir_a_pesos(Dinero(Decimal("1000"), CLP), tipo(date(2026, 10, 18)), HOY)
    assert importe.revisar_cotizacion is True


def test_sin_cotizacion_no_se_puede_convertir():
    with pytest.raises(ReglaNegocioViolada):
        convertir_a_pesos(Dinero(Decimal("1000"), CLP), None, HOY)


def test_no_se_usa_una_cotizacion_posterior_al_gasto():
    with pytest.raises(ReglaNegocioViolada):
        convertir_a_pesos(Dinero(Decimal("1000"), CLP), tipo(date(2026, 10, 21)), HOY)


def test_tipo_de_cambio_valida_monedas_y_valor():
    with pytest.raises(DatosInvalidos):
        TipoCambio(fecha=HOY, cotizacion=Decimal("1"), moneda_origen=ARS)
    with pytest.raises(DatosInvalidos):
        tipo(cotizacion="0")


# ---------- Casos de uso (CU-13) ----------
def test_una_sola_cotizacion_por_dia():
    uow = UnidadDeTrabajoFake()
    CargarCotizacion(uow).ejecutar(HOY, Decimal("1.25"))
    with pytest.raises(Duplicado):
        CargarCotizacion(uow).ejecutar(HOY, Decimal("1.30"))


def test_corregir_una_cotizacion_usada_exige_confirmar_y_no_cambia_los_gastos():
    """RF-41: la cotización aplicada a un gasto queda fija."""
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    cotizacion = CargarCotizacion(uow).ejecutar(HOY, Decimal("1.25"))
    carga = RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(flota.camion.id, datetime(2026, 10, 20, 9), Decimal("100"),
                   monto=Decimal("1000"), moneda=CLP)
    )  # fmt: skip

    with pytest.raises(ReglaNegocioViolada):
        CorregirCotizacion(uow).ejecutar(cotizacion.id, Decimal("1.40"), "error de tipeo")
    corregida = CorregirCotizacion(uow).ejecutar(
        cotizacion.id, Decimal("1.40"), "error de tipeo", confirmar=True
    )

    assert corregida.cotizacion == Decimal("1.40")
    assert uow.cargas.obtener(carga.id).costo_ars == Decimal("1250.00")  # no cambió


def test_corregir_una_cotizacion_sin_uso_no_pide_confirmacion():
    uow = UnidadDeTrabajoFake()
    cotizacion = CargarCotizacion(uow).ejecutar(HOY, Decimal("1.25"))
    corregida = CorregirCotizacion(uow).ejecutar(cotizacion.id, Decimal("1.26"), "BCRA")
    assert (corregida.cotizacion, corregida.fuente) == (Decimal("1.26"), "BCRA")
