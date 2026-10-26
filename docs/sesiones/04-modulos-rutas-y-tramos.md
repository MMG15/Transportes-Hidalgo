# Sesión 4 — Módulos, rutas y tramos cargado / vacío

**Objetivo:** reorganizar el código por módulo (decisión 4.2 del
[análisis de brechas](../brechas-requisitos-v1.1.md)) y alinear viajes y consumo con el documento de
requisitos: rutas, tramos cargado / vacío y referencia de consumo por ruta.

**Requisitos:** RF-09, RF-10, RF-11, RF-12, RF-13, RF-16 (parcial), RF-52 · **Casos de uso:** CU-03, CU-05 ·
**Módulos:** MOD-01, MOD-02, MOD-03, MOD-12.

## Qué se hizo

### Paso 0 — Reorganización por módulo (commit `refactor:` aparte)
- De cuatro carpetas globales (`domain/`, `application/`, `infrastructure/`, `presentation/`) a una
  carpeta por módulo con sus capas: `shared/`, `catalogo/`, `viajes/`, `combustible/`, `reportes/`, `web/`.
- Sin cambios de comportamiento: los 26 tests pasaron igual y `alembic check` confirmó que la base no cambió.
- Cada módulo declara su unidad de trabajo como `Protocol` (`UoWCatalogo`, `UoWViajes`, …).

### Rutas y tramos
- **`Ruta`** (MOD-02): origen, destino, país, km estimados y referencia L/100 km cargado y vacío
  (opcionales). Página nueva **Rutas** en el panel y endpoints `/api/v1/rutas`.
- **`TramoViaje`**: cada viaje se divide en tramos. `Viaje.iniciar(...)` abre el primero (cargado o vacío);
  **Registrar descarga** cierra el tramo cargado y abre el regreso vacío; **Finalizar** cierra el último.
- El viaje ya no guarda origen/destino como texto: usa la ruta. Cliente, producto y cantidad son
  opcionales (un viaje puede salir vacío), pero obligatorios si sale cargado.
- **Camión:** año y odómetro actual (`km_actual`), que se actualiza con cada viaje y nunca retrocede.
  Edición y baja lógica de camiones y choferes desde el panel y la API.

### Consumo por tramo (RF-10, RF-11, RF-13)
- Cada carga se asigna al tramo que estaba en curso en su fecha; el L/100 km se calcula por tramo y para el viaje.
- Referencia de cada tramo, en orden: **configurada en la ruta → promedio histórico de la ruta
  (≥ 3 viajes) → referencia del camión**.
- **Decisión:** la referencia del camión informa el desvío pero **no genera alerta**. Es una sola para
  cargado y vacío; en la prueba con datos de ejemplo, los tres primeros viajes a Chile daban "alerta"
  sólo por ir cargados. Para tener alertas desde el primer viaje de una ruta, se configura su referencia.

### Reportes (RF-12, RF-52)
- Filtros por camión, chofer, ruta, país y período (panel, API y Excel).
- Resúmenes por chofer y por ruta, con consumo cargado y vacío. El Excel suma las hojas "Por chofer" y "Por ruta".

### Base de datos
- Migración `5d0917e47e58` con **migración de datos**: crea una ruta por cada par origen/destino existente
  y un tramo cargado por viaje. Probada en PostgreSQL y SQLite, en las dos direcciones (`upgrade` y `downgrade`).

### Datos de ejemplo
- `flota datos-demo` ahora usa rutas reales de la empresa: Planta Albardón → Mendoza (con referencias
  configuradas) y Planta Albardón → Los Andes, Chile (sin referencias: usa el histórico), con 8 viajes
  de ida cargado y regreso vacío.

### Tests
- De 26 a **59**. Reorganizados por módulo: `test_catalogo.py`, `test_viajes.py`, `test_consumo.py`,
  `test_combustible.py`, `test_reportes.py`, `test_repositorios.py`, y los de API y panel.

## Conceptos nuevos

### `Protocol`: interfaces que se cumplen "por forma"
Un `Protocol` dice qué atributos debe tener un objeto, sin obligarlo a heredar. Cada módulo pide sólo
los repositorios que usa (`UoWViajes` pide `rutas` y `viajes`), y la clase concreta
`UnidadDeTrabajoSql` los tiene todos. Es la **segregación de interfaces** (la "I" de SOLID).

### Agregado: el viaje y sus tramos
Los tramos no tienen sentido sin su viaje y sólo cambian a través de él (`viaje.registrar_descarga`).
El repositorio guarda y lee **el viaje entero**. En SQLAlchemy esto es una `relationship` con
`cascade="all, delete-orphan"` y `lazy="selectin"` (una sola consulta extra para todos los tramos).

### `@classmethod` como fábrica
`Viaje.iniciar(...)` es un "constructor con nombre" que arma un viaje nuevo con su primer tramo. El
constructor normal `Viaje(...)` queda para reconstruir un viaje guardado.

### Servicio de dominio vs. servicio de aplicación
- `combustible/domain/consumo.py` **calcula** (funciones puras, sin base de datos).
- `combustible/application/consumo.py` (`CalculadoraConsumo`) **busca** lo que el cálculo necesita
  (ruta, histórico, cargas) y guarda en caché el historial de cada ruta, para que un reporte de muchos
  viajes no repita consultas.

### Migraciones con datos
El borrador de Alembic agregaba `ruta_id` obligatorio de una vez, y eso falla si ya hay viajes. La
migración correcta tiene tres pasos: columna opcional → completar datos → volverla obligatoria. Usa
`sa.table(...)` (vistas mínimas, no los modelos de la app) y `batch_alter_table` para que funcione en SQLite.

### Object Mother en los tests
`tests/escenarios.py` arma datos de prueba completos (`flota_basica`, `viaje_ida_y_vuelta`), así cada
test muestra sólo lo que le importa.

### Otros
- `dict | dict` para combinar datos: `Camion(**(asdict(actual) | asdict(cambios)))` reconstruye la
  entidad con los cambios y vuelve a correr las validaciones.
- Un checkbox HTML destildado **no se envía**: en FastAPI se declara `activo: bool = Form(False)`.
- Para probar migraciones sin la base real se levantó un PostgreSQL temporal en otro puerto
  (`initdb` + `pg_ctl`).

## Pendiente para próximas sesiones
- Sesión 5: `Dinero` y `TipoCambio` (ARS / CLP) y alertas guardadas con su ciclo de vida (CU-06).
- La alerta por desvío todavía se calcula al vuelo; en la Sesión 5 pasa a ser una entidad con estado.
