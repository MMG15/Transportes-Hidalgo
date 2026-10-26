"""Utilidades comunes a todas las páginas del panel.

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

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from flota import marca
from flota.shared.domain.errores import ErrorDominio
from flota.usuarios.domain.entidades import Modulo, Usuario
from flota.web.formato import FILTROS

CARPETA_WEB = Path(__file__).parent

# (ruta, texto, módulo): el menú muestra sólo lo que el rol del usuario puede ver.
MENU = [
    ("/", "Tablero", Modulo.TABLERO),
    ("/viajes", "Viajes", Modulo.VIAJES),
    ("/rutas", "Rutas", Modulo.VIAJES),
    ("/combustible", "Combustible", Modulo.COMBUSTIBLE),
    ("/comprobantes", "Tickets", Modulo.COMBUSTIBLE),
    ("/alertas", "Alertas", Modulo.ALERTAS),
    ("/monedas", "Tipo de cambio", Modulo.PEAJES_MONEDAS),
    ("/reportes", "Reportes", Modulo.TABLERO),
    ("/catalogo", "Flota y clientes", Modulo.FLOTA),
    ("/usuarios", "Usuarios", Modulo.USUARIOS),
]


def primera_pagina(usuario: Usuario) -> str:
    """La primera página del menú que el usuario puede ver (su "inicio")."""
    return next((ruta for ruta, _, modulo in MENU if usuario.puede(modulo)), "/mi-cuenta")


templates = Jinja2Templates(directory=CARPETA_WEB / "templates")
templates.env.globals.update(colores=marca.COLORES, empresa=marca.NOMBRE_EMPRESA)
templates.env.filters.update(FILTROS)

# Tipos de los campos de formulario (FastAPI los lee del cuerpo del POST).
Texto = Annotated[str, Form()]
TextoOpcional = Annotated[str | None, Form()]
Numero = Annotated[Decimal, Form()]
Id = Annotated[UUID, Form()]
FechaHora = Annotated[datetime, Form()]


def pagina(request: Request, plantilla: str, seccion: str, **contexto) -> HTMLResponse:
    usuario = getattr(request.state, "usuario", None)  # lo deja `usuario_actual`
    menu = [(r, t) for r, t, m in MENU if usuario and usuario.puede(m)]
    contexto |= {"seccion": seccion, "anio": date.today().year, "usuario": usuario, "menu": menu}
    return templates.TemplateResponse(request, plantilla, contexto)


def volver(ruta: str, *, ok: str | None = None, error: str | None = None) -> RedirectResponse:
    parametros = urlencode({k: v for k, v in {"ok": ok, "error": error}.items() if v})
    return RedirectResponse(f"{ruta}?{parametros}" if parametros else ruta, status_code=303)


def ejecutar(ruta: str, accion: Callable[[], object], mensaje_ok: str) -> RedirectResponse:
    """Ejecuta un caso de uso y vuelve a la página con el resultado."""
    try:
        accion()
    except ErrorDominio as error:
        return volver(ruta, error=str(error))
    return volver(ruta, ok=mensaje_ok)


def decimal_opcional(valor: str | None) -> Decimal | None:
    """Los campos numéricos opcionales llegan como "" cuando quedan vacíos."""
    if valor is None or not valor.strip():
        return None
    try:
        return Decimal(valor.replace(",", "."))
    except InvalidOperation:
        return None


def periodo(desde: date | None, hasta: date | None, dias: int = 30) -> tuple[date, date]:
    hasta = hasta or date.today()
    return desde or hasta - timedelta(days=dias), hasta


def es_htmx(request: Request) -> bool:
    """HTMX agrega este encabezado a sus pedidos: así sabemos que espera un fragmento."""
    return request.headers.get("HX-Request") == "true"


def fragmento(request: Request, plantilla: str, **contexto) -> HTMLResponse:
    """Un pedazo de página (sin encabezado ni menú) para que HTMX lo reemplace en el lugar."""
    return templates.TemplateResponse(request, plantilla, contexto)
