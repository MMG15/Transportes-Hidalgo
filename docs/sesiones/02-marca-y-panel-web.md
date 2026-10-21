# Sesión 2 — Marca Hidalgo, panel web y repositorio

**Objetivo:** aplicar la identidad visual de Transportes Hidalgo, crear el panel web y publicar el proyecto en GitHub.

## Qué se hizo
- Proyecto movido a `C:\Users\Usuario\OneDrive\Documentos\Transportes-Hidalgo` y conectado a
  https://github.com/MMG15/Transportes-Hidalgo
- Paleta extraída de los píxeles del logo: **azul `#0706E5`** y **naranja `#F56A11`**.
- Logos convertidos a PNG con fondo transparente, más `favicon.ico` e ícono para celulares.
- Módulo `flota/marca`: única fuente de colores y logos.
- **Panel web** (`/`): tablero con indicadores, viajes (iniciar/finalizar), combustible (carga manual e
  importación de archivos), reportes (con descarga de Excel) y catálogo (flota y clientes).
- **Excel** con portada: logo, título, período, franja naranja y encabezados azules.
- Documentación de la API (`/docs`) con el favicon de la empresa.
- **Bug corregido** de la sesión 1: los listados de camiones/choferes/clientes/productos fallaban.
- Tests: de 20 a 26.

## Conceptos nuevos

### Jinja2 (plantillas HTML)
- `{% extends "base.html" %}` + `{% block contenido %}`: herencia. Todas las páginas comparten encabezado y menú.
- `{% macro %}` (`_macros.html`): funciones reutilizables dentro de las plantillas.
- Filtros (`{{ valor | numero(1) }}`): funciones Python registradas en `web/formato.py` para mostrar
  números y fechas en formato argentino.
- **Autoescape**: Jinja convierte `<` en `&lt;` automáticamente. Por eso un mensaje con HTML malicioso no se ejecuta.

### Post / Redirect / Get
Los formularios hacen `POST`, el servidor ejecuta el caso de uso y responde con una **redirección 303**
a la página (con `?ok=...` o `?error=...`). Si el usuario recarga, no se reenvía el formulario.

### Variables CSS como puente entre Python y el diseño
`base.html` recorre `marca.COLORES` y genera `:root { --azul: #0706E5; ... }`. El CSS sólo usa
`var(--azul)`. Cambiando un color en Python cambian el panel **y** el Excel.

### Descriptores (el bug de esta sesión)
Un *descriptor* es un objeto con método `__get__` que Python ejecuta al leerlo como atributo.
Las columnas de SQLAlchemy (`CamionModel.patente`) son descriptores: guardadas como atributo de
clase en el repositorio y leídas con `self.orden`, SQLAlchemy intentaba buscar "patente" en el
repositorio. Solución: guardar una *expresión* (`CamionModel.patente.asc()`), que no es descriptor.
Lección: un test que cubre el camino real (`GET /camiones`) encuentra lo que la lectura no ve.

### Otros
- `fixture` en `tests/integration/conftest.py`: pytest la comparte entre archivos de tests sin importarla.
- `StaticFiles`: FastAPI sirve CSS e imágenes desde una carpeta.
- Pillow: librería de imágenes. Se usó para recortar el logo y quitarle el fondo, y openpyxl la usa para
  insertar el logo en el Excel.
- `.gitattributes`: normaliza los finales de línea (Windows usa CRLF, Linux/GitHub LF).
- CSS `minmax(min(320px, 100%), 1fr)`: grillas que se adaptan al celular sin desbordar.
