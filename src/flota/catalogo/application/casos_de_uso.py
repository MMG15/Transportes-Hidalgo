"""Alta y consulta de camiones, choferes, clientes y productos (arquitectura liviana)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from uuid import UUID

from flota.catalogo.application.puertos import UoWCatalogo
from flota.catalogo.domain.entidades import Camion, Chofer, Cliente, Producto
from flota.shared.application.comun import obtener_o_fallar
from flota.shared.domain.errores import Duplicado


@dataclass(frozen=True)
class DatosCamion:
    patente: str
    marca: str
    modelo: str
    capacidad_tanque_litros: Decimal
    consumo_referencia_l100km: Decimal
    anio: int | None = None
    km_actual: Decimal | None = None


@dataclass(frozen=True)
class CambiosCamion:
    """Campos editables de un camión (la patente no cambia: identifica al camión)."""

    marca: str
    modelo: str
    capacidad_tanque_litros: Decimal
    consumo_referencia_l100km: Decimal
    anio: int | None
    activo: bool


@dataclass(frozen=True)
class DatosChofer:
    nombre: str
    dni: str


@dataclass(frozen=True)
class DatosCliente:
    razon_social: str
    cuit: str | None = None
    localidad: str | None = None


@dataclass(frozen=True)
class DatosProducto:
    nombre: str
    unidad: str = "tn"


class RegistrarCamion:
    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosCamion) -> Camion:
        camion = Camion(**asdict(datos))
        with self._uow as uow:
            if uow.camiones.obtener_por_patente(camion.patente):
                raise Duplicado(f"Ya existe un camión con patente {camion.patente}")
            uow.camiones.guardar(camion)
            uow.commit()
        return camion


class ActualizarCamion:
    """MOD-01: edición y baja lógica (activo = False) de un camión."""

    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def ejecutar(self, camion_id: UUID, cambios: CambiosCamion) -> Camion:
        with self._uow as uow:
            actual = obtener_o_fallar(uow.camiones, camion_id, "camión")
            # Se reconstruye la entidad para que vuelvan a correr las validaciones.
            camion = Camion(**(asdict(actual) | asdict(cambios)))
            uow.camiones.guardar(camion)
            uow.commit()
        return camion


class ActualizarChofer:
    """MOD-01: edición y baja lógica de un chofer."""

    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def ejecutar(self, chofer_id: UUID, nombre: str, activo: bool) -> Chofer:
        with self._uow as uow:
            actual = obtener_o_fallar(uow.choferes, chofer_id, "chofer")
            chofer = Chofer(**(asdict(actual) | {"nombre": nombre, "activo": activo}))
            uow.choferes.guardar(chofer)
            uow.commit()
        return chofer


class RegistrarChofer:
    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosChofer) -> Chofer:
        chofer = Chofer(**asdict(datos))
        with self._uow as uow:
            if uow.choferes.obtener_por_dni(chofer.dni):
                raise Duplicado(f"Ya existe un chofer con DNI {chofer.dni}")
            uow.choferes.guardar(chofer)
            uow.commit()
        return chofer


class RegistrarCliente:
    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosCliente) -> Cliente:
        cliente = Cliente(**asdict(datos))
        with self._uow as uow:
            uow.clientes.guardar(cliente)
            uow.commit()
        return cliente


class RegistrarProducto:
    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosProducto) -> Producto:
        producto = Producto(**asdict(datos))
        with self._uow as uow:
            if uow.productos.obtener_por_nombre(producto.nombre):
                raise Duplicado(f"Ya existe el producto '{producto.nombre}'")
            uow.productos.guardar(producto)
            uow.commit()
        return producto


class ConsultasCatalogo:
    """Lecturas simples del catálogo (lado 'query' de CQRS)."""

    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def listar_camiones(self, limite: int = 100, desplazamiento: int = 0) -> list[Camion]:
        with self._uow as uow:
            return uow.camiones.listar(limite, desplazamiento)

    def obtener_camion(self, id: UUID) -> Camion:
        with self._uow as uow:
            return obtener_o_fallar(uow.camiones, id, "camión")

    def listar_choferes(self, limite: int = 100, desplazamiento: int = 0) -> list[Chofer]:
        with self._uow as uow:
            return uow.choferes.listar(limite, desplazamiento)

    def listar_clientes(self, limite: int = 100, desplazamiento: int = 0) -> list[Cliente]:
        with self._uow as uow:
            return uow.clientes.listar(limite, desplazamiento)

    def listar_productos(self, limite: int = 100, desplazamiento: int = 0) -> list[Producto]:
        with self._uow as uow:
            return uow.productos.listar(limite, desplazamiento)
