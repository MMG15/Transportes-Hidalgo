"""Raíz de composición: el ÚNICO lugar donde se eligen las implementaciones concretas.

API, panel y consola piden sus dependencias acá. Para cambiar PostgreSQL por otra cosa, o Excel
por Google Sheets, se toca sólo este archivo.

También arma el BUS DE EVENTOS y suscribe los manejadores de cada módulo: por ejemplo, cuando
`viajes` publica `ViajeFinalizado`, `alertas` evalúa el consumo del viaje.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from flota import marca
from flota.alertas.application import manejadores as alertas
from flota.reportes.application.puertos import GeneradorReporte
from flota.reportes.infrastructure.excel import GeneradorReporteExcel
from flota.shared.application.eventos import BusEventos
from flota.shared.domain.auditoria import SISTEMA, Actor
from flota.shared.infrastructure.config import get_settings
from flota.shared.infrastructure.db import crear_engine, crear_session_factory
from flota.unidad_de_trabajo import UnidadDeTrabajoSistema, UnidadDeTrabajoSql
from flota.usuarios.application.puertos import HasherContrasenas
from flota.usuarios.infrastructure.repositorios import HasherArgon2


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return crear_session_factory(crear_engine())


def crear_bus(crear_uow) -> BusEventos:
    """Bus con los manejadores de todos los módulos. `crear_uow` arma la unidad de trabajo
    que usa cada manejador (en los tests se le pasa una sobre SQLite)."""
    config = get_settings()
    bus = BusEventos()
    alertas.suscribir(bus, crear_uow, config.umbral_desvio_pct, config.tolerancia_tanque_pct)
    return bus


@lru_cache
def _bus() -> BusEventos:
    return crear_bus(crear_uow)


def crear_uow(actor: Actor = SISTEMA) -> UnidadDeTrabajoSistema:
    """`actor`: quién opera (para la auditoría). El panel y la API lo cambian al identificar
    al usuario; la consola usa `CONSOLA`."""
    return UnidadDeTrabajoSql(_session_factory(), _bus(), actor)


def crear_hasher() -> HasherContrasenas:
    return HasherArgon2()


def crear_generador_reporte() -> GeneradorReporte:
    return GeneradorReporteExcel(logo=marca.LOGO)
