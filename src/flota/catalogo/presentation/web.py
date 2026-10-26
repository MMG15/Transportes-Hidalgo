"""Páginas del panel: Flota y clientes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

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
from flota.dependencias import UoW
from flota.web.plantillas import Numero, Texto, TextoOpcional, ejecutar, pagina

router = APIRouter(include_in_schema=False)  # no aparece en la documentación de la API


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


@router.post("/catalogo/camiones")
def alta_camion(
    uow: UoW,
    patente: Texto,
    marca_camion: Annotated[str, Form(alias="marca")],
    modelo: Texto,
    capacidad_tanque_litros: Numero,
    consumo_referencia_l100km: Numero,
):
    datos = DatosCamion(
        patente, marca_camion, modelo, capacidad_tanque_litros, consumo_referencia_l100km
    )
    return ejecutar(
        "/catalogo", lambda: RegistrarCamion(uow).ejecutar(datos), f"Camión {patente} registrado."
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
