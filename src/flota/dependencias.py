"""Inyección de dependencias de FastAPI. En los tests se reemplazan con `dependency_overrides`."""

from typing import Annotated

from fastapi import Depends

from flota import bootstrap
from flota.reportes.application.puertos import GeneradorReporte
from flota.shared.application.archivos import AlmacenArchivos
from flota.shared.infrastructure.config import Settings, get_settings
from flota.unidad_de_trabajo import UnidadDeTrabajoSistema
from flota.usuarios.application.puertos import HasherContrasenas


def obtener_uow() -> UnidadDeTrabajoSistema:
    return bootstrap.crear_uow()


def obtener_generador() -> GeneradorReporte:
    return bootstrap.crear_generador_reporte()


UoW = Annotated[UnidadDeTrabajoSistema, Depends(obtener_uow)]
Config = Annotated[Settings, Depends(get_settings)]
Generador = Annotated[GeneradorReporte, Depends(obtener_generador)]


def obtener_almacen() -> AlmacenArchivos:
    return bootstrap.crear_almacen()


Almacen = Annotated[AlmacenArchivos, Depends(obtener_almacen)]


def obtener_hasher() -> HasherContrasenas:
    return bootstrap.crear_hasher()


Hasher = Annotated[HasherContrasenas, Depends(obtener_hasher)]
