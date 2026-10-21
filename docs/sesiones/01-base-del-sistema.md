# Sesión 1 — Base del sistema

**Objetivo:** instalar el entorno y crear el núcleo del sistema con arquitectura limpia.

## Qué se hizo
- Instalación de Python 3.13 y `uv`. PostgreSQL 17 ya estaba instalado.
- Dominio: `Camion`, `Chofer`, `Cliente`, `Producto`, `Viaje`, `CargaCombustible` y el cálculo de consumo.
- Casos de uso: alta de catálogo, iniciar/finalizar viaje, registrar carga, importar archivo, reporte de consumo.
- Infraestructura: PostgreSQL (SQLAlchemy + Alembic), lectores de Excel/CSV, generador de Excel.
- Presentación: API REST (FastAPI, documentación en `/docs`) y comandos de consola (Typer).
- 20 tests (unitarios con repositorios en memoria + integración de la API con SQLite).

## Conceptos de Python
| Concepto | Dónde | Para qué |
|---|---|---|
| `@dataclass` | `domain/entities.py` | Genera `__init__`, `__repr__` y `__eq__`. `kw_only=True` obliga a nombrar argumentos; `frozen=True` vuelve el objeto inmutable. |
| `__post_init__` | `Camion` | Validar y normalizar al crear el objeto ("ab 123-cd" → "AB123CD"). |
| `Decimal` | dominio | Cuentas exactas (con `float`, `0.1 + 0.2 = 0.30000000000000004`). |
| `StrEnum` | `OrigenDato`, `EstadoViaje` | Valores cerrados que se comportan como texto. |
| `ABC` / `@abstractmethod` | `domain/repositories.py` | Interfaces: obligan a implementar ciertos métodos. |
| Genéricos `class Repositorio[E]` | `domain/repositories.py` | Sintaxis de Python 3.12+: un repositorio "de algo", con tipos. |
| `with` (context manager) | `UnidadDeTrabajo` | `__enter__` abre la transacción; `__exit__` la descarta si no hubo `commit()`. |
| Generadores (`yield`) | lectores de archivos | Procesan fila por fila sin cargar todo en memoria. |
| Operador morsa `:=` | `use_cases/combustible.py` | Asignar y evaluar en una sola expresión. |

## Patrones de diseño
- **Repositorio**: el caso de uso pide datos sin conocer SQL.
- **Unidad de trabajo**: varias operaciones en una sola transacción.
- **Inyección de dependencias**: los casos de uso reciben su `uow`; en los tests se pasa uno en memoria.
- **Adaptador**: `LectorExcel` y `LectorCsv` cumplen el mismo contrato (`LectorCargas`).
- **Raíz de composición** (`bootstrap.py`): único lugar donde se eligen las implementaciones concretas.

## Librerías
`uv` (entorno y dependencias) · FastAPI (API) · Pydantic / pydantic-settings (validación y `.env`) ·
SQLAlchemy 2 (ORM) · Alembic (migraciones) · psycopg 3 (driver PostgreSQL) · openpyxl (Excel) ·
Typer (CLI) · pytest (tests) · ruff (estilo).
