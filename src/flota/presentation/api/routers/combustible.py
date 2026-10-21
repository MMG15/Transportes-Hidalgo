import shutil
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile

from flota.application.use_cases.combustible import (
    ConsultasCargas,
    DatosCarga,
    RegistrarCargaCombustible,
)
from flota.application.use_cases.importacion import ImportarCargas
from flota.domain.entities import OrigenDato
from flota.infrastructure.importacion import lector_para_archivo
from flota.presentation.api.dependencias import Config, UoW
from flota.presentation.api.schemas import CargaCrear, CargaLeer, ResultadoImportacionLeer

router = APIRouter(prefix="/cargas", tags=["Combustible"])


@router.post("", response_model=CargaLeer, status_code=201)
def registrar_carga(datos: CargaCrear, uow: UoW, config: Config):
    carga = RegistrarCargaCombustible(uow, config.tolerancia_tanque_pct).ejecutar(
        DatosCarga(**datos.model_dump(), origen=OrigenDato.MANUAL)
    )
    return CargaLeer.model_validate(carga)


@router.get("", response_model=list[CargaLeer])
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


@router.post("/importar", response_model=ResultadoImportacionLeer)
def importar_cargas(
    archivo: UploadFile, uow: UoW, config: Config, origen: OrigenDato = OrigenDato.EXCEL
):
    """Sube un Excel (.xlsx) o CSV (tarjeta de combustible) con cargas."""
    extension = Path(archivo.filename or "").suffix.lower()
    try:
        lector = lector_para_archivo(Path(f"archivo{extension}"))
    except ValueError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error

    # Se guarda en un archivo temporal porque los lectores trabajan con rutas.
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / f"importacion{extension}"
        with ruta.open("wb") as destino:
            shutil.copyfileobj(archivo.file, destino)
        resultado = ImportarCargas(uow, lector, origen, config.tolerancia_tanque_pct).ejecutar(ruta)
    return ResultadoImportacionLeer.model_validate(resultado)
