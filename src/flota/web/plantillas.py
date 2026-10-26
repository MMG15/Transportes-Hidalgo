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
from flota.web.formato import FILTROS

CARPETA_WEB = Path(__file__).parent

MENU = [
    ("/", "Tablero"),
    ("/viajes", "Viajes"),
    ("/rutas", "Rutas"),
    ("/combustible", "Combustible"),
    ("/alertas", "Alertas"),
    ("/monedas", "Tipo de cambio"),
    ("/reportes", "Reportes"),
    ("/catalogo", "Flota y clientes"),
]

templates = Jinja2Templates(directory=CARPETA_WEB / "templates")
templates.env.globals.update(colores=marca.COLORES, empresa=marca.NOMBRE_EMPRESA, menu=MENU)
templates.env.filters.update(FILTROS)

# Tipos de los campos de formulario (FastAPI los lee del cuerpo del POST).
Texto = Annotated[str, Form()]
TextoOpcional = Annotated[str | None, Form()]
Numero = Annotated[Decimal, Form()]
Id = Annotated[UUID, Form()]
FechaHora = Annotated[datetime, Form()]


def pagina(request: Request, plantilla: str, seccion: str, **contexto) -> HTMLResponse:
    contexto |= {"seccion": seccion, "anio": date.today().year}
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
