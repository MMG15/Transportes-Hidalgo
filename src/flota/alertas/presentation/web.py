"""Página del panel: Alertas (CU-06)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from flota.alertas.application.casos_de_uso import AccionAlerta, ConsultasAlertas, ResolverAlerta
from flota.catalogo.application.casos_de_uso import ConsultasCatalogo
from flota.dependencias import UoW
from flota.shared.domain.errores import ErrorDominio
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere
from flota.web.plantillas import Texto, ejecutar, es_htmx, fragmento, pagina

router = APIRouter(include_in_schema=False, dependencies=requiere(Modulo.ALERTAS))

MENSAJES = {
    AccionAlerta.EN_ANALISIS: "Alerta en análisis.",
    AccionAlerta.JUSTIFICAR: "Alerta justificada y cerrada.",
    AccionAlerta.CONFIRMAR: "Desvío confirmado: se escaló a Gerencia.",
}


def _patentes(uow: UoW) -> dict:
    return {c.id: c.patente for c in ConsultasCatalogo(uow).listar_camiones(1000)}


@router.get("/alertas", response_class=HTMLResponse)
def alertas(request: Request, uow: UoW, ver: str = "abiertas"):
    consultas = ConsultasAlertas(uow)
    lista = consultas.abiertas() if ver == "abiertas" else consultas.listar(limite=300)
    return pagina(
        request, "alertas.html", "/alertas", alertas=lista, ver=ver, patentes=_patentes(uow)
    )


@router.post("/alertas/{alerta_id}")
def resolver(
    request: Request,
    alerta_id: UUID,
    uow: UoW,
    accion: Annotated[AccionAlerta, Form()],
    comentario: Texto,
):
    """Con HTMX devuelve sólo la fila actualizada; sin HTMX, redirige a la página (PRG)."""
    if not es_htmx(request):
        return ejecutar(
            "/alertas",
            lambda: ResolverAlerta(uow).ejecutar(alerta_id, accion, comentario),
            MENSAJES[accion],
        )
    try:
        alerta = ResolverAlerta(uow).ejecutar(alerta_id, accion, comentario)
        mensaje, error = MENSAJES[accion], False
    except ErrorDominio as problema:
        alerta = ConsultasAlertas(uow).obtener(alerta_id)
        mensaje, error = str(problema), True
    return fragmento(
        request,
        "_fila_alerta.html",
        a=alerta,
        patentes=_patentes(uow),
        mensaje=mensaje,
        error=error,
    )
