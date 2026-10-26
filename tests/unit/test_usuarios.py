"""MOD-13 · Usuarios, roles, permisos y auditoría (RF-53, RF-55, CU-17)."""

from datetime import date
from decimal import Decimal

import pytest

from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.monedas.application.casos_de_uso import CargarCotizacion, CorregirCotizacion
from flota.shared.domain.auditoria import AccionAuditoria, Actor
from flota.shared.domain.errores import DatosInvalidos, Duplicado, NoAutenticado, SinPermiso
from flota.usuarios.application.casos_de_uso import (
    ActualizarUsuario,
    Autenticar,
    CambiarContrasena,
    CrearUsuario,
    DatosUsuario,
)
from flota.usuarios.domain.entidades import Modulo, Nivel, Rol, Usuario
from tests.escenarios import SALIDA, flota_basica
from tests.fakes import HasherFake, UnidadDeTrabajoFake


def usuario(rol: Rol, **cambios) -> Usuario:
    return Usuario(**({"nombre": "Ana", "email": "Ana@Hidalgo.com", "rol": rol} | cambios))


# ---------- Permisos por rol ----------
def test_gerencia_lee_todo_y_gestiona_alertas():
    gerencia = usuario(Rol.GERENCIA)
    assert gerencia.puede(Modulo.COMBUSTIBLE, Nivel.LECTURA)
    assert not gerencia.puede(Modulo.COMBUSTIBLE, Nivel.ESCRITURA)
    assert gerencia.puede(Modulo.ALERTAS, Nivel.ESCRITURA)
    assert not gerencia.puede(Modulo.USUARIOS)


def test_taller_solo_ve_mantenimiento_neumaticos_stock_y_flota():
    taller = usuario(Rol.JEFE_TALLER)
    assert taller.puede(Modulo.MANTENIMIENTO, Nivel.ESCRITURA)
    assert taller.puede(Modulo.STOCK, Nivel.LECTURA)
    assert not taller.puede(Modulo.STOCK, Nivel.ESCRITURA)
    assert not taller.puede(Modulo.COMBUSTIBLE)
    with pytest.raises(SinPermiso):
        taller.exigir(Modulo.COMBUSTIBLE)


def test_solo_el_administrador_de_sistema_gestiona_usuarios():
    assert usuario(Rol.ADMIN_SISTEMA).puede(Modulo.USUARIOS, Nivel.ESCRITURA)
    assert not usuario(Rol.RESP_SISTEMAS).puede(Modulo.USUARIOS)


def test_el_chofer_no_usa_el_panel_y_un_deshabilitado_no_puede_nada():
    assert not usuario(Rol.CHOFER).usa_el_panel
    assert not usuario(Rol.ADMIN_SISTEMA, activo=False).puede(Modulo.TABLERO)


def test_email_se_normaliza_y_se_valida():
    assert usuario(Rol.GERENCIA).email == "ana@hidalgo.com"
    with pytest.raises(DatosInvalidos):
        usuario(Rol.GERENCIA, email="sin-arroba")


# ---------- Casos de uso ----------
@pytest.fixture
def uow():
    return UnidadDeTrabajoFake()


def crear(uow, email="ana@hidalgo.com", rol=Rol.ADMINISTRATIVO, contrasena="secreta123"):
    return CrearUsuario(uow, HasherFake()).ejecutar(DatosUsuario("Ana", email, rol), contrasena)


def test_crear_usuario_guarda_el_hash_y_audita_sin_el_hash(uow):
    nuevo = crear(uow)
    assert nuevo.password_hash == "hash:secreta123"
    (registro,) = uow.auditoria.listar_filtrado(tabla="usuarios")
    assert registro.accion == AccionAuditoria.ALTA
    assert registro.valor_nuevo["password_hash"] == "***"


def test_email_repetido(uow):
    crear(uow)
    with pytest.raises(Duplicado):
        crear(uow, email="ANA@hidalgo.com")


def test_contrasena_corta(uow):
    with pytest.raises(DatosInvalidos):
        crear(uow, contrasena="corta")


def test_autenticar(uow):
    crear(uow)
    assert Autenticar(uow, HasherFake()).ejecutar("ana@hidalgo.com", "secreta123").ultimo_acceso
    with pytest.raises(NoAutenticado, match="Email o contraseña incorrectos"):
        Autenticar(uow, HasherFake()).ejecutar("ana@hidalgo.com", "otra")
    with pytest.raises(NoAutenticado, match="Email o contraseña incorrectos"):
        Autenticar(uow, HasherFake()).ejecutar("nadie@hidalgo.com", "secreta123")


def test_un_chofer_no_puede_entrar_al_panel(uow):
    crear(uow, rol=Rol.CHOFER)
    with pytest.raises(NoAutenticado, match="no tiene acceso al panel"):
        Autenticar(uow, HasherFake()).ejecutar("ana@hidalgo.com", "secreta123")


def test_cambiar_contrasena_exige_la_actual(uow):
    ana = crear(uow)
    with pytest.raises(NoAutenticado):
        CambiarContrasena(uow, HasherFake()).ejecutar(ana.id, "equivocada", "nueva12345")
    CambiarContrasena(uow, HasherFake()).ejecutar(ana.id, "secreta123", "nueva12345")
    assert Autenticar(uow, HasherFake()).ejecutar("ana@hidalgo.com", "nueva12345")


def test_cambiar_rol_queda_auditado_con_antes_y_despues(uow):
    ana = crear(uow)
    ActualizarUsuario(uow).ejecutar(
        ana.id, DatosUsuario("Ana", "ana@hidalgo.com", Rol.GERENCIA), activo=True
    )
    ultimo = uow.auditoria.listar_filtrado(tabla="usuarios")[0]
    assert ultimo.campos_cambiados == ["rol"]
    assert (ultimo.valor_anterior["rol"], ultimo.valor_nuevo["rol"]) == ("ROL-03", "ROL-01")


# ---------- Auditoría de gastos (RF-55) ----------
def test_los_gastos_quedan_auditados_con_el_usuario_que_opera(uow):
    flota = flota_basica(uow)
    uow.actor = Actor(None, "Administración")  # lo fija el panel al identificar al usuario
    carga = RegistrarCargaCombustible(uow).ejecutar(
        DatosCarga(flota.camion.id, SALIDA, Decimal("100"), precio_litro=Decimal("1500"))
    )
    cotizacion = CargarCotizacion(uow).ejecutar(date(2026, 10, 1), Decimal("1.25"))
    CorregirCotizacion(uow).ejecutar(cotizacion.id, Decimal("1.30"), "BCRA")

    (alta_carga,) = uow.auditoria.listar_filtrado(registro_id=carga.id)
    assert alta_carga.usuario_nombre == "Administración"
    assert alta_carga.valor_nuevo["litros"] == "100"
    correccion = uow.auditoria.listar_filtrado(tabla="tipos_cambio")[0]
    assert correccion.accion == AccionAuditoria.MODIFICACION
    assert correccion.campos_cambiados == ["cotizacion", "fuente"]
    assert correccion.valor_anterior["cotizacion"] == "1.25"
