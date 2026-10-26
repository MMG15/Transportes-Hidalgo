"""Fixtures compartidas: pytest las encuentra solas en cualquier conftest.py."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from flota import bootstrap
from flota.dependencias import obtener_almacen, obtener_uow
from flota.main import create_app
from flota.modelos import Base
from flota.shared.infrastructure.archivos import AlmacenEnDisco
from flota.shared.infrastructure.db import crear_session_factory
from flota.unidad_de_trabajo import UnidadDeTrabajoSql
from flota.usuarios.application.casos_de_uso import CrearUsuario, DatosUsuario
from flota.usuarios.domain.entidades import Rol

CONTRASENA = "clave-de-prueba"


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
def cliente_anonimo(crear_uow, tmp_path):
    """App completa (API + panel) sobre la base de prueba, sin sesión iniciada.
    Los comprobantes se guardan en una carpeta temporal que pytest borra sola."""
    app = create_app()
    app.dependency_overrides[obtener_uow] = crear_uow
    app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(tmp_path / "archivos")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def entrar(cliente_anonimo, crear_uow):
    """`entrar(Rol.GERENCIA)` crea un usuario con ese rol e inicia sesión con él."""

    def iniciar_sesion(rol: Rol, email: str | None = None):
        email = email or f"{rol.value.lower()}@prueba.com"
        CrearUsuario(crear_uow(), bootstrap.crear_hasher()).ejecutar(
            DatosUsuario(f"Usuario {rol.value}", email, rol), CONTRASENA
        )
        cliente_anonimo.post("/logout")
        respuesta = cliente_anonimo.post(
            "/login", data={"email": email, "contrasena": CONTRASENA}, follow_redirects=False
        )
        assert respuesta.status_code == 303, respuesta.text
        return cliente_anonimo

    return iniciar_sesion


@pytest.fixture
def cliente(entrar):
    """Cliente con sesión de Administrador de sistema (puede todo)."""
    return entrar(Rol.ADMIN_SISTEMA, "admin@prueba.com")
