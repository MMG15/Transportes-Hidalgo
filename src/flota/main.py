"""Aplicación FastAPI: API REST (/api/v1), panel web (/) y documentación (/docs).

Ejecutar con:  uv run flota servidor
"""

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from flota import marca
from flota.alertas.presentation import api as alertas_api
from flota.alertas.presentation import web as alertas_web
from flota.catalogo.presentation import api as catalogo_api
from flota.catalogo.presentation import web as catalogo_web
from flota.combustible.presentation import api as combustible_api
from flota.combustible.presentation import web as combustible_web
from flota.monedas.presentation import api as monedas_api
from flota.monedas.presentation import web as monedas_web
from flota.reportes.presentation import api as reportes_api
from flota.reportes.presentation import web as reportes_web
from flota.shared.domain.errores import (
    DatosInvalidos,
    Duplicado,
    ErrorDominio,
    NoEncontrado,
    ReglaNegocioViolada,
)
from flota.viajes.presentation import api as viajes_api
from flota.viajes.presentation import web as viajes_web
from flota.web.plantillas import CARPETA_WEB

ROUTERS_API = (catalogo_api, viajes_api, combustible_api, alertas_api, monedas_api, reportes_api)
ROUTERS_WEB = (reportes_web, viajes_web, combustible_web, alertas_web, monedas_web, catalogo_web)

# Traducción de errores del negocio a códigos HTTP.
_CODIGOS_HTTP: dict[type[ErrorDominio], int] = {
    NoEncontrado: 404,
    Duplicado: 409,
    DatosInvalidos: 422,
    ReglaNegocioViolada: 400,
}


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{marca.NOMBRE_EMPRESA} · API",
        description="Control de viajes y consumo de combustible de la flota. Panel web en [/](/).",
        version="0.2.0",
        docs_url=None,  # se reemplaza abajo por una versión con el logo
    )

    @app.exception_handler(ErrorDominio)
    async def manejar_error_dominio(_: Request, error: ErrorDominio) -> JSONResponse:
        codigo = next((c for t, c in _CODIGOS_HTTP.items() if isinstance(error, t)), 400)
        return JSONResponse(status_code=codigo, content={"detail": str(error)})

    app.mount("/static/css", StaticFiles(directory=CARPETA_WEB / "static" / "css"), name="css")
    app.mount("/static/img", StaticFiles(directory=marca.CARPETA_IMG), name="img")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(marca.FAVICON)

    @app.get("/docs", include_in_schema=False)
    def documentacion() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title,
            swagger_favicon_url="/favicon.ico",
        )

    @app.get("/salud", tags=["Sistema"])
    def salud() -> dict[str, str]:
        return {"estado": "ok"}

    for modulo in ROUTERS_API:
        app.include_router(modulo.router, prefix="/api/v1")
    for modulo in ROUTERS_WEB:
        app.include_router(modulo.router)
    return app


app = create_app()
