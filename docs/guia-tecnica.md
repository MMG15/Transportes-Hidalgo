# Guía técnica · Transportes Hidalgo

Documento de estudio del proyecto: **qué se usa de Python, para qué y dónde está en el código**.
Se actualiza cada vez que el proyecto cambia (ver [Bitácora](#13-bitácora-de-la-guía)).

<!-- solo-md:inicio -->
> **Cómo leerla en VS Code:** abrí este archivo y presioná `Ctrl+Shift+V` (vista previa) o
> `Ctrl+K V` (vista previa al costado). Los enlaces a archivos se abren con un clic; el índice
> también es navegable. El panel **Esquema** (*Outline*) del explorador muestra los títulos.
>
> **Versión Word:** [docs/word/Guia-tecnica.docx](word/Guia-tecnica.docx) (se regenera con
> `uv run python scripts/generar_word.py`).
<!-- solo-md:fin -->

---

## Índice

1. [Mapa del proyecto](#1-mapa-del-proyecto)
2. [Herramientas del entorno](#2-herramientas-del-entorno)
3. [Características del lenguaje Python](#3-características-del-lenguaje-python)
4. [Librerías externas](#4-librerías-externas)
5. [Arquitectura limpia y patrones de diseño](#5-arquitectura-limpia-y-patrones-de-diseño)
6. [Recorrido de una petición de punta a punta](#6-recorrido-de-una-petición-de-punta-a-punta)
7. [Tests](#7-tests)
8. [Ejecutar el proyecto en local](#8-ejecutar-el-proyecto-en-local)
9. [Cómo agregar una funcionalidad nueva](#9-cómo-agregar-una-funcionalidad-nueva)
10. [Ruta de estudio sugerida](#10-ruta-de-estudio-sugerida)
11. [Documentación: Markdown y Word](#11-documentación-markdown-y-word)
12. [Glosario](#12-glosario)
13. [Bitácora de la guía](#13-bitácora-de-la-guía)

---

## 1. Mapa del proyecto

```
Transportes-Hidalgo/
├── pyproject.toml        Definición del proyecto: dependencias, comando `flota`, config de pytest/ruff
├── uv.lock               Versiones exactas instaladas (no se edita a mano)
├── .env / .env.example   Configuración (contraseña de la base). .env NO se sube a git
├── alembic.ini           Configuración de migraciones
├── migrations/           Historial de cambios de la base de datos
├── docs/                 Esta guía, requisitos v1.1, análisis de brechas, notas de sesión,
│                         prompts de trabajo (docs/prompts/) y versiones Word (docs/word/)
├── tests/                Tests unitarios y de integración
└── src/flota/
    ├── domain/           Reglas del negocio (Python puro)
    ├── application/      Casos de uso (qué puede hacer el sistema)
    ├── infrastructure/   Base de datos, Excel, CSV, configuración
    ├── presentation/     API REST, panel web y consola
    ├── marca/            Colores y logos de la empresa
    └── bootstrap.py      Conecta las piezas entre sí
```

Archivos clave: [entities.py](../src/flota/domain/entities.py) ·
[consumo.py](../src/flota/domain/consumo.py) ·
[use_cases/viajes.py](../src/flota/application/use_cases/viajes.py) ·
[models.py](../src/flota/infrastructure/db/models.py) ·
[app.py](../src/flota/presentation/api/app.py) ·
[bootstrap.py](../src/flota/bootstrap.py)

---

## 2. Herramientas del entorno

| Herramienta | Para qué sirve |
|---|---|
| **Python 3.13** | Versión moderna; permite sintaxis nueva como `class Repositorio[E]` o `str \| None`. |
| **uv** | Gestor de paquetes y entornos (reemplaza `pip` + `venv`). Lee `pyproject.toml`, crea `.venv/` y fija versiones en `uv.lock`. |
| **pyproject.toml** | Archivo central: dependencias, comandos y configuración de herramientas. |
| **.venv/** | Entorno virtual: un Python aislado con las librerías de este proyecto. |
| **ruff** | Linter/formateador: detecta errores, imports sin usar y estilo inconsistente. |
| **pytest** | Framework de tests. |
| **git / GitHub** | Control de versiones. Remoto: https://github.com/MMG15/Transportes-Hidalgo |
| **pandoc** | Convierte la documentación Markdown a Word (ver [sección 11](#11-documentación-markdown-y-word)). |

El comando `flota` sale de esta sección de [pyproject.toml](../pyproject.toml):

```toml
[project.scripts]
flota = "flota.presentation.cli:app"
```

Significa: "el comando `flota` ejecuta el objeto `app` del módulo `flota/presentation/cli.py`".

Comandos útiles:

```powershell
uv sync                    # instala/actualiza dependencias según pyproject.toml
uv add nombre-paquete      # agrega una dependencia nueva
uv run pytest              # corre los tests
uv run ruff check .        # revisa el estilo
uv run ruff format .       # formatea el código
```

> Si `uv` no está en el PATH de la terminal, se puede usar el `.venv` directamente:
> `.venv\Scripts\flota.exe`, `.venv\Scripts\pytest.exe`, `.venv\Scripts\alembic.exe`.

---

## 3. Características del lenguaje Python

### 3.1 Dataclasses — las entidades del negocio

En [entities.py](../src/flota/domain/entities.py):

```python
@dataclass(kw_only=True)
class Camion:
    patente: str
    capacidad_tanque_litros: Decimal
    activo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.patente = normalizar_patente(_requerido(self.patente, "patente"))
        _positivo(self.capacidad_tanque_litros, "capacidad_tanque_litros")
```

- `@dataclass` genera `__init__`, `__repr__` y `__eq__` a partir de los campos declarados.
- `kw_only=True` obliga a crear el objeto con nombres: `Camion(patente="AB123CD", ...)`.
- `field(default_factory=uuid4)`: genera un ID **nuevo por cada objeto**. Si se escribiera
  `id = uuid4()`, se evaluaría una sola vez y todos compartirían el mismo ID.
- `__post_init__` corre después del constructor: ahí van **validaciones y normalizaciones**
  ("ab 123-cd" → "AB123CD"). Un `Camion` inválido no puede existir.
- `@dataclass(frozen=True)` (ej. `ResumenConsumo` en [consumo.py](../src/flota/domain/consumo.py))
  vuelve el objeto **inmutable**: ideal para resultados.

### 3.2 `Decimal` en lugar de `float`

```python
consumo = (litros / km * 100).quantize(DOS_DECIMALES)   # DOS_DECIMALES = Decimal("0.01")
litros = sum((c.litros for c in propias), Decimal("0"))
```

- `float` tiene errores binarios: `0.1 + 0.2 == 0.30000000000000004`. Para **dinero y litros** se usa `Decimal`.
- `.quantize(Decimal("0.01"))` redondea a 2 decimales.
- `sum(..., Decimal("0"))`: se pasa un valor inicial `Decimal` para no mezclar tipos.
- Crear siempre desde texto: `Decimal("0.1")`, nunca `Decimal(0.1)` (arrastraría el error del float).

### 3.3 `StrEnum` — valores cerrados

```python
class EstadoViaje(StrEnum):
    EN_CURSO = "en_curso"
    FINALIZADO = "finalizado"
```

Evita "strings mágicos" mal escritos y, al ser también `str`, se guarda directo en la base y en el JSON.

### 3.4 Type hints (anotaciones de tipo)

```python
def obtener(self, id: UUID) -> Camion | None: ...
```

- Python **no** las verifica al ejecutar; sirven para el editor (autocompletado, errores en VS Code),
  como documentación, y **FastAPI, Pydantic y Typer las usan para validar**.
- `X | None`: "puede ser X o nada".
- `from __future__ import annotations` (al inicio de casi todos los archivos): evalúa las anotaciones
  de forma diferida, evita problemas de referencias circulares.
- `Self`: "devuelve una instancia de esta misma clase".
- `Annotated[Tipo, extra]`: un tipo con información adicional (ver FastAPI y Typer).

### 3.5 Clases abstractas (`ABC`) y genéricos — los "puertos"

En [repositories.py](../src/flota/domain/repositories.py):

```python
class Repositorio[E](ABC):
    @abstractmethod
    def guardar(self, entidad: E) -> None: ...

class RepositorioCamiones(Repositorio[Camion]):
    @abstractmethod
    def obtener_por_patente(self, patente: str) -> Camion | None: ...
```

- `ABC` + `@abstractmethod` definen un **contrato**: no se puede instanciar una clase que no implemente esos métodos.
- `[E]` es la sintaxis de genéricos de Python 3.12+: `Repositorio[Camion]` es "un repositorio de camiones".
- Hay **dos implementaciones** del mismo contrato: SQL ([repositorios.py](../src/flota/infrastructure/db/repositorios.py))
  y en memoria para tests ([fakes.py](../tests/fakes.py)).

### 3.6 Context managers (`with`) — transacciones

En [ports.py](../src/flota/application/ports.py) y [unidad_de_trabajo.py](../src/flota/infrastructure/db/unidad_de_trabajo.py):

```python
with self._uow as uow:        # __enter__: abre la sesión de base de datos
    uow.viajes.guardar(viaje)
    uow.commit()               # confirma
# __exit__: descarta lo no confirmado y cierra la sesión, AUNQUE haya ocurrido una excepción
```

Cualquier clase con `__enter__` y `__exit__` se puede usar con `with`.

### 3.7 Excepciones propias

[exceptions.py](../src/flota/domain/exceptions.py) define una jerarquía: `ErrorDominio` →
`NoEncontrado`, `Duplicado`, `DatosInvalidos`, `ReglaNegocioViolada`.
El dominio lanza errores **con significado de negocio**; la API los traduce a HTTP en un solo lugar
([app.py](../src/flota/presentation/api/app.py)):

```python
_CODIGOS_HTTP = {NoEncontrado: 404, Duplicado: 409, DatosInvalidos: 422, ReglaNegocioViolada: 400}
```

### 3.8 Generadores (`yield`) — importación de archivos

En [mapeo.py](../src/flota/infrastructure/importacion/mapeo.py) y [lector_excel.py](../src/flota/infrastructure/importacion/lector_excel.py):

```python
yield FilaCarga(...)                # entrega una fila válida
yield ErrorLectura(numero, msg)     # o un error, sin cortar la importación
yield from procesar_filas(...)      # delega en otro generador
```

Procesan fila por fila: poca memoria con archivos grandes y una fila mala no detiene el resto.

### 3.9 Otras herramientas de la librería estándar

| Recurso | Ejemplo / dónde | Para qué |
|---|---|---|
| `@lru_cache` | [bootstrap.py](../src/flota/bootstrap.py), `get_settings` | Guarda el resultado: el motor de la base y la config se crean **una sola vez**. |
| Comprensiones | `[c for c in cargas if c.viaje_id == viaje.id]` | Filtrar/transformar en una línea. |
| `**asdict(datos)` | `Viaje(**asdict(datos))` | Convierte una dataclass en dict y la pasa como argumentos con nombre. |
| `pathlib.Path` | config, CLI, web | Rutas de archivos sin pelear con `\` y `/`. |
| `uuid4()` | entidades | IDs únicos sin depender de la base. |
| Operador morsa `:=` | [combustible.py](../src/flota/application/use_cases/combustible.py) | Asignar y evaluar en una misma expresión. |
| Descriptores (`__get__`) | columnas de SQLAlchemy | Ver la nota del bug en [sesión 2](sesiones/02-marca-y-panel-web.md#descriptores-el-bug-de-esta-sesión). |
| `match` / `case` | [generar_word.py](../scripts/generar_word.py) | *Pattern matching* (3.10+): elegir una acción según un valor. |
| `subprocess.run` | [generar_word.py](../scripts/generar_word.py) | Ejecutar programas externos (`pandoc`, `git`); `check=True` falla si el programa falla. |
| `zipfile` / `io.BytesIO` | [generar_word.py](../scripts/generar_word.py) | Leer y escribir ZIP (un `.docx` lo es); bytes en memoria como si fueran un archivo. |
| `re.sub(..., flags=re.S)` | [generar_word.py](../scripts/generar_word.py) | Reemplazos con expresiones regulares; `re.S` hace que `.` abarque saltos de línea. |
| `tempfile.TemporaryDirectory` | [generar_word.py](../scripts/generar_word.py) | Carpeta temporal que se borra sola al salir del `with`. |
| `if __name__ == "__main__":` | scripts | El bloque sólo corre al ejecutar el archivo, no al importarlo. |

---

## 4. Librerías externas

### 4.1 FastAPI + Uvicorn — API y servidor web

- **FastAPI** es el framework; **Uvicorn** el servidor que lo ejecuta (`flota servidor`).
- Las rutas se declaran con decoradores y **los type hints son la validación**
  ([routers/viajes.py](../src/flota/presentation/api/routers/viajes.py)):

  ```python
  @router.get("", response_model=list[ViajeLeer])
  def listar_viajes(uow: UoW, desde: date, hasta: date, camion_id: UUID | None = None):
  ```

  `desde: date` hace que FastAPI exija y convierta el parámetro (si falta → **422**).
  Con esa misma información genera la documentación en `/docs`.
- **Inyección de dependencias** ([dependencias.py](../src/flota/presentation/api/dependencias.py)):

  ```python
  UoW = Annotated[UnidadDeTrabajo, Depends(obtener_uow)]
  ```

  La ruta "pide" una unidad de trabajo y FastAPI la crea. En tests se reemplaza con `app.dependency_overrides`.
- `APIRouter` agrupa rutas por tema; `@app.exception_handler` captura errores globalmente;
  `StaticFiles` sirve CSS e imágenes.

### 4.2 Pydantic y pydantic-settings — validación y configuración

[schemas.py](../src/flota/presentation/api/schemas.py):

```python
class CamionCrear(BaseModel):
    patente: str = Field(min_length=6, max_length=15)
```

- Valida el JSON que entra; si no cumple responde 422 con el detalle.
- `ConfigDict(from_attributes=True)` → `ViajeLeer.model_validate(viaje)` arma la respuesta desde una entidad.
- `PlainSerializer(float)` envía los `Decimal` como número en el JSON.
- **pydantic-settings** ([config.py](../src/flota/infrastructure/config.py)) lee `.env` y variables de
  entorno con tipos (`DB_PORT=5432` llega como `int`). Una variable de entorno pisa al `.env`:
  así se puede usar `DATABASE_URL` para apuntar a otra base sin tocar código.

### 4.3 SQLAlchemy 2.0 — ORM

[models.py](../src/flota/infrastructure/db/models.py):

```python
class CamionModel(_ConAuditoria, Base):
    __tablename__ = "camiones"
    patente: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    capacidad_tanque_litros: Mapped[Decimal] = mapped_column(Numeric(10, 2))
```

- Mapea clases a tablas con el estilo tipado moderno (`Mapped` + `mapped_column`).
- **Decisión clave:** `CamionModel` (tabla) ≠ `Camion` (entidad). El repositorio traduce entre ambos,
  así el negocio no depende de la base.
- `_ConAuditoria` es un **mixin**: aporta `creado_en` a todas las tablas por herencia múltiple.
- `Session` / `sessionmaker`: conexión + transacción. `pool_pre_ping=True` verifica que la conexión siga viva.
- **psycopg 3** es el driver que habla con PostgreSQL.

### 4.4 Alembic — migraciones

Versiona el esquema de la base (como git, pero de tablas). Cada cambio es un archivo en
[migrations/versions/](../migrations/versions/).

```powershell
uv run alembic revision --autogenerate -m "agrega campo x"   # genera la migración comparando models.py con la base
uv run alembic upgrade head                                  # aplica las pendientes
uv run alembic downgrade -1                                  # deshace la última
```

Siempre **revisar** el archivo generado antes de aplicarlo.

### 4.5 Jinja2 — panel web

- Plantillas en [templates/](../src/flota/presentation/web/templates/).
- `{% extends "base.html" %}` + `{% block contenido %}`: herencia, todas comparten menú y encabezado.
- `{% macro %}` en `_macros.html`: componentes reutilizables.
- Filtros (`{{ valor | numero(1) }}`) definidos en [formato.py](../src/flota/presentation/web/formato.py): formato argentino.
- **Autoescape**: `<` se convierte en `&lt;`, evita inyección de HTML.
- Patrón **Post/Redirect/Get** en [rutas.py](../src/flota/presentation/web/rutas.py): tras un `POST` se
  redirige con 303, así recargar no reenvía el formulario.
- Los colores de [marca](../src/flota/marca/__init__.py) se inyectan como variables CSS (`--azul`), y
  el mismo módulo los usa el Excel: un solo lugar para cambiar la paleta.
- **python-multipart** permite a FastAPI recibir formularios y archivos subidos.

### 4.6 openpyxl + Pillow — Excel

- **openpyxl** lee los Excel importados ([lector_excel.py](../src/flota/infrastructure/importacion/lector_excel.py))
  y genera reportes con estilos ([generador_excel.py](../src/flota/infrastructure/excel/generador_excel.py)).
- **Pillow** (imágenes): se usó para preparar los logos, y openpyxl la necesita para insertar el logo en el Excel.

### 4.7 Typer — comandos de consola

[cli.py](../src/flota/presentation/cli.py):

```python
@app.command()
def importar(archivo: Path, origen: Annotated[OrigenDato, typer.Option(help="excel o tarjeta")] = ...):
```

Igual que FastAPI: los type hints generan argumentos, `--help` y validación. Cada `@app.command()` es un subcomando.

---

## 5. Arquitectura limpia y patrones de diseño

```
presentation  ──►  application  ──►  domain
      │                                 ▲
      └──── bootstrap ──► infrastructure ┘  (implementa los puertos del dominio/aplicación)
```

**Regla de oro:** `domain/` no importa nada de FastAPI, SQLAlchemy ni openpyxl. Por eso el negocio se
testea sin base de datos y se puede cambiar de tecnología tocando sólo `infrastructure/` y `bootstrap.py`.

| Patrón | Dónde | Idea |
|---|---|---|
| **Repositorio** | `domain/repositories.py` | El caso de uso pide datos sin saber SQL. |
| **Unidad de trabajo** | `application/ports.py` | Varias operaciones, una sola transacción. |
| **Inyección de dependencias** | casos de uso, `Depends` | Las piezas reciben lo que necesitan; en tests se pasan fakes. |
| **Adaptador** | `LectorExcel`, `LectorCsv` | Distintas fuentes, mismo contrato (`LectorCargas`). |
| **Raíz de composición** | `bootstrap.py` | Único lugar donde se eligen implementaciones concretas. |
| **Servicio de dominio** | `domain/consumo.py` | Lógica que involucra varias entidades. |
| **DTO** | `application/dto.py` | Objetos simples para mover datos entre capas. |

---

## 6. Recorrido de una petición de punta a punta

`POST /api/v1/viajes` (iniciar un viaje):

1. **Uvicorn** recibe el HTTP y se lo pasa a **FastAPI**.
2. **Pydantic** (`ViajeCrear`) valida el JSON.
3. `Depends` arma la **Unidad de Trabajo** real (vía `bootstrap.py`).
4. La ruta llama al caso de uso `IniciarViaje(uow).ejecutar(...)` ([viajes.py](../src/flota/application/use_cases/viajes.py)).
5. Se aplican reglas: ¿camión activo?, ¿ya tiene viaje en curso? → si falla, `ReglaNegocioViolada`.
6. El repositorio SQL convierte `Viaje` → `ViajeModel` y **SQLAlchemy** hace el `INSERT`.
7. `commit()` → respuesta con `ViajeLeer`. Si hubo error, el `exception_handler` lo traduce a 400/404/409/422.

---

## 7. Tests

- **Unitarios** ([tests/unit/](../tests/unit/)): dominio y casos de uso con los **fakes en memoria**
  ([fakes.py](../tests/fakes.py)). Rápidos, sin base.
- **Integración** ([tests/integration/](../tests/integration/)): API, panel y lectores con **SQLite**
  y el `TestClient` de FastAPI (usa **httpx**).
- **Fixtures** en [conftest.py](../tests/integration/conftest.py): objetos que pytest prepara y
  entrega a cada test que los pide por nombre.

```powershell
uv run pytest              # todos
uv run pytest -k viaje     # sólo los que contienen "viaje" en el nombre
uv run pytest -x -v        # detenerse en el primer fallo, con detalle
```

---

## 8. Ejecutar el proyecto en local

**Con PostgreSQL** (requiere `DB_PASSWORD` en `.env`):

```powershell
uv run flota crear-db
uv run alembic upgrade head
uv run flota datos-demo        # opcional
uv run flota servidor          # http://127.0.0.1:8000 · API en /docs
```

**Con SQLite, para probar rápido** (sin contraseña, base en un archivo):

```powershell
$env:DATABASE_URL = "sqlite:///flota-prueba.db"
uv run alembic upgrade head
uv run flota datos-demo
uv run flota servidor
```

> El archivo `.db` está en `.gitignore` (no se sube). Los datos de SQLite no pasan a PostgreSQL.

---

## 9. Cómo agregar una funcionalidad nueva

Casi todo requerimiento sigue el mismo camino, de adentro hacia afuera:

1. **Dominio**: entidad, campo o regla en `domain/` + test unitario.
2. **Aplicación**: caso de uso en `application/use_cases/` + test con fakes.
3. **Infraestructura**: columna/tabla en `models.py`, traducción en `repositorios.py`, migración con Alembic.
4. **Presentación**: esquema Pydantic + ruta en la API y/o página en el panel + test de integración.
5. `uv run pytest` y `uv run ruff check .` en verde, registrar la sesión en `docs/sesiones/` y regenerar los Word (`uv run python scripts/generar_word.py`).

---

## 10. Ruta de estudio sugerida

De lo más puro a lo más técnico:

1. [entities.py](../src/flota/domain/entities.py) → [consumo.py](../src/flota/domain/consumo.py)
2. [test_dominio.py](../tests/unit/test_dominio.py) (ver cómo se prueba)
3. [use_cases/viajes.py](../src/flota/application/use_cases/viajes.py) → [fakes.py](../tests/fakes.py) → [test_casos_de_uso.py](../tests/unit/test_casos_de_uso.py)
4. [infrastructure/db/](../src/flota/infrastructure/db/)
5. [presentation/api/](../src/flota/presentation/api/) → [presentation/web/](../src/flota/presentation/web/)

Ejercicio: cambiar un valor en un test, correr `pytest` y leer el error. Es la forma más rápida de entender cada pieza.

---

## 11. Documentación: Markdown y Word

La documentación se escribe en **Markdown** (fácil de editar y versionar en git) y se genera una
**versión Word** de cada documento:

| Markdown (fuente) | Word (generado) |
|---|---|
| `docs/guia-tecnica.md` | `docs/word/Guia-tecnica.docx` |
| `docs/sesiones/NN-nombre.md` | `docs/word/Sesion-NN-nombre.docx` (uno por sesión) |

```powershell
uv run python scripts/generar_word.py     # regenera todos los Word
```

Cómo funciona ([generar_word.py](../scripts/generar_word.py) + [word_filtro.lua](../scripts/word_filtro.lua)):

1. Toma la plantilla Word de pandoc y le aplica la marca: colores de `flota.marca`, márgenes A4 y un
   pie de página con "Página N de M". Un `.docx` es un **ZIP de archivos XML**; se edita con `zipfile` y `re`.
2. **pandoc** lee cada Markdown como un árbol de elementos y el **filtro Lua** lo ajusta: logo arriba,
   primer título como título del documento, enlaces a archivos locales convertidos en texto.
3. Escribe el `.docx` con fecha fija (`SOURCE_DATE_EPOCH` = último commit): si el texto no cambió,
   el Word sale idéntico y git no lo marca como modificado. Como pandoc no aplica esa fecha a las
   partes que copia de la plantilla, el script reescribe el ZIP con la misma fecha en todas las entradas.

Reglas:

- **Nunca editar los Word a mano**: se pisan al regenerar. Se edita el Markdown.
- Lo que va entre `<!-- solo-md:inicio -->` y `<!-- solo-md:fin -->` aparece sólo en VS Code, no en el Word.
- Word exige un orden fijo de los elementos XML; si se modifican estilos en el script, validar que el
  documento abra sin aviso de "reparar".

---

## 12. Glosario

| Término | Significado |
|---|---|
| **Entidad** | Objeto del negocio con identidad propia (un camión, un viaje). |
| **Caso de uso** | Una acción que el sistema permite (iniciar viaje, importar cargas). |
| **Puerto** | Interfaz (contrato) que define qué se necesita, sin decir cómo. |
| **Adaptador** | Implementación concreta de un puerto (SQL, Excel, CSV). |
| **ORM** | Traduce objetos Python ↔ tablas SQL. |
| **Migración** | Cambio versionado del esquema de la base. |
| **Fake** | Implementación falsa (en memoria) usada en tests. |
| **Fixture** | Dato u objeto preparado por pytest para los tests. |
| **Endpoint** | Una URL + método HTTP de la API (`GET /api/v1/camiones`). |
| **422 / 404 / 409 / 400** | Datos inválidos / no existe / duplicado / regla de negocio violada. |
| **Entorno virtual** | Instalación aislada de Python y librerías para un proyecto. |

---

## 13. Bitácora de la guía

Cada cambio del proyecto agrega una línea acá y, si introduce conceptos nuevos, los suma en la sección que corresponda.

| Fecha | Cambio | Secciones |
|---|---|---|
| 2026-10-21 | Creación de la guía a partir de las sesiones 1 y 2. Proyecto verificado en local (26 tests OK, servidor con SQLite). | Todas |
| 2026-10-21 | Versión Word de la guía y de cada sesión (`scripts/generar_word.py`). Conceptos: `match`/`case`, `subprocess`, `zipfile`, `re`, pandoc y filtros Lua. | 2, 3.9, 11 |
| 2026-10-26 | Incorporación del [documento de requisitos v1.1](requisitos_v1.1.md) y del [análisis de brechas](brechas-requisitos-v1.1.md) (cobertura, decisiones pendientes y plan de sesiones). Sin cambios de código. | 1 |

Notas por sesión: [01 · Base del sistema](sesiones/01-base-del-sistema.md) ·
[02 · Marca y panel web](sesiones/02-marca-y-panel-web.md) ·
[03 · Entorno local y documentación](sesiones/03-entorno-local-y-documentacion.md)
