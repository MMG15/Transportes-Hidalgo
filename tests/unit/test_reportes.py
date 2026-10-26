"""MOD-12 · Reportes de consumo (RF-12, RF-52)."""

from datetime import date, timedelta
from decimal import Decimal

from flota.catalogo.application.casos_de_uso import DatosChofer, RegistrarChofer
from flota.reportes.application.casos_de_uso import GenerarReporteConsumo
from flota.viajes.application.casos_de_uso import DatosRuta, RegistrarRuta
from flota.viajes.domain.entidades import Pais
from tests.escenarios import SALIDA, flota_basica, viaje_ida_y_vuelta
from tests.fakes import UnidadDeTrabajoFake

OCTUBRE = (date(2026, 10, 1), date(2026, 10, 31))


def test_reporte_con_consumo_por_tramo_y_resumenes():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow, ref_cargado=Decimal("42"), ref_vacio=Decimal("31"))
    viaje_ida_y_vuelta(uow, flota, litros_ida="84", litros_vuelta="62")  # 42 y 31 L/100km

    reporte = GenerarReporteConsumo(uow, Decimal("15")).ejecutar(*OCTUBRE)

    (fila,) = reporte.filas
    assert fila.ruta == "Albardón → Mendoza" and fila.pais == "AR"
    assert fila.consumo_l100km == Decimal("36.50")  # 146 L / 400 km
    assert fila.consumo_cargado_l100km == Decimal("42.00")
    assert fila.consumo_vacio_l100km == Decimal("31.00")
    assert fila.fuente_referencia == "ruta"
    assert fila.alerta is False
    assert reporte.resumen_por_camion[0].consumo_promedio_l100km == Decimal("36.50")
    assert reporte.resumen_por_chofer[0].nombre == "Juan Pérez"
    assert reporte.resumen_por_ruta[0].consumo_cargado_l100km == Decimal("42.00")


def test_filtros_por_chofer_ruta_y_pais():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    viaje_ida_y_vuelta(uow, flota)
    # Segundo viaje: otro chofer, a Chile
    flota.chofer = RegistrarChofer(uow).ejecutar(DatosChofer("María Gómez", "28987654"))
    flota.ruta = RegistrarRuta(uow).ejecutar(DatosRuta("Albardón", "Los Andes", Pais.CL))
    viaje_ida_y_vuelta(uow, flota, SALIDA + timedelta(days=1), km_salida=2000)

    generar = GenerarReporteConsumo(uow, Decimal("15"))
    assert len(generar.ejecutar(*OCTUBRE).filas) == 2
    assert [f.chofer for f in generar.ejecutar(*OCTUBRE, chofer_id=flota.chofer.id).filas] == [
        "María Gómez"
    ]
    assert [f.pais for f in generar.ejecutar(*OCTUBRE, pais="CL").filas] == ["CL"]
    assert len(generar.ejecutar(*OCTUBRE, ruta_id=flota.ruta.id).filas) == 1
