"""Páginas del panel: Viajes."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from flota.catalogo.application.casos_de_uso import ConsultasCatalogo
from flota.dependencias import Config, UoW
from flota.reportes.application.casos_de_uso import GenerarReporteConsumo
from flota.viajes.application.casos_de_uso import DatosInicioViaje, FinalizarViaje, IniciarViaje
from flota.web.plantillas import (
    FechaHora,
    Id,
    Numero,
    Texto,
    TextoOpcional,
    ejecutar,
    pagina,
    periodo,
)

router = APIRouter(include_in_schema=False)


@router.get("/viajes", response_class=HTMLResponse)
def viajes(
    request: Request, uow: UoW, config: Config, desde: date | None = None, hasta: date | None = None
):
    desde, hasta = periodo(desde, hasta)
    reporte = GenerarReporteConsumo(uow, config.umbral_desvio_pct).ejecutar(desde, hasta)
    catalogo = ConsultasCatalogo(uow)
    return pagina(
        request,
        "viajes.html",
        "/viajes",
        filas=list(reversed(reporte.filas)),
        desde=desde,
        hasta=hasta,
        camiones=[c for c in catalogo.listar_camiones(1000) if c.activo],
        choferes=[c for c in catalogo.listar_choferes(1000) if c.activo],
        clientes=catalogo.listar_clientes(1000),
        productos=catalogo.listar_productos(1000),
        ahora=datetime.now(),
    )


@router.post("/viajes")
def iniciar_viaje(
    uow: UoW,
    camion_id: Id,
    chofer_id: Id,
    cliente_id: Id,
    producto_id: Id,
    origen: Texto,
    destino: Texto,
    cantidad: Numero,
    fecha_salida: FechaHora,
    km_salida: Numero,
    observaciones: TextoOpcional = None,
):
    datos = DatosInicioViaje(
        camion_id, chofer_id, cliente_id, producto_id, origen, destino, cantidad,
        fecha_salida, km_salida, observaciones,
    )  # fmt: skip
    return ejecutar("/viajes", lambda: IniciarViaje(uow).ejecutar(datos), "Viaje iniciado.")


@router.post("/viajes/{viaje_id}/finalizar")
def finalizar_viaje(viaje_id: UUID, uow: UoW, fecha_llegada: FechaHora, km_llegada: Numero):
    return ejecutar(
        "/viajes",
        lambda: FinalizarViaje(uow).ejecutar(viaje_id, fecha_llegada, km_llegada),
        "Viaje finalizado.",
    )
