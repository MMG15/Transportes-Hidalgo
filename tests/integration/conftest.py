"""Fixtures compartidas: pytest las encuentra solas en cualquier conftest.py."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from flota import bootstrap
from flota.dependencias import obtener_uow
from flota.main import create_app
from flota.modelos import Base
from flota.shared.infrastructure.db import crear_session_factory
from flota.unidad_de_trabajo import UnidadDeTrabajoSql


@pytest.fixture
def crear_uow():
    """Fábrica de unidades de trabajo sobre SQLite en memoria (cada test arranca vacío),
    con el bus de eventos real: las alertas se generan igual que en el sistema."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = crear_session_factory(engine)

    def crear():
        return UnidadDeTrabajoSql(factory, bus)

    bus = bootstrap.crear_bus(crear)
    return crear


@pytest.fixture
def cliente(crear_uow):
    """App completa (API + panel) sobre la base de prueba."""
    app = create_app()
    app.dependency_overrides[obtener_uow] = crear_uow
    with TestClient(app) as c:
        yield c
