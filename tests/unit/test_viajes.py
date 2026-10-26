"""MOD-02 · Viajes y rutas: tramos cargado / vacío y ciclo de vida del viaje (CU-03)."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from flota.shared.domain.errores import DatosInvalidos, Duplicado, ReglaNegocioViolada
from flota.viajes.application.casos_de_uso import (
    ActualizarRuta,
    CambiarEstadoCarga,
    DatosRuta,
    FinalizarViaje,
    RegistrarRuta,
)
from flota.viajes.domain.entidades import EstadoCarga, EstadoViaje, Pais, Ruta, Viaje
from tests.escenarios import SALIDA, flota_basica, iniciar_viaje
from tests.fakes import UnidadDeTrabajoFake


def nuevo_viaje(**cambios) -> Viaje:
    datos = dict(
        camion_id=uuid4(),
        chofer_id=uuid4(),
        ruta_id=uuid4(),
        fecha_salida=SALIDA,
        km_salida=Decimal("1000"),
        producto_id=uuid4(),
        cantidad=Decimal("28"),
    )
    return Viaje.iniciar(**(datos | cambios))


# ---------- Ruta ----------
def test_ruta_nombre_y_referencias():
    ruta = Ruta(
        origen=" Albardón ", destino="Los Andes", pais=Pais.CL, ref_l100_cargado=Decimal(48)
    )
    assert ruta.nombre == "Albardón → Los Andes"
    assert ruta.referencia_configurada(EstadoCarga.CARGADO) == Decimal(48)
    assert ruta.referencia_configurada(EstadoCarga.VACIO) is None


def test_ruta_rechaza_referencia_no_positiva():
    with pytest.raises(DatosInvalidos):
        Ruta(origen="A", destino="B", ref_l100_vacio=Decimal("0"))


# ---------- Viaje y tramos ----------
def test_iniciar_crea_el_primer_tramo_cargado():
    viaje = nuevo_viaje()
    assert len(viaje.tramos) == 1
    assert viaje.tramo_actual.estado_carga == EstadoCarga.CARGADO
    assert viaje.tramo_actual.km_inicio == Decimal("1000")


def test_viaje_cargado_exige_producto_y_cantidad():
    with pytest.raises(DatosInvalidos):
        nuevo_viaje(producto_id=None, cantidad=None)


def test_viaje_que_sale_vacio_no_necesita_producto():
    viaje = nuevo_viaje(estado_carga=EstadoCarga.VACIO, producto_id=None, cantidad=None)
    assert viaje.tramo_actual.estado_carga == EstadoCarga.VACIO


def test_descarga_cierra_el_tramo_y_abre_el_regreso_vacio():
    viaje = nuevo_viaje()
    viaje.registrar_descarga(SALIDA + timedelta(hours=5), Decimal("1200"))

    ida, vuelta = viaje.tramos
    assert ida.km_recorridos == Decimal("200") and not ida.abierto
    assert vuelta.estado_carga == EstadoCarga.VACIO and vuelta.abierto
    assert vuelta.km_inicio == Decimal("1200")


def test_no_se_puede_pasar_al_mismo_estado_de_carga():
    viaje = nuevo_viaje()
    with pytest.raises(ReglaNegocioViolada):
        viaje.cambiar_estado_carga(
            SALIDA + timedelta(hours=1), Decimal("1100"), EstadoCarga.CARGADO
        )


def test_el_odometro_de_un_tramo_debe_avanzar():
    viaje = nuevo_viaje()
    with pytest.raises(DatosInvalidos):
        viaje.registrar_descarga(SALIDA + timedelta(hours=5), Decimal("900"))


def test_finalizar_cierra_el_ultimo_tramo():
    viaje = nuevo_viaje()
    viaje.registrar_descarga(SALIDA + timedelta(hours=5), Decimal("1200"))
    viaje.finalizar(SALIDA + timedelta(hours=10), Decimal("1400"))

    assert viaje.estado == EstadoViaje.FINALIZADO
    assert viaje.km_recorridos == Decimal("400")
    assert [t.km_recorridos for t in viaje.tramos] == [Decimal("200"), Decimal("200")]


def test_no_se_puede_finalizar_dos_veces():
    viaje = nuevo_viaje()
    viaje.finalizar(SALIDA + timedelta(hours=5), Decimal("1400"))
    with pytest.raises(ReglaNegocioViolada):
        viaje.finalizar(SALIDA + timedelta(hours=6), Decimal("1500"))


def test_tramo_en_una_fecha():
    viaje = nuevo_viaje()
    viaje.registrar_descarga(SALIDA + timedelta(hours=5), Decimal("1200"))
    assert viaje.tramo_en(SALIDA + timedelta(hours=2)).estado_carga == EstadoCarga.CARGADO
    assert viaje.tramo_en(SALIDA + timedelta(hours=7)).estado_carga == EstadoCarga.VACIO


# ---------- Casos de uso ----------
def test_no_permite_dos_viajes_en_curso():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    iniciar_viaje(uow, flota)
    with pytest.raises(ReglaNegocioViolada):
        iniciar_viaje(uow, flota, SALIDA + timedelta(hours=1))


def test_no_permite_iniciar_en_una_ruta_inactiva():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    ActualizarRuta(uow).ejecutar(
        flota.ruta.id, DatosRuta("Albardón", "Mendoza", Pais.AR, activa=False)
    )
    with pytest.raises(ReglaNegocioViolada):
        iniciar_viaje(uow, flota)


def test_ruta_duplicada():
    uow = UnidadDeTrabajoFake()
    flota_basica(uow)
    with pytest.raises(Duplicado):
        RegistrarRuta(uow).ejecutar(DatosRuta("Albardón", "Mendoza"))


def test_el_viaje_actualiza_el_odometro_del_camion():
    uow = UnidadDeTrabajoFake()
    flota = flota_basica(uow)
    viaje = iniciar_viaje(uow, flota)
    CambiarEstadoCarga(uow).ejecutar(
        viaje.id, SALIDA + timedelta(hours=5), Decimal("1200"), EstadoCarga.VACIO
    )
    FinalizarViaje(uow).ejecutar(viaje.id, SALIDA + timedelta(hours=9), Decimal("1400"))

    assert uow.camiones.obtener(flota.camion.id).km_actual == Decimal("1400")
    guardado = uow.viajes.obtener(viaje.id)
    assert [t.estado_carga for t in guardado.tramos] == [EstadoCarga.CARGADO, EstadoCarga.VACIO]
