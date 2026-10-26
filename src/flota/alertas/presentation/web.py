"""Página del panel: Alertas (CU-06)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from flota.alertas.application.casos_de_uso import AccionAlerta, ConsultasAlertas, ResolverAlerta
from flota.catalogo.application.casos_de_uso import ConsultasCatalogo
from flota.dependencias import UoW
from flota.web.plantillas import Texto, ejecutar, pagina

router = APIRouter(include_in_schema=False)

MENSAJES = {
    AccionAlerta.EN_ANALISIS: "Alerta en análisis.",
    AccionAlerta.JUSTIFICAR: "Alerta justificada y cerrada.",
    AccionAlerta.CONFIRMAR: "Desvío confirmado: se escaló a Gerencia.",
}


@router.get("/alertas", response_class=HTMLResponse)
def alertas(request: Request, uow: UoW, ver: str = "abiertas"):
    consultas = ConsultasAlertas(uow)
    lista = consultas.abiertas() if ver == "abiertas" else consultas.listar(limite=300)
    patentes = {c.id: c.patente for c in ConsultasCatalogo(uow).listar_camiones(1000)}
    return pagina(request, "alertas.html", "/alertas", alertas=lista, ver=ver, patentes=patentes)


@router.post("/alertas/{alerta_id}")
def resolver(alerta_id: UUID, uow: UoW, accion: Annotated[AccionAlerta, Form()], comentario: Texto):
    return ejecutar(
        "/alertas",
        lambda: ResolverAlerta(uow).ejecutar(alerta_id, accion, comentario),
        MENSAJES[accion],
    )
