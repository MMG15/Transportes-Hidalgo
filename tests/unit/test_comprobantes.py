"""Comprobantes y validación de cargas (CU-02; RF-02, RF-04, RF-06, RF-07, RF-08)."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from flota.combustible.application.casos_de_uso import (
    AnularCarga,
    DatosCarga,
    ObtenerConsumoViaje,
    RegistrarCargaCombustible,
)
from flota.combustible.domain.entidades import EstadoValidacion, OrigenDato
from flota.combustible.domain.eventos import CargaAnulada
from flota.comprobantes.application.casos_de_uso import (
    SIN_LECTURA,
    ArchivoRecibido,
    DescartarComprobante,
    LeerArchivoComprobante,
    RecibirComprobante,
    ValidarComprobanteCombustible,
)
from flota.comprobantes.domain.entidades import EstadoComprobante, validar_archivo
from flota.comprobantes.domain.eventos import ComprobantePendiente, ComprobanteRecibido
from flota.shared.domain.errores import DatosInvalidos, Duplicado, ReglaNegocioViolada
from tests.escenarios import SALIDA, flota_basica, viaje_ida_y_vuelta
from tests.fakes import AlmacenFake, UnidadDeTrabajoFake

FOTO = ArchivoRecibido(b"\xff\xd8\xff contenido de una foto", "image/jpeg")


def reloj():
    return SALIDA + timedelta(days=1)


@pytest.fixture
def uow():
    return UnidadDeTrabajoFake()


@pytest.fixture
def almacen():
    return AlmacenFake()


# ---------- Archivo ----------
def test_solo_fotos_o_pdf_de_hasta_10_mb():
    assert validar_archivo("image/png", 100) == "png"
    assert validar_archivo("application/pdf", 100) == "pdf"
    with pytest.raises(DatosInvalidos):
        validar_archivo("text/html", 100)
    with pytest.raises(DatosInvalidos):
        validar_archivo("image/jpeg", 11 * 1024 * 1024)
    with pytest.raises(DatosInvalidos):
        validar_archivo("image/jpeg", 0)


# ---------- Recepción ----------
def test_recibir_guarda_la_imagen_y_queda_pendiente_sin_lectura_automatica(uow, almacen):
    comprobante = RecibirComprobante(uow, almacen, reloj=reloj).ejecutar(FOTO)

    assert comprobante.estado == EstadoComprobante.PENDIENTE
    assert comprobante.problemas == [SIN_LECTURA]
    assert almacen.leer(comprobante.archivo) == FOTO.contenido  # RF-07
    assert LeerArchivoComprobante(uow, almacen).ejecutar(comprobante.id) == (
        FOTO.contenido,
        "image/jpeg",
    )
    assert ComprobanteRecibido(comprobante.id) in uow.eventos_publicados
    assert ComprobantePendiente(comprobante.id) in uow.eventos_publicados


# ---------- Validación (CU-02) ----------
def test_validar_registra_la_carga_vinculada_al_comprobante(uow, almacen):
    flota = flota_basica(uow)
    comprobante = RecibirComprobante(uow, almacen, reloj=reloj).ejecutar(FOTO)

    carga = ValidarComprobanteCombustible(uow, reloj).ejecutar(
        comprobante.id,
        DatosCarga(flota.camion.id, SALIDA, Decimal("200"), monto=Decimal("300000")),
    )

    assert carga.comprobante_id == comprobante.id
    assert carga.origen == OrigenDato.TICKET
    assert carga.estado_validacion == EstadoValidacion.VALIDADA
    procesado = uow.comprobantes.obtener(comprobante.id)
    assert procesado.estado == EstadoComprobante.PROCESADO and procesado.registro_id == carga.id


def test_si_la_carga_no_es_valida_el_comprobante_sigue_pendiente(uow, almacen):
    """Una sola transacción: o se registran la carga y el comprobante, o nada."""
    flota = flota_basica(uow)
    comprobante = RecibirComprobante(uow, almacen, reloj=reloj).ejecutar(FOTO)
    with pytest.raises(DatosInvalidos):
        ValidarComprobanteCombustible(uow, reloj).ejecutar(
            comprobante.id,
            DatosCarga(flota.camion.id, SALIDA, Decimal("5000")),  # absurdo
        )
    assert uow.comprobantes.obtener(comprobante.id).estado == EstadoComprobante.PENDIENTE


def test_no_se_valida_dos_veces(uow, almacen):
    flota = flota_basica(uow)
    comprobante = RecibirComprobante(uow, almacen, reloj=reloj).ejecutar(FOTO)
    datos = DatosCarga(flota.camion.id, SALIDA, Decimal("200"))
    ValidarComprobanteCombustible(uow, reloj).ejecutar(comprobante.id, datos)
    with pytest.raises(ReglaNegocioViolada):
        ValidarComprobanteCombustible(uow, reloj).ejecutar(comprobante.id, datos)


def test_descartar_exige_motivo(uow, almacen):
    comprobante = RecibirComprobante(uow, almacen, reloj=reloj).ejecutar(FOTO)
    with pytest.raises(DatosInvalidos):
        DescartarComprobante(uow).ejecutar(comprobante.id, " ")
    descartado = DescartarComprobante(uow).ejecutar(comprobante.id, "No es de la empresa")
    assert descartado.estado == EstadoComprobante.DESCARTADO


# ---------- Reglas de la carga ----------
def test_fecha_futura_se_rechaza(uow):
    """RF-04 (con una hora de margen para relojes desfasados)."""
    flota = flota_basica(uow)
    registrar = RegistrarCargaCombustible(uow, reloj=lambda: SALIDA)
    registrar.ejecutar(DatosCarga(flota.camion.id, SALIDA + timedelta(minutes=30), Decimal("50")))
    with pytest.raises(DatosInvalidos, match="futura"):
        registrar.ejecutar(DatosCarga(flota.camion.id, SALIDA + timedelta(hours=3), Decimal("50")))


def test_duplicado_por_estacion_fecha_y_monto(uow):
    """RF-08: mismo camión, estación, fecha y hora y monto (aunque cambien los litros leídos)."""
    flota = flota_basica(uow)
    registrar = RegistrarCargaCombustible(uow)
    datos = DatosCarga(
        flota.camion.id, SALIDA, Decimal("200"), estacion="YPF Ruta 40", monto=Decimal("300000")
    )
    registrar.ejecutar(datos)
    with pytest.raises(Duplicado):
        registrar.ejecutar(
            DatosCarga(
                flota.camion.id, SALIDA, Decimal("201"), estacion="YPF Ruta 40",
                monto=Decimal("300000"),
            )
        )  # fmt: skip


def test_una_carga_anulada_no_cuenta_para_el_consumo(uow):
    flota = flota_basica(uow)
    viaje = viaje_ida_y_vuelta(uow, flota, litros_ida="80", litros_vuelta="60")
    (ida, _) = sorted(uow.cargas.listar_por_viajes([viaje.id]), key=lambda c: c.fecha)

    anulada = AnularCarga(uow).ejecutar(ida.id, "Ticket de otro camión")

    assert anulada.estado_validacion == EstadoValidacion.ANULADA
    assert CargaAnulada(ida.id, viaje.id) in uow.eventos_publicados
    resumen = ObtenerConsumoViaje(uow, Decimal("15")).ejecutar(viaje.id)
    assert resumen.litros == Decimal("60")
    assert uow.auditoria.listar_filtrado(registro_id=ida.id)[0].valor_nuevo["motivo_anulacion"]


def test_no_se_anula_dos_veces(uow):
    flota = flota_basica(uow)
    carga = RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(flota.camion.id, datetime(2026, 10, 1), Decimal("50"))
    )
    AnularCarga(uow).ejecutar(carga.id, "error")
    with pytest.raises(ReglaNegocioViolada):
        AnularCarga(uow).ejecutar(carga.id, "error")
