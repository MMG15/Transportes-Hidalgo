"""Panel web: páginas, formularios (Post/Redirect/Get) y marca."""

from datetime import datetime, timedelta
from io import BytesIO

from openpyxl import Workbook

from flota import marca


def enviar(cliente, ruta, datos):
    """Envía un formulario y devuelve la página a la que redirige."""
    respuesta = cliente.post(ruta, data=datos, follow_redirects=False)
    assert respuesta.status_code == 303, respuesta.text
    return cliente.get(respuesta.headers["location"])


def test_paginas_cargan_con_la_marca(cliente):
    for ruta in ("/", "/viajes", "/combustible", "/reportes", "/catalogo"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 200, ruta
        assert "/static/img/logo-hidalgo.png" in respuesta.text
        assert f"--azul: {marca.COLORES['azul']}" in respuesta.text
        assert f"--naranja: {marca.COLORES['naranja']}" in respuesta.text


def test_recursos_estaticos(cliente):
    assert cliente.get("/static/css/hidalgo.css").status_code == 200
    logo = cliente.get("/static/img/logo-hidalgo.png")
    assert logo.status_code == 200 and logo.headers["content-type"] == "image/png"
    assert cliente.get("/favicon.ico").status_code == 200
    assert "favicon.ico" in cliente.get("/docs").text


def test_flujo_completo_desde_el_panel(cliente):
    pagina = enviar(
        cliente,
        "/catalogo/camiones",
        {
            "patente": "AB123CD",
            "marca": "Scania",
            "modelo": "R450",
            "capacidad_tanque_litros": "600",
            "consumo_referencia_l100km": "38",
        },
    )
    assert "Camión AB123CD registrado" in pagina.text
    enviar(cliente, "/catalogo/choferes", {"nombre": "Juan Pérez", "dni": "30123456"})
    enviar(cliente, "/catalogo/clientes", {"razon_social": "Agropecuaria San José", "cuit": ""})
    enviar(cliente, "/catalogo/productos", {"nombre": "Cal viva", "unidad": "tn"})

    ids = {
        nombre: cliente.get(f"/api/v1/{nombre}").json()[0]["id"]
        for nombre in ("camiones", "choferes", "clientes", "productos")
    }
    salida = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=6)
    pagina = enviar(
        cliente,
        "/viajes",
        {
            "camion_id": ids["camiones"],
            "chofer_id": ids["choferes"],
            "cliente_id": ids["clientes"],
            "producto_id": ids["productos"],
            "origen": "Planta",
            "destino": "Campo",
            "cantidad": "28",
            "fecha_salida": salida.strftime("%Y-%m-%dT%H:%M"),
            "km_salida": "1000",
        },
    )
    assert "Viaje iniciado" in pagina.text and "En curso" in pagina.text

    # Carga manual con campos opcionales vacíos
    pagina = enviar(
        cliente,
        "/combustible",
        {
            "camion_id": ids["camiones"],
            "fecha": (salida + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "litros": "170",
            "precio_litro": "",
            "odometro_km": "",
            "estacion": "",
            "referencia_externa": "",
        },
    )
    assert "Carga registrada" in pagina.text and "Asignada" in pagina.text

    viaje_id = cliente.get(
        "/api/v1/viajes", params={"desde": salida.date(), "hasta": salida.date()}
    ).json()[0]["id"]
    pagina = enviar(
        cliente,
        f"/viajes/{viaje_id}/finalizar",
        {
            "fecha_llegada": (salida + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M"),
            "km_llegada": "1400",
        },
    )
    assert "Viaje finalizado" in pagina.text

    tablero = cliente.get("/").text
    assert "42,5" in tablero  # 170 L / 400 km * 100, en formato argentino
    assert "+11,8 %" in tablero  # (42,5 - 38) / 38
    assert "Sin alertas" in tablero

    reportes = cliente.get("/reportes").text
    assert "/api/v1/reportes/consumo.xlsx?desde=" in reportes


def test_error_de_negocio_se_muestra_en_la_pagina(cliente):
    datos = {
        "patente": "AB123CD",
        "marca": "Scania",
        "modelo": "R450",
        "capacidad_tanque_litros": "600",
        "consumo_referencia_l100km": "38",
    }
    enviar(cliente, "/catalogo/camiones", datos)
    pagina = enviar(cliente, "/catalogo/camiones", datos)
    assert "aviso--error" in pagina.text
    assert "Ya existe un camión con patente AB123CD" in pagina.text


def test_importar_desde_el_panel(cliente):
    enviar(
        cliente,
        "/catalogo/camiones",
        {
            "patente": "AB123CD",
            "marca": "Scania",
            "modelo": "R450",
            "capacidad_tanque_litros": "600",
            "consumo_referencia_l100km": "38",
        },
    )
    libro = Workbook()
    libro.active.append(["Fecha", "Dominio", "Litros", "Ticket"])
    libro.active.append(["20/10/2026 15:00", "AB123CD", 200, "T-1"])
    libro.active.append(["20/10/2026 16:00", "ZZ000ZZ", 50, "T-2"])
    buffer = BytesIO()
    libro.save(buffer)

    pagina = cliente.post(
        "/combustible/importar",
        files={"archivo": ("tarjeta.xlsx", buffer.getvalue())},
        data={"origen": "tarjeta"},
    )
    assert pagina.status_code == 200
    assert "1 importadas" in pagina.text
    assert "no existe un camión con patente ZZ000ZZ" in pagina.text
