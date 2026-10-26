"""Páginas del panel: Viajes y Rutas (CU-03)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from flota.catalogo.application.casos_de_uso import ConsultasCatalogo
from flota.combustible.application.consumo import CalculadoraConsumo
from flota.dependencias import Config, UoW
from flota.reportes.application.casos_de_uso import GenerarReporteConsumo
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere
from flota.viajes.application.casos_de_uso import (
    ActualizarRuta,
    CambiarEstadoCarga,
    ConsultasRutas,
    ConsultasViajes,
    DatosInicioViaje,
    DatosRuta,
    FinalizarViaje,
    IniciarViaje,
    RegistrarRuta,
)
from flota.viajes.domain.entidades import EstadoCarga, EstadoViaje, Pais
from flota.web.plantillas import (
    FechaHora,
    Id,
    Numero,
    Texto,
    TextoOpcional,
    decimal_opcional,
    ejecutar,
    pagina,
    periodo,
)

router = APIRouter(include_in_schema=False, dependencies=requiere(Modulo.VIAJES))

IdOpcional = Annotated[str | None, Form()]  # los <select> opcionales mandan "" si no se elige


def _uuid(valor: str | None) -> UUID | None:
    return UUID(valor) if valor else None


# ---------- Viajes ----------
@router.get("/viajes", response_class=HTMLResponse)
def viajes(
    request: Request, uow: UoW, config: Config, desde: date | None = None, hasta: date | None = None
):
    desde, hasta = periodo(desde, hasta)
    reporte = GenerarReporteConsumo(uow, config.umbral_desvio_pct).ejecutar(desde, hasta)
    inicio = datetime.combine(desde, time.min)
    fin = datetime.combine(hasta + timedelta(days=1), time.min)
    # Estado de carga actual de los viajes en curso (para el botón "Registrar descarga").
    tramo_actual = {
        v.id: v.tramo_actual.estado_carga
        for v in ConsultasViajes(uow).listar(inicio, fin)
        if v.estado == EstadoViaje.EN_CURSO
    }
    catalogo = ConsultasCatalogo(uow)
    return pagina(
        request,
        "viajes.html",
        "/viajes",
        filas=list(reversed(reporte.filas)),
        tramo_actual=tramo_actual,
        desde=desde,
        hasta=hasta,
        camiones=[c for c in catalogo.listar_camiones(1000) if c.activo],
        choferes=[c for c in catalogo.listar_choferes(1000) if c.activo],
        rutas=ConsultasRutas(uow).listar(solo_activas=True),
        clientes=catalogo.listar_clientes(1000),
        productos=catalogo.listar_productos(1000),
        ahora=datetime.now(),
    )


@router.post("/viajes")
def iniciar_viaje(
    uow: UoW,
    camion_id: Id,
    chofer_id: Id,
    ruta_id: Id,
    fecha_salida: FechaHora,
    km_salida: Numero,
    estado_carga: Annotated[EstadoCarga, Form()] = EstadoCarga.CARGADO,
    cliente_id: IdOpcional = None,
    producto_id: IdOpcional = None,
    cantidad: TextoOpcional = None,
    observaciones: TextoOpcional = None,
):
    datos = DatosInicioViaje(
        camion_id=camion_id,
        chofer_id=chofer_id,
        ruta_id=ruta_id,
        fecha_salida=fecha_salida,
        km_salida=km_salida,
        estado_carga=estado_carga,
        cliente_id=_uuid(cliente_id),
        producto_id=_uuid(producto_id),
        cantidad=decimal_opcional(cantidad),
        observaciones=observaciones,
    )
    return ejecutar("/viajes", lambda: IniciarViaje(uow).ejecutar(datos), "Viaje iniciado.")


@router.post("/viajes/{viaje_id}/tramos")
def cambiar_estado_carga(
    viaje_id: UUID,
    uow: UoW,
    fecha: FechaHora,
    km: Numero,
    estado_carga: Annotated[EstadoCarga, Form()] = EstadoCarga.VACIO,
):
    mensaje = (
        "Descarga registrada: empieza el tramo vacío."
        if estado_carga == "vacio"
        else ("Carga registrada: empieza un tramo cargado.")
    )
    return ejecutar(
        "/viajes",
        lambda: CambiarEstadoCarga(uow).ejecutar(viaje_id, fecha, km, estado_carga),
        mensaje,
    )


@router.post("/viajes/{viaje_id}/finalizar")
def finalizar_viaje(viaje_id: UUID, uow: UoW, fecha_llegada: FechaHora, km_llegada: Numero):
    return ejecutar(
        "/viajes",
        lambda: FinalizarViaje(uow).ejecutar(viaje_id, fecha_llegada, km_llegada),
        "Viaje finalizado.",
    )


# ---------- Rutas ----------
@router.get("/rutas", response_class=HTMLResponse)
def rutas(request: Request, uow: UoW, config: Config):
    lista = ConsultasRutas(uow).listar()
    with uow:
        calculadora = CalculadoraConsumo(uow, config.umbral_desvio_pct)
        historicos = {r.id: calculadora.historicos(r.id) for r in lista}
    return pagina(
        request, "rutas.html", "/rutas", rutas=lista, historicos=historicos, paises=list(Pais)
    )


def _datos_ruta(
    origen: str,
    destino: str,
    pais: Pais,
    km_estimados: str | None,
    ref_l100_cargado: str | None,
    ref_l100_vacio: str | None,
    activa: bool = True,
) -> DatosRuta:
    return DatosRuta(
        origen=origen,
        destino=destino,
        pais=pais,
        km_estimados=decimal_opcional(km_estimados),
        ref_l100_cargado=decimal_opcional(ref_l100_cargado),
        ref_l100_vacio=decimal_opcional(ref_l100_vacio),
        activa=activa,
    )


@router.post("/rutas")
def alta_ruta(
    uow: UoW,
    origen: Texto,
    destino: Texto,
    pais: Annotated[Pais, Form()] = Pais.AR,
    km_estimados: TextoOpcional = None,
    ref_l100_cargado: TextoOpcional = None,
    ref_l100_vacio: TextoOpcional = None,
):
    datos = _datos_ruta(origen, destino, pais, km_estimados, ref_l100_cargado, ref_l100_vacio)
    return ejecutar(
        "/rutas", lambda: RegistrarRuta(uow).ejecutar(datos), f"Ruta {origen} → {destino} creada."
    )


@router.post("/rutas/{ruta_id}")
def editar_ruta(
    ruta_id: UUID,
    uow: UoW,
    origen: Texto,
    destino: Texto,
    pais: Annotated[Pais, Form()] = Pais.AR,
    km_estimados: TextoOpcional = None,
    ref_l100_cargado: TextoOpcional = None,
    ref_l100_vacio: TextoOpcional = None,
    activa: Annotated[bool, Form()] = False,  # un checkbox sin tildar no se envía
):
    datos = _datos_ruta(
        origen, destino, pais, km_estimados, ref_l100_cargado, ref_l100_vacio, activa
    )
    return ejecutar(
        "/rutas", lambda: ActualizarRuta(uow).ejecutar(ruta_id, datos), "Ruta actualizada."
    )
