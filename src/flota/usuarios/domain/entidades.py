"""Usuarios, roles y permisos por módulo (RF-53, secciones 7 y 12 del documento de requisitos)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from flota.shared.domain.errores import DatosInvalidos, SinPermiso
from flota.shared.domain.validaciones import opcional, requerido


class Rol(StrEnum):
    GERENCIA = "ROL-01"
    RESP_SISTEMAS = "ROL-02"
    ADMINISTRATIVO = "ROL-03"
    JEFE_TALLER = "ROL-04"
    ENCARGADO_STOCK = "ROL-05"
    CHOFER = "ROL-06"
    ADMIN_SISTEMA = "ROL-07"


NOMBRES_ROL = {
    Rol.GERENCIA: "Gerencia",
    Rol.RESP_SISTEMAS: "Resp. de Sistemas de Gestión",
    Rol.ADMINISTRATIVO: "Administrativo",
    Rol.JEFE_TALLER: "Jefe de Taller / Mantenimiento",
    Rol.ENCARGADO_STOCK: "Encargado de Stock",
    Rol.CHOFER: "Chofer",
    Rol.ADMIN_SISTEMA: "Administrador de sistema",
}


class Modulo(StrEnum):
    FLOTA = "MOD-01"
    VIAJES = "MOD-02"
    COMBUSTIBLE = "MOD-03"
    GPS = "MOD-04"
    ALERTAS = "MOD-05"
    MANTENIMIENTO = "MOD-06"
    NEUMATICOS = "MOD-07"
    STOCK = "MOD-08"
    VIATICOS = "MOD-09"
    PEAJES_MONEDAS = "MOD-10"
    ASISTENTE_EXCEL = "MOD-11"
    TABLERO = "MOD-12"
    USUARIOS = "MOD-13"
    TELEGRAM = "MOD-14"


class Nivel(StrEnum):
    LECTURA = "lectura"
    ESCRITURA = "escritura"


L, E = Nivel.LECTURA, Nivel.ESCRITURA
_TODOS = list(Modulo)

# Matriz de permisos. Lo que no figura, no se puede ver.
PERMISOS: dict[Rol, dict[Modulo, Nivel]] = {
    # Lectura de todo; gestiona alertas (CU-06: recibe las escaladas y decide).
    Rol.GERENCIA: {m: L for m in _TODOS if m != Modulo.USUARIOS} | {Modulo.ALERTAS: E},
    # Configura el sistema: todos los módulos menos usuarios.
    Rol.RESP_SISTEMAS: {m: E for m in _TODOS if m != Modulo.USUARIOS},
    Rol.ADMINISTRATIVO: {
        Modulo.FLOTA: E,
        Modulo.VIAJES: E,
        Modulo.COMBUSTIBLE: E,
        Modulo.ALERTAS: E,
        Modulo.VIATICOS: E,
        Modulo.PEAJES_MONEDAS: E,
        Modulo.ASISTENTE_EXCEL: E,
        Modulo.TABLERO: L,
    },
    Rol.JEFE_TALLER: {
        Modulo.MANTENIMIENTO: E,
        Modulo.NEUMATICOS: E,
        Modulo.STOCK: L,
        Modulo.FLOTA: L,
    },
    Rol.ENCARGADO_STOCK: {Modulo.STOCK: E, Modulo.MANTENIMIENTO: L, Modulo.FLOTA: L},
    Rol.CHOFER: {},  # opera sólo por Telegram: sin acceso al panel
    Rol.ADMIN_SISTEMA: {m: E for m in _TODOS},
}

LARGO_MINIMO_CONTRASENA = 8


@dataclass(kw_only=True)
class Usuario:
    nombre: str
    email: str
    rol: Rol
    password_hash: str = ""
    activo: bool = True
    telegram_chat_id: str | None = None  # para recibir avisos de alertas (RF-19)
    ultimo_acceso: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.nombre = requerido(self.nombre, "nombre")
        self.email = requerido(self.email, "email").lower()
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise DatosInvalidos(f"'{self.email}' no es un email válido")
        self.rol = Rol(self.rol)
        self.telegram_chat_id = opcional(self.telegram_chat_id)

    @property
    def nombre_rol(self) -> str:
        return NOMBRES_ROL[self.rol]

    def nivel_en(self, modulo: Modulo) -> Nivel | None:
        return PERMISOS[self.rol].get(modulo)

    def puede(self, modulo: Modulo, nivel: Nivel = Nivel.LECTURA) -> bool:
        if not self.activo:
            return False
        tiene = self.nivel_en(modulo)
        return tiene == Nivel.ESCRITURA or (tiene == Nivel.LECTURA and nivel == Nivel.LECTURA)

    def exigir(self, modulo: Modulo, nivel: Nivel = Nivel.LECTURA) -> None:
        if not self.puede(modulo, nivel):
            raise SinPermiso(
                f"Tu rol ({self.nombre_rol}) no tiene permiso de {nivel.value} en {modulo.value}"
            )

    @property
    def usa_el_panel(self) -> bool:
        return self.activo and bool(PERMISOS[self.rol])


def validar_contrasena(contrasena: str) -> None:
    """RNF-03: largo mínimo. (La contraseña nunca se guarda: se guarda su hash.)"""
    if len(contrasena or "") < LARGO_MINIMO_CONTRASENA:
        raise DatosInvalidos(
            f"La contraseña debe tener al menos {LARGO_MINIMO_CONTRASENA} caracteres"
        )
