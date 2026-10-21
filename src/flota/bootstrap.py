"""Raíz de composición: el ÚNICO lugar donde se eligen las implementaciones concretas.

API y CLI piden sus dependencias acá. Para cambiar PostgreSQL por otra cosa, o Excel por
Google Sheets, se toca sólo este archivo.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from flota.application.ports import GeneradorReporte, UnidadDeTrabajo
from flota.infrastructure.db.session import crear_engine, crear_session_factory
from flota.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSql
from flota.infrastructure.excel.generador_excel import GeneradorReporteExcel


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return crear_session_factory(crear_engine())


def crear_uow() -> UnidadDeTrabajo:
    return UnidadDeTrabajoSql(_session_factory())


def crear_generador_reporte() -> GeneradorReporte:
    return GeneradorReporteExcel()
