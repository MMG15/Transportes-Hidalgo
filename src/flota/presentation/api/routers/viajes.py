from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter

from flota.application.use_cases.viajes import (
    ConsultasViajes,
    DatosInicioViaje,
    FinalizarViaje,
    IniciarViaje,
    ObtenerConsumoViaje,
)
from flota.presentation.api.dependencias import Config, UoW
from flota.presentation.api.schemas import ConsumoLeer, ViajeCrear, ViajeFinalizar, ViajeLeer

router = APIRouter(prefix="/viajes", tags=["Viajes"])


@router.post("", response_model=ViajeLeer, status_code=201)
def iniciar_viaje(datos: ViajeCrear, uow: UoW):
    viaje = IniciarViaje(uow).ejecutar(DatosInicioViaje(**datos.model_dump()))
    return ViajeLeer.model_validate(viaje)


@router.get("", response_model=list[ViajeLeer])
def listar_viajes(uow: UoW, desde: date, hasta: date, camion_id: UUID | None = None):
    inicio = datetime.combine(desde, time.min)
    fin = datetime.combine(hasta + timedelta(days=1), time.min)
    viajes = ConsultasViajes(uow).listar(inicio, fin, camion_id)
    return [ViajeLeer.model_validate(v) for v in viajes]


@router.get("/{viaje_id}", response_model=ViajeLeer)
def obtener_viaje(viaje_id: UUID, uow: UoW):
    return ViajeLeer.model_validate(ConsultasViajes(uow).obtener(viaje_id))


@router.post("/{viaje_id}/finalizar", response_model=ViajeLeer)
def finalizar_viaje(viaje_id: UUID, datos: ViajeFinalizar, uow: UoW):
    viaje = FinalizarViaje(uow).ejecutar(viaje_id, datos.fecha_llegada, datos.km_llegada)
    return ViajeLeer.model_validate(viaje)


@router.get("/{viaje_id}/consumo", response_model=ConsumoLeer)
def consumo_viaje(viaje_id: UUID, uow: UoW, config: Config):
    resumen = ObtenerConsumoViaje(uow, config.umbral_desvio_pct).ejecutar(viaje_id)
    return ConsumoLeer.model_validate(resumen)
