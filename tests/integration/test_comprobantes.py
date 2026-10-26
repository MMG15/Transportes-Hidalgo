"""Tickets: subir la foto, verla al lado de los datos, validar o descartar (CU-02)."""

from datetime import datetime

CAMION = {
    "patente": "AB123CD",
    "marca": "Scania",
    "modelo": "R450",
    "capacidad_tanque_litros": 600,
    "consumo_referencia_l100km": 38,
}
FOTO = ("ticket.jpg", b"\xff\xd8\xff una foto", "image/jpeg")


def test_subir_validar_y_ver_el_ticket_desde_el_panel(cliente):
    camion_id = cliente.post("/api/v1/camiones", json=CAMION).json()["id"]

    respuesta = cliente.post("/comprobantes", files={"archivo": FOTO}, follow_redirects=False)
    assert respuesta.status_code == 303
    detalle_url = respuesta.headers["location"]  # va directo a la pantalla de revisión
    detalle = cliente.get(detalle_url).text
    assert "Imagen original" in detalle and "/archivo" in detalle

    imagen = cliente.get(f"{detalle_url}/archivo")
    assert imagen.content == FOTO[1] and imagen.headers["content-type"] == "image/jpeg"
    assert "1" in cliente.get("/comprobantes").text  # aparece en pendientes

    pagina = cliente.post(
        f"{detalle_url}/validar",
        data={
            "camion_id": camion_id,
            "fecha": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "litros": "250",
            "monto": "362500",
            "moneda": "ARS",
            "estacion": "YPF Ruta 40",
        },
    )
    assert "Ticket validado" in pagina.text
    assert "No hay tickets pendientes" in pagina.text
    (carga,) = cliente.get("/api/v1/cargas").json()
    assert carga["origen"] == "ticket" and carga["comprobante_id"] is not None
    assert "🧾" in cliente.get("/combustible").text  # enlace al ticket desde la carga


def test_archivo_no_permitido(cliente):
    pagina = cliente.post("/comprobantes", files={"archivo": ("a.html", b"<h1>", "text/html")})
    assert "foto (JPG, PNG, WEBP) o un PDF" in pagina.text


def test_api_descartar_y_anular(cliente):
    camion_id = cliente.post("/api/v1/camiones", json=CAMION).json()["id"]
    comprobante = cliente.post("/api/v1/comprobantes", files={"archivo": FOTO}).json()
    assert comprobante["estado"] == "pendiente"

    descartado = cliente.post(
        f"/api/v1/comprobantes/{comprobante['id']}/descartar", json={"motivo": "Ilegible"}
    ).json()
    assert descartado["estado"] == "descartado"
    otra_vez = cliente.post(
        f"/api/v1/comprobantes/{comprobante['id']}/descartar", json={"motivo": "Ilegible"}
    )
    assert otra_vez.status_code == 400

    carga = cliente.post(
        "/api/v1/cargas",
        json={"camion_id": camion_id, "fecha": datetime.now().isoformat(), "litros": 100},
    ).json()
    anulada = cliente.post(f"/api/v1/cargas/{carga['id']}/anular", json={"motivo": "Error"})
    assert anulada.json()["estado_validacion"] == "anulada"
    pagina = cliente.get("/combustible").text
    assert "Anulada" in pagina
