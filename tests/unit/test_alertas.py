"""MOD-05 · Alertas: ciclo de vida (CU-06) y generación automática por eventos (RF-16, RF-18)."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from flota import bootstrap
from flota.alertas.application.casos_de_uso import (
    AccionAlerta,
    EvaluarAlertasViaje,
    ResolverAlerta,
)
from flota.alertas.domain.entidades import Alerta, EstadoAlerta, TipoAlerta
from flota.alertas.domain.eventos import AlertaEscalada
from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.shared.domain.errores import DatosInvalidos, ReglaNegocioViolada
from tests.escenarios import SALIDA, flota_basica, viaje_ida_y_vuelta
from tests.fakes import UnidadDeTrabajoFake

AHORA = datetime(2026, 10, 2, 9, 0)


def nueva_alerta() -> Alerta:
    return Alerta(
        tipo=TipoAlerta.DESVIO_CONSUMO,
        origen_tabla="tramos_viaje",
        origen_id=uuid4(),
        descripcion="Consumo alto",
        creada_en=AHORA,
    )


# ---------- Ciclo de vida ----------
def test_justificar_cierra_la_alerta():
    alerta = nueva_alerta()
    alerta.justificar("Corte de ruta: cargó para dos días", AHORA, None)
    assert alerta.estado == EstadoAlerta.JUSTIFICADA
    assert not alerta.abierta and alerta.resuelta_en == AHORA


def test_confirmar_desvio_escala_a_gerencia():
    alerta = nueva_alerta()
    alerta.poner_en_analisis("Consultando al chofer", AHORA, None)
    alerta.confirmar_desvio("No hay explicación", AHORA, None)
    assert alerta.estado == EstadoAlerta.CONFIRMADA and alerta.escalada


def test_resolver_exige_comentario():
    with pytest.raises(DatosInvalidos):
        nueva_alerta().justificar("  ", AHORA, None)


def test_una_alerta_resuelta_no_se_vuelve_a_resolver():
    alerta = nueva_alerta()
    alerta.justificar("ok", AHORA, None)
    with pytest.raises(ReglaNegocioViolada):
        alerta.confirmar_desvio("otra vez", AHORA, None)


# ---------- Generación automática ----------
def uow_con_eventos() -> UnidadDeTrabajoFake:
    """Unidad de trabajo en memoria conectada al bus real: los manejadores de alertas
    reciben los eventos como en el sistema (comparten los mismos datos en memoria)."""
    uow = UnidadDeTrabajoFake()
    uow.bus = bootstrap.crear_bus(lambda: uow)
    return uow


def test_finalizar_un_viaje_con_desvio_genera_la_alerta_del_tramo():
    uow = uow_con_eventos()
    flota = flota_basica(uow, ref_cargado=Decimal("40"), ref_vacio=Decimal("30"))
    # Ida: 100 L / 200 km = 50 L/100km contra 40 (+25 %) -> alerta. Vuelta: 60 / 200 = 30: normal.
    viaje = viaje_ida_y_vuelta(uow, flota, litros_ida="100", litros_vuelta="60")

    (alerta,) = uow.alertas.listar_por_estado([EstadoAlerta.ABIERTA])
    assert alerta.tipo == TipoAlerta.DESVIO_CONSUMO
    assert alerta.viaje_id == viaje.id and alerta.origen_id == viaje.tramos[0].id
    assert (alerta.valor_detectado, alerta.valor_referencia) == (Decimal("50.00"), Decimal("40"))
    assert "+25,0 %" in alerta.descripcion and "configurada en la ruta" in alerta.descripcion


def test_si_el_consumo_se_normaliza_el_sistema_cierra_la_alerta():
    uow = uow_con_eventos()
    flota = flota_basica(uow, ref_cargado=Decimal("40"), ref_vacio=Decimal("30"))
    viaje = viaje_ida_y_vuelta(uow, flota, litros_ida="100", litros_vuelta="60")
    # Alguien corrige la referencia de la ruta: el tramo deja de estar fuera de rango.
    ruta = uow.rutas.obtener(flota.ruta.id)
    ruta.ref_l100_cargado = Decimal("48")
    uow.rutas.guardar(ruta)

    EvaluarAlertasViaje(uow, Decimal("15")).ejecutar(viaje.id)

    (alerta,) = uow.alertas.listar_por_estado()
    assert alerta.estado == EstadoAlerta.JUSTIFICADA and alerta.usuario_id is None


def test_una_alerta_resuelta_por_una_persona_no_se_reabre():
    uow = uow_con_eventos()
    flota = flota_basica(uow, ref_cargado=Decimal("40"), ref_vacio=Decimal("30"))
    viaje = viaje_ida_y_vuelta(uow, flota, litros_ida="100", litros_vuelta="60")
    (alerta,) = uow.alertas.listar_por_estado()
    ResolverAlerta(uow).ejecutar(alerta.id, AccionAlerta.JUSTIFICAR, "Viento en contra")

    EvaluarAlertasViaje(uow, Decimal("15")).ejecutar(viaje.id)

    assert [a.estado for a in uow.alertas.listar_por_estado()] == [EstadoAlerta.JUSTIFICADA]


def test_carga_que_supera_el_tanque_genera_alerta():
    """RF-18 (tanque de 600 L, tolerancia 5 %)."""
    uow = uow_con_eventos()
    flota = flota_basica(uow)
    RegistrarCargaCombustible(uow).ejecutar(DatosCarga(flota.camion.id, SALIDA, Decimal("650")))
    RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(flota.camion.id, SALIDA + timedelta(hours=1), Decimal("620"))  # dentro del 5 %
    )

    (alerta,) = uow.alertas.listar_por_estado()
    assert alerta.tipo == TipoAlerta.CAPACIDAD_TANQUE
    assert alerta.valor_detectado == Decimal("650")


def test_confirmar_publica_el_evento_de_escalamiento():
    uow = uow_con_eventos()
    flota = flota_basica(uow, ref_cargado=Decimal("40"), ref_vacio=Decimal("30"))
    viaje_ida_y_vuelta(uow, flota, litros_ida="100")
    (alerta,) = uow.alertas.listar_por_estado()

    ResolverAlerta(uow).ejecutar(alerta.id, AccionAlerta.CONFIRMAR, "Sin explicación")

    assert AlertaEscalada(alerta.id) in uow.eventos_publicados
