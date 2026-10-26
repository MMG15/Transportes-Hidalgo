"""Gestión de usuarios y roles (CU-17), autenticación y consulta de auditoría (RF-53, RF-55)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from flota.shared.application.comun import obtener_o_fallar
from flota.shared.domain.auditoria import AccionAuditoria, RegistroAuditoria
from flota.shared.domain.errores import Duplicado, NoAutenticado
from flota.usuarios.application.puertos import HasherContrasenas, UoWUsuarios
from flota.usuarios.domain.entidades import Rol, Usuario, validar_contrasena

TABLA = "usuarios"


def _sin_hash(usuario: Usuario) -> Usuario:
    """Copia para auditar: el hash de la contraseña nunca se guarda en la auditoría."""
    return replace(usuario, password_hash="***")


@dataclass(frozen=True)
class DatosUsuario:
    nombre: str
    email: str
    rol: Rol
    telegram_chat_id: str | None = None


class CrearUsuario:
    """CU-17 — RF-53: alta de un usuario con su rol (sólo el Administrador de sistema)."""

    def __init__(self, uow: UoWUsuarios, hasher: HasherContrasenas) -> None:
        self._uow = uow
        self._hasher = hasher

    def ejecutar(self, datos: DatosUsuario, contrasena: str) -> Usuario:
        validar_contrasena(contrasena)
        usuario = Usuario(
            nombre=datos.nombre,
            email=datos.email,
            rol=datos.rol,
            telegram_chat_id=datos.telegram_chat_id,
            password_hash=self._hasher.hash(contrasena),
        )
        with self._uow as uow:
            # CU-17 E1: email ya usado por otro usuario.
            if uow.usuarios.obtener_por_email(usuario.email):
                raise Duplicado(f"Ya existe un usuario con el email {usuario.email}")
            uow.usuarios.guardar(usuario)
            uow.auditar(TABLA, usuario.id, AccionAuditoria.ALTA, despues=_sin_hash(usuario))
            uow.commit()
        return usuario


class ActualizarUsuario:
    """CU-17: cambiar nombre, rol, habilitación o Telegram de un usuario."""

    def __init__(self, uow: UoWUsuarios) -> None:
        self._uow = uow

    def ejecutar(self, usuario_id: UUID, datos: DatosUsuario, activo: bool) -> Usuario:
        with self._uow as uow:
            antes = obtener_o_fallar(uow.usuarios, usuario_id, "usuario")
            otro = uow.usuarios.obtener_por_email(datos.email)
            if otro and otro.id != usuario_id:
                raise Duplicado(f"Ya existe un usuario con el email {datos.email}")
            despues = Usuario(
                id=antes.id,
                nombre=datos.nombre,
                email=datos.email,
                rol=datos.rol,
                telegram_chat_id=datos.telegram_chat_id,
                activo=activo,
                password_hash=antes.password_hash,
                ultimo_acceso=antes.ultimo_acceso,
            )
            uow.usuarios.guardar(despues)
            uow.auditar(
                TABLA,
                despues.id,
                AccionAuditoria.MODIFICACION,
                _sin_hash(antes),
                _sin_hash(despues),
            )
            uow.commit()
        return despues


class CambiarContrasena:
    """El propio usuario cambia su contraseña (necesita la actual)."""

    def __init__(self, uow: UoWUsuarios, hasher: HasherContrasenas) -> None:
        self._uow = uow
        self._hasher = hasher

    def ejecutar(self, usuario_id: UUID, actual: str, nueva: str) -> None:
        validar_contrasena(nueva)
        with self._uow as uow:
            usuario = obtener_o_fallar(uow.usuarios, usuario_id, "usuario")
            if not self._hasher.verificar(actual, usuario.password_hash):
                raise NoAutenticado("La contraseña actual no es correcta")
            usuario.password_hash = self._hasher.hash(nueva)
            uow.usuarios.guardar(usuario)
            uow.auditar(
                TABLA, usuario.id, AccionAuditoria.MODIFICACION, despues={"contrasena": "cambiada"}
            )
            uow.commit()


class RestablecerContrasena:
    """El Administrador de sistema asigna una contraseña nueva (p. ej. si el usuario la olvidó)."""

    def __init__(self, uow: UoWUsuarios, hasher: HasherContrasenas) -> None:
        self._uow = uow
        self._hasher = hasher

    def ejecutar(self, usuario_id: UUID, nueva: str) -> None:
        validar_contrasena(nueva)
        with self._uow as uow:
            usuario = obtener_o_fallar(uow.usuarios, usuario_id, "usuario")
            usuario.password_hash = self._hasher.hash(nueva)
            uow.usuarios.guardar(usuario)
            uow.auditar(
                TABLA,
                usuario.id,
                AccionAuditoria.MODIFICACION,
                despues={"contrasena": "restablecida"},
            )
            uow.commit()


class Autenticar:
    """Login: email + contraseña. El mensaje de error no dice cuál de los dos falló."""

    MENSAJE = "Email o contraseña incorrectos"

    def __init__(self, uow: UoWUsuarios, hasher: HasherContrasenas) -> None:
        self._uow = uow
        self._hasher = hasher

    def ejecutar(self, email: str, contrasena: str) -> Usuario:
        with self._uow as uow:
            usuario = uow.usuarios.obtener_por_email((email or "").strip().lower())
            if usuario is None or not self._hasher.verificar(contrasena, usuario.password_hash):
                raise NoAutenticado(self.MENSAJE)
            if not usuario.usa_el_panel:
                raise NoAutenticado("Tu usuario no tiene acceso al panel")
            usuario.ultimo_acceso = datetime.now()
            uow.usuarios.guardar(usuario)
            uow.commit()
        return usuario


class ConsultasUsuarios:
    def __init__(self, uow: UoWUsuarios) -> None:
        self._uow = uow

    def listar(self) -> list[Usuario]:
        with self._uow as uow:
            return uow.usuarios.listar(limite=1000)

    def obtener(self, usuario_id: UUID) -> Usuario:
        with self._uow as uow:
            return obtener_o_fallar(uow.usuarios, usuario_id, "usuario")

    def obtener_habilitado(self, usuario_id: UUID) -> Usuario:
        """Para cada pedido autenticado: el usuario tiene que seguir existiendo y habilitado."""
        with self._uow as uow:
            usuario = uow.usuarios.obtener(usuario_id)
        if usuario is None or not usuario.usa_el_panel:
            raise NoAutenticado("La sesión ya no es válida")
        return usuario

    def hay_usuarios(self) -> bool:
        with self._uow as uow:
            return bool(uow.usuarios.listar(limite=1))


class ConsultarAuditoria:
    """RF-55: historial de cambios, filtrable por tabla, registro y usuario."""

    def __init__(self, uow: UoWUsuarios) -> None:
        self._uow = uow

    def ejecutar(
        self,
        tabla: str | None = None,
        registro_id: UUID | None = None,
        usuario_id: UUID | None = None,
        limite: int = 200,
    ) -> list[RegistroAuditoria]:
        with self._uow as uow:
            return uow.auditoria.listar_filtrado(tabla, registro_id, usuario_id, limite)
