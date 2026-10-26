from datetime import datetime
from decimal import Decimal

from openpyxl import Workbook

from flota.combustible.application.dto import ErrorLectura, FilaCarga
from flota.combustible.infrastructure.importacion import LectorCsv, LectorExcel
from flota.combustible.infrastructure.importacion.mapeo import a_decimal


def test_numeros_en_formato_argentino_e_ingles():
    assert a_decimal("1.234,56") == Decimal("1234.56")
    assert a_decimal("1,234.56") == Decimal("1234.56")
    assert a_decimal("350,5") == Decimal("350.5")
    assert a_decimal("$ 1.450") == Decimal("1450")
    assert a_decimal(350.5) == Decimal("350.5")


def test_csv_de_tarjeta_con_punto_y_coma_y_alias(tmp_path):
    archivo = tmp_path / "tarjeta.csv"
    archivo.write_text(
        "Fecha y Hora;Dominio;Cantidad Litros;Precio Unitario;Establecimiento;Nro Comprobante\n"
        "21/10/2026 08:30;AB 123 CD;350,50;1.450,00;YPF Ruta 5;0001-123\n"
        "fecha mala;AB123CD;100;;;\n",
        encoding="latin-1",
    )
    filas = list(LectorCsv().leer(archivo))

    assert isinstance(filas[0], FilaCarga)
    assert filas[0].fecha == datetime(2026, 10, 21, 8, 30)
    assert filas[0].litros == Decimal("350.50")
    assert filas[0].precio_litro == Decimal("1450.00")
    assert filas[0].referencia == "0001-123"
    assert isinstance(filas[1], ErrorLectura)
    assert filas[1].numero_fila == 3


def test_excel_sin_columnas_obligatorias(tmp_path):
    archivo = tmp_path / "malo.xlsx"
    libro = Workbook()
    libro.active.append(["fecha", "litros"])
    libro.save(archivo)

    (error,) = LectorExcel().leer(archivo)
    assert isinstance(error, ErrorLectura)
    assert "patente" in error.mensaje
