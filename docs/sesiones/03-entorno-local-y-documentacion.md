# Sesión 3 — Entorno local y documentación de estudio

**Objetivo:** verificar el proyecto, levantarlo en el servidor local y crear la documentación técnica
para ir aprendiendo Python a medida que el proyecto crece, con una versión Word por sesión.

## Qué se hizo
- Revisión del repositorio: `main` sincronizada con https://github.com/MMG15/Transportes-Hidalgo
  (sesiones 1 y 2 subidas; `.env` correctamente fuera de git).
- Verificación: **26 tests OK** y `ruff` sin observaciones.
- Servidor local funcionando en http://127.0.0.1:8000 con una base **SQLite temporal**
  (PostgreSQL 17 está instalado, pero falta `DB_PASSWORD` en `.env`).
- **Guía técnica** ([docs/guia-tecnica.md](../guia-tecnica.md)): referencia por temas de todo lo que usa el
  proyecto. Se actualiza en cada sesión.
- **Documentos Word** en `docs/word/`: la guía y un Word por cada sesión, con logo, colores y pie de
  página de la empresa. Se generan con `uv run python scripts/generar_word.py`.
- `.gitignore`: se agregó `*.db` (bases SQLite de prueba). `.gitattributes`: `*.docx` como binario.

## Conceptos nuevos

### Variables de entorno que pisan al `.env`
`pydantic-settings` da prioridad a las variables de entorno sobre el archivo `.env`. Definiendo
`DATABASE_URL=sqlite:///archivo.db` antes de ejecutar, el sistema usa SQLite **sin tocar código**:
es la ventaja de que la configuración esté en un solo lugar (`infrastructure/config.py`).

### Un `.docx` es un ZIP con archivos XML
Si se renombra `documento.docx` a `.zip` y se abre, aparecen `word/document.xml` (el texto),
`word/styles.xml` (los estilos), `word/footer1.xml` (el pie de página), `word/media/` (imágenes), etc.
El script modifica la plantilla de pandoc con el módulo **`zipfile`** de Python y reemplaza estilos
con expresiones regulares (**`re`**).

Lección: Word exige un **orden fijo** de los elementos XML. Un `<w:wordWrap>` puesto antes de
`<w:pBdr>` hizo que Word no pudiera abrir el archivo sin "repararlo". Se detectó validando contra el
esquema oficial antes de entregar.

### pandoc y los filtros Lua
**pandoc** convierte entre formatos (Markdown → Word). Internamente lee el documento como un
**árbol** (título → párrafo → texto, enlace, código…) y luego lo escribe en el formato de salida.
Un **filtro Lua** ([scripts/word_filtro.lua](../../scripts/word_filtro.lua)) recibe ese árbol y lo
modifica en el medio: acá convierte los enlaces a archivos locales en texto, agrega el logo y
transforma el primer título en el título del documento.

### Python usado en el generador ([scripts/generar_word.py](../../scripts/generar_word.py))
| Recurso | Para qué |
|---|---|
| `subprocess.run([...], check=True)` | Ejecutar programas externos (`pandoc`, `git`). `check=True` lanza una excepción si fallan. |
| `zipfile.ZipFile` | Leer y escribir el `.docx` (que es un ZIP). |
| `io.BytesIO` | Tratar bytes en memoria como si fueran un archivo. |
| `re.sub` / `re.compile` con `re.S` | Buscar y reemplazar bloques de XML (`re.S`: el `.` también abarca saltos de línea). |
| `match` / `case` | *Pattern matching* (Python 3.10+): elegir qué hacer según el nombre del archivo. |
| `with (A as a, B as b):` | Varios context managers en un solo `with`, entre paréntesis (Python 3.10+). |
| `tempfile.TemporaryDirectory()` | Carpeta temporal que se borra sola al salir del `with`. |
| f-strings con `{{ }}` | Las llaves dobles producen una llave literal dentro de una f-string. |
| `{**os.environ, "CLAVE": valor}` | Copiar un diccionario agregando o pisando una clave. |
| `if __name__ == "__main__":` | El código sólo corre al ejecutar el archivo, no al importarlo. |

### Builds reproducibles: `SOURCE_DATE_EPOCH`
pandoc guarda fechas dentro del `.docx`. Si cada ejecución pusiera la fecha actual, todos los Word
cambiarían siempre y git los mostraría como modificados. El script le pasa a pandoc la fecha del último
commit de cada Markdown: si el texto no cambió, el Word sale idéntico.

## Cómo seguir
- Completar `DB_PASSWORD` en `.env` para trabajar sobre PostgreSQL.
- Documento de requerimientos para la próxima etapa del proyecto.
