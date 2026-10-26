"""Fixtures compartidas: pytest las encuentra solas en cualquier conftest.py."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from flota.dependencias import obtener_uow
from flota.main import create_app
from flota.modelos import Base
from flota.shared.infrastructure.db import crear_session_factory
from flota.unidad_de_trabajo import UnidadDeTrabajoSql


@pytest.fixture
def cliente():
    """App completa sobre SQLite en memoria (cada test arranca con la base vacía)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = crear_session_factory(engine)
    app = create_app()
    app.dependency_overrides[obtener_uow] = lambda: UnidadDeTrabajoSql(factory)
    with TestClient(app) as c:
        yield c
