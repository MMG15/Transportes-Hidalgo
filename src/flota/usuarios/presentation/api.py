"""API REST de autenticación, usuarios (CU-17) y auditoría (RF-55)."""

from uuid import UUID

from fastapi import APIRouter

from flota.dependencias import Hasher, UoW
from flota.usuarios.application.casos_de_uso import (
    ActualizarUsuario,
    Autenticar,
    ConsultarAuditoria,
    ConsultasUsuarios,
    CrearUsuario,
    DatosUsuario,
)
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.esquemas import (
    AuditoriaLeer,
    Credenciales,
    Token,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioLeer,
)
from flota.usuarios.presentation.seguridad import UsuarioActual, crear_token, requiere

publico = APIRouter(prefix="/auth", tags=["Autenticación"])
router = APIRouter(dependencies=requiere(Modulo.USUARIOS), tags=["Usuarios"])


@publico.post("/token", response_model=Token)
def obtener_token(datos: Credenciales, uow: UoW, hasher: Hasher):
    """Devuelve un token para usar como `Authorization: Bearer <token>` (vence en 12 horas)."""
    usuario = Autenticar(uow, hasher).ejecutar(datos.email, datos.contrasena)
    return Token(access_token=crear_token(usuario))


@publico.get("/yo", response_model=UsuarioLeer)
def quien_soy(usuario: UsuarioActual):
    return UsuarioLeer.model_validate(usuario)


@router.get("/usuarios", response_model=list[UsuarioLeer])
def listar_usuarios(uow: UoW):
    return [UsuarioLeer.model_validate(u) for u in ConsultasUsuarios(uow).listar()]


@router.post("/usuarios", response_model=UsuarioLeer, status_code=201)
def crear_usuario(datos: UsuarioCrear, uow: UoW, hasher: Hasher):
    usuario = CrearUsuario(uow, hasher).ejecutar(
        DatosUsuario(datos.nombre, datos.email, datos.rol, datos.telegram_chat_id),
        datos.contrasena,
    )
    return UsuarioLeer.model_validate(usuario)


@router.put("/usuarios/{usuario_id}", response_model=UsuarioLeer)
def actualizar_usuario(usuario_id: UUID, datos: UsuarioActualizar, uow: UoW):
    usuario = ActualizarUsuario(uow).ejecutar(
        usuario_id,
        DatosUsuario(datos.nombre, datos.email, datos.rol, datos.telegram_chat_id),
        datos.activo,
    )
    return UsuarioLeer.model_validate(usuario)


@router.get("/auditoria", response_model=list[AuditoriaLeer])
def consultar_auditoria(
    uow: UoW,
    tabla: str | None = None,
    registro_id: UUID | None = None,
    usuario_id: UUID | None = None,
    limite: int = 200,
):
    registros = ConsultarAuditoria(uow).ejecutar(tabla, registro_id, usuario_id, limite)
    return [AuditoriaLeer.model_validate(r) for r in registros]
