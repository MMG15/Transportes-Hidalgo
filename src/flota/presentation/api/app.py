"""Aplicación FastAPI. Ejecutar con:  uv run flota servidor"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from flota.domain.exceptions import (
    DatosInvalidos,
    Duplicado,
    ErrorDominio,
    NoEncontrado,
    ReglaNegocioViolada,
)
from flota.presentation.api.routers import catalogo, combustible, reportes, viajes

# Traducción de errores del negocio a códigos HTTP.
_CODIGOS_HTTP: dict[type[ErrorDominio], int] = {
    NoEncontrado: 404,
    Duplicado: 409,
    DatosInvalidos: 422,
    ReglaNegocioViolada: 400,
}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gestión de Flota",
        description="Control de viajes y consumo de combustible de camiones.",
        version="0.1.0",
    )

    @app.exception_handler(ErrorDominio)
    async def manejar_error_dominio(_: Request, error: ErrorDominio) -> JSONResponse:
        codigo = next((c for t, c in _CODIGOS_HTTP.items() if isinstance(error, t)), 400)
        return JSONResponse(status_code=codigo, content={"detail": str(error)})

    @app.get("/salud", tags=["Sistema"])
    def salud() -> dict[str, str]:
        return {"estado": "ok"}

    for modulo in (catalogo, viajes, combustible, reportes):
        app.include_router(modulo.router, prefix="/api/v1")
    return app


app = create_app()
