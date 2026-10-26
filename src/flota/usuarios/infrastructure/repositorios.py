"""Repositorio SQL de usuarios y hasher de contraseñas con Argon2."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select

from flota.shared.infrastructure.db import RepositorioSql
from flota.usuarios.application.puertos import HasherContrasenas
from flota.usuarios.domain.entidades import Usuario
from flota.usuarios.domain.repositorios import RepositorioUsuarios
from flota.usuarios.infrastructure.modelos import UsuarioModel


class RepositorioUsuariosSql(RepositorioSql[Usuario, UsuarioModel], RepositorioUsuarios):
    entidad, modelo, orden = Usuario, UsuarioModel, UsuarioModel.nombre.asc()

    def obtener_por_email(self, email: str) -> Usuario | None:
        return self._uno(select(UsuarioModel).where(UsuarioModel.email == email.strip().lower()))


class HasherArgon2(HasherContrasenas):
    """Argon2id: el algoritmo recomendado hoy para guardar contraseñas (RNF-03).

    Cada hash incluye su propia "sal" aleatoria: dos usuarios con la misma contraseña tienen
    hashes distintos, y no se puede volver del hash a la contraseña.
    """

    def __init__(self) -> None:
        self._ph = PasswordHasher()

    def hash(self, contrasena: str) -> str:
        return self._ph.hash(contrasena)

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            return self._ph.verify(hash_guardado, contrasena)
        except (VerificationError, InvalidHashError):
            return False
