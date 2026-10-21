<p align="center"><img src="src/flota/marca/img/logo-hidalgo.png" alt="Transportes Hidalgo" height="80"></p>

# Transportes Hidalgo · Gestión de Flota

Control de viajes de camiones (distribución de cal y otros productos) y del **consumo de combustible por viaje**.

- **Panel web** en http://127.0.0.1:8000 — tablero, viajes, combustible, reportes y catálogo.
- **API REST** en http://127.0.0.1:8000/docs
- **Reportes Excel** con la identidad de la empresa.
- Historial de cada sesión de trabajo en [`docs/sesiones/`](docs/sesiones/).

## Paleta de marca

| Color | Hex | Uso |
|---|---|---|
| Azul Hidalgo | `#0706E5` | Botones, encabezados de tabla, acentos principales |
| Azul oscuro | `#06057F` | Barra de navegación y títulos |
| Naranja Hidalgo | `#F56A11` | Acentos, franja del encabezado, alertas |
| Naranja oscuro | `#B84A06` | Texto naranja legible sobre blanco |

Definida en un único lugar: [`src/flota/marca/__init__.py`](src/flota/marca/__init__.py). La usan el CSS del panel
(se inyecta como variables CSS) y el generador de Excel.

## Arquitectura limpia

```
src/flota/
├── domain/            Reglas del negocio. No depende de nada.
│   ├── entities.py        Camion, Chofer, Cliente, Producto, Viaje, CargaCombustible
│   ├── consumo.py         Cálculo de L/100km, desvío y alertas
│   ├── repositories.py    Puertos (interfaces) de persistencia
│   └── exceptions.py
├── application/       Casos de uso. Depende sólo del dominio.
│   ├── ports.py           UnidadDeTrabajo, LectorCargas, GeneradorReporte
│   ├── dto.py
│   └── use_cases/         catalogo, viajes, combustible, importacion, reportes
├── infrastructure/    Adaptadores: PostgreSQL, Excel, CSV, configuración.
│   ├── db/                Modelos SQLAlchemy, repositorios, unidad de trabajo
│   ├── importacion/       Lectores de Excel y CSV de tarjetas de combustible
│   └── excel/             Generador del reporte Excel
├── presentation/      Entradas al sistema.
│   ├── api/               API REST (FastAPI)
│   ├── web/               Panel web (Jinja2 + CSS con la paleta de marca)
│   └── cli.py             Comandos de consola (automatización)
├── marca/             Colores y logos de Transportes Hidalgo
└── bootstrap.py       Raíz de composición: conecta puertos con adaptadores
```

Regla de dependencias: las flechas apuntan siempre hacia adentro
(`presentation → application → domain`; `infrastructure` implementa los puertos).

## Puesta en marcha

```powershell
copy .env.example .env          # y completar DB_PASSWORD
uv sync                         # instala dependencias en .venv
uv run flota crear-db           # crea la base 'flota' en PostgreSQL
uv run alembic upgrade head     # crea las tablas
uv run flota datos-demo         # (opcional) datos de ejemplo
uv run flota servidor           # panel en http://127.0.0.1:8000 · API en /docs
```

## Comandos

| Comando | Qué hace |
|---|---|
| `uv run flota importar archivo.xlsx` | Importa cargas desde Excel o CSV |
| `uv run flota importar-carpeta entrada --origen tarjeta` | Importa todo lo de una carpeta y lo mueve a `procesados/` o `errores/` |
| `uv run flota exportar --desde 2026-10-01 --hasta 2026-10-31` | Genera el reporte de consumo en `reportes/` |
| `uv run flota plantilla` | Genera la planilla modelo para importar |
| `uv run pytest` | Corre los tests |

### Columnas reconocidas al importar

Obligatorias: `fecha`, `patente`, `litros`. Opcionales: `precio_litro`, `odometro_km`, `estacion`, `referencia`.
Se aceptan sinónimos habituales de tarjetas de combustible (`Dominio`, `Cantidad Litros`, `Nro Comprobante`, …)
y números en formato argentino (`1.234,56`). Reimportar un archivo no duplica cargas.

### Automatizar con el Programador de tareas de Windows

```powershell
# Importar cada hora lo que deje la tarjeta de combustible en la carpeta 'entrada'
schtasks /Create /TN "Flota - Importar" /SC HOURLY /TR "cmd /c cd /d C:\Users\Usuario\OneDrive\Documentos\Transportes-Hidalgo && uv run flota importar-carpeta entrada --origen tarjeta"

# Reporte diario a las 7:00
schtasks /Create /TN "Flota - Reporte" /SC DAILY /ST 07:00 /TR "cmd /c cd /d C:\Users\Usuario\OneDrive\Documentos\Transportes-Hidalgo && uv run flota exportar"
```

## Cómo se calcula el consumo

- Cada carga de combustible se asigna automáticamente al viaje que el camión tenía en curso en esa fecha.
- `L/100km = litros cargados en el viaje / km recorridos × 100`
- `desvío % = (consumo real − consumo de referencia) / referencia × 100`
- Si el desvío supera `UMBRAL_DESVIO_PCT` (15 % por defecto), el viaje se marca con **alerta**.
