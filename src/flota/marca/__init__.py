"""Identidad visual de Transportes Hidalgo.

Fuente única de colores y logos: la usan el panel web (CSS) y los reportes Excel.
Los colores base se tomaron de los píxeles del logo oficial.
"""

from pathlib import Path

NOMBRE_EMPRESA = "Transportes Hidalgo"

CARPETA_IMG = Path(__file__).parent / "img"
LOGO = CARPETA_IMG / "logo-hidalgo.png"
ISOTIPO = CARPETA_IMG / "isotipo-hidalgo.png"
FAVICON = CARPETA_IMG / "favicon.ico"

COLORES: dict[str, str] = {
    # Marca
    "azul": "#0706E5",  # azul del logo
    "azul-oscuro": "#06057F",  # barra de navegación, títulos
    "azul-claro": "#E9E9FD",  # fondos suaves, encabezados de tabla
    "naranja": "#F56A11",  # naranja del logo: acentos y botones secundarios
    "naranja-oscuro": "#B84A06",  # naranja legible como texto sobre blanco
    "naranja-claro": "#FEEBDD",  # fondo de filas con alerta
    # Neutros
    "fondo": "#F4F5FA",
    "superficie": "#FFFFFF",
    "borde": "#DCDDEA",
    "texto": "#16172B",
    "texto-suave": "#5B5E78",
    # Estados
    "exito": "#1B7F3B",
    "exito-claro": "#E6F4EA",
    "error": "#C62828",
    "error-claro": "#FDECEC",
}


def color_excel(nombre: str) -> str:
    """openpyxl espera el color sin '#': 'azul' -> '0706E5'."""
    return COLORES[nombre].removeprefix("#")
