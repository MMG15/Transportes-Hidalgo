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
from flota.alertas.application.casos_de_uso import EvaluarAlertasViaje
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
from flota.monedas.application.casos_de_uso import CargarCotizacion
from flota.reportes.application.casos_de_uso import ExportarReporteConsumo, GenerarReporteConsumo
from flota.reportes.infrastructure.excel import crear_plantilla_importacion
from flota.shared.domain.dinero import Moneda
from flota.shared.infrastructure.config import get_settings
from flota.viajes.application.casos_de_uso import (
    CambiarEstadoCarga,
    ConsultasViajes,
    DatosInicioViaje,
    DatosRuta,
    FinalizarViaje,
    IniciarViaje,
    RegistrarRuta,
)
from flota.viajes.domain.entidades import EstadoCarga, EstadoViaje, Pais

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
    caso_uso = ImportarCargas(bootstrap.crear_uow(), lector_para_archivo(archivo), origen)
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
def recalcular_alertas(dias: int = 90) -> None:
    """Evalúa las alertas de consumo de los viajes cerrados de los últimos días (RF-16).

    Útil después de migrar datos o de cambiar referencias de rutas.
    """
    config = get_settings()
    fin = datetime.now() + timedelta(days=1)
    viajes = ConsultasViajes(bootstrap.crear_uow()).listar(fin - timedelta(days=dias + 1), fin)
    generadas = 0
    for viaje in viajes:
        if viaje.estado == EstadoViaje.FINALIZADO:
            evaluar = EvaluarAlertasViaje(bootstrap.crear_uow(), config.umbral_desvio_pct)
            generadas += len(evaluar.ejecutar(viaje.id))
    typer.echo(f"{len(viajes)} viajes revisados, {generadas} alertas nuevas.")


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
        DatosCamion("AB123CD", "Scania", "R450", Decimal("600"), Decimal("40"), anio=2019)
    )
    mercedes = RegistrarCamion(uow).ejecutar(
        DatosCamion("AC456EF", "Mercedes-Benz", "Actros 2645", Decimal("500"), Decimal("38"), 2021)
    )
    juan = RegistrarChofer(uow).ejecutar(DatosChofer("Juan Pérez", "30123456"))
    maria = RegistrarChofer(uow).ejecutar(DatosChofer("María Gómez", "28987654"))
    cliente = RegistrarCliente(uow).ejecutar(
        DatosCliente("Cliente principal (demo)", "30-71234567-8", "San Juan")
    )
    cal_viva = RegistrarProducto(uow).ejecutar(DatosProducto("Cal viva"))
    RegistrarProducto(uow).ejecutar(DatosProducto("Cal hidratada"))
    # Mendoza tiene referencias configuradas; Los Andes no: usa el histórico o el camión.
    mendoza = RegistrarRuta(uow).ejecutar(
        DatosRuta(
            "Planta Albardón (SJ)", "Mendoza (MZA)", Pais.AR, Decimal("170"),
            Decimal("42"), Decimal("31"),
        )
    )  # fmt: skip
    los_andes = RegistrarRuta(uow).ejecutar(
        DatosRuta("Planta Albardón (SJ)", "Los Andes (CL)", Pais.CL, Decimal("390"))
    )

    registrar_carga = RegistrarCargaCombustible(uow)
    hoy = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
    # Cotización CLP -> ARS de los últimos días (con un hueco: esos gastos quedan "a revisar").
    for dias in range(25, -1, -1):
        if dias not in (10, 11):
            CargarCotizacion(uow).ejecutar(
                (hoy - timedelta(days=dias)).date(), Decimal("1.30") + Decimal(dias) / 1000
            )
    km = {scania.id: Decimal("125000"), mercedes.id: Decimal("98000")}
    # (camión, chofer, ruta, días atrás, km por tramo, litros ida cargado, litros regreso vacío)
    viajes = [
        (scania, juan, los_andes, 20, 390, 188, 132),
        (mercedes, maria, mendoza, 18, 170, 71, 52),
        (scania, juan, los_andes, 15, 390, 182, 130),
        (mercedes, maria, mendoza, 13, 170, 73, 54),
        (scania, juan, los_andes, 10, 390, 186, 135),
        (mercedes, maria, mendoza, 7, 170, 70, 53),
        (scania, juan, los_andes, 4, 390, 232, 134),  # ida con consumo alto -> alerta
        (mercedes, maria, mendoza, 2, 170, 72, 51),
    ]
    for camion, chofer, ruta, dias, distancia, litros_ida, litros_vuelta in viajes:
        salida = hoy - timedelta(days=dias)
        km_salida = km[camion.id]
        viaje = IniciarViaje(uow).ejecutar(
            DatosInicioViaje(
                camion.id,
                chofer.id,
                ruta.id,
                salida,
                km_salida,
                cliente_id=cliente.id,
                producto_id=cal_viva.id,
                cantidad=Decimal("28"),
            )
        )
        en_chile = ruta.pais == Pais.CL
        for horas, litros in ((2, litros_ida), (8, litros_vuelta)):
            vuelta_en_chile = en_chile and horas == 8  # la vuelta desde Chile se carga en CLP
            registrar_carga.ejecutar(
                DatosCarga(
                    camion.id,
                    salida + timedelta(hours=horas),
                    Decimal(litros),
                    Decimal("1250") if vuelta_en_chile else Decimal("1450"),
                    estacion="Copec Los Andes" if vuelta_en_chile else "YPF Ruta 40",
                    referencia_externa=f"DEMO-{viaje.id.hex[:8]}-{horas}",
                    moneda=Moneda.CLP if vuelta_en_chile else Moneda.ARS,
                )
            )
        CambiarEstadoCarga(uow).ejecutar(
            viaje.id, salida + timedelta(hours=6), km_salida + distancia, EstadoCarga.VACIO
        )
        km[camion.id] = km_salida + 2 * distancia
        FinalizarViaje(uow).ejecutar(viaje.id, salida + timedelta(hours=12), km[camion.id])
    typer.echo(
        "Datos de ejemplo cargados: 2 camiones, 2 choferes, 2 rutas y 8 viajes "
        "(ida cargado y regreso vacío)."
    )


if __name__ == "__main__":
    app()
