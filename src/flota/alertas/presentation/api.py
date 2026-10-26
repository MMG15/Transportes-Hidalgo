"""API REST de alertas (CU-06)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from flota.alertas.application.casos_de_uso import ConsultasAlertas, ResolverAlerta
from flota.alertas.domain.entidades import EstadoAlerta
from flota.alertas.presentation.esquemas import AlertaLeer, AlertaResolver
from flota.dependencias import UoW
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere

router = APIRouter(prefix="/alertas", tags=["Alertas"], dependencies=requiere(Modulo.ALERTAS))


@router.get("", response_model=list[AlertaLeer])
def listar_alertas(uow: UoW, estado: Annotated[list[EstadoAlerta] | None, Query()] = None):
    """Sin filtro devuelve todas; por ejemplo `?estado=abierta&estado=en_analisis`."""
    return [AlertaLeer.model_validate(a) for a in ConsultasAlertas(uow).listar(estado)]


@router.get("/{alerta_id}", response_model=AlertaLeer)
def obtener_alerta(alerta_id: UUID, uow: UoW):
    return AlertaLeer.model_validate(ConsultasAlertas(uow).obtener(alerta_id))


@router.post("/{alerta_id}/resolver", response_model=AlertaLeer)
def resolver_alerta(alerta_id: UUID, datos: AlertaResolver, uow: UoW):
    """`en_analisis` (falta información), `justificar` o `confirmar` (se escala a Gerencia)."""
    alerta = ResolverAlerta(uow).ejecutar(alerta_id, datos.accion, datos.comentario)
    return AlertaLeer.model_validate(alerta)
