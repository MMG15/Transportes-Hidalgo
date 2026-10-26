"""Páginas del panel: tickets (comprobantes) pendientes y su validación (CU-02)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from flota.catalogo.application.casos_de_uso import ConsultasCatalogo
from flota.combustible.application.casos_de_uso import DatosCarga
from flota.comprobantes.application.casos_de_uso import (
    ArchivoRecibido,
    ConsultasComprobantes,
    DescartarComprobante,
    LeerArchivoComprobante,
    RecibirComprobante,
    ValidarComprobanteCombustible,
)
from flota.dependencias import Almacen, UoW
from flota.shared.domain.dinero import Moneda
from flota.shared.domain.errores import ErrorDominio
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


@router.get("/comprobantes", response_class=HTMLResponse)
def pendientes(request: Request, uow: UoW):
    camiones = ConsultasCatalogo(uow).listar_camiones(1000)
    return pagina(
        request,
        "comprobantes.html",
        "/comprobantes",
        comprobantes=ConsultasComprobantes(uow).pendientes(),
        patentes={c.id: c.patente for c in camiones},
    )


@router.post("/comprobantes")
async def subir(uow: UoW, almacen: Almacen, archivo: UploadFile):
    """RF-02: Administración sube la foto o el PDF de un ticket."""
    recibido = ArchivoRecibido(await archivo.read(), archivo.content_type or "")
    try:
        comprobante = RecibirComprobante(uow, almacen).ejecutar(recibido)
    except ErrorDominio as error:
        return volver("/comprobantes", error=str(error))
    return RedirectResponse(f"/comprobantes/{comprobante.id}", status_code=303)


@router.get("/comprobantes/{comprobante_id}", response_class=HTMLResponse)
def detalle(request: Request, comprobante_id: UUID, uow: UoW):
    comprobante = ConsultasComprobantes(uow).obtener(comprobante_id)
    datos = comprobante.datos_extraidos or {}
    return pagina(
        request,
        "comprobante.html",
        "/comprobantes",
        c=comprobante,
        datos=datos,
        camiones=[c for c in ConsultasCatalogo(uow).listar_camiones(1000) if c.activo],
        ahora=datetime.now(),
    )


@router.get("/comprobantes/{comprobante_id}/archivo")
def archivo(comprobante_id: UUID, uow: UoW, almacen: Almacen):
    """RF-07: la imagen original del ticket."""
    contenido, tipo = LeerArchivoComprobante(uow, almacen).ejecutar(comprobante_id)
    return Response(
        contenido,
        media_type=tipo,
        # inline: se muestra en el navegador; nosniff: no "adivinar" otro tipo de archivo.
        headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/comprobantes/{comprobante_id}/validar")
def validar(
    comprobante_id: UUID,
    uow: UoW,
    camion_id: Id,
    fecha: FechaHora,
    litros: Numero,
    monto: TextoOpcional = None,
    moneda: Annotated[Moneda, Form()] = Moneda.ARS,
    odometro_km: TextoOpcional = None,
    estacion: TextoOpcional = None,
    referencia_externa: TextoOpcional = None,
):
    """CU-02 pasos 3 a 5: confirma o corrige los datos y registra la carga."""
    datos = DatosCarga(
        camion_id=camion_id,
        fecha=fecha,
        litros=litros,
        monto=decimal_opcional(monto),
        moneda=moneda,
        odometro_km=decimal_opcional(odometro_km),
        estacion=estacion,
        referencia_externa=referencia_externa,
    )
    try:
        ValidarComprobanteCombustible(uow).ejecutar(comprobante_id, datos)
    except ErrorDominio as error:
        return volver(f"/comprobantes/{comprobante_id}", error=str(error))
    return volver("/comprobantes", ok="Ticket validado: la carga quedó registrada.")


@router.post("/comprobantes/{comprobante_id}/descartar")
def descartar(comprobante_id: UUID, uow: UoW, motivo: Texto):
    """CU-02 E1."""
    return ejecutar(
        "/comprobantes",
        lambda: DescartarComprobante(uow).ejecutar(comprobante_id, motivo),
        "Ticket descartado.",
    )
