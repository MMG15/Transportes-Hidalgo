# Análisis de brechas · Código actual ↔ Requisitos v1.1

Comparación entre el sistema construido en las sesiones 1 a 3 (commit `64ce913`) y el
[documento de requisitos v1.1](requisitos_v1.1.md). Elaborado el 26/10/2026.

**Referencias:** ✅ Implementado · 🟡 Parcial · ❌ Falta · ↔️ Diferente (el código lo resuelve de otra forma).
Las rutas de código son relativas a `src/flota/`.

---

## Índice

1. [Resumen de cobertura](#1-resumen-de-cobertura)
2. [Matriz de cobertura](#2-matriz-de-cobertura)
3. [Diferencias entre código y documento](#3-diferencias-entre-código-y-documento)
4. [Decisiones pendientes](#4-decisiones-pendientes)
5. [Plan de sesiones](#5-plan-de-sesiones)
6. [Propuesta de cambios para el documento v1.2](#6-propuesta-de-cambios-para-el-documento-v12)

---

## 1. Resumen de cobertura

| Elemento | ✅ | 🟡 | ↔️ | ❌ | Total |
|---|---|---|---|---|---|
| Requisitos funcionales (RF) | 0 | 9 | 3 | 43 | 55 |
| Requisitos no funcionales (RNF) | 1 | 2 | 0 | 7 | 10 |
| Casos de uso (CU) | 0 | 3 | 0 | 14 | 17 |
| Módulos (MOD) | 0 | 5 | 0 | 9 | 14 |

Lectura: el código actual es una **base sólida del núcleo** (MOD-01, MOD-02, MOD-03, MOD-05 y MOD-12
en forma parcial) con la arquitectura que pide RNF-09. Todo lo que depende de **IA, Telegram, GPS,
moneda, usuarios** y los módulos de gestión (mantenimiento, neumáticos, stock, viáticos, peajes,
Excel de la empresa) está por construir. Ningún RF está completo porque el modelo del documento
agrega a cada uno algo que hoy no existe (ruta, moneda, estado de validación, imagen, usuario).

---

## 2. Matriz de cobertura

### 2.1 Requisitos funcionales

#### Ingesta y extracción (MOD-03 · MOD-14)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-01 | ❌ | — | Bot de Telegram vinculado al chofer. |
| RF-02 | 🟡 | Carga manual: `RegistrarCargaCombustible` (`application/use_cases/combustible.py`), formulario `/combustible`, `POST /api/v1/cargas`. | Subir **imagen o PDF** del ticket desde el panel. |
| RF-03 | ❌ | — | Puerto `ExtractorComprobantes` + adaptador Claude con visión que devuelva JSON. |
| RF-04 | 🟡 | `CargaCombustible.__post_init__` (litros > 0); `RegistrarCargaCombustible` (litros ≤ tanque + tolerancia); `ImportarCargas` (patente existente). Pydantic en `presentation/api/schemas.py`. | Validar **fecha no futura**; validar con Pydantic la **salida de la IA**. |
| RF-05 | ❌ | — | Cola de tareas en segundo plano y confirmación del bot al chofer. |
| RF-06 | ❌ | — | Estado `estado_validacion` ("Pendiente de validación") y diálogo con el chofer. |
| RF-07 | ❌ | — | Puerto `AlmacenArchivos` e `imagen_url` en la carga. |
| RF-08 | ↔️ | `RepositorioCargasSql.existe_duplicado`: misma `referencia_externa`, o mismo camión + fecha + litros. | Criterio del documento: estación + fecha/hora + monto + patente. Combinar ambos (ver §3). |

#### Viajes y consumo (MOD-02 · MOD-03)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-09 | 🟡 | `Viaje` (`domain/entities.py`): camión, chofer, fechas, producto (material), cantidad (toneladas), km de salida y llegada. | Entidad **`Ruta`**; **estado de carga por tramo** (cargado / vacío). |
| RF-10 | ↔️ | `calcular_consumo` (`domain/consumo.py`): L/100 km = litros ÷ km × 100 con los km **del odómetro del viaje**. | Método "tanque lleno" (km entre cargas consecutivas) y km del GPS. |
| RF-11 | ❌ | — | Consumo por tramo comparado con la referencia de la ruta para ese estado de carga. |
| RF-12 | 🟡 | `GenerarReporteConsumo` (`use_cases/reportes.py`): por viaje, por camión y por período; panel `/reportes` y Excel. | Agregados por **chofer** y por **ruta**. |
| RF-13 | ❌ | — | Promedio histórico por ruta y estado de carga, actualizado al cerrar el viaje. |

#### Integración GPS (MOD-04)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-14 | ❌ | — | Puerto `ProveedorGPS`; importación de posiciones y odómetro. Depende del proveedor (punto abierto 2). |
| RF-15 | ❌ | — | Entidad `LecturaGPS` y asociación por patente y horario. |

#### Alertas (MOD-05)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-16 | 🟡 | `calcular_consumo` marca `alerta` si el desvío supera `UMBRAL_DESVIO_PCT` (configurable, 15 %). | Comparar contra el **histórico de la ruta** (hoy: referencia del camión) y **persistir** la alerta. |
| RF-17 | ❌ | — | Coordenadas de estación, lectura GPS y regla de distancia (objeto de valor `Coordenada`). |
| RF-18 | ↔️ | `RegistrarCargaCombustible` **rechaza** la carga si supera tanque + `TOLERANCIA_TANQUE_PCT`. | El documento pide **registrar y alertar** (ver §3). |
| RF-19 | 🟡 | El tablero (`/`) lista los viajes con alerta del período. | Notificación por Telegram o correo (puerto `Notificador`). |
| RF-20 | ❌ | — | Entidad `Alerta` con estados y resolución (usuario, fecha, comentario). |

#### Mantenimiento, neumáticos, stock y viáticos (MOD-06 a MOD-09)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-21 a RF-25 | ❌ | — | Módulo de mantenimiento completo (órdenes, planes, avisos, historial, descuento de stock). |
| RF-26 a RF-29 | ❌ | — | Módulo de neumáticos completo. |
| RF-30 a RF-33 | ❌ | — | Módulo de stock completo. |
| RF-34 a RF-37 | ❌ | — | Módulo de viáticos completo (reutiliza IA, Telegram y `Dinero`). |

#### Peajes y moneda (MOD-10)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-38 | ❌ | — | Entidad `Peaje`. |
| RF-39 | ❌ | — | Entidad `TipoCambio`, puerto `ProveedorTipoCambio` y carga manual. |
| RF-40 | ❌ | Sólo `precio_litro` en `CargaCombustible`, sin moneda. | Objeto de valor `Dinero` (monto + moneda) y conversión con cotización guardada. |
| RF-41 | ❌ | — | Cotización fija por gasto; corrección sólo con auditoría. |
| RF-42 | ❌ | — | Catálogo de puestos de peaje con tarifa de referencia. |

#### Asistente IA — Excel (MOD-11)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-43 a RF-49 | ❌ | El generador `infrastructure/excel/generador_excel.py` escribe **reportes propios**, no la planilla de la empresa. openpyxl ya está integrado. | Plantillas, mapeo con IA, sincronización, respaldo y pedidos en lenguaje natural. |

#### Tablero y reportes (MOD-12)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-50 | 🟡 | Tablero `/` (`presentation/web/rutas.py`): gasto del período, L/100 km, viajes en curso y con alerta. | Mantenimientos próximos, stock crítico, gastos en Chile (dependen de otros módulos). |
| RF-51 | 🟡 | Excel con la marca (`GeneradorReporteExcel`). | Exportación a **PDF** (nuevo adaptador del puerto `GeneradorReporte`). |
| RF-52 | 🟡 | Filtros por camión y período. | Filtros por chofer, ruta y país. |

#### Usuarios, seguridad y auditoría (MOD-13)

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RF-53 | ❌ | — | Usuarios, roles ROL-01 a ROL-07 y permisos por módulo; login en el panel y en la API. |
| RF-54 | ❌ | — | `telegram_id` en el chofer y código de vinculación. |
| RF-55 | ❌ | Sólo `creado_en` en todas las tablas (`_ConAuditoria`). | Tabla `Auditoria` (usuario, acción, valor anterior y nuevo) y `actualizado_en`. |

### 2.2 Requisitos no funcionales

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| RNF-01 | ❌ | — | Depende del bot (MOD-14). |
| RNF-02 | ❌ | — | Medible recién con IA + Telegram. |
| RNF-03 | ❌ | — | Hash de contraseñas, acceso por rol; HTTPS en el despliegue. |
| RNF-04 | ❌ | — | Respaldo diario de la base y de los comprobantes. |
| RNF-05 | 🟡 | CSS con grillas adaptables y `@media (max-width: 640px)` (`static/css/hidalgo.css`). | Validar en celular las pantallas nuevas. |
| RNF-06 | ❌ | — | Juego de tickets reales para medir precisión. |
| RNF-07 | ❌ | — | Registro de tokens y costo por comprobante; límite mensual. |
| RNF-08 | 🟡 | Español; formatos argentinos de números y fechas (`presentation/web/formato.py`); importación acepta `1.234,56`. | Formatos de Chile y moneda CLP. |
| RNF-09 | ✅ | `domain/` sin dependencias externas; reglas de consumo cubiertas por `tests/unit/test_dominio.py`; puertos y `bootstrap.py`. | Mantener el criterio en los módulos nuevos (conversión y alertas también con tests unitarios). |
| RNF-10 | ❌ | Hoy: Windows nativo + PostgreSQL local. | Docker Compose (ver decisión 4.3). |

### 2.3 Casos de uso

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| CU-01 | ❌ | — | Bot + extracción IA + cola. |
| CU-02 | ❌ | — | Estado "Pendiente de validación" y pantalla de revisión con imagen. |
| CU-03 | 🟡 | `IniciarViaje` / `FinalizarViaje` (`use_cases/viajes.py`); E1 (camión con viaje abierto) **ya implementado**. | Ruta, tramos cargado / vacío, km del GPS (E2: km manual marcado como "manual"). |
| CU-04 | ❌ | — | Importación GPS. |
| CU-05 | 🟡 | `GenerarReporteConsumo`, `ExportarReporteConsumo`, panel `/reportes`. | Comparación por ruta y estado de carga, ranking, evolución mensual, PDF. |
| CU-06 | ❌ | Sólo la marca `alerta` calculada. | Ciclo de vida de la alerta. |
| CU-07 a CU-15 | ❌ | — | Módulos 06 a 11. |
| CU-16 | 🟡 | Tablero `/`. | Indicadores de módulos futuros, clic al detalle, filtro de período en el tablero. |
| CU-17 | ❌ | — | Usuarios y roles. |
| *(sin código)* | — | `ImportarCargas` (`use_cases/importacion.py`), CLI `importar` e `importar-carpeta`. | **No existe en el documento** → se propone CU-18 (ver §6). |

### 2.4 Módulos

| ID | Estado | Dónde está en el código | Qué falta |
|---|---|---|---|
| MOD-01 Flota y choferes | 🟡 | `Camion`, `Chofer`, `RegistrarCamion`, `RegistrarChofer`, panel `/catalogo`. | Año, km actual, estado del camión; `telegram_id`; edición y baja (el campo `activo` existe pero no hay caso de uso). |
| MOD-02 Viajes y rutas | 🟡 | `Viaje`, `IniciarViaje`, `FinalizarViaje`, panel `/viajes`. | `Ruta`, tramos, referencias por ruta. |
| MOD-03 Combustible | 🟡 | `CargaCombustible`, registro manual, importación Excel/CSV, cálculo de consumo. | IA, imagen, estados de validación, moneda. |
| MOD-04 Integración GPS | ❌ | — | Todo. |
| MOD-05 Alertas | 🟡 | Regla de desvío en `calcular_consumo`. | Entidad, tipos, ciclo de vida, notificación. |
| MOD-06 a MOD-11 | ❌ | — | Todo. |
| MOD-12 Tablero y reportes | 🟡 | Tablero, reportes, Excel con marca. | PDF, más filtros e indicadores. |
| MOD-13 Usuarios y roles | ❌ | — | Todo. |
| MOD-14 Bot de Telegram | ❌ | — | Todo. |

---

## 3. Diferencias entre código y documento

Clasificación: **(a)** el código debe cambiar · **(b)** el documento debe actualizarse ·
**(c)** decisión del responsable del proyecto.

### 3.1 Diferencias conocidas (verificadas)

| Tema | Código actual | Documento v1.1 | Clasificación y comentario |
|---|---|---|---|
| Identificadores | `UUID` generado en el dominio (`field(default_factory=uuid4)`). | `int` en el diagrama de entidades. | **(b)** Confirmado. El UUID permite crear entidades sin consultar la base (útil para el procesamiento en segundo plano de tickets) y no expone cantidades de registros en URLs. |
| `Cliente` y `Producto` | Existen como entidades; el viaje los referencia. | No figuran; el viaje tiene `material` como texto. | **(b)** Confirmado. `Producto` reemplaza a `material` con un catálogo (evita "Cal", "cal viva", "CAL"…); `Cliente` prepara la futura facturación aunque hoy sea uno solo. |
| Importación de tarjeta de combustible | `ImportarCargas` con lectores Excel/CSV, sinónimos de columnas, números argentinos y sin duplicados. | Sin RF propio. | **(b)** Confirmado. Es un segundo canal de ingesta; además sirve para validar tickets contra el resumen del proveedor (punto abierto 3). |
| Consumo de referencia | Por camión (`consumo_referencia_l100km`). | Por ruta y estado de carga. | **(a)** Confirmado. Agregar `Ruta` con referencias cargado / vacío; usar el valor del camión como **respaldo** cuando la ruta todavía no tiene historial. |
| Viaje | `origen` y `destino` como texto; sin estado de carga. | `RUTA` con país, km y referencias; `estado_carga`. | **(a)** Confirmado. Ver además 3.2 sobre tramos. |
| Moneda | Sólo `precio_litro`; sin moneda. | `monto_original`, `moneda`, `id_tipo_cambio`, `monto_ars`. | **(a)** Confirmado. Objeto de valor `Dinero` y entidad `TipoCambio`. |
| Alertas | Booleano calculado al generar el reporte. | Tabla `ALERTA` con estado y resolución. | **(a)** Confirmado. |
| Frontend | Jinja2 (server-side). | React + TypeScript. | **(c)** Ver decisión 4.1. |
| Estructura de carpetas | Capas globales. | Carpeta por módulo con sus capas. | **(c)** Ver decisión 4.2. |
| Entorno | Windows nativo, PostgreSQL 17 local, Programador de tareas. | WSL2 + Docker Compose, Celery + Redis. | **(c)** Ver decisión 4.3. |
| Python | 3.13 | 3.12 | **(b)** Confirmado (`pyproject.toml`: `requires-python = ">=3.13"`). |
| Colores de marca | `#0706E5` y `#F56A11` (`marca/__init__.py`). | Aproximaciones (`#1A3DC8`, `#F47B20` en los diagramas). | **(b)** Confirmado. |

### 3.2 Diferencias nuevas encontradas en el análisis

| Tema | Código actual | Documento v1.1 | Clasificación y comentario |
|---|---|---|---|
| Carga que supera el tanque (RF-18) | Se **rechaza** (`ReglaNegocioViolada`). | Se **registra y genera alerta**. | **(a)** El documento tiene razón: con tickets leídos por IA, rechazar pierde el dato. Propuesta: registrar con alerta; mantener el rechazo sólo para valores absurdos (por ejemplo, más del doble del tanque), que casi siempre son errores de lectura. |
| Tramos dentro del viaje | — | **Inconsistencia interna:** RF-09 y CU-03 hablan de estado de carga **por tramo**, pero el diagrama tiene un único `VIAJE.estado_carga`. | **(a) + (b)** Modelar `TramoViaje` (estado de carga, km inicio, km fin) dentro del viaje: un viaje típico = ida cargado + regreso vacío. Corregir el diagrama. Depende del punto abierto 4. |
| Criterio de duplicados (RF-08) | Referencia externa, o camión + fecha + litros. | Estación + fecha/hora + monto + patente. | **(b)** Documentar ambos: el del documento para tickets por foto y la referencia externa para archivos de tarjeta. |
| Origen de los km (RF-10) | Odómetro de salida y llegada del viaje. | Km entre cargas consecutivas (tanque lleno) o GPS. | **(b)** Agregar el odómetro del viaje como tercer método (es el más preciso para un viaje cerrado). Implementar los otros dos con GPS. |
| Tolerancia del tanque | `TOLERANCIA_TANQUE_PCT` configurable (5 %). | "≤ capacidad del tanque". | **(b)** Documentar la tolerancia: los tanques admiten algo más que la capacidad nominal. |
| Camión | `marca` y `modelo` separados; `activo`; `consumo_referencia_l100km`. | `marca_modelo`, `anio`, `km_actual`, `estado`. | **(a)** agregar `anio` y `km_actual`; **(b)** mantener marca y modelo separados y la referencia del camión como respaldo. |
| Fechas de auditoría | Sólo `creado_en`. | `created_at` y `updated_at`. | **(a)** Agregar `actualizado_en` junto con la auditoría; **(b)** el documento puede nombrarlas en español. |
| Estación de servicio | Texto en la carga. | Entidad con latitud y longitud. | **(a)** Cuando llegue la validación geográfica (RF-17). |
| PostgreSQL | 17 (instalado). | 16. | **(b)** |
| Canal adicional: consola (CLI) | `flota importar`, `importar-carpeta`, `exportar`, tareas del Programador de Windows. | No mencionado. | **(b)** Documentar como herramienta de backoffice (ROL-07). |

---

## 4. Decisiones pendientes

Las tres son decisiones de la persona a cargo del proyecto. Las recomendaciones están pensadas para **un
desarrollador solo**, con un piloto de 2 camiones previsto para febrero de 2027.

### 4.1 Frontend: Jinja2 o React

| Opción | Ventajas | Costo de migración | Riesgo |
|---|---|---|---|
| **A. Mantener Jinja2** | Ya funciona; un solo lenguaje y un solo proceso; sin build de frontend. | Ninguno. | Pantallas muy interactivas (mapa, validación con imagen al lado) se vuelven incómodas. |
| **B. Jinja2 + HTMX** | Interactividad parcial (filtros, modales, tablas que se recargan) sin escribir JavaScript; se agrega de a una pantalla. | Bajo: una librería JS desde CDN y fragmentos de plantilla. | Bajo. Si después se migra a React, la API REST ya existe y se reutiliza. |
| **C. React + TypeScript (documento)** | Ecosistema para tableros y mapas (Recharts, Leaflet); separación total front/back. | Alto: reescribir las 5 pantallas, autenticación por token, tooling (Node, Vite), un segundo lenguaje. Estimado 3 a 4 sesiones sin funcionalidad nueva. | Medio/alto para una sola persona aprendiendo Python a la vez. |

**Recomendación:** **B (Jinja2 + HTMX) hasta el piloto.** La API `/api/v1` ya está separada, así que
pasar a React más adelante no tira trabajo del backend. Reevaluar antes de MOD-12 (tablero completo,
abril 2027): si el tablero y el mapa de validación geográfica lo piden, migrar en ese momento.
Leaflet y los gráficos también funcionan dentro de una plantilla Jinja2, así que no son motivo suficiente por sí solos.

### 4.2 Estructura de carpetas

| Opción | Ventajas | Costo | Riesgo |
|---|---|---|---|
| **A. Migrar ahora a carpeta por módulo** (`flota/combustible/domain/…`, `flota/shared/`) | Coincide con el documento; cada módulo nuevo nace en su lugar; es el momento más barato (6 entidades, 26 tests que protegen). | 1 sesión corta, sólo mover archivos e imports. | Bajo si se hace **sin cambiar comportamiento** y en un commit aparte. |
| **B. Migrar más adelante** | Nada que hacer ahora. | Crece con cada módulo: con 14 módulos, mover todo es una sesión larga y riesgosa. | Las carpetas globales se llenan (`entities.py` con ~25 entidades). |
| **C. Subpaquetes por módulo dentro de cada capa** (`domain/combustible/`, `application/combustible/`…) | Cambio menor que A; se mantiene la vista por capa. | Similar a A. | Para trabajar en un módulo hay que abrir 4 carpetas distintas. Contradice el documento. |

**Recomendación:** **A, como primer paso de la Sesión 4**, en un commit separado (`refactor:`) que sólo
mueve código y deja los 26 tests en verde. Estructura propuesta:

```text
src/flota/
├── shared/          Dinero, Moneda, UnidadDeTrabajo, errores, auditoría, config
├── flota/           MOD-01 Camion, Chofer   (+ Cliente, Producto: catálogo)
├── viajes/          MOD-02 Ruta, Viaje, TramoViaje
├── combustible/     MOD-03 CargaCombustible, calcular_consumo, importación
├── alertas/         MOD-05
├── monedas/         MOD-10 TipoCambio (peajes después)
├── reportes/        MOD-12 (sólo lectura)
├── web/             panel Jinja2 (transversal)
├── cli.py
└── bootstrap.py     raíz de composición
```

Cada módulo con `domain/`, `application/`, `infrastructure/` y `presentation/` **sólo si los necesita**
(criterio de "arquitectura liviana" de la sección 14.2 del documento).

### 4.3 Tareas en segundo plano en Windows (Celery)

| Opción | Ventajas | Costo | Riesgo |
|---|---|---|---|
| **A. WSL2 + Docker Compose (documento)** | Igual que producción; Celery con soporte oficial. | Instalar WSL2 y Docker; mover el entorno de trabajo; aprender Docker. | Medio: cambio de entorno en medio del aprendizaje. |
| **B. Celery en Windows con `--pool=solo`** | Sin cambiar de entorno. | Redis en Windows (Memurai) o en Docker. | Sin soporte oficial: errores difíciles de diagnosticar. |
| **C. Puerto `ColaTareas` + adaptador simple para el piloto** (tareas en un hilo del propio proceso / `BackgroundTasks` de FastAPI, y el Programador de tareas para lo diario); Celery como segundo adaptador al desplegar | Funciona hoy en Windows; la arquitectura limpia permite cambiar de adaptador sin tocar casos de uso; probado con un adaptador falso en los tests. | Bajo. | Si el proceso se reinicia con tareas a medio hacer, se pierden (aceptable con el volumen del piloto si el ticket queda guardado antes de encolarlo). |

**Recomendación:** **C ahora y A al desplegar.** Producción va a ser un servidor Linux (VPS), donde Docker
Compose con Celery + Redis es lo natural (RNF-10). En desarrollo, seguir en Windows nativo hasta que haya
que probar el despliegue. Agregar un `docker-compose.yml` con PostgreSQL y Redis en la sesión de
despliegue. El bot de Telegram puede correr por *polling* en desarrollo y por *webhook* en producción.

---

## 5. Plan de sesiones

### 5.1 Criterio

El orden de la sección 15.2 del documento (usuarios → flota → viajes → Telegram → combustible → monedas → …)
está pensado para construir **desde cero**. Acá la base ya existe, así que conviene ajustarlo:

1. **Alinear primero el dominio que ya existe** (rutas, tramos, moneda, alertas). Así no se migran datos dos veces, y Telegram e IA nacen con el modelo definitivo.
2. **Usuarios y roles antes de cualquier canal externo** (Telegram, IA): la auditoría (RF-55) y la vinculación de choferes (RF-54) necesitan un usuario.
3. **Validación humana (CU-02) antes que la IA**: la IA deja cargas "Pendientes de validación", y esa pantalla tiene que existir antes.

Sobre la sugerencia original (Sesión 4 con ruta + estado de carga + Dinero + TipoCambio + Alerta + auditoría):
**es demasiado grande para una sesión**, y la auditoría depende de los usuarios. Se divide en dos sesiones, y la auditoría pasa a la de usuarios.

### 5.2 Sesiones propuestas

| Sesión | Objetivo | RF / CU | Dominio y migraciones | Tests nuevos | Riesgo |
|---|---|---|---|---|---|
| **4 — Rutas y tramos** | (Paso 0: reorganización por módulo si se aprueba 4.2.) Viaje sobre rutas, con tramos cargado / vacío y referencia por ruta. | RF-09, RF-10, RF-11, RF-13 · CU-03 · MOD-01, MOD-02 | `Ruta` (origen, destino, país, km estimados, ref. cargado y vacío); `TramoViaje`; `Viaje.ruta_id`; `Camion.anio` y `km_actual`. Migración que **crea rutas a partir de los pares origen/destino existentes** y un tramo "cargado" por viaje. Consumo por tramo con respaldo en la referencia del camión. Histórico por ruta. | Consumo por tramo; respaldo al camión; histórico por ruta; migración de datos con SQLite. | **Medio**: migración de datos existentes; depende del punto abierto 4 (cómo se identifican los tramos). |
| **5 — Moneda y alertas** | `Dinero`, `TipoCambio` con carga manual, alertas persistentes con ciclo de vida. | RF-16, RF-18, RF-20, RF-40, RF-41 · CU-06, CU-13 (manual) · MOD-05, MOD-10 | Objeto de valor `Dinero` (monto + `Moneda` ARS/CLP) con conversión; `TipoCambio`; la carga pasa a `monto_original`/`moneda`/`tipo_cambio_id`/`monto_ars` (migración desde `precio_litro`); entidad `Alerta` (tipo, origen, valores, estado, resolución). RF-18 pasa de rechazo a alerta. | Aritmética y conversión de `Dinero`; cotización fija; transiciones de estado de `Alerta`; RF-18. | **Medio**: cambia la forma de guardar importes. |
| **6 — Usuarios, roles y auditoría** | Login en el panel, permisos por módulo, registro de cambios. | RF-53, RF-55, RNF-03 · CU-17 (sin Telegram) · MOD-13 | `Usuario`, `Rol` (ROL-01 a ROL-07), permisos por módulo; `Auditoria` (valor anterior y nuevo en JSON); `actualizado_en` en las tablas; resolución de alertas con usuario real. | Permisos por rol; hash de contraseñas; auditoría en altas, cambios y bajas de gastos. | **Medio**: toca todas las rutas del panel y de la API. |
| **7 — Validación de cargas e imagen** | Estados de validación, imagen respaldatoria y pantalla de pendientes. | RF-02, RF-04, RF-06, RF-07, RF-08 · CU-02 · MOD-03 | `estado_validacion`, `imagen_url`, `json_extraido`, `confianza_ia` en la carga; puerto `AlmacenArchivos` (adaptador en disco); fecha no futura; criterio de duplicados combinado. | Transiciones de validación; duplicados; almacenamiento con adaptador falso. | Bajo. |
| **8 — Extracción de tickets con IA** | Leer tickets (AR y CL) con Claude y validar la salida. | RF-03, RF-05 (cola) · RNF-06, RNF-07 · MOD-03 | Puertos `ExtractorComprobantes` y `ColaTareas`; adaptador Claude con visión; esquema Pydantic de salida; registro de costo por comprobante. | Extractor falso en unitarios; JSON inválido o baja confianza → pendiente; prueba manual con tickets reales. | **Medio/alto**: necesita tickets reales y una API key; costo por uso. |
| **9 — Bot de Telegram** | Canal del chofer: enviar ticket, confirmar y vincular cuenta. | RF-01, RF-05, RF-54, RNF-01 · CU-01, CU-17 (vinculación) · MOD-14 | `Chofer.telegram_id`; código de vinculación; handlers que invocan casos de uso. | Handlers con bot y extractor falsos; chofer no vinculado rechazado. | Medio: punto abierto 9 (celulares y datos en Chile). |
| **10 — Peajes y tipo de cambio automático** | Peajes en ARS/CLP y cotización diaria. | RF-38, RF-39, RF-42 · CU-12, CU-13 · MOD-10 | `Peaje`, `PuestoPeaje`; puerto `ProveedorTipoCambio` con adaptador HTTP. | Conversión de peajes; sin cotización del día → última disponible y marca de revisión. | Bajo; depende del punto abierto 6 (fuente oficial). |
| **11 — Integración GPS** | Importar lecturas y usar km reales. | RF-14, RF-15 · CU-04 · MOD-04 | `LecturaGPS`; puerto `ProveedorGPS` (primero por archivo). | Asociación por patente y horario; patente desconocida. | **Alto**: depende del proveedor (punto abierto 2). |
| **12 — Alertas geográficas y notificaciones** | Validar la ubicación de cada carga y avisar. | RF-17, RF-19 · MOD-05 | `EstacionServicio` con coordenadas; objeto de valor `Coordenada` (distancia); puerto `Notificador`. | Distancia ticket–GPS; notificador falso. | Medio. |
| **13 — Asistente IA para Excel** | Volcar datos validados en la planilla de la empresa. | RF-43 a RF-49 · CU-14, CU-15 · MOD-11 | `PlantillaExcel`, `SincronizacionExcel`; puerto `PlanillaDestino`. | Mapeo, agregado sin sobrescribir, respaldo previo. | Medio: punto abierto 5 (dónde vive la planilla). |
| **14 a 17 — Módulos de gestión** | Viáticos, mantenimiento, stock, neumáticos (en ese orden, según 15.2). | RF-21 a RF-37 · CU-07 a CU-11 · MOD-06 a MOD-09 | Arquitectura liviana: entidad + caso de uso + repositorio por módulo. | Reglas de stock (egreso mayor al disponible), planes preventivos, posiciones de neumáticos. | Bajo/medio. |
| **18 — Tablero, reportes y despliegue** | Indicadores completos, PDF, filtros; Docker y respaldos. | RF-50 a RF-52 · RNF-04, RNF-10 · CU-05, CU-16 · MOD-12 | Consultas de sólo lectura; `docker-compose.yml`; respaldo diario. | Reportes por chofer, ruta y país. | Medio. |

---

## 6. Propuesta de cambios para el documento v1.2

Puntos clasificados **(b)**: el documento debe reflejar lo que el código ya resolvió. **No se editó el documento.**

1. **Identificadores:** reemplazar `int id_xxx PK` por `uuid id PK` en los tres diagramas de entidades y explicar el motivo en los criterios de la sección 10.
2. **Entidades `CLIENTE` y `PRODUCTO`:** agregarlas al diagrama 10.1; `VIAJE` referencia `id_cliente` e `id_producto` en lugar de `material`. Agregar `PRODUCTO` al glosario (cal viva, cal hidratada, …).
3. **Nuevo RF-56 (sección 5.1):** "El sistema debe importar cargas de combustible desde archivos Excel o CSV del proveedor de la tarjeta de combustible, reconociendo los nombres de columna habituales, números en formato argentino y sin duplicar cargas al reimportar." Prioridad 🟡. Mencionar en 1.2 que hay **dos canales de ingesta** (Telegram y archivo de tarjeta) y vincularlo al punto abierto 3.
4. **Nuevo CU-18 — Importar cargas desde archivo de tarjeta** (actor: Administrativo / Sistema), que implementa RF-56; agregarlo a la tabla 8.1, al diagrama de casos de uso y a la matriz de trazabilidad (H-01, H-02).
5. **RF-08:** completar el criterio de duplicados: "… o misma referencia externa (número de comprobante o de transacción de la tarjeta)".
6. **RF-10:** agregar como método de cálculo los km del odómetro de salida y llegada del viaje.
7. **RF-04 / RF-18:** documentar la **tolerancia configurable sobre la capacidad del tanque** (`TOLERANCIA_TANQUE_PCT`, 5 % inicial).
8. **Camión:** mantener `marca` y `modelo` como campos separados y agregar `consumo_referencia_l100km` como referencia de respaldo cuando la ruta no tiene historial (RF-11, RF-13).
9. **Tramos (corrección de inconsistencia):** reemplazar `VIAJE.estado_carga` por una entidad `TRAMO_VIAJE` (estado de carga, km inicio, km fin), coherente con RF-09 y CU-03.
10. **Stack (secciones 14.1 y 14.5):** Python **3.13** y PostgreSQL **17**.
11. **Colores de marca:** usar `#0706E5` (azul) y `#F56A11` (naranja) en los diagramas, con sus variantes oscuras `#06057F` y `#B84A06`.
12. **Nombres de columnas de auditoría:** `creado_en` / `actualizado_en` (español, como el resto del modelo).
13. **Herramientas de backoffice:** documentar la consola (`flota importar`, `importar-carpeta`, `exportar`) y su uso con tareas programadas, como funciones de ROL-07 en la sección 13.2.
14. **Sección 14.3 (estructura):** actualizar el árbol al que se apruebe en la decisión 4.2 (paquete `flota` en `src/`, sin carpeta `backend/` mientras no exista `frontend/`).
15. **Comprobante como entidad propia** (agregado en la Sesión 7): agregar `COMPROBANTE` al modelo de datos (archivo, canal, estado, JSON extraído, confianza, problemas). La carga, el peaje y el viático se crean recién cuando los datos están completos y validados, y referencian su comprobante; `CARGA_COMBUSTIBLE.estado_validacion` queda en validada / validada por IA / anulada. Así un ticket incompleto nunca es una carga a medias.
16. **Control de cambios (sección 18):** registrar la v1.2 con estos puntos y las decisiones 4.1 a 4.3 una vez tomadas.
