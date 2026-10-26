"""Esquemas Pydantic de usuarios, autenticación y auditoría."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from flota.shared.domain.auditoria import AccionAuditoria
from flota.shared.presentation.esquemas import Esquema
from flota.usuarios.domain.entidades import Rol


class Credenciales(BaseModel):
    email: str = Field(examples=["admin@hidalgo.demo"])
    contrasena: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioCrear(BaseModel):
    nombre: str
    email: str
    rol: Rol
    contrasena: str = Field(min_length=8)
    telegram_chat_id: str | None = None


class UsuarioActualizar(BaseModel):
    nombre: str
    email: str
    rol: Rol
    activo: bool = True
    telegram_chat_id: str | None = None


class UsuarioLeer(Esquema):
    id: UUID
    nombre: str
    email: str
    rol: Rol
    nombre_rol: str
    activo: bool
    telegram_chat_id: str | None
    ultimo_acceso: datetime | None


class AuditoriaLeer(Esquema):
    id: UUID
    fecha: datetime
    tabla: str
    registro_id: UUID
    accion: AccionAuditoria
    usuario_nombre: str
    campos_cambiados: list[str]
    valor_anterior: dict | None
    valor_nuevo: dict | None
