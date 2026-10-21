"""Prueba de punta a punta: API -> casos de uso -> SQLAlchemy (SQLite en memoria) -> Excel."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from flota.infrastructure.db.models import Base
from flota.infrastructure.db.session import crear_session_factory
from flota.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSql
from flota.presentation.api.app import create_app
from flota.presentation.api.dependencias import obtener_uow

API = "/api/v1"


@pytest.fixture
def cliente():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = crear_session_factory(engine)
    app = create_app()
    app.dependency_overrides[obtener_uow] = lambda: UnidadDeTrabajoSql(factory)
    with TestClient(app) as c:
        yield c


def crear(cliente, ruta, datos):
    respuesta = cliente.post(f"{API}/{ruta}", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_flujo_completo(cliente):
    camion = crear(
        cliente,
        "camiones",
        {
            "patente": "AB123CD",
            "marca": "Scania",
            "modelo": "R450",
            "capacidad_tanque_litros": 600,
            "consumo_referencia_l100km": 38,
        },
    )
    chofer = crear(cliente, "choferes", {"nombre": "Juan Pérez", "dni": "30123456"})
    productor = crear(cliente, "clientes", {"razon_social": "Agropecuaria San José"})
    cal = crear(cliente, "productos", {"nombre": "Cal viva"})

    viaje = crear(
        cliente,
        "viajes",
        {
            "camion_id": camion["id"],
            "chofer_id": chofer["id"],
            "cliente_id": productor["id"],
            "producto_id": cal["id"],
            "origen": "Planta",
            "destino": "Campo",
            "cantidad": 28,
            "fecha_salida": "2026-10-20T08:00:00",
            "km_salida": 125000,
        },
    )
    assert viaje["estado"] == "en_curso"

    carga = crear(
        cliente,
        "cargas",
        {
            "camion_id": camion["id"],
            "fecha": "2026-10-20T12:00:00",
            "litros": 180,
            "precio_litro": 1450,
            "referencia_externa": "T-1",
        },
    )
    assert carga["viaje_id"] == viaje["id"]  # asignada automáticamente
    assert carga["importe"] == 261000.0

    # Duplicado -> 409
    repetida = cliente.post(
        f"{API}/cargas",
        json={
            "camion_id": camion["id"],
            "fecha": "2026-10-20T12:00:00",
            "litros": 180,
            "referencia_externa": "T-1",
        },
    )
    assert repetida.status_code == 409

    finalizado = cliente.post(
        f"{API}/viajes/{viaje['id']}/finalizar",
        json={
            "fecha_llegada": "2026-10-20T17:00:00",
            "km_llegada": 125400,
        },
    )
    assert finalizado.status_code == 200
    assert finalizado.json()["km_recorridos"] == 400.0

    consumo = cliente.get(f"{API}/viajes/{viaje['id']}/consumo").json()
    assert consumo["consumo_l100km"] == 45.0  # 180 / 400 * 100
    assert consumo["alerta"] is True  # 18,4 % sobre 38 L/100km

    # Importación desde Excel: se asigna al viaje por fecha
    libro = Workbook()
    libro.active.append(["Fecha", "Patente", "Litros", "Ticket"])
    libro.active.append(["20/10/2026 15:00", "ab123cd", 20, "T-2"])
    libro.active.append(["20/10/2026 15:00", "ZZ000ZZ", 20, "T-3"])
    buffer = BytesIO()
    libro.save(buffer)
    importacion = cliente.post(
        f"{API}/cargas/importar",
        files={"archivo": ("cargas.xlsx", buffer.getvalue())},
    ).json()
    assert importacion["importadas"] == 1
    assert len(importacion["errores"]) == 1

    reporte = cliente.get(
        f"{API}/reportes/consumo",
        params={
            "desde": "2026-10-01",
            "hasta": "2026-10-31",
        },
    ).json()
    assert reporte["filas"][0]["litros"] == 200.0
    assert reporte["resumen_por_camion"][0]["consumo_promedio_l100km"] == 50.0

    excel = cliente.get(
        f"{API}/reportes/consumo.xlsx",
        params={
            "desde": "2026-10-01",
            "hasta": "2026-10-31",
        },
    )
    assert excel.status_code == 200
    hoja = load_workbook(BytesIO(excel.content)).active
    assert hoja["D2"].value == "AB123CD"


def test_recurso_inexistente_devuelve_404(cliente):
    respuesta = cliente.get(f"{API}/camiones/00000000-0000-0000-0000-000000000000")
    assert respuesta.status_code == 404
