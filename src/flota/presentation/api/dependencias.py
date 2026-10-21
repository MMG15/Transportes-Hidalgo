"""Inyección de dependencias de FastAPI. En los tests se reemplazan con `dependency_overrides`."""

from typing import Annotated

from fastapi import Depends

from flota import bootstrap
from flota.application.ports import GeneradorReporte, UnidadDeTrabajo
from flota.infrastructure.config import Settings, get_settings


def obtener_uow() -> UnidadDeTrabajo:
    return bootstrap.crear_uow()


def obtener_generador() -> GeneradorReporte:
    return bootstrap.crear_generador_reporte()


UoW = Annotated[UnidadDeTrabajo, Depends(obtener_uow)]
Config = Annotated[Settings, Depends(get_settings)]
Generador = Annotated[GeneradorReporte, Depends(obtener_generador)]
