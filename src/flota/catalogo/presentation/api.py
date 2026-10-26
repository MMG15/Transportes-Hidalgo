"""API REST del catálogo."""

from uuid import UUID

from fastapi import APIRouter

from flota.catalogo.application.casos_de_uso import (
    ConsultasCatalogo,
    DatosCamion,
    DatosChofer,
    DatosCliente,
    DatosProducto,
    RegistrarCamion,
    RegistrarChofer,
    RegistrarCliente,
    RegistrarProducto,
)
from flota.catalogo.presentation.esquemas import (
    CamionCrear,
    CamionLeer,
    ChoferCrear,
    ChoferLeer,
    ClienteCrear,
    ClienteLeer,
    ProductoCrear,
    ProductoLeer,
)
from flota.dependencias import UoW
from flota.shared.presentation.esquemas import Desplazamiento, Limite

router = APIRouter()


@router.post("/camiones", response_model=CamionLeer, status_code=201, tags=["Camiones"])
def crear_camion(datos: CamionCrear, uow: UoW):
    camion = RegistrarCamion(uow).ejecutar(DatosCamion(**datos.model_dump()))
    return CamionLeer.model_validate(camion)


@router.get("/camiones", response_model=list[CamionLeer], tags=["Camiones"])
def listar_camiones(uow: UoW, limite: int = Limite, desplazamiento: int = Desplazamiento):
    camiones = ConsultasCatalogo(uow).listar_camiones(limite, desplazamiento)
    return [CamionLeer.model_validate(c) for c in camiones]


@router.get("/camiones/{camion_id}", response_model=CamionLeer, tags=["Camiones"])
def obtener_camion(camion_id: UUID, uow: UoW):
    return CamionLeer.model_validate(ConsultasCatalogo(uow).obtener_camion(camion_id))


@router.post("/choferes", response_model=ChoferLeer, status_code=201, tags=["Choferes"])
def crear_chofer(datos: ChoferCrear, uow: UoW):
    return ChoferLeer.model_validate(
        RegistrarChofer(uow).ejecutar(DatosChofer(**datos.model_dump()))
    )


@router.get("/choferes", response_model=list[ChoferLeer], tags=["Choferes"])
def listar_choferes(uow: UoW, limite: int = Limite, desplazamiento: int = Desplazamiento):
    choferes = ConsultasCatalogo(uow).listar_choferes(limite, desplazamiento)
    return [ChoferLeer.model_validate(c) for c in choferes]


@router.post("/clientes", response_model=ClienteLeer, status_code=201, tags=["Clientes"])
def crear_cliente(datos: ClienteCrear, uow: UoW):
    cliente = RegistrarCliente(uow).ejecutar(DatosCliente(**datos.model_dump()))
    return ClienteLeer.model_validate(cliente)


@router.get("/clientes", response_model=list[ClienteLeer], tags=["Clientes"])
def listar_clientes(uow: UoW, limite: int = Limite, desplazamiento: int = Desplazamiento):
    clientes = ConsultasCatalogo(uow).listar_clientes(limite, desplazamiento)
    return [ClienteLeer.model_validate(c) for c in clientes]


@router.post("/productos", response_model=ProductoLeer, status_code=201, tags=["Productos"])
def crear_producto(datos: ProductoCrear, uow: UoW):
    producto = RegistrarProducto(uow).ejecutar(DatosProducto(**datos.model_dump()))
    return ProductoLeer.model_validate(producto)


@router.get("/productos", response_model=list[ProductoLeer], tags=["Productos"])
def listar_productos(uow: UoW, limite: int = Limite, desplazamiento: int = Desplazamiento):
    productos = ConsultasCatalogo(uow).listar_productos(limite, desplazamiento)
    return [ProductoLeer.model_validate(p) for p in productos]
