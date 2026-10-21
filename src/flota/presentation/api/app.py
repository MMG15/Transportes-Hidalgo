"""Aplicación FastAPI: API REST (/api/v1), panel web (/) y documentación (/docs).

Ejecutar con:  uv run flota servidor
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from flota import marca
from flota.domain.exceptions import (
    DatosInvalidos,
    Duplicado,
    ErrorDominio,
    NoEncontrado,
    ReglaNegocioViolada,
)
from flota.presentation.api.routers import catalogo, combustible, reportes, viajes
from flota.presentation.web import rutas as web

CARPETA_WEB = Path(__file__).resolve().parents[1] / "web"

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

    for modulo in (catalogo, viajes, combustible, reportes):
        app.include_router(modulo.router, prefix="/api/v1")
    app.include_router(web.router)
    return app


app = create_app()
