"""Aplicación FastAPI: API REST (/api/v1), panel web (/) y documentación (/docs).

Ejecutar con:  uv run flota servidor
"""

from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from flota import marca
from flota.alertas.presentation import api as alertas_api
from flota.alertas.presentation import web as alertas_web
from flota.catalogo.presentation import api as catalogo_api
from flota.catalogo.presentation import web as catalogo_web
from flota.combustible.presentation import api as combustible_api
from flota.combustible.presentation import web as combustible_web
from flota.comprobantes.presentation import api as comprobantes_api
from flota.comprobantes.presentation import web as comprobantes_web
from flota.monedas.presentation import api as monedas_api
from flota.monedas.presentation import web as monedas_web
from flota.reportes.presentation import api as reportes_api
from flota.reportes.presentation import web as reportes_web
from flota.shared.domain.errores import (
    DatosInvalidos,
    Duplicado,
    ErrorDominio,
    NoAutenticado,
    NoEncontrado,
    ReglaNegocioViolada,
    SinPermiso,
)
from flota.shared.infrastructure.config import get_settings
from flota.usuarios.presentation import api as usuarios_api
from flota.usuarios.presentation import web as usuarios_web
from flota.usuarios.presentation.seguridad import clave_secreta
from flota.viajes.presentation import api as viajes_api
from flota.viajes.presentation import web as viajes_web
from flota.web.plantillas import CARPETA_WEB, pagina

ROUTERS_API = (
    usuarios_api.publico,
    usuarios_api.router,
    catalogo_api.router,
    viajes_api.router,
    combustible_api.router,
    comprobantes_api.router,
    alertas_api.router,
    monedas_api.router,
    reportes_api.router,
)
ROUTERS_WEB = (
    usuarios_web.publico,
    usuarios_web.router,
    reportes_web.router,
    viajes_web.router,
    combustible_web.router,
    comprobantes_web.router,
    alertas_web.router,
    monedas_web.router,
    catalogo_web.router,
)

# Traducción de errores del negocio a códigos HTTP.
_CODIGOS_HTTP: dict[type[ErrorDominio], int] = {
    NoAutenticado: 401,
    SinPermiso: 403,
    NoEncontrado: 404,
    Duplicado: 409,
    DatosInvalidos: 422,
    ReglaNegocioViolada: 400,
}


def _es_api(request: Request) -> bool:
    return request.url.path.startswith("/api/")


def create_app() -> FastAPI:
    config = get_settings()
    app = FastAPI(
        title=f"{marca.NOMBRE_EMPRESA} · API",
        description=(
            "Gestión de flota y trazabilidad de combustible. Panel web en [/](/).\n\n"
            "Autenticación: `POST /api/v1/auth/token` y luego `Authorization: Bearer <token>`."
        ),
        version="0.6.0",
        docs_url=None,  # se reemplaza abajo por una versión con el logo
    )
    # Cookie de sesión firmada con la clave secreta (el navegador no puede alterarla).
    app.add_middleware(
        SessionMiddleware,
        secret_key=clave_secreta(),
        session_cookie="hidalgo_sesion",
        max_age=config.horas_sesion * 3600,
        same_site="lax",  # no se envía en formularios de otros sitios (protege contra CSRF)
        https_only=config.cookies_seguras,
    )

    @app.exception_handler(NoAutenticado)
    async def manejar_no_autenticado(request: Request, error: NoAutenticado):
        if _es_api(request):
            return JSONResponse(
                status_code=401,
                content={"detail": str(error)},
                headers={"WWW-Authenticate": "Bearer"},
            )
        destino = urlencode({"siguiente": request.url.path})
        return RedirectResponse(f"/login?{destino}", status_code=303)

    @app.exception_handler(SinPermiso)
    async def manejar_sin_permiso(request: Request, error: SinPermiso):
        if _es_api(request):
            return JSONResponse(status_code=403, content={"detail": str(error)})
        respuesta = pagina(request, "sin_permiso.html", "", mensaje=str(error))
        respuesta.status_code = 403
        return respuesta

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

    for router in ROUTERS_API:
        app.include_router(router, prefix="/api/v1")
    for router in ROUTERS_WEB:
        app.include_router(router)
    return app


app = create_app()
