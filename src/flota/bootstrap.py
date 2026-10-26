"""Raíz de composición: el ÚNICO lugar donde se eligen las implementaciones concretas.

API y CLI piden sus dependencias acá. Para cambiar PostgreSQL por otra cosa, o Excel por
Google Sheets, se toca sólo este archivo.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from flota import marca
from flota.reportes.application.puertos import GeneradorReporte
from flota.reportes.infrastructure.excel import GeneradorReporteExcel
from flota.shared.infrastructure.db import crear_engine, crear_session_factory
from flota.unidad_de_trabajo import UnidadDeTrabajoSistema, UnidadDeTrabajoSql


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return crear_session_factory(crear_engine())


def crear_uow() -> UnidadDeTrabajoSistema:
    return UnidadDeTrabajoSql(_session_factory())


def crear_generador_reporte() -> GeneradorReporte:
    return GeneradorReporteExcel(logo=marca.LOGO)
