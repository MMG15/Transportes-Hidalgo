"""Páginas del panel: login, mi cuenta, usuarios (CU-17) y auditoría (RF-55)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from flota.dependencias import Hasher, UoW
from flota.shared.domain.errores import NoAutenticado
from flota.usuarios.application.casos_de_uso import (
    ActualizarUsuario,
    Autenticar,
    CambiarContrasena,
    ConsultarAuditoria,
    ConsultasUsuarios,
    CrearUsuario,
    DatosUsuario,
    RestablecerContrasena,
)
from flota.usuarios.domain.entidades import NOMBRES_ROL, Modulo, Rol
from flota.usuarios.presentation.seguridad import CLAVE_SESION, UsuarioActual, requiere
from flota.web.plantillas import Texto, TextoOpcional, ejecutar, pagina, primera_pagina

publico = APIRouter(include_in_schema=False)
router = APIRouter(include_in_schema=False, dependencies=requiere(Modulo.USUARIOS))


def _destino_seguro(siguiente: str | None) -> str | None:
    """Sólo rutas internas: evita que un enlace malicioso redirija a otro sitio."""
    if siguiente and siguiente.startswith("/") and not siguiente.startswith("//"):
        return siguiente
    return None


# ---------- Login y sesión ----------
@publico.get("/login", response_class=HTMLResponse)
def login(request: Request, siguiente: str | None = None):
    return pagina(request, "login.html", "/login", siguiente=_destino_seguro(siguiente))


@publico.post("/login", response_class=HTMLResponse)
def iniciar_sesion(
    request: Request,
    uow: UoW,
    hasher: Hasher,
    email: Texto,
    contrasena: Texto,
    siguiente: TextoOpcional = None,
):
    try:
        usuario = Autenticar(uow, hasher).ejecutar(email, contrasena)
    except NoAutenticado as error:
        return pagina(
            request, "login.html", "/login", error=str(error), email=email, siguiente=siguiente
        )
    request.session.clear()  # sesión nueva en cada login
    request.session[CLAVE_SESION] = str(usuario.id)
    destino = _destino_seguro(siguiente) or primera_pagina(usuario)
    return RedirectResponse(destino, status_code=303)


@publico.post("/logout")
def cerrar_sesion(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@publico.get("/mi-cuenta", response_class=HTMLResponse)
def mi_cuenta(request: Request, usuario: UsuarioActual):
    return pagina(request, "mi_cuenta.html", "/mi-cuenta")


@publico.post("/mi-cuenta")
def cambiar_contrasena(
    usuario: UsuarioActual, uow: UoW, hasher: Hasher, actual: Texto, nueva: Texto
):
    return ejecutar(
        "/mi-cuenta",
        lambda: CambiarContrasena(uow, hasher).ejecutar(usuario.id, actual, nueva),
        "Contraseña actualizada.",
    )


# ---------- Administración de usuarios (ROL-07) ----------
@router.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request, uow: UoW):
    return pagina(
        request,
        "usuarios.html",
        "/usuarios",
        usuarios=ConsultasUsuarios(uow).listar(),
        roles=NOMBRES_ROL,
    )


@router.post("/usuarios")
def crear_usuario(
    uow: UoW,
    hasher: Hasher,
    nombre: Texto,
    email: Texto,
    rol: Annotated[Rol, Form()],
    contrasena: Texto,
    telegram_chat_id: TextoOpcional = None,
):
    datos = DatosUsuario(nombre, email, rol, telegram_chat_id)
    return ejecutar(
        "/usuarios",
        lambda: CrearUsuario(uow, hasher).ejecutar(datos, contrasena),
        f"Usuario {email} creado.",
    )


@router.post("/usuarios/{usuario_id}")
def editar_usuario(
    usuario_id: UUID,
    uow: UoW,
    nombre: Texto,
    email: Texto,
    rol: Annotated[Rol, Form()],
    telegram_chat_id: TextoOpcional = None,
    activo: Annotated[bool, Form()] = False,
):
    datos = DatosUsuario(nombre, email, rol, telegram_chat_id)
    return ejecutar(
        "/usuarios",
        lambda: ActualizarUsuario(uow).ejecutar(usuario_id, datos, activo),
        "Usuario actualizado.",
    )


@router.post("/usuarios/{usuario_id}/contrasena")
def restablecer_contrasena(usuario_id: UUID, uow: UoW, hasher: Hasher, nueva: Texto):
    return ejecutar(
        "/usuarios",
        lambda: RestablecerContrasena(uow, hasher).ejecutar(usuario_id, nueva),
        "Contraseña restablecida.",
    )


@router.get("/auditoria", response_class=HTMLResponse)
def auditoria(request: Request, uow: UoW, tabla: str | None = None):
    return pagina(
        request,
        "auditoria.html",
        "/usuarios",
        registros=ConsultarAuditoria(uow).ejecutar(tabla=tabla or None, limite=300),
        tabla=tabla,
        tablas=["cargas_combustible", "tipos_cambio", "alertas", "usuarios"],
    )
