"""Autenticación y permisos para el panel y la API (RF-53, RNF-03).

- Panel: después del login, el id del usuario queda en una COOKIE DE SESIÓN firmada
  (el navegador no puede modificarla sin que se note).
- API: además de la cookie, acepta `Authorization: Bearer <token>`; el token se obtiene en
  `POST /api/v1/auth/token` y vence a las `HORAS_SESION` horas.
- `Permiso(modulo)`: dependencia que exige lectura para GET y escritura para el resto.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from flota.dependencias import UoW
from flota.shared.domain.auditoria import Actor
from flota.shared.domain.errores import NoAutenticado
from flota.shared.infrastructure.config import get_settings
from flota.usuarios.application.casos_de_uso import ConsultasUsuarios
from flota.usuarios.domain.entidades import Modulo, Nivel, Usuario

CLAVE_SESION = "usuario_id"
METODOS_DE_LECTURA = {"GET", "HEAD", "OPTIONS"}


@lru_cache
def clave_secreta() -> str:
    """La de `.env` (SECRET_KEY) o, si no hay, una aleatoria por cada arranque del servidor."""
    return get_settings().secret_key or secrets.token_urlsafe(32)


def _serializador() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(clave_secreta(), salt="token-api")


def crear_token(usuario: Usuario) -> str:
    return _serializador().dumps(str(usuario.id))


def _id_desde_token(token: str) -> UUID:
    try:
        texto = _serializador().loads(token, max_age=get_settings().horas_sesion * 3600)
        return UUID(texto)
    except SignatureExpired as error:
        raise NoAutenticado("El token venció; pedí uno nuevo") from error
    except (BadSignature, ValueError) as error:
        raise NoAutenticado("Token inválido") from error


def usuario_actual(request: Request, uow: UoW) -> Usuario:
    """Identifica al usuario y lo registra como ACTOR de la unidad de trabajo del pedido:
    así la auditoría sabe quién hizo cada cambio sin que los casos de uso lo reciban."""
    encabezado = request.headers.get("authorization", "")
    if encabezado.lower().startswith("bearer "):
        usuario_id = _id_desde_token(encabezado[7:].strip())
    elif texto := request.session.get(CLAVE_SESION):
        usuario_id = UUID(texto)
    else:
        raise NoAutenticado("Iniciá sesión para continuar")
    usuario = ConsultasUsuarios(uow).obtener_habilitado(usuario_id)
    uow.actor = Actor(usuario.id, usuario.nombre)
    request.state.usuario = usuario  # lo usan las plantillas (menú, nombre)
    return usuario


UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]


class Permiso:
    """Dependencia de FastAPI: `APIRouter(dependencies=[Depends(Permiso(Modulo.VIAJES))])`."""

    def __init__(self, modulo: Modulo) -> None:
        self.modulo = modulo

    def __call__(self, request: Request, usuario: UsuarioActual) -> Usuario:
        nivel = Nivel.LECTURA if request.method in METODOS_DE_LECTURA else Nivel.ESCRITURA
        usuario.exigir(self.modulo, nivel)
        return usuario


def requiere(modulo: Modulo) -> list:
    """Atajo para declarar los permisos de un router: `APIRouter(dependencies=requiere(...))`."""
    return [Depends(Permiso(modulo))]
