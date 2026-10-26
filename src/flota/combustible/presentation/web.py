"""Páginas del panel: Combustible."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from flota.catalogo.application.casos_de_uso import ConsultasCatalogo
from flota.combustible.application.casos_de_uso import (
    AnularCarga,
    ConsultasCargas,
    DatosCarga,
    RegistrarCargaCombustible,
)
from flota.combustible.domain.entidades import OrigenDato
from flota.combustible.presentation.archivos import importar_subida
from flota.dependencias import UoW
from flota.shared.domain.dinero import Moneda
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere
from flota.web.plantillas import (
    FechaHora,
    Id,
    Numero,
    Texto,
    TextoOpcional,
    decimal_opcional,
    ejecutar,
    pagina,
    volver,
)

router = APIRouter(include_in_schema=False, dependencies=requiere(Modulo.COMBUSTIBLE))


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
    camion_id: Id,
    fecha: FechaHora,
    litros: Numero,
    monto: TextoOpcional = None,
    precio_litro: TextoOpcional = None,
    moneda: Annotated[Moneda, Form()] = Moneda.ARS,
    odometro_km: TextoOpcional = None,
    estacion: TextoOpcional = None,
    referencia_externa: TextoOpcional = None,
):
    datos = DatosCarga(
        camion_id=camion_id,
        fecha=fecha,
        litros=litros,
        monto=decimal_opcional(monto),
        precio_litro=decimal_opcional(precio_litro),
        moneda=moneda,
        odometro_km=decimal_opcional(odometro_km),
        estacion=estacion,
        origen=OrigenDato.MANUAL,
        referencia_externa=referencia_externa,
    )
    registrar = RegistrarCargaCombustible(uow)
    return ejecutar("/combustible", lambda: registrar.ejecutar(datos), "Carga registrada.")


@router.post("/combustible/{carga_id}/anular")
def anular_carga(carga_id: UUID, uow: UoW, motivo: Texto):
    return ejecutar(
        "/combustible", lambda: AnularCarga(uow).ejecutar(carga_id, motivo), "Carga anulada."
    )


@router.post("/combustible/importar", response_class=HTMLResponse)
def importar(
    request: Request,
    uow: UoW,
    archivo: UploadFile,
    origen: Annotated[OrigenDato, Form()] = OrigenDato.EXCEL,
):
    try:
        resultado = importar_subida(uow, archivo.file, archivo.filename or "", origen)
    except ValueError as error:
        return volver("/combustible", error=str(error))
    return _pagina_combustible(request, uow, resultado=resultado, nombre_archivo=archivo.filename)
