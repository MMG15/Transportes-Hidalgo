"""Páginas del panel: Combustible."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from flota.catalogo.application.casos_de_uso import ConsultasCatalogo
from flota.combustible.application.casos_de_uso import (
    ConsultasCargas,
    DatosCarga,
    RegistrarCargaCombustible,
)
from flota.combustible.domain.entidades import OrigenDato
from flota.combustible.presentation.archivos import importar_subida
from flota.dependencias import Config, UoW
from flota.web.plantillas import (
    FechaHora,
    Id,
    Numero,
    TextoOpcional,
    decimal_opcional,
    ejecutar,
    pagina,
    volver,
)

router = APIRouter(include_in_schema=False)


def _pagina_combustible(request: Request, uow: UoW, **extra) -> HTMLResponse:
    camiones = ConsultasCatalogo(uow).listar_camiones(1000)
    return pagina(
        request,
        "combustible.html",
        "/combustible",
        cargas=ConsultasCargas(uow).listar(limite=50),
        camiones=camiones,
        patentes={c.id: c.patente for c in camiones},
        ahora=datetime.now(),
        **({"resultado": None} | extra),
    )


@router.get("/combustible", response_class=HTMLResponse)
def combustible(request: Request, uow: UoW):
    return _pagina_combustible(request, uow)


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
        precio_litro=decimal_opcional(precio_litro),
        odometro_km=decimal_opcional(odometro_km),
        estacion=estacion,
        origen=OrigenDato.MANUAL,
        referencia_externa=referencia_externa,
    )
    registrar = RegistrarCargaCombustible(uow, config.tolerancia_tanque_pct)
    return ejecutar("/combustible", lambda: registrar.ejecutar(datos), "Carga registrada.")


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
        return volver("/combustible", error=str(error))
    return _pagina_combustible(request, uow, resultado=resultado, nombre_archivo=archivo.filename)
