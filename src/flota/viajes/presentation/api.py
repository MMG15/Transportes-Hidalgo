"""API REST de rutas y viajes."""

from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter

from flota.dependencias import UoW
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere
from flota.viajes.application.casos_de_uso import (
    ActualizarRuta,
    CambiarEstadoCarga,
    ConsultasRutas,
    ConsultasViajes,
    DatosInicioViaje,
    DatosRuta,
    FinalizarViaje,
    IniciarViaje,
    RegistrarRuta,
)
from flota.viajes.presentation.esquemas import (
    CambioEstadoCarga,
    RutaCrear,
    RutaLeer,
    TramoLeer,
    ViajeCrear,
    ViajeFinalizar,
    ViajeLeer,
)

router = APIRouter(dependencies=requiere(Modulo.VIAJES))


# ---------- Rutas ----------
@router.post("/rutas", response_model=RutaLeer, status_code=201, tags=["Rutas"])
def crear_ruta(datos: RutaCrear, uow: UoW):
    return RutaLeer.model_validate(RegistrarRuta(uow).ejecutar(DatosRuta(**datos.model_dump())))


@router.get("/rutas", response_model=list[RutaLeer], tags=["Rutas"])
def listar_rutas(uow: UoW, solo_activas: bool = False):
    return [RutaLeer.model_validate(r) for r in ConsultasRutas(uow).listar(solo_activas)]


@router.put("/rutas/{ruta_id}", response_model=RutaLeer, tags=["Rutas"])
def actualizar_ruta(ruta_id: UUID, datos: RutaCrear, uow: UoW):
    ruta = ActualizarRuta(uow).ejecutar(ruta_id, DatosRuta(**datos.model_dump()))
    return RutaLeer.model_validate(ruta)


# ---------- Viajes ----------
@router.post("/viajes", response_model=ViajeLeer, status_code=201, tags=["Viajes"])
def iniciar_viaje(datos: ViajeCrear, uow: UoW):
    viaje = IniciarViaje(uow).ejecutar(DatosInicioViaje(**datos.model_dump()))
    return ViajeLeer.model_validate(viaje)


@router.get("/viajes", response_model=list[ViajeLeer], tags=["Viajes"])
def listar_viajes(
    uow: UoW,
    desde: date,
    hasta: date,
    camion_id: UUID | None = None,
    chofer_id: UUID | None = None,
    ruta_id: UUID | None = None,
):
    inicio = datetime.combine(desde, time.min)
    fin = datetime.combine(hasta + timedelta(days=1), time.min)
    viajes = ConsultasViajes(uow).listar(inicio, fin, camion_id, chofer_id, ruta_id)
    return [ViajeLeer.model_validate(v) for v in viajes]


@router.get("/viajes/{viaje_id}", response_model=ViajeLeer, tags=["Viajes"])
def obtener_viaje(viaje_id: UUID, uow: UoW):
    return ViajeLeer.model_validate(ConsultasViajes(uow).obtener(viaje_id))


@router.post("/viajes/{viaje_id}/tramos", response_model=TramoLeer, tags=["Viajes"])
def cambiar_estado_carga(viaje_id: UUID, datos: CambioEstadoCarga, uow: UoW):
    """Cierra el tramo actual y abre otro: por ejemplo, al descargar empieza el regreso vacío."""
    tramo = CambiarEstadoCarga(uow).ejecutar(viaje_id, datos.fecha, datos.km, datos.estado_carga)
    return TramoLeer.model_validate(tramo)


@router.post("/viajes/{viaje_id}/finalizar", response_model=ViajeLeer, tags=["Viajes"])
def finalizar_viaje(viaje_id: UUID, datos: ViajeFinalizar, uow: UoW):
    viaje = FinalizarViaje(uow).ejecutar(viaje_id, datos.fecha_llegada, datos.km_llegada)
    return ViajeLeer.model_validate(viaje)
