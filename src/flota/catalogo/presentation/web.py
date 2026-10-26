"""Páginas del panel: Flota y clientes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from flota.catalogo.application.casos_de_uso import (
    ActualizarCamion,
    ActualizarChofer,
    CambiosCamion,
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
from flota.dependencias import UoW
from flota.usuarios.domain.entidades import Modulo
from flota.usuarios.presentation.seguridad import requiere
from flota.web.plantillas import (
    Numero,
    Texto,
    TextoOpcional,
    decimal_opcional,
    ejecutar,
    pagina,
)

# include_in_schema=False: las páginas no aparecen en la documentación de la API.
router = APIRouter(include_in_schema=False, dependencies=requiere(Modulo.FLOTA))


@router.get("/catalogo", response_class=HTMLResponse)
def catalogo(request: Request, uow: UoW):
    consultas = ConsultasCatalogo(uow)
    return pagina(
        request,
        "catalogo.html",
        "/catalogo",
        camiones=consultas.listar_camiones(1000),
        choferes=consultas.listar_choferes(1000),
        clientes=consultas.listar_clientes(1000),
        productos=consultas.listar_productos(1000),
    )


def _entero_opcional(valor: str | None) -> int | None:
    return int(valor) if valor and valor.strip().isdigit() else None


@router.post("/catalogo/camiones")
def alta_camion(
    uow: UoW,
    patente: Texto,
    marca_camion: Annotated[str, Form(alias="marca")],
    modelo: Texto,
    capacidad_tanque_litros: Numero,
    consumo_referencia_l100km: Numero,
    anio: TextoOpcional = None,
    km_actual: TextoOpcional = None,
):
    datos = DatosCamion(
        patente,
        marca_camion,
        modelo,
        capacidad_tanque_litros,
        consumo_referencia_l100km,
        anio=_entero_opcional(anio),
        km_actual=decimal_opcional(km_actual),
    )
    return ejecutar(
        "/catalogo", lambda: RegistrarCamion(uow).ejecutar(datos), f"Camión {patente} registrado."
    )


@router.post("/catalogo/camiones/{camion_id}")
def editar_camion(
    camion_id: UUID,
    uow: UoW,
    marca_camion: Annotated[str, Form(alias="marca")],
    modelo: Texto,
    capacidad_tanque_litros: Numero,
    consumo_referencia_l100km: Numero,
    anio: TextoOpcional = None,
    activo: Annotated[bool, Form()] = False,  # un checkbox sin tildar no se envía
):
    cambios = CambiosCamion(
        marca_camion,
        modelo,
        capacidad_tanque_litros,
        consumo_referencia_l100km,
        _entero_opcional(anio),
        activo,
    )
    return ejecutar(
        "/catalogo",
        lambda: ActualizarCamion(uow).ejecutar(camion_id, cambios),
        "Camión actualizado.",
    )


@router.post("/catalogo/choferes/{chofer_id}")
def editar_chofer(
    chofer_id: UUID, uow: UoW, nombre: Texto, activo: Annotated[bool, Form()] = False
):
    return ejecutar(
        "/catalogo",
        lambda: ActualizarChofer(uow).ejecutar(chofer_id, nombre, activo),
        "Chofer actualizado.",
    )


@router.post("/catalogo/choferes")
def alta_chofer(uow: UoW, nombre: Texto, dni: Texto):
    return ejecutar(
        "/catalogo",
        lambda: RegistrarChofer(uow).ejecutar(DatosChofer(nombre, dni)),
        f"Chofer {nombre} registrado.",
    )


@router.post("/catalogo/clientes")
def alta_cliente(
    uow: UoW, razon_social: Texto, cuit: TextoOpcional = None, localidad: TextoOpcional = None
):
    return ejecutar(
        "/catalogo",
        lambda: RegistrarCliente(uow).ejecutar(DatosCliente(razon_social, cuit, localidad)),
        f"Cliente {razon_social} registrado.",
    )


@router.post("/catalogo/productos")
def alta_producto(uow: UoW, nombre: Texto, unidad: Texto = "tn"):
    return ejecutar(
        "/catalogo",
        lambda: RegistrarProducto(uow).ejecutar(DatosProducto(nombre, unidad)),
        f"Producto {nombre} registrado.",
    )
