"""Páginas del panel web.

Patrón usado en los formularios: POST -> caso de uso -> redirección (303) a la página con un
mensaje de éxito o error ("Post/Redirect/Get"). Así recargar la página no reenvía el formulario.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from flota import marca
from flota.application.dto import FilaReporteConsumo
from flota.application.use_cases.catalogo import (
    ConsultasCatalogo,
    DatosCamion,
    DatosChofer,
    DatosCliente,
    DatosProducto,
    RegistrarCamion,
    RegistrarChofer,
    RegistrarCliente,
    RegistrarProducto,
)
from flota.application.use_cases.combustible import (
    ConsultasCargas,
    DatosCarga,
    RegistrarCargaCombustible,
)
from flota.application.use_cases.reportes import GenerarReporteConsumo
from flota.application.use_cases.viajes import DatosInicioViaje, FinalizarViaje, IniciarViaje
from flota.domain.entities import OrigenDato
from flota.domain.exceptions import ErrorDominio
from flota.presentation.api.dependencias import Config, UoW
from flota.presentation.archivos import importar_subida
from flota.presentation.web.formato import FILTROS

MENU = [
    ("/", "Tablero"),
    ("/viajes", "Viajes"),
    ("/combustible", "Combustible"),
    ("/reportes", "Reportes"),
    ("/catalogo", "Flota y clientes"),
]

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals.update(colores=marca.COLORES, empresa=marca.NOMBRE_EMPRESA, menu=MENU)
templates.env.filters.update(FILTROS)

router = APIRouter(include_in_schema=False)  # no aparece en la documentación de la API


# ---------- Utilidades ----------
def _pagina(request: Request, plantilla: str, seccion: str, **contexto) -> HTMLResponse:
    contexto |= {"seccion": seccion, "anio": date.today().year}
    return templates.TemplateResponse(request, plantilla, contexto)


def _volver(ruta: str, *, ok: str | None = None, error: str | None = None) -> RedirectResponse:
    parametros = urlencode({k: v for k, v in {"ok": ok, "error": error}.items() if v})
    return RedirectResponse(f"{ruta}?{parametros}" if parametros else ruta, status_code=303)


def _ejecutar(ruta: str, accion: Callable[[], object], mensaje_ok: str) -> RedirectResponse:
    """Corre un caso de uso y vuelve a la página con el resultado."""
    try:
        accion()
    except ErrorDominio as error:
        return _volver(ruta, error=str(error))
    return _volver(ruta, ok=mensaje_ok)


def _decimal_opcional(valor: str | None) -> Decimal | None:
    """Los campos opcionales de un formulario llegan como texto vacío."""
    if not valor or not valor.strip():
        return None
    try:
        return Decimal(valor.replace(",", "."))
    except InvalidOperation:
        return None


def _periodo(desde: date | None, hasta: date | None, dias: int = 30) -> tuple[date, date]:
    hasta = hasta or date.today()
    return (desde or hasta - timedelta(days=dias)), hasta


def _indicadores(filas: list[FilaReporteConsumo]) -> dict[str, object]:
    completos = [f for f in filas if f.km_recorridos and f.litros]
    km = sum((f.km_recorridos for f in completos), Decimal("0"))
    litros_completos = sum((f.litros for f in completos), Decimal("0"))
    return {
        "viajes": len(filas),
        "km": km,
        "litros": sum((f.litros for f in filas), Decimal("0")),
        "costo": sum((f.costo for f in filas if f.costo is not None), Decimal("0")),
        "consumo": litros_completos / km * 100 if km else None,
        "alertas": sum(1 for f in filas if f.alerta),
    }


Texto = Annotated[str, Form()]
TextoOpcional = Annotated[str | None, Form()]
Numero = Annotated[Decimal, Form()]
Id = Annotated[UUID, Form()]
FechaHora = Annotated[datetime, Form()]


# ---------- Tablero ----------
@router.get("/", response_class=HTMLResponse)
def tablero(request: Request, uow: UoW, config: Config):
    desde, hasta = _periodo(None, None)
    reporte = GenerarReporteConsumo(uow, config.umbral_desvio_pct).ejecutar(desde, hasta)
    return _pagina(
        request,
        "tablero.html",
        "/",
        reporte=reporte,
        indicadores=_indicadores(reporte.filas),
        en_curso=[f for f in reporte.filas if f.estado == "en_curso"],
        alertas=[f for f in reversed(reporte.filas) if f.alerta][:10],
        umbral=config.umbral_desvio_pct,
    )


# ---------- Viajes ----------
@router.get("/viajes", response_class=HTMLResponse)
def viajes(
    request: Request, uow: UoW, config: Config, desde: date | None = None, hasta: date | None = None
):
    desde, hasta = _periodo(desde, hasta)
    reporte = GenerarReporteConsumo(uow, config.umbral_desvio_pct).ejecutar(desde, hasta)
    catalogo = ConsultasCatalogo(uow)
    return _pagina(
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
    return _ejecutar("/viajes", lambda: IniciarViaje(uow).ejecutar(datos), "Viaje iniciado.")


@router.post("/viajes/{viaje_id}/finalizar")
def finalizar_viaje(viaje_id: UUID, uow: UoW, fecha_llegada: FechaHora, km_llegada: Numero):
    return _ejecutar(
        "/viajes",
        lambda: FinalizarViaje(uow).ejecutar(viaje_id, fecha_llegada, km_llegada),
        "Viaje finalizado.",
    )


# ---------- Combustible ----------
@router.get("/combustible", response_class=HTMLResponse)
def combustible(request: Request, uow: UoW):
    camiones = ConsultasCatalogo(uow).listar_camiones(1000)
    return _pagina(
        request,
        "combustible.html",
        "/combustible",
        cargas=ConsultasCargas(uow).listar(limite=50),
        camiones=camiones,
        patentes={c.id: c.patente for c in camiones},
        ahora=datetime.now(),
        resultado=None,
    )


@router.post("/combustible")
def registrar_carga(
    uow: UoW,
    config: Config,
    camion_id: Id,
    fecha: FechaHora,
    litros: Numero,
    precio_litro: TextoOpcional = None,
    odometro_km: TextoOpcional = None,
    estacion: TextoOpcional = None,
    referencia_externa: TextoOpcional = None,
):
    datos = DatosCarga(
        camion_id=camion_id,
        fecha=fecha,
        litros=litros,
        precio_litro=_decimal_opcional(precio_litro),
        odometro_km=_decimal_opcional(odometro_km),
        estacion=estacion,
        origen=OrigenDato.MANUAL,
        referencia_externa=referencia_externa,
    )
    registrar = RegistrarCargaCombustible(uow, config.tolerancia_tanque_pct)
    return _ejecutar("/combustible", lambda: registrar.ejecutar(datos), "Carga registrada.")


@router.post("/combustible/importar", response_class=HTMLResponse)
def importar(
    request: Request,
    uow: UoW,
    config: Config,
    archivo: UploadFile,
    origen: Annotated[OrigenDato, Form()] = OrigenDato.EXCEL,
):
    try:
        resultado = importar_subida(
            uow, archivo.file, archivo.filename or "", origen, config.tolerancia_tanque_pct
        )
    except ValueError as error:
        return _volver("/combustible", error=str(error))
    camiones = ConsultasCatalogo(uow).listar_camiones(1000)
    return _pagina(
        request,
        "combustible.html",
        "/combustible",
        cargas=ConsultasCargas(uow).listar(limite=50),
        camiones=camiones,
        patentes={c.id: c.patente for c in camiones},
        ahora=datetime.now(),
        resultado=resultado,
        nombre_archivo=archivo.filename,
    )


# ---------- Reportes ----------
@router.get("/reportes", response_class=HTMLResponse)
def reportes(
    request: Request,
    uow: UoW,
    config: Config,
    desde: date | None = None,
    hasta: date | None = None,
    camion_id: str | None = None,  # texto: el <select> manda "" para "Todos"
):
    desde, hasta = _periodo(desde, hasta)
    try:
        camion = UUID(camion_id) if camion_id else None
    except ValueError:
        camion = None
    reporte = GenerarReporteConsumo(uow, config.umbral_desvio_pct).ejecutar(desde, hasta, camion)
    parametros = {"desde": desde, "hasta": hasta} | ({"camion_id": camion} if camion else {})
    return _pagina(
        request,
        "reportes.html",
        "/reportes",
        reporte=reporte,
        indicadores=_indicadores(reporte.filas),
        camiones=ConsultasCatalogo(uow).listar_camiones(1000),
        camion_id=camion,
        url_excel=f"/api/v1/reportes/consumo.xlsx?{urlencode(parametros)}",
    )


# ---------- Catálogo ----------
@router.get("/catalogo", response_class=HTMLResponse)
def catalogo(request: Request, uow: UoW):
    consultas = ConsultasCatalogo(uow)
    return _pagina(
        request,
        "catalogo.html",
        "/catalogo",
        camiones=consultas.listar_camiones(1000),
        choferes=consultas.listar_choferes(1000),
        clientes=consultas.listar_clientes(1000),
        productos=consultas.listar_productos(1000),
    )


@router.post("/catalogo/camiones")
def alta_camion(
    uow: UoW,
    patente: Texto,
    marca_camion: Annotated[str, Form(alias="marca")],
    modelo: Texto,
    capacidad_tanque_litros: Numero,
    consumo_referencia_l100km: Numero,
):
    datos = DatosCamion(
        patente, marca_camion, modelo, capacidad_tanque_litros, consumo_referencia_l100km
    )
    return _ejecutar(
        "/catalogo", lambda: RegistrarCamion(uow).ejecutar(datos), f"Camión {patente} registrado."
    )


@router.post("/catalogo/choferes")
def alta_chofer(uow: UoW, nombre: Texto, dni: Texto):
    return _ejecutar(
        "/catalogo",
        lambda: RegistrarChofer(uow).ejecutar(DatosChofer(nombre, dni)),
        f"Chofer {nombre} registrado.",
    )


@router.post("/catalogo/clientes")
def alta_cliente(
    uow: UoW, razon_social: Texto, cuit: TextoOpcional = None, localidad: TextoOpcional = None
):
    return _ejecutar(
        "/catalogo",
        lambda: RegistrarCliente(uow).ejecutar(DatosCliente(razon_social, cuit, localidad)),
        f"Cliente {razon_social} registrado.",
    )


@router.post("/catalogo/productos")
def alta_producto(uow: UoW, nombre: Texto, unidad: Texto = "tn"):
    return _ejecutar(
        "/catalogo",
        lambda: RegistrarProducto(uow).ejecutar(DatosProducto(nombre, unidad)),
        f"Producto {nombre} registrado.",
    )
