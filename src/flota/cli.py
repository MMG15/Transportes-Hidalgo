"""Comandos de consola. Ver todos con:  uv run flota --help

Pensados para automatizar con el Programador de tareas de Windows, por ejemplo:
    uv run flota importar-carpeta entrada      (cada hora)
    uv run flota exportar --salida reportes    (todos los días a las 7:00)
"""

from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import typer

from flota import bootstrap
from flota.catalogo.application.casos_de_uso import (
    DatosCamion,
    DatosChofer,
    DatosCliente,
    DatosProducto,
    RegistrarCamion,
    RegistrarChofer,
    RegistrarCliente,
    RegistrarProducto,
)
from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.combustible.application.importacion import ImportarCargas
from flota.combustible.domain.entidades import OrigenDato
from flota.combustible.infrastructure.importacion import EXTENSIONES_SOPORTADAS, lector_para_archivo
from flota.reportes.application.casos_de_uso import ExportarReporteConsumo, GenerarReporteConsumo
from flota.reportes.infrastructure.excel import crear_plantilla_importacion
from flota.shared.infrastructure.config import get_settings
from flota.viajes.application.casos_de_uso import DatosInicioViaje, FinalizarViaje, IniciarViaje

app = typer.Typer(help="Gestión de flota y consumo de combustible.", no_args_is_help=True)


@app.command()
def crear_db() -> None:
    """Crea la base en PostgreSQL si no existe. Después: uv run alembic upgrade head"""
    from sqlalchemy import create_engine, text

    config = get_settings()
    engine = create_engine(config.url_db(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conexion:
        existe = conexion.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :nombre"), {"nombre": config.db_name}
        )
        if existe:
            typer.echo(f"La base '{config.db_name}' ya existe.")
        else:
            conexion.execute(text(f'CREATE DATABASE "{config.db_name}"'))
            typer.echo(f"Base '{config.db_name}' creada.")


@app.command()
def importar(
    archivo: Path,
    origen: Annotated[OrigenDato, typer.Option(help="excel o tarjeta")] = OrigenDato.EXCEL,
) -> None:
    """Importa cargas de combustible desde un .xlsx o .csv."""
    resultado = _importar_archivo(archivo, origen)
    typer.echo(
        f"{archivo.name}: {resultado.importadas} importadas, {resultado.duplicadas} duplicadas, "
        f"{len(resultado.errores)} con error (de {resultado.procesadas} filas)"
    )
    for error in resultado.errores:
        typer.echo(f"  - {error}", err=True)


@app.command()
def importar_carpeta(
    carpeta: Path,
    origen: Annotated[OrigenDato, typer.Option(help="excel o tarjeta")] = OrigenDato.EXCEL,
) -> None:
    """Importa todos los archivos de una carpeta y los mueve a 'procesados' o 'errores'."""
    procesados, con_errores = carpeta / "procesados", carpeta / "errores"
    procesados.mkdir(parents=True, exist_ok=True)
    con_errores.mkdir(parents=True, exist_ok=True)

    archivos = sorted(
        a for a in carpeta.iterdir() if a.is_file() and a.suffix.lower() in EXTENSIONES_SOPORTADAS
    )
    if not archivos:
        typer.echo("No hay archivos para importar.")
        return

    for archivo in archivos:
        resultado = _importar_archivo(archivo, origen)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = con_errores if resultado.errores else procesados
        shutil.move(archivo, destino / f"{marca}_{archivo.name}")
        typer.echo(
            f"{archivo.name}: {resultado.importadas} importadas, "
            f"{resultado.duplicadas} duplicadas, {len(resultado.errores)} con error"
        )
        if resultado.errores:
            log = destino / f"{marca}_{archivo.stem}_errores.txt"
            log.write_text("\n".join(resultado.errores), encoding="utf-8")


def _importar_archivo(archivo: Path, origen: OrigenDato):
    if not archivo.exists():
        raise typer.BadParameter(f"No existe el archivo {archivo}")
    config = get_settings()
    caso_uso = ImportarCargas(
        bootstrap.crear_uow(), lector_para_archivo(archivo), origen, config.tolerancia_tanque_pct
    )
    return caso_uso.ejecutar(archivo)


@app.command()
def exportar(
    desde: Annotated[datetime | None, typer.Option(formats=["%Y-%m-%d"])] = None,
    hasta: Annotated[datetime | None, typer.Option(formats=["%Y-%m-%d"])] = None,
    salida: Annotated[Path, typer.Option(help="Carpeta o archivo .xlsx")] = Path("reportes"),
) -> None:
    """Exporta el reporte de consumo a Excel. Por defecto: los últimos 30 días."""
    fin = hasta.date() if hasta else date.today()
    inicio = desde.date() if desde else fin - timedelta(days=30)
    if salida.suffix.lower() != ".xlsx":
        salida.mkdir(parents=True, exist_ok=True)
        salida = salida / f"consumo_{inicio}_{fin}.xlsx"

    generar = GenerarReporteConsumo(bootstrap.crear_uow(), get_settings().umbral_desvio_pct)
    exportar_uc = ExportarReporteConsumo(generar, bootstrap.crear_generador_reporte())
    reporte = exportar_uc.ejecutar(inicio, fin, salida)
    alertas = sum(1 for f in reporte.filas if f.alerta)
    typer.echo(f"Reporte generado: {salida} ({len(reporte.filas)} viajes, {alertas} con alerta)")


@app.command()
def plantilla(salida: Path = Path("plantilla_cargas.xlsx")) -> None:
    """Genera la planilla modelo para cargar combustible desde Excel."""
    crear_plantilla_importacion(salida)
    typer.echo(f"Plantilla creada: {salida}")


@app.command()
def servidor(host: str = "127.0.0.1", puerto: int = 8000, recargar: bool = False) -> None:
    """Inicia la API REST. Documentación en http://127.0.0.1:8000/docs"""
    import uvicorn

    uvicorn.run("flota.main:app", host=host, port=puerto, reload=recargar)


@app.command()
def datos_demo() -> None:
    """Carga datos de ejemplo para probar el sistema."""
    uow = bootstrap.crear_uow()
    with uow:
        if uow.camiones.listar(limite=1):
            typer.echo("Ya hay datos cargados; no se agregan datos de ejemplo.")
            raise typer.Exit()

    scania = RegistrarCamion(uow).ejecutar(
        DatosCamion("AB123CD", "Scania", "R450", Decimal("600"), Decimal("38"))
    )
    mercedes = RegistrarCamion(uow).ejecutar(
        DatosCamion("AC456EF", "Mercedes-Benz", "Actros 2645", Decimal("500"), Decimal("36"))
    )
    juan = RegistrarChofer(uow).ejecutar(DatosChofer("Juan Pérez", "30123456"))
    maria = RegistrarChofer(uow).ejecutar(DatosChofer("María Gómez", "28987654"))
    productor = RegistrarCliente(uow).ejecutar(
        DatosCliente("Agropecuaria San José S.A.", "30-71234567-8", "Pergamino")
    )
    cal_viva = RegistrarProducto(uow).ejecutar(DatosProducto("Cal viva"))
    RegistrarProducto(uow).ejecutar(DatosProducto("Cal hidratada"))

    config = get_settings()
    registrar_carga = RegistrarCargaCombustible(uow, config.tolerancia_tanque_pct)
    hoy = datetime.now().replace(minute=0, second=0, microsecond=0)
    # (camión, chofer, días atrás, km salida, km recorridos, litros cargados)
    viajes = [
        (scania, juan, 6, 125000, 420, 160),
        (mercedes, maria, 5, 98000, 380, 132),
        (scania, juan, 3, 125420, 415, 190),  # consumo alto -> alerta
        (mercedes, maria, 2, 98380, 390, 140),
    ]
    for camion, chofer, dias, km, recorrido, litros in viajes:
        salida = hoy - timedelta(days=dias)
        viaje = IniciarViaje(uow).ejecutar(
            DatosInicioViaje(
                camion.id,
                chofer.id,
                productor.id,
                cal_viva.id,
                "Planta Olavarría",
                "Campo La Esperanza",
                Decimal("28"),
                salida,
                Decimal(km),
            )
        )
        registrar_carga.ejecutar(
            DatosCarga(
                camion.id,
                salida + timedelta(hours=4),
                Decimal(litros),
                Decimal("1450"),
                estacion="YPF Ruta 226",
                referencia_externa=f"DEMO-{viaje.id.hex[:8]}",
            )
        )
        FinalizarViaje(uow).ejecutar(viaje.id, salida + timedelta(hours=9), Decimal(km + recorrido))
    typer.echo("Datos de ejemplo cargados: 2 camiones, 2 choferes, 1 productor, 4 viajes.")


if __name__ == "__main__":
    app()
