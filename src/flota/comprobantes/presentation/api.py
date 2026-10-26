"""API REST de comprobantes (RF-02, RF-07; CU-02)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from flota.combustible.application.casos_de_uso import DatosCarga
from flota.combustible.presentation.esquemas import CargaLeer
from flota.comprobantes.application.casos_de_uso import (
    ArchivoRecibido,
    ConsultasComprobantes,
    DescartarComprobante,
    LeerArchivoComprobante,
    RecibirComprobante,
    ValidarComprobanteCombustible,
)
from flota.comprobantes.domain.entidades import (
    CanalIngreso,
    EstadoComprobante,
    TipoComprobante,
)
from flota.dependencias import Almacen, UoW
from flota.shared.domain.dinero import Moneda
from flota.shared.presentation.esquemas import Esquema, Numero
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere

router = APIRouter(
    prefix="/comprobantes", tags=["Comprobantes"], dependencies=requiere(Modulo.COMBUSTIBLE)
)


class ComprobanteLeer(Esquema):
    id: UUID
    tipo: TipoComprobante
    canal: CanalIngreso
    estado: EstadoComprobante
    tipo_mime: str
    recibido_en: datetime
    chofer_id: UUID | None
    camion_id: UUID | None
    datos_extraidos: dict | None
    confianza: Numero | None
    problemas: list[str]
    registro_id: UUID | None
    motivo_descarte: str | None


class ValidacionCarga(BaseModel):
    camion_id: UUID
    fecha: datetime
    litros: Decimal = Field(gt=0)
    monto: Decimal | None = Field(default=None, ge=0)
    moneda: Moneda = Moneda.ARS
    odometro_km: Decimal | None = Field(default=None, ge=0)
    estacion: str | None = None
    referencia_externa: str | None = None


class Descarte(BaseModel):
    motivo: str = Field(min_length=1)


@router.post("", response_model=ComprobanteLeer, status_code=201)
async def subir(uow: UoW, almacen: Almacen, archivo: UploadFile):
    """Foto (JPG, PNG, WEBP) o PDF de un ticket de combustible, hasta 10 MB."""
    recibido = ArchivoRecibido(await archivo.read(), archivo.content_type or "")
    return ComprobanteLeer.model_validate(RecibirComprobante(uow, almacen).ejecutar(recibido))


@router.get("", response_model=list[ComprobanteLeer])
def pendientes(uow: UoW):
    return [ComprobanteLeer.model_validate(c) for c in ConsultasComprobantes(uow).pendientes()]


@router.get("/{comprobante_id}", response_model=ComprobanteLeer)
def obtener(comprobante_id: UUID, uow: UoW):
    return ComprobanteLeer.model_validate(ConsultasComprobantes(uow).obtener(comprobante_id))


@router.get("/{comprobante_id}/archivo", response_class=Response)
def archivo(comprobante_id: UUID, uow: UoW, almacen: Almacen):
    contenido, tipo = LeerArchivoComprobante(uow, almacen).ejecutar(comprobante_id)
    return Response(contenido, media_type=tipo, headers={"X-Content-Type-Options": "nosniff"})


@router.post("/{comprobante_id}/validar", response_model=CargaLeer, status_code=201)
def validar(comprobante_id: UUID, datos: ValidacionCarga, uow: UoW):
    """CU-02: registra la carga a partir del comprobante."""
    carga = ValidarComprobanteCombustible(uow).ejecutar(
        comprobante_id, DatosCarga(**datos.model_dump())
    )
    return CargaLeer.model_validate(carga)


@router.post("/{comprobante_id}/descartar", response_model=ComprobanteLeer)
def descartar(comprobante_id: UUID, datos: Descarte, uow: UoW):
    comprobante = DescartarComprobante(uow).ejecutar(comprobante_id, datos.motivo)
    return ComprobanteLeer.model_validate(comprobante)
