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

El código está organizado **por módulo** (como el documento de requisitos: MOD-01, MOD-02, …) y,
dentro de cada módulo, **por capa**.

```
Transportes-Hidalgo/
├── pyproject.toml        Dependencias, comando `flota`, configuración de pytest/ruff
├── uv.lock               Versiones exactas instaladas (no se edita a mano)
├── .env / .env.example   Configuración (contraseña de la base). .env NO se sube a git
├── alembic.ini           Configuración de migraciones
├── migrations/versions/  Historial de cambios de la base de datos
├── docs/                 Esta guía, requisitos v1.1, análisis de brechas, notas de sesión, Word
├── scripts/              Generador de los documentos Word
├── tests/                unit/ (sin base) · integration/ (SQLite) · fakes.py · escenarios.py
└── src/flota/
    ├── shared/           Común a todos: errores, validaciones, Repositorio[E], UnidadDeTrabajo, db, config
    ├── catalogo/         MOD-01 Camiones, choferes, clientes y productos
    ├── viajes/           MOD-02 Rutas, viajes y tramos (cargado / vacío)
    ├── combustible/      MOD-03 Cargas, importación de tarjeta y cálculo de consumo
    ├── reportes/         MOD-12 Tablero, reportes y Excel (sólo lectura)
    ├── web/              Plantillas, estilos y utilidades del panel
    ├── marca/            Colores y logos de la empresa
    ├── bootstrap.py      Raíz de composición: elige las implementaciones concretas
    ├── unidad_de_trabajo.py   Unidad de trabajo concreta (conoce todos los repositorios)
    ├── dependencias.py   Inyección de dependencias de FastAPI
    ├── modelos.py        Registro de todas las tablas (lo usan Alembic y los tests)
    ├── main.py           Aplicación FastAPI (API + panel)
    └── cli.py            Comandos de consola
```

Cada módulo tiene las capas que necesita:

```
viajes/
├── domain/           entidades.py (Ruta, Viaje, TramoViaje) · repositorios.py (puertos)
├── application/      casos_de_uso.py (IniciarViaje, CambiarEstadoCarga…) · puertos.py (UoWViajes)
├── infrastructure/   modelos.py (tablas) · repositorios.py (SQLAlchemy)
└── presentation/     api.py (REST) · esquemas.py (Pydantic) · web.py (panel)
```

Archivos clave para empezar: [viajes/domain/entidades.py](../src/flota/viajes/domain/entidades.py) ·
[combustible/domain/consumo.py](../src/flota/combustible/domain/consumo.py) ·
[viajes/application/casos_de_uso.py](../src/flota/viajes/application/casos_de_uso.py) ·
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
| **PostgreSQL 17** | Base de datos del sistema. |
| **git / GitHub** | Control de versiones. Remoto: https://github.com/MMG15/Transportes-Hidalgo |
| **pandoc** | Convierte la documentación Markdown a Word (ver [sección 11](#11-documentación-markdown-y-word)). |

El comando `flota` sale de esta sección de [pyproject.toml](../pyproject.toml):

```toml
[project.scripts]
flota = "flota.cli:app"
```

Significa: "el comando `flota` ejecuta el objeto `app` del módulo `flota/cli.py`".

```powershell
uv sync                    # instala/actualiza dependencias según pyproject.toml
uv add nombre-paquete      # agrega una dependencia nueva
uv run pytest              # corre los tests
uv run ruff check .        # revisa el estilo
uv run ruff format .       # formatea el código
```

> Si `uv` no está en el PATH de la terminal, se puede usar el `.venv` directamente:
> `.venv\Scripts\flota.exe`, `.venv\Scripts\pytest.exe`, `.venv\Scripts\alembic.exe`.
>
> El proyecto vive en OneDrive: si `uv sync` falla con "Acceso denegado", suele ser OneDrive
> sincronizando un archivo del `.venv`; reintentar suele alcanzar.

---

## 3. Características del lenguaje Python

### 3.1 Dataclasses — las entidades del negocio

En [catalogo/domain/entidades.py](../src/flota/catalogo/domain/entidades.py):

```python
@dataclass(kw_only=True)
class Camion:
    patente: str
    capacidad_tanque_litros: Decimal
    km_actual: Decimal | None = None
    activo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.patente = normalizar_patente(requerido(self.patente, "patente"))
        positivo(self.capacidad_tanque_litros, "capacidad_tanque_litros")

    def registrar_km(self, km: Decimal) -> None:
        if self.km_actual is None or km > self.km_actual:   # el odómetro nunca retrocede
            self.km_actual = km
```

- `@dataclass` genera `__init__`, `__repr__` y `__eq__` a partir de los campos declarados.
- `kw_only=True` obliga a crear el objeto con nombres: `Camion(patente="AB123CD", ...)`.
- `field(default_factory=uuid4)`: genera un ID **nuevo por cada objeto**. Si se escribiera
  `id = uuid4()`, se evaluaría una sola vez y todos compartirían el mismo ID. Lo mismo con listas:
  `tramos: list[TramoViaje] = field(default_factory=list)`.
- `__post_init__` corre después del constructor: ahí van **validaciones y normalizaciones**.
  Un `Camion` inválido no puede existir.
- Los **métodos** expresan reglas del negocio (`registrar_km`, `Viaje.finalizar`): el estado de la
  entidad sólo cambia a través de ellos.
- `@dataclass(frozen=True)` (ej. `ResumenConsumo`) vuelve el objeto **inmutable**: ideal para resultados.

### 3.2 `@classmethod` como fábrica

En [viajes/domain/entidades.py](../src/flota/viajes/domain/entidades.py):

```python
@classmethod
def iniciar(cls, *, camion_id, chofer_id, ruta_id, fecha_salida, km_salida,
            estado_carga=EstadoCarga.CARGADO, ...) -> Viaje:
    primer_tramo = TramoViaje(estado_carga=estado_carga, fecha_inicio=fecha_salida, km_inicio=km_salida)
    return cls(..., tramos=[primer_tramo])
```

Un `@classmethod` recibe la **clase** (`cls`) en lugar de una instancia. Se usa como "constructor con
nombre": `Viaje.iniciar(...)` crea un viaje nuevo con su primer tramo, mientras que el constructor
normal `Viaje(...)` lo usa el repositorio para reconstruir un viaje guardado (con todos sus tramos).
El `*` en la firma obliga a pasar todo lo que sigue por nombre.

### 3.3 `Decimal` en lugar de `float`

```python
consumo = (litros / km * 100).quantize(DOS_DECIMALES)   # DOS_DECIMALES = Decimal("0.01")
litros = sum((c.litros for c in propias), Decimal("0"))
```

- `float` tiene errores binarios: `0.1 + 0.2 == 0.30000000000000004`. Para **dinero y litros** se usa `Decimal`.
- `.quantize(Decimal("0.01"))` redondea a 2 decimales.
- `sum(..., Decimal("0"))`: se pasa un valor inicial `Decimal` para no mezclar tipos.
- Crear siempre desde texto: `Decimal("0.1")`, nunca `Decimal(0.1)` (arrastraría el error del float).

### 3.4 `StrEnum` — valores cerrados

```python
class EstadoCarga(StrEnum):
    CARGADO = "cargado"
    VACIO = "vacio"
```

Evita "strings mágicos" mal escritos y, al ser también `str`, se guarda directo en la base y en el
JSON, y se compara con texto: `EstadoCarga.VACIO == "vacio"` es `True` (por eso una plantilla puede
buscar `historicos["cargado"]` en un diccionario cuyas claves son `EstadoCarga`).

### 3.5 Type hints (anotaciones de tipo)

```python
def obtener(self, id: UUID) -> Camion | None: ...
```

- Python **no** las verifica al ejecutar; sirven para el editor (autocompletado, errores en VS Code),
  como documentación, y **FastAPI, Pydantic y Typer las usan para validar**.
- `X | None`: "puede ser X o nada".
- `from __future__ import annotations`: evalúa las anotaciones de forma diferida, evita problemas de
  referencias circulares.
- `Self`: "devuelve una instancia de esta misma clase".
- `Annotated[Tipo, extra]`: un tipo con información adicional (ver FastAPI y Typer).

### 3.6 Clases abstractas (`ABC`) y genéricos — los repositorios

En [shared/domain/repositorio.py](../src/flota/shared/domain/repositorio.py) y
[viajes/domain/repositorios.py](../src/flota/viajes/domain/repositorios.py):

```python
class Repositorio[E](ABC):
    @abstractmethod
    def guardar(self, entidad: E) -> None: ...

class RepositorioRutas(Repositorio[Ruta]):
    @abstractmethod
    def obtener_por_origen_destino(self, origen: str, destino: str) -> Ruta | None: ...
```

- `ABC` + `@abstractmethod` definen un **contrato**: no se puede instanciar una clase que no implemente esos métodos.
- `[E]` es la sintaxis de genéricos de Python 3.12+: `Repositorio[Ruta]` es "un repositorio de rutas".
- Hay **dos implementaciones** del mismo contrato: SQL
  ([viajes/infrastructure/repositorios.py](../src/flota/viajes/infrastructure/repositorios.py))
  y en memoria para tests ([fakes.py](../tests/fakes.py)).

### 3.7 `Protocol` — interfaces "por forma" (la unidad de trabajo de cada módulo)

En [viajes/application/puertos.py](../src/flota/viajes/application/puertos.py):

```python
class UoWViajes(UoWCatalogo, Protocol):
    rutas: RepositorioRutas
    viajes: RepositorioViajes
```

Un `Protocol` describe **qué atributos y métodos debe tener** un objeto, sin obligarlo a heredar de
nadie (*tipado estructural* o *duck typing* con tipos). Cada módulo declara **sólo los repositorios
que usa**; la clase concreta `UnidadDeTrabajoSql` ([unidad_de_trabajo.py](../src/flota/unidad_de_trabajo.py))
los tiene todos, así que cumple los protocolos de todos los módulos. Es el **principio de segregación
de interfaces** (la "I" de SOLID): nadie depende de lo que no usa.

| | `ABC` | `Protocol` |
|---|---|---|
| Cómo se cumple | Heredando explícitamente | Teniendo los atributos/métodos (sin heredar) |
| Se usa para | Repositorios (contrato con implementación obligatoria) | Unidad de trabajo por módulo |

### 3.8 Context managers (`with`) — transacciones

En [shared/application/unidad_de_trabajo.py](../src/flota/shared/application/unidad_de_trabajo.py):

```python
with self._uow as uow:        # __enter__: abre la sesión de base de datos
    uow.viajes.guardar(viaje)
    uow.commit()               # confirma
# __exit__: descarta lo no confirmado y cierra la sesión, AUNQUE haya ocurrido una excepción
```

Cualquier clase con `__enter__` y `__exit__` se puede usar con `with`.

### 3.9 Excepciones propias

[shared/domain/errores.py](../src/flota/shared/domain/errores.py) define una jerarquía:
`ErrorDominio` → `NoEncontrado`, `Duplicado`, `DatosInvalidos`, `ReglaNegocioViolada`.
El dominio lanza errores **con significado de negocio**; la API los traduce a HTTP en un solo lugar
([main.py](../src/flota/main.py)):

```python
_CODIGOS_HTTP = {NoEncontrado: 404, Duplicado: 409, DatosInvalidos: 422, ReglaNegocioViolada: 400}
```

### 3.10 Generadores (`yield`) — importación de archivos

En [combustible/infrastructure/importacion/mapeo.py](../src/flota/combustible/infrastructure/importacion/mapeo.py):

```python
yield FilaCarga(...)                # entrega una fila válida
yield ErrorLectura(numero, msg)     # o un error, sin cortar la importación
yield from procesar_filas(...)      # delega en otro generador
```

Procesan fila por fila: poca memoria con archivos grandes y una fila mala no detiene el resto.

### 3.11 Otras herramientas de la librería estándar

| Recurso | Ejemplo / dónde | Para qué |
|---|---|---|
| `@lru_cache` | [bootstrap.py](../src/flota/bootstrap.py), `get_settings` | Guarda el resultado: el motor de la base y la config se crean **una sola vez**. |
| Comprensiones | `[c for c in cargas if c.viaje_id == viaje.id]` | Filtrar/transformar en una línea. |
| `**asdict(datos)` | `Viaje.iniciar(**asdict(datos))` | Convierte una dataclass en dict y la pasa como argumentos con nombre. |
| `dict \| dict` | `asdict(actual) \| asdict(cambios)` | Une dos diccionarios; el de la derecha pisa al de la izquierda. |
| `collections.defaultdict` | reportes | Diccionario que crea el valor por defecto al pedir una clave nueva. |
| `pathlib.Path` | config, CLI, web | Rutas de archivos sin pelear con `\` y `/`. |
| `uuid4()` | entidades | IDs únicos sin depender de la base. |
| Operador morsa `:=` | `if ruta and (configurada := ruta.referencia_configurada(estado)):` | Asignar y evaluar en una misma expresión. |
| `@property` | `Viaje.km_recorridos`, `Ruta.nombre` | Un método que se lee como atributo (dato calculado). |
| Descriptores (`__get__`) | columnas de SQLAlchemy | Ver la nota del bug en [sesión 2](sesiones/02-marca-y-panel-web.md#descriptores-el-bug-de-esta-sesión). |
| `match` / `case` | [generar_word.py](../scripts/generar_word.py) | *Pattern matching* (3.10+): elegir una acción según un valor. |
| `subprocess.run` | [generar_word.py](../scripts/generar_word.py) | Ejecutar programas externos (`pandoc`, `git`). |
| `zipfile` / `io.BytesIO` | [generar_word.py](../scripts/generar_word.py) | Leer y escribir ZIP (un `.docx` lo es); bytes en memoria como si fueran un archivo. |
| `re.sub(..., flags=re.S)` | [generar_word.py](../scripts/generar_word.py) | Reemplazos con expresiones regulares. |
| `tempfile.TemporaryDirectory` | [generar_word.py](../scripts/generar_word.py) | Carpeta temporal que se borra sola al salir del `with`. |
| `if __name__ == "__main__":` | scripts | El bloque sólo corre al ejecutar el archivo, no al importarlo. |

---

## 4. Librerías externas

### 4.1 FastAPI + Uvicorn — API y servidor web

- **FastAPI** es el framework; **Uvicorn** el servidor que lo ejecuta (`flota servidor`).
- Cada módulo tiene su router en `presentation/api.py`; [main.py](../src/flota/main.py) los reúne.
- **Los type hints son la validación** ([viajes/presentation/api.py](../src/flota/viajes/presentation/api.py)):

  ```python
  @router.get("/viajes", response_model=list[ViajeLeer], tags=["Viajes"])
  def listar_viajes(uow: UoW, desde: date, hasta: date, ruta_id: UUID | None = None):
  ```

  `desde: date` hace que FastAPI exija y convierta el parámetro (si falta → **422**).
- **Inyección de dependencias** ([dependencias.py](../src/flota/dependencias.py)):
  `UoW = Annotated[UnidadDeTrabajoSistema, Depends(obtener_uow)]`. En tests se reemplaza con
  `app.dependency_overrides`.
- `@app.exception_handler` captura errores globalmente; `StaticFiles` sirve CSS e imágenes.

### 4.2 Pydantic y pydantic-settings — validación y configuración

Cada módulo tiene sus esquemas en `presentation/esquemas.py`:

```python
class RutaCrear(BaseModel):
    origen: str
    km_estimados: Decimal | None = Field(default=None, gt=0)
```

- Valida el JSON que entra; si no cumple responde 422 con el detalle.
- `Esquema` ([shared/presentation/esquemas.py](../src/flota/shared/presentation/esquemas.py)) tiene
  `from_attributes=True`: `ViajeLeer.model_validate(viaje)` arma la respuesta desde una entidad,
  incluidas listas anidadas (`tramos: list[TramoLeer]`) y propiedades (`km_recorridos`).
- **pydantic-settings** ([shared/infrastructure/config.py](../src/flota/shared/infrastructure/config.py))
  lee `.env` y variables de entorno con tipos. Una variable de entorno pisa al `.env`.

### 4.3 SQLAlchemy 2.0 — ORM

En [viajes/infrastructure/modelos.py](../src/flota/viajes/infrastructure/modelos.py):

```python
class ViajeModel(ConAuditoria, Base):
    __tablename__ = "viajes"
    ruta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rutas.id", name="fk_viajes_ruta_id_rutas"))
    tramos: Mapped[list[TramoViajeModel]] = relationship(
        cascade="all, delete-orphan", order_by="TramoViajeModel.orden", lazy="selectin"
    )
```

- Mapea clases a tablas con el estilo tipado moderno (`Mapped` + `mapped_column`).
- **Decisión clave:** `ViajeModel` (tabla) ≠ `Viaje` (entidad). El repositorio traduce entre ambos.
- `relationship(...)`: la lista de tramos del viaje.
  - `cascade="all, delete-orphan"`: al guardar el viaje se guardan sus tramos, y un tramo que
    desaparece de la lista se borra.
  - `lazy="selectin"`: los tramos de muchos viajes se leen en **una** consulta extra (evita el
    problema "N+1": una consulta por cada viaje).
- `RepositorioSql` ([shared/infrastructure/db.py](../src/flota/shared/infrastructure/db.py)) convierte
  entidad ↔ modelo copiando campos con el mismo nombre; el repositorio de viajes redefine
  `_a_entidad` / `_a_modelo` porque tiene que convertir también la lista de tramos.
- `ConAuditoria` es un **mixin**: aporta `creado_en` a todas las tablas por herencia múltiple.
- **psycopg 3** es el driver que habla con PostgreSQL.

### 4.4 Alembic — migraciones

Versiona el esquema de la base (como git, pero de tablas). Cada cambio es un archivo en
[migrations/versions/](../migrations/versions/).

```powershell
uv run alembic revision --autogenerate -m "descripción"   # genera un borrador comparando modelos y base
uv run alembic upgrade head                               # aplica las pendientes
uv run alembic downgrade -1                               # deshace la última
uv run alembic check                                      # ¿los modelos coinciden con la base?
```

El borrador automático **siempre se revisa**. En la Sesión 4 hubo que reescribirlo a mano
([migración de rutas y tramos](../migrations/versions/20261026_5d0917e47e58_rutas_y_tramos_de_viaje.py)):

1. **Migración de datos:** además de cambiar tablas, crea una ruta por cada par origen/destino que ya
   existía y un tramo por viaje. Usa vistas mínimas `sa.table(...)` en lugar de importar los modelos
   (los modelos cambian con el tiempo; una migración vieja no debe cambiar).
2. **Orden seguro:** la columna `ruta_id` se agrega opcional, se completa con datos y recién después
   se vuelve obligatoria.
3. **`op.batch_alter_table`:** SQLite no sabe modificar columnas; el modo *batch* recrea la tabla.
   Así la misma migración sirve para PostgreSQL y SQLite.
4. **Restricciones con nombre** (`fk_viajes_ruta_id_rutas`): sin nombre, el `downgrade` no puede borrarlas.

### 4.5 Jinja2 — panel web

- Plantillas en [web/templates/](../src/flota/web/templates/); utilidades comunes en
  [web/plantillas.py](../src/flota/web/plantillas.py); páginas de cada módulo en `<modulo>/presentation/web.py`.
- `{% extends "base.html" %}` + `{% block contenido %}`: herencia, todas comparten menú y encabezado.
- `{% macro %}` en `_macros.html`: componentes reutilizables (`tabla_resumen`, `tabla_grupo`, …).
- Filtros (`{{ valor | numero(1) }}`) definidos en [web/formato.py](../src/flota/web/formato.py): formato argentino.
- **Autoescape**: `<` se convierte en `&lt;`, evita inyección de HTML.
- Patrón **Post/Redirect/Get**: tras un `POST` se redirige con 303, así recargar no reenvía el formulario.
- Un checkbox **destildado no se envía** en el formulario: por eso `activa: bool = Form(False)`.
- Los colores de [marca](../src/flota/marca/__init__.py) se inyectan como variables CSS (`--azul`).

### 4.6 openpyxl + Pillow — Excel

- **openpyxl** lee los Excel importados y genera los reportes con estilos
  ([reportes/infrastructure/excel.py](../src/flota/reportes/infrastructure/excel.py)): resumen por
  camión, consumo por viaje (con cargado / vacío), por chofer y por ruta.
- **Pillow** (imágenes): openpyxl la necesita para insertar el logo en el Excel.

### 4.7 Typer — comandos de consola

[cli.py](../src/flota/cli.py): los type hints generan argumentos, `--help` y validación. Cada
`@app.command()` es un subcomando (`flota importar`, `flota exportar`, `flota datos-demo`, …).

---

## 5. Arquitectura limpia y patrones de diseño

```
            ┌──────────────────── un módulo (ej. viajes/) ────────────────────┐
            │                                                                 │
 HTTP ───►  │  presentation  ──►  application  ──►  domain                    │
            │  (api, web)         (casos de uso,    (entidades, reglas,       │
            │                      puertos)          repositorios = puertos)  │
            │                          ▲                  ▲                    │
            │                          └── infrastructure ┘ (implementa)      │
            └─────────────────────────────────────────────────────────────────┘
                   bootstrap.py elige qué infraestructura se usa
```

**Regla de oro:** `domain/` no importa nada de FastAPI, SQLAlchemy ni openpyxl. Por eso el negocio se
testea sin base de datos y se puede cambiar de tecnología tocando sólo `infrastructure/` y `bootstrap.py`.

**Dependencias entre módulos:** `combustible` usa el dominio de `viajes` y `catalogo`; `viajes` usa
`catalogo`; `reportes` lee de todos. Nunca al revés: `catalogo` no conoce a nadie.

| Patrón | Dónde | Idea |
|---|---|---|
| **Entidad** | `Camion`, `Ruta`, `Viaje` | Objeto con identidad (id) y reglas propias. |
| **Agregado** | `Viaje` + sus `TramoViaje` | Un grupo que se guarda y se lee junto; los tramos sólo se modifican a través del viaje. |
| **Repositorio** | `<modulo>/domain/repositorios.py` | El caso de uso pide datos sin saber SQL. |
| **Unidad de trabajo** | `UoWViajes`, `UnidadDeTrabajoSql` | Varias operaciones, una sola transacción. |
| **Caso de uso** | `<modulo>/application/casos_de_uso.py` | Una acción del sistema; el docstring lleva su código (CU-03, RF-09). |
| **Servicio de dominio** | `combustible/domain/consumo.py` | Lógica pura que involucra varias entidades (sabe **calcular**). |
| **Servicio de aplicación** | `combustible/application/consumo.py` (`CalculadoraConsumo`) | Busca en los repositorios lo que el cálculo necesita (sabe **buscar**). |
| **Fábrica** | `Viaje.iniciar(...)` | Crea un objeto válido con sus partes. |
| **Inyección de dependencias** | casos de uso, `Depends` | Las piezas reciben lo que necesitan; en tests se pasan fakes. |
| **Adaptador** | `LectorExcel`, `LectorCsv` | Distintas fuentes, mismo contrato (`LectorCargas`). |
| **Raíz de composición** | `bootstrap.py` | Único lugar donde se eligen implementaciones concretas. |
| **DTO** | `*/application/dto.py`, `Datos*` | Objetos simples para mover datos entre capas. |
| **CQRS liviano** | `Consultas*` vs `Registrar*` | Las lecturas se separan de los cambios. |

### Regla de negocio destacada: referencia de consumo (RF-11, RF-13, RF-16)

Para cada tramo, [consumo.py](../src/flota/combustible/domain/consumo.py) elige la referencia así:

1. la **configurada en la ruta** para ese estado de carga;
2. si no hay, el **promedio histórico** de la ruta (con 3 viajes o más);
3. si tampoco, la **referencia general del camión** (respaldo).

Hay alerta si el consumo supera la referencia en más del umbral (15 %), **sólo** si la referencia
es de la ruta: la del camión es una sola para cargado y vacío y daría falsas alarmas.

---

## 6. Recorrido de una petición de punta a punta

`POST /api/v1/viajes/{id}/tramos` (registrar la descarga: empieza el regreso vacío):

1. **Uvicorn** recibe el HTTP y se lo pasa a **FastAPI**.
2. **Pydantic** (`CambioEstadoCarga`) valida el JSON: fecha, km y nuevo estado.
3. `Depends` arma la **unidad de trabajo** real (vía `bootstrap.py`).
4. La ruta llama a `CambiarEstadoCarga(uow).ejecutar(...)`
   ([viajes/application/casos_de_uso.py](../src/flota/viajes/application/casos_de_uso.py)).
5. El caso de uso lee el viaje (con sus tramos) y le pide a la **entidad** que cambie de estado:
   `viaje.cambiar_estado_carga(...)` cierra el tramo cargado y abre uno vacío. Si el viaje ya terminó
   o el odómetro no avanza, la entidad lanza `ReglaNegocioViolada` / `DatosInvalidos`.
6. El repositorio convierte `Viaje` → `ViajeModel` (+ `TramoViajeModel`) y SQLAlchemy hace el
   `UPDATE` del viaje y el `INSERT` del tramo nuevo.
7. `commit()` → respuesta con `TramoLeer`. Si hubo error, el `exception_handler` lo traduce a 400/422.

---

## 7. Tests

| Carpeta | Qué prueba | Con qué |
|---|---|---|
| [tests/unit/](../tests/unit/) | Dominio y casos de uso, un archivo por módulo | **Fakes en memoria** ([fakes.py](../tests/fakes.py)); sin base, milisegundos |
| [tests/integration/](../tests/integration/) | API, panel, repositorios y lectores de archivos | **SQLite en memoria** y el `TestClient` de FastAPI |

- [escenarios.py](../tests/escenarios.py) es un **"Object Mother"**: funciones que arman datos de
  prueba listos (`flota_basica`, `viaje_ida_y_vuelta`), para que cada test muestre sólo lo que importa.
- **Fixtures** (`@pytest.fixture`): objetos que pytest prepara y entrega a cada test que los pide por nombre.
- Los nombres de los tests describen la regla: `test_la_referencia_del_camion_informa_el_desvio_pero_no_alerta`.

```powershell
uv run pytest              # todos
uv run pytest tests/unit   # sólo unitarios
uv run pytest -k tramo     # sólo los que contienen "tramo" en el nombre
uv run pytest -x -v        # detenerse en el primer fallo, con detalle
```

---

## 8. Ejecutar el proyecto en local

**Con PostgreSQL** (requiere `DB_PASSWORD` en `.env`):

```powershell
uv run flota crear-db
uv run alembic upgrade head
uv run flota datos-demo        # opcional: 2 camiones, 2 rutas, 8 viajes ida cargado / regreso vacío
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

Casi todo requerimiento sigue el mismo camino, de adentro hacia afuera, **dentro de su módulo**:

1. **Dominio** (`<modulo>/domain/`): entidad, campo o regla + test unitario.
2. **Aplicación** (`<modulo>/application/`): caso de uso (con su código CU/RF en el docstring) +
   test con fakes. Si necesita un repositorio nuevo, agregarlo al `UoW<Modulo>` del módulo.
3. **Infraestructura** (`<modulo>/infrastructure/`): tabla en `modelos.py`, repositorio SQL; registrarlo
   en [unidad_de_trabajo.py](../src/flota/unidad_de_trabajo.py) y el módulo de modelos en
   [modelos.py](../src/flota/modelos.py). Migración con Alembic (revisar el borrador; probar
   `upgrade`, `downgrade` y `check`).
4. **Presentación** (`<modulo>/presentation/`): esquema Pydantic + `api.py` y/o `web.py`; registrar
   el router en [main.py](../src/flota/main.py) + test de integración.
5. `uv run pytest` y `uv run ruff check .` en verde; nota de la sesión en `docs/sesiones/`; actualizar
   esta guía y regenerar los Word (`uv run python scripts/generar_word.py`).

---

## 10. Ruta de estudio sugerida

De lo más puro a lo más técnico:

1. [shared/domain/](../src/flota/shared/domain/) → [catalogo/domain/entidades.py](../src/flota/catalogo/domain/entidades.py)
2. [viajes/domain/entidades.py](../src/flota/viajes/domain/entidades.py) (agregado viaje + tramos) y su test [test_viajes.py](../tests/unit/test_viajes.py)
3. [combustible/domain/consumo.py](../src/flota/combustible/domain/consumo.py) y [test_consumo.py](../tests/unit/test_consumo.py)
4. [viajes/application/casos_de_uso.py](../src/flota/viajes/application/casos_de_uso.py) → [fakes.py](../tests/fakes.py) → [escenarios.py](../tests/escenarios.py)
5. [viajes/infrastructure/](../src/flota/viajes/infrastructure/) y la migración de la Sesión 4
6. [viajes/presentation/](../src/flota/viajes/presentation/) → [main.py](../src/flota/main.py) → [bootstrap.py](../src/flota/bootstrap.py)

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

---

## 12. Glosario

| Término | Significado |
|---|---|
| **Entidad** | Objeto del negocio con identidad propia (un camión, un viaje). |
| **Agregado** | Entidad "raíz" con sus partes, que se guardan y modifican juntas (viaje + tramos). |
| **Tramo** | Parte de un viaje recorrida cargado o vacío. |
| **Caso de uso** | Una acción que el sistema permite (iniciar viaje, registrar descarga). |
| **Puerto** | Interfaz (contrato) que define qué se necesita, sin decir cómo. |
| **Adaptador** | Implementación concreta de un puerto (SQL, Excel, CSV). |
| **Protocol** | Interfaz que se cumple "por forma", sin herencia. |
| **ORM** | Traduce objetos Python ↔ tablas SQL. |
| **Migración** | Cambio versionado del esquema de la base (y a veces de los datos). |
| **Fake** | Implementación falsa (en memoria) usada en tests. |
| **Fixture** | Dato u objeto preparado por pytest para los tests. |
| **Object Mother** | Módulo de fábricas de datos de prueba (`tests/escenarios.py`). |
| **Endpoint** | Una URL + método HTTP de la API (`GET /api/v1/rutas`). |
| **422 / 404 / 409 / 400** | Datos inválidos / no existe / duplicado / regla de negocio violada. |
| **Entorno virtual** | Instalación aislada de Python y librerías para un proyecto. |

---

## 13. Bitácora de la guía

Cada cambio del proyecto agrega una línea acá y, si introduce conceptos nuevos, los suma en la sección que corresponda.

| Fecha | Cambio | Secciones |
|---|---|---|
| 2026-10-21 | Creación de la guía a partir de las sesiones 1 y 2. Proyecto verificado en local (26 tests OK, servidor con SQLite). | Todas |
| 2026-10-21 | Versión Word de la guía y de cada sesión (`scripts/generar_word.py`). Conceptos: `match`/`case`, `subprocess`, `zipfile`, `re`, pandoc y filtros Lua. | 2, 3.11, 11 |
| 2026-10-26 | Incorporación del [documento de requisitos v1.1](requisitos_v1.1.md) y del [análisis de brechas](brechas-requisitos-v1.1.md). Sin cambios de código. | 1 |
| 2026-10-26 | **Sesión 4**: código reorganizado por módulo; rutas y tramos cargado / vacío; referencia por ruta e histórico. Conceptos: `Protocol`, `@classmethod` fábrica, agregados, `relationship` con cascada, migración de datos con `batch_alter_table`, Object Mother. Guía reescrita con las rutas nuevas. | Todas |

Notas por sesión: [01 · Base del sistema](sesiones/01-base-del-sistema.md) ·
[02 · Marca y panel web](sesiones/02-marca-y-panel-web.md) ·
[03 · Entorno local y documentación](sesiones/03-entorno-local-y-documentacion.md) ·
[04 · Módulos, rutas y tramos](sesiones/04-modulos-rutas-y-tramos.md)
