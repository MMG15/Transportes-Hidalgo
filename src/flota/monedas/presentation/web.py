"""Página del panel: Tipo de cambio (CU-13)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from flota.dependencias import UoW
from flota.monedas.application.casos_de_uso import (
    CargarCotizacion,
    ConsultasTiposCambio,
    CorregirCotizacion,
)
from flota.shared.domain.dinero import Moneda
from flota.web.plantillas import Numero, Texto, ejecutar, pagina

router = APIRouter(include_in_schema=False)


@router.get("/monedas", response_class=HTMLResponse)
def monedas(request: Request, uow: UoW):
    consultas = ConsultasTiposCambio(uow)
    return pagina(
        request,
        "monedas.html",
        "/monedas",
        cotizaciones=consultas.recientes(90),
        vigente=consultas.vigente(Moneda.CLP),
        hoy=date.today(),
    )


@router.post("/monedas")
def cargar(uow: UoW, fecha: Annotated[date, Form()], cotizacion: Numero, fuente: Texto = "manual"):
    return ejecutar(
        "/monedas",
        lambda: CargarCotizacion(uow).ejecutar(fecha, cotizacion, Moneda.CLP, fuente),
        f"Cotización del {fecha:%d/%m/%Y} cargada.",
    )


@router.post("/monedas/{tipo_cambio_id}")
def corregir(
    tipo_cambio_id: UUID,
    uow: UoW,
    cotizacion: Numero,
    fuente: Texto = "corrección manual",
    confirmar: Annotated[bool, Form()] = False,
):
    return ejecutar(
        "/monedas",
        lambda: CorregirCotizacion(uow).ejecutar(tipo_cambio_id, cotizacion, fuente, confirmar),
        "Cotización corregida. Los gastos ya registrados conservan la cotización original.",
    )
