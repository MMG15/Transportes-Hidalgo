<p align="center"><img src="src/flota/marca/img/logo-hidalgo.png" alt="Transportes Hidalgo" height="80"></p>

# Transportes Hidalgo · Gestión de Flota

Control de viajes de camiones (distribución de cal y otros productos) y del **consumo de combustible por viaje**.

- **Panel web** en http://127.0.0.1:8000 — tablero, viajes, rutas, combustible, alertas, tipo de cambio, reportes y catálogo.
- **API REST** en http://127.0.0.1:8000/docs
- **Reportes Excel** con la identidad de la empresa.
- **Documento de requisitos v1.1** (referencia funcional del sistema): [`docs/requisitos_v1.1.md`](docs/requisitos_v1.1.md) · [versión Word](docs/word/Requisitos_Sistema_Trazabilidad_Hidalgo_v1.1.docx) · análisis de brechas código ↔ requisitos en [`docs/brechas-requisitos-v1.1.md`](docs/brechas-requisitos-v1.1.md).
- **Guía técnica para estudiar el proyecto:** [`docs/guia-tecnica.md`](docs/guia-tecnica.md) · versión Word de la guía y de cada sesión en [`docs/word/`](docs/word/) (`uv run python scripts/generar_word.py`).
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

## Arquitectura limpia, organizada por módulo

```
src/flota/
├── shared/        Común: errores, validaciones, Repositorio[E], UnidadDeTrabajo, base de datos, config
├── catalogo/      MOD-01  Camiones, choferes, clientes y productos
├── viajes/        MOD-02  Rutas, viajes y tramos cargado / vacío
├── combustible/   MOD-03  Cargas, importación de tarjeta y cálculo de consumo por tramo
├── alertas/       MOD-05  Alertas con estado y resolución (generadas por eventos)
├── monedas/       MOD-10  Tipo de cambio CLP → ARS y conversión de gastos
├── reportes/      MOD-12  Tablero, reportes filtrables y Excel
├── usuarios/      MOD-13  Usuarios, roles, permisos, login y auditoría
├── web/           Plantillas Jinja2 y estilos del panel
├── marca/         Colores y logos de Transportes Hidalgo
├── bootstrap.py   Raíz de composición: conecta puertos con adaptadores
└── main.py · cli.py · unidad_de_trabajo.py · dependencias.py · modelos.py
```

Cada módulo tiene sus capas: `domain/` (reglas, sin dependencias) → `application/` (casos de uso y
puertos) → `infrastructure/` (SQLAlchemy, archivos) y `presentation/` (API, panel).
Regla de dependencias: las flechas apuntan siempre hacia el dominio.
Detalle completo en la [guía técnica](docs/guia-tecnica.md).

## Puesta en marcha

```powershell
copy .env.example .env          # y completar DB_PASSWORD y SECRET_KEY
uv sync                         # instala dependencias en .venv
uv run flota crear-db           # crea la base 'flota' en PostgreSQL
uv run alembic upgrade head     # crea las tablas
uv run flota crear-usuario admin@empresa.com "Tu nombre"   # primer administrador (ROL-07)
uv run flota datos-demo         # (opcional) datos de ejemplo + un usuario por rol (contraseña demo1234)
uv run flota servidor           # panel en http://127.0.0.1:8000 · API en /docs
```

## Comandos

| Comando | Qué hace |
|---|---|
| `uv run flota importar archivo.xlsx` | Importa cargas desde Excel o CSV |
| `uv run flota importar-carpeta entrada --origen tarjeta` | Importa todo lo de una carpeta y lo mueve a `procesados/` o `errores/` |
| `uv run flota exportar --desde 2026-10-01 --hasta 2026-10-31` | Genera el reporte de consumo en `reportes/` |
| `uv run flota plantilla` | Genera la planilla modelo para importar |
| `uv run flota crear-usuario EMAIL NOMBRE --rol ROL-03` | Crea un usuario (pide la contraseña) |
| `uv run flota recalcular-alertas` | Evalúa las alertas de consumo de los viajes cerrados |
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

- Cada viaje se divide en **tramos** cargado / vacío (al descargar empieza el regreso vacío).
- Cada carga se asigna al viaje que el camión tenía en curso y, dentro de él, al tramo de su fecha.
- `L/100km = litros cargados en el tramo / km del tramo × 100` (y lo mismo para el viaje completo).
- Referencia de cada tramo: la **configurada en la ruta** → el **promedio histórico de la ruta**
  (3 viajes o más) → la **referencia del camión** (respaldo).
- `desvío % = (consumo real − referencia) / referencia × 100`. Si supera `UMBRAL_DESVIO_PCT`
  (15 % por defecto) y la referencia es de la ruta, el viaje se marca con **alerta**.
