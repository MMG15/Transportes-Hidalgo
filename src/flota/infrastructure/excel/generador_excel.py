"""Reporte de consumo en Excel con formato, filtros y alertas resaltadas."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from flota.application.dto import ReporteConsumo
from flota.application.ports import GeneradorReporte

_ENCABEZADO_FONDO = PatternFill("solid", fgColor="1F4E78")
_ENCABEZADO_FUENTE = Font(bold=True, color="FFFFFF")
_ALERTA_FONDO = PatternFill("solid", fgColor="F8CBAD")
_FORMATO_FECHA = "dd/mm/yyyy hh:mm"
_FORMATO_NUM = "#,##0.00"
_FORMATO_PCT = '0.0"%"'

COLUMNAS_PLANTILLA = [
    "fecha",
    "patente",
    "litros",
    "precio_litro",
    "odometro_km",
    "estacion",
    "referencia",
]


class GeneradorReporteExcel(GeneradorReporte):
    def generar(self, reporte: ReporteConsumo, destino: Path | BinaryIO) -> None:
        libro = Workbook()
        self._hoja_viajes(libro.active, reporte)
        self._hoja_resumen(libro.create_sheet("Resumen por camión"), reporte)
        libro.save(destino)

    def _hoja_viajes(self, hoja: Worksheet, reporte: ReporteConsumo) -> None:
        hoja.title = "Consumo por viaje"
        encabezados = [
            ("Salida", 17, _FORMATO_FECHA),
            ("Llegada", 17, _FORMATO_FECHA),
            ("Estado", 11, None),
            ("Patente", 10, None),
            ("Chofer", 22, None),
            ("Cliente", 28, None),
            ("Producto", 16, None),
            ("Cantidad", 10, _FORMATO_NUM),
            ("Unidad", 7, None),
            ("Origen", 18, None),
            ("Destino", 18, None),
            ("Km", 10, _FORMATO_NUM),
            ("Litros", 10, _FORMATO_NUM),
            ("Costo $", 13, _FORMATO_NUM),
            ("L/100km", 10, _FORMATO_NUM),
            ("Ref. L/100km", 12, _FORMATO_NUM),
            ("Desvío", 9, _FORMATO_PCT),
            ("L por unidad", 12, _FORMATO_NUM),
            ("Alerta", 8, None),
        ]
        _escribir_encabezado(hoja, encabezados)
        for f in reporte.filas:
            hoja.append(
                [
                    f.fecha_salida,
                    f.fecha_llegada,
                    f.estado,
                    f.patente,
                    f.chofer,
                    f.cliente,
                    f.producto,
                    f.cantidad,
                    f.unidad,
                    f.origen,
                    f.destino,
                    f.km_recorridos,
                    f.litros,
                    f.costo,
                    f.consumo_l100km,
                    f.consumo_referencia_l100km,
                    f.desvio_pct,
                    f.litros_por_unidad,
                    "SÍ" if f.alerta else "",
                ]
            )
            if f.alerta:
                for celda in hoja[hoja.max_row]:
                    celda.fill = _ALERTA_FONDO
        _aplicar_formatos(hoja, encabezados)

    def _hoja_resumen(self, hoja: Worksheet, reporte: ReporteConsumo) -> None:
        encabezados = [
            ("Patente", 10, None),
            ("Viajes", 8, None),
            ("Km", 12, _FORMATO_NUM),
            ("Litros", 12, _FORMATO_NUM),
            ("Costo $", 14, _FORMATO_NUM),
            ("L/100km promedio", 16, _FORMATO_NUM),
            ("Ref. L/100km", 12, _FORMATO_NUM),
            ("Desvío", 9, _FORMATO_PCT),
            ("Viajes con alerta", 16, None),
        ]
        _escribir_encabezado(hoja, encabezados)
        for r in reporte.resumen_por_camion:
            hoja.append(
                [
                    r.patente,
                    r.viajes,
                    r.km_recorridos,
                    r.litros,
                    r.costo,
                    r.consumo_promedio_l100km,
                    r.consumo_referencia_l100km,
                    r.desvio_pct,
                    r.viajes_con_alerta,
                ]
            )
        _aplicar_formatos(hoja, encabezados)
        hoja.append([])
        hoja.append([f"Período: {reporte.desde:%d/%m/%Y} al {reporte.hasta:%d/%m/%Y}"])


def _escribir_encabezado(hoja: Worksheet, encabezados: list[tuple]) -> None:
    hoja.append([titulo for titulo, _, _ in encabezados])
    for celda in hoja[1]:
        celda.fill = _ENCABEZADO_FONDO
        celda.font = _ENCABEZADO_FUENTE
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    hoja.freeze_panes = "A2"  # el encabezado queda fijo al hacer scroll


def _aplicar_formatos(hoja: Worksheet, encabezados: list[tuple]) -> None:
    for indice, (_, ancho, formato) in enumerate(encabezados, start=1):
        letra = get_column_letter(indice)
        hoja.column_dimensions[letra].width = ancho
        if formato:
            for (celda,) in hoja.iter_rows(min_row=2, min_col=indice, max_col=indice):
                celda.number_format = formato
    hoja.auto_filter.ref = hoja.dimensions


def crear_plantilla_importacion(destino: Path | BinaryIO) -> None:
    """Planilla vacía con las columnas que entiende el importador, más una fila de ejemplo."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Cargas"
    encabezados = [(c, 16, None) for c in COLUMNAS_PLANTILLA]
    _escribir_encabezado(hoja, encabezados)
    hoja.append(["21/10/2026 08:30", "AB123CD", 350.5, 1450.0, 125400, "YPF Ruta 5", "T-0001"])
    _aplicar_formatos(hoja, encabezados)
    libro.save(destino)
