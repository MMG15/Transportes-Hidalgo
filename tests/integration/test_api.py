"""Prueba de punta a punta: API -> casos de uso -> SQLAlchemy (SQLite en memoria) -> Excel."""

from io import BytesIO

from openpyxl import Workbook, load_workbook

API = "/api/v1"


def crear(cliente, ruta, datos):
    respuesta = cliente.post(f"{API}/{ruta}", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


CAMION = {
    "patente": "AB123CD",
    "marca": "Scania",
    "modelo": "R450",
    "capacidad_tanque_litros": 600,
    "consumo_referencia_l100km": 38,
}


def test_flujo_completo(cliente):
    camion = crear(cliente, "camiones", CAMION | {"anio": 2019})
    chofer = crear(cliente, "choferes", {"nombre": "Juan Pérez", "dni": "30123456"})
    productor = crear(cliente, "clientes", {"razon_social": "Cliente SA"})
    cal = crear(cliente, "productos", {"nombre": "Cal viva"})
    ruta = crear(
        cliente,
        "rutas",
        {
            "origen": "Albardón",
            "destino": "Los Andes",
            "pais": "CL",
            "km_estimados": 200,
            "ref_l100_cargado": 45,
            "ref_l100_vacio": 30,
        },
    )
    assert ruta["nombre"] == "Albardón → Los Andes"

    viaje = crear(
        cliente,
        "viajes",
        {
            "camion_id": camion["id"],
            "chofer_id": chofer["id"],
            "ruta_id": ruta["id"],
            "cliente_id": productor["id"],
            "producto_id": cal["id"],
            "cantidad": 28,
            "fecha_salida": "2026-10-20T08:00:00",
            "km_salida": 125000,
        },
    )
    assert viaje["estado"] == "en_curso"
    assert [t["estado_carga"] for t in viaje["tramos"]] == ["cargado"]

    carga = crear(
        cliente,
        "cargas",
        {
            "camion_id": camion["id"],
            "fecha": "2026-10-20T10:00:00",
            "litros": 100,
            "precio_litro": 1450,
            "referencia_externa": "T-1",
        },
    )
    assert carga["viaje_id"] == viaje["id"]  # asignada automáticamente
    assert carga["costo_ars"] == 145000.0
    assert carga["importe"]["original"] == {"monto": 145000.0, "moneda": "ARS"}

    # Duplicado -> 409
    repetida = cliente.post(
        f"{API}/cargas",
        json={
            "camion_id": camion["id"],
            "fecha": "2026-10-20T10:00:00",
            "litros": 100,
            "referencia_externa": "T-1",
        },
    )
    assert repetida.status_code == 409

    # Descarga: empieza el regreso vacío
    tramo = cliente.post(
        f"{API}/viajes/{viaje['id']}/tramos",
        json={"fecha": "2026-10-20T13:00:00", "km": 125200, "estado_carga": "vacio"},
    )
    assert tramo.status_code == 200, tramo.text
    assert tramo.json()["estado_carga"] == "vacio"

    finalizado = cliente.post(
        f"{API}/viajes/{viaje['id']}/finalizar",
        json={"fecha_llegada": "2026-10-20T18:00:00", "km_llegada": 125400},
    )
    assert finalizado.status_code == 200
    assert finalizado.json()["km_recorridos"] == 400.0
    assert [t["km_recorridos"] for t in finalizado.json()["tramos"]] == [200.0, 200.0]

    # Importación desde Excel durante el regreso: va al tramo vacío
    libro = Workbook()
    libro.active.append(["Fecha", "Patente", "Litros", "Ticket"])
    libro.active.append(["20/10/2026 15:00", "ab123cd", 70, "T-2"])
    libro.active.append(["20/10/2026 15:00", "ZZ000ZZ", 20, "T-3"])
    buffer = BytesIO()
    libro.save(buffer)
    importacion = cliente.post(
        f"{API}/cargas/importar",
        files={"archivo": ("cargas.xlsx", buffer.getvalue())},
    ).json()
    assert importacion["importadas"] == 1
    assert len(importacion["errores"]) == 1

    consumo = cliente.get(f"{API}/viajes/{viaje['id']}/consumo").json()
    ida, vuelta = consumo["tramos"]
    assert (ida["consumo_l100km"], ida["referencia"]["fuente"]) == (50.0, "ruta")
    assert ida["alerta"] is False  # 50 contra 45: +11,1 %, dentro del umbral del 15 %
    assert (vuelta["consumo_l100km"], vuelta["alerta"]) == (35.0, True)  # 35 contra 30: +16,7 %
    assert consumo["alerta"] is True

    # El bus de eventos generó la alerta del tramo vacío al finalizar el viaje (RF-16)
    (alerta,) = cliente.get(f"{API}/alertas", params={"estado": "abierta"}).json()
    assert alerta["tipo"] == "desvio_consumo" and alerta["viaje_id"] == viaje["id"]
    assert alerta["valor_detectado"] == 35.0 and alerta["valor_referencia"] == 30.0


def test_reporte_y_excel(cliente):
    test_flujo_completo(cliente)
    params = {"desde": "2026-10-01", "hasta": "2026-10-31"}

    reporte = cliente.get(f"{API}/reportes/consumo", params=params).json()
    fila = reporte["filas"][0]
    assert fila["litros"] == 170.0
    assert (fila["ruta"], fila["pais"]) == ("Albardón → Los Andes", "CL")
    assert reporte["resumen_por_ruta"][0]["consumo_vacio_l100km"] == 35.0
    vacio = cliente.get(f"{API}/reportes/consumo", params=params | {"pais": "AR"}).json()
    assert vacio["filas"] == []

    excel = cliente.get(f"{API}/reportes/consumo.xlsx", params=params)
    assert excel.status_code == 200
    libro = load_workbook(BytesIO(excel.content))
    assert libro.sheetnames == ["Resumen por camión", "Consumo por viaje", "Por chofer", "Por ruta"]
    resumen = libro["Resumen por camión"]
    assert len(resumen._images) == 1  # logo de la empresa
    assert resumen["A10"].value == "AB123CD"  # la tabla empieza debajo de la portada
    assert libro["Consumo por viaje"]["D2"].value == "AB123CD"
    assert libro["Por ruta"]["A2"].value == "Albardón → Los Andes"


def test_listados_del_catalogo(cliente):
    """Regresión: los listados ordenados por columna fallaban (bug de la sesión 1)."""
    for ruta, datos in [
        ("camiones", CAMION),
        ("choferes", {"nombre": "Juan Pérez", "dni": "30123456"}),
        ("clientes", {"razon_social": "Cliente SA"}),
        ("productos", {"nombre": "Cal viva"}),
        ("rutas", {"origen": "A", "destino": "B"}),
    ]:
        crear(cliente, ruta, datos)
        respuesta = cliente.get(f"{API}/{ruta}")
        assert respuesta.status_code == 200, ruta
        assert len(respuesta.json()) == 1


def test_editar_camion(cliente):
    camion = crear(cliente, "camiones", CAMION)
    cambios = {
        "marca": "Scania",
        "modelo": "R500",
        "capacidad_tanque_litros": 650,
        "consumo_referencia_l100km": 39,
        "anio": 2020,
        "activo": False,
    }
    respuesta = cliente.put(f"{API}/camiones/{camion['id']}", json=cambios)
    assert respuesta.status_code == 200
    assert (respuesta.json()["modelo"], respuesta.json()["activo"]) == ("R500", False)


def test_recurso_inexistente_devuelve_404(cliente):
    respuesta = cliente.get(f"{API}/camiones/00000000-0000-0000-0000-000000000000")
    assert respuesta.status_code == 404
