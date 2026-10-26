"""API REST del tipo de cambio (CU-13)."""

from uuid import UUID

from fastapi import APIRouter

from flota.dependencias import UoW
from flota.monedas.application.casos_de_uso import (
    CargarCotizacion,
    ConsultasTiposCambio,
    CorregirCotizacion,
)
from flota.monedas.presentation.esquemas import CotizacionCorregir, CotizacionCrear, TipoCambioLeer
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere

router = APIRouter(
    prefix="/tipos-cambio", tags=["Monedas"], dependencies=requiere(Modulo.PEAJES_MONEDAS)
)


@router.post("", response_model=TipoCambioLeer, status_code=201)
def cargar_cotizacion(datos: CotizacionCrear, uow: UoW):
    tipo = CargarCotizacion(uow).ejecutar(
        datos.fecha, datos.cotizacion, datos.moneda_origen, datos.fuente
    )
    return TipoCambioLeer.model_validate(tipo)


@router.get("", response_model=list[TipoCambioLeer])
def listar_cotizaciones(uow: UoW, dias: int = 60):
    return [TipoCambioLeer.model_validate(t) for t in ConsultasTiposCambio(uow).recientes(dias)]


@router.put("/{tipo_cambio_id}", response_model=TipoCambioLeer)
def corregir_cotizacion(tipo_cambio_id: UUID, datos: CotizacionCorregir, uow: UoW):
    """Si la cotización ya se usó, hay que enviar `confirmar: true`. Los gastos no cambian."""
    tipo = CorregirCotizacion(uow).ejecutar(
        tipo_cambio_id, datos.cotizacion, datos.fuente, datos.confirmar
    )
    return TipoCambioLeer.model_validate(tipo)
