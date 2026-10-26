"""Login, permisos por rol, token de la API, auditoría y HTMX (RF-53, RF-55, RNF-03)."""

from datetime import datetime

from flota.usuarios.domain.entidades import Rol
from tests.integration.conftest import CONTRASENA

CAMION = {
    "patente": "AB123CD",
    "marca": "Scania",
    "modelo": "R450",
    "capacidad_tanque_litros": 600,
    "consumo_referencia_l100km": 38,
}


def test_sin_sesion_el_panel_lleva_al_login_y_la_api_responde_401(cliente_anonimo):
    respuesta = cliente_anonimo.get("/viajes", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login?siguiente=%2Fviajes"
    assert cliente_anonimo.get("/api/v1/camiones").status_code == 401
    assert cliente_anonimo.get("/login").status_code == 200
    assert cliente_anonimo.get("/salud").status_code == 200


def test_login_con_datos_incorrectos(cliente_anonimo, entrar):
    entrar(Rol.GERENCIA, "gerencia@prueba.com")
    cliente_anonimo.post("/logout")
    pagina = cliente_anonimo.post(
        "/login", data={"email": "gerencia@prueba.com", "contrasena": "mala"}
    )
    assert "Email o contraseña incorrectos" in pagina.text


def test_despues_del_login_vuelve_a_la_pagina_pedida(cliente_anonimo, entrar):
    entrar(Rol.ADMINISTRATIVO, "adm@prueba.com")
    cliente_anonimo.post("/logout")
    respuesta = cliente_anonimo.post(
        "/login",
        data={"email": "adm@prueba.com", "contrasena": CONTRASENA, "siguiente": "/combustible"},
        follow_redirects=False,
    )
    assert respuesta.headers["location"] == "/combustible"
    # Nunca a otro sitio (redirección abierta)
    respuesta = cliente_anonimo.post(
        "/login",
        data={"email": "adm@prueba.com", "contrasena": CONTRASENA, "siguiente": "//malo.com"},
        follow_redirects=False,
    )
    assert respuesta.headers["location"] == "/"


def test_gerencia_puede_leer_pero_no_modificar(entrar):
    cliente = entrar(Rol.GERENCIA)
    assert cliente.get("/viajes").status_code == 200
    assert cliente.get("/api/v1/camiones").status_code == 200
    assert cliente.post("/api/v1/camiones", json=CAMION).status_code == 403
    pagina = cliente.post("/catalogo/camiones", data={"patente": "AB123CD"})
    assert pagina.status_code == 403 and "no tiene permiso de escritura" in pagina.text


def test_el_taller_va_a_su_inicio_y_no_ve_combustible(entrar):
    cliente = entrar(Rol.JEFE_TALLER)
    respuesta = cliente.get("/", follow_redirects=False)
    assert respuesta.headers["location"] == "/catalogo"  # su primera página permitida
    assert cliente.get("/combustible").status_code == 403
    menu = cliente.get("/catalogo").text
    assert 'href="/catalogo"' in menu and 'href="/combustible"' not in menu


def test_solo_el_administrador_gestiona_usuarios(cliente, entrar):
    assert cliente.get("/usuarios").status_code == 200
    pagina = cliente.post(
        "/usuarios",
        data={"nombre": "Silvana", "email": "silvana@prueba.com", "rol": "ROL-02",
              "contrasena": "inicial123"},
    )  # fmt: skip
    assert "Usuario silvana@prueba.com creado" in pagina.text
    otro = entrar(Rol.RESP_SISTEMAS)
    assert otro.get("/usuarios").status_code == 403


def test_token_bearer_para_la_api(cliente_anonimo, entrar):
    entrar(Rol.ADMINISTRATIVO, "api@prueba.com")
    cliente_anonimo.post("/logout")
    token = cliente_anonimo.post(
        "/api/v1/auth/token", json={"email": "api@prueba.com", "contrasena": CONTRASENA}
    ).json()["access_token"]

    encabezado = {"Authorization": f"Bearer {token}"}
    yo = cliente_anonimo.get("/api/v1/auth/yo", headers=encabezado).json()
    assert yo["rol"] == "ROL-03"
    assert (
        cliente_anonimo.post("/api/v1/camiones", json=CAMION, headers=encabezado).status_code == 201
    )
    falso = {"Authorization": "Bearer inventado"}
    assert cliente_anonimo.get("/api/v1/camiones", headers=falso).status_code == 401


def test_la_auditoria_registra_quien_hizo_el_cambio(cliente):
    camion = cliente.post("/api/v1/camiones", json=CAMION).json()
    cliente.post(
        "/api/v1/cargas",
        json={"camion_id": camion["id"], "fecha": "2026-10-20T10:00:00", "litros": 100,
              "precio_litro": 1450},
    )  # fmt: skip
    (registro,) = cliente.get("/api/v1/auditoria", params={"tabla": "cargas_combustible"}).json()
    assert registro["usuario_nombre"] == "Usuario ROL-07"
    assert registro["accion"] == "alta"
    assert "cargas_combustible" in cliente.get("/auditoria").text


def test_resolver_una_alerta_con_htmx_devuelve_solo_la_fila(cliente):
    camion = cliente.post("/api/v1/camiones", json=CAMION).json()
    cliente.post(
        "/api/v1/cargas",
        json={"camion_id": camion["id"], "fecha": datetime.now().isoformat(), "litros": 700},
    )  # supera el tanque -> alerta
    alerta = cliente.get("/api/v1/alertas").json()[0]

    fila = cliente.post(
        f"/alertas/{alerta['id']}",
        data={"accion": "justificar", "comentario": "Tanque auxiliar"},
        headers={"HX-Request": "true"},
    )
    assert fila.status_code == 200
    assert "<tr" in fila.text
    assert "<html" not in fila.text  # sólo el fragmento, sin la página entera
    assert "Alerta justificada" in fila.text and "Justificada" in fila.text
    resuelta = cliente.get(f"/api/v1/alertas/{alerta['id']}").json()
    assert resuelta["comentario"] == "Tanque auxiliar"
