"""API REST de combustible."""

from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile

from flota.combustible.application.casos_de_uso import (
    ConsultasCargas,
    DatosCarga,
    ObtenerConsumoViaje,
    RegistrarCargaCombustible,
)
from flota.combustible.domain.entidades import OrigenDato
from flota.combustible.presentation.archivos import importar_subida
from flota.combustible.presentation.esquemas import (
    CargaCrear,
    CargaLeer,
    ConsumoLeer,
    ResultadoImportacionLeer,
)
from flota.dependencias import Config, UoW

router = APIRouter(tags=["Combustible"])


@router.post("/cargas", response_model=CargaLeer, status_code=201)
def registrar_carga(datos: CargaCrear, uow: UoW):
    carga = RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(**datos.model_dump(), origen=OrigenDato.MANUAL)
    )
    return CargaLeer.model_validate(carga)


@router.get("/cargas", response_model=list[CargaLeer])
def listar_cargas(
    uow: UoW,
    camion_id: UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(100, ge=1, le=1000),
    desplazamiento: int = Query(0, ge=0),
):
    inicio = datetime.combine(desde, time.min) if desde else None
    fin = datetime.combine(hasta + timedelta(days=1), time.min) if hasta else None
    cargas = ConsultasCargas(uow).listar(camion_id, inicio, fin, limite, desplazamiento)
    return [CargaLeer.model_validate(c) for c in cargas]


@router.post("/cargas/importar", response_model=ResultadoImportacionLeer)
def importar_cargas(archivo: UploadFile, uow: UoW, origen: OrigenDato = OrigenDato.EXCEL):
    """Sube un Excel (.xlsx) o CSV (tarjeta de combustible) con cargas."""
    try:
        resultado = importar_subida(uow, archivo.file, archivo.filename or "", origen)
    except ValueError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    return ResultadoImportacionLeer.model_validate(resultado)


@router.get("/viajes/{viaje_id}/consumo", response_model=ConsumoLeer, tags=["Viajes"])
def consumo_viaje(viaje_id: UUID, uow: UoW, config: Config):
    resumen = ObtenerConsumoViaje(uow, config.umbral_desvio_pct).ejecutar(viaje_id)
    return ConsumoLeer.model_validate(resumen)
