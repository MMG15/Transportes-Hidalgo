"""Repositorios SQL sobre SQLite: el viaje se guarda y se lee con sus tramos (agregado)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from flota.modelos import Base
from flota.shared.infrastructure.db import crear_session_factory
from flota.unidad_de_trabajo import UnidadDeTrabajoSql
from flota.viajes.domain.entidades import EstadoCarga
from tests.escenarios import SALIDA, flota_basica, iniciar_viaje, viaje_ida_y_vuelta


@pytest.fixture
def uow():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return UnidadDeTrabajoSql(crear_session_factory(engine))


def test_viaje_con_tramos_ida_y_vuelta(uow):
    flota = flota_basica(uow)
    viaje = viaje_ida_y_vuelta(uow, flota)

    with uow:
        leido = uow.viajes.obtener(viaje.id)
    assert [t.estado_carga for t in leido.tramos] == [EstadoCarga.CARGADO, EstadoCarga.VACIO]
    assert [t.km_recorridos for t in leido.tramos] == [Decimal("200.0"), Decimal("200.0")]


def test_historial_de_la_ruta(uow):
    flota = flota_basica(uow)
    for dia in range(3):
        viaje_ida_y_vuelta(uow, flota, SALIDA + timedelta(days=dia), 1000 + dia * 400)
    abierto = iniciar_viaje(uow, flota, SALIDA + timedelta(days=5), "3000")

    with uow:
        finalizados = uow.viajes.listar_finalizados_por_ruta(flota.ruta.id)
        anteriores = uow.viajes.listar_finalizados_por_ruta(
            flota.ruta.id, antes_de=SALIDA + timedelta(days=1)
        )
        en_curso = uow.viajes.buscar_en_curso(flota.camion.id)
    assert len(finalizados) == 3
    assert finalizados[0].fecha_salida > finalizados[-1].fecha_salida  # más nuevo primero
    assert len(anteriores) == 1
    assert en_curso.id == abierto.id


def test_filtros_del_listado(uow):
    flota = flota_basica(uow)
    viaje_ida_y_vuelta(uow, flota)
    desde, hasta = SALIDA - timedelta(days=1), SALIDA + timedelta(days=1)
    with uow:
        assert len(uow.viajes.listar_por_periodo(desde, hasta, ruta_id=flota.ruta.id)) == 1
        assert uow.viajes.listar_por_periodo(desde, hasta, chofer_id=flota.camion.id) == []
