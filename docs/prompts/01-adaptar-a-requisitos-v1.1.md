# Instrucción para Claude (VS Code) — Adaptar el proyecto al documento de requisitos v1.1

## Contexto

Este repositorio (`gestion-flota`, paquete `src/flota`) se construyó en las sesiones 1 a 3 **antes** de que existiera el documento de requisitos. Ya funciona: tiene arquitectura limpia, PostgreSQL con Alembic, API FastAPI, panel web con Jinja2, CLI con Typer, importación de cargas desde Excel/CSV de la tarjeta de combustible, reporte Excel con la marca y 26 tests.

Ahora existe el documento de requisitos **v1.1**: `requisitos_trazabilidad_hidalgo_v1.1.md` (está en la raíz del proyecto). Es la referencia funcional del sistema completo. Tiene 55 RF y 10 RNF, 7 roles, 17 casos de uso, 14 módulos, un modelo de datos y un orden de desarrollo.

**Objetivo:** alinear el código existente con el documento sin tirar lo que ya funciona, y dejar un plan por sesiones para construir lo que falta.

## Reglas de trabajo

1. **No escribas código en esta primera tarea.** Primero analizá y proponé. Esperá mi aprobación antes de modificar `src/`, `tests/` o `migrations/`.
2. Respetá la arquitectura limpia actual: `presentation → application → domain`, con `infrastructure` implementando puertos y `bootstrap.py` como raíz de composición.
3. Mantené las convenciones del proyecto:
   - `Decimal` para montos y litros.
   - `dataclass(kw_only=True)` en el dominio.
   - Errores con `DatosInvalidos` y `ReglaNegocioViolada`.
   - Español en nombres de negocio.
   - `ruff` sin observaciones.
4. Todo cambio debe dejar los **26 tests existentes en verde** y agregar tests nuevos. Las reglas de dominio llevan tests unitarios sin base de datos.
5. Los cambios de base de datos van siempre por **migraciones de Alembic**, nunca editando tablas a mano.
6. Al cerrar cada sesión de trabajo:
   - Crear `docs/sesiones/NN-titulo.md` con el mismo formato que las anteriores: qué se hizo, conceptos de Python, patrones y librerías.
   - Actualizar `docs/guia-tecnica.md`.
   - Regenerar los Word con `uv run python scripts/generar_word.py`.
   - Proponer el mensaje de commit "Sesión N: …".
7. **Trazabilidad en el código:** cada caso de uso nuevo o adaptado lleva en su docstring el código del documento (por ejemplo `"""CU-01 — RF-01, RF-03 a RF-08"""`).

## Tarea 1 — Ordenar la documentación

- Mover `requisitos_trazabilidad_hidalgo_v1.1.md` a `docs/requisitos_v1.1.md` y el `.docx` a `docs/word/`.
- El archivo `documento_requerimientos_trazabilidad.docx` de la raíz es el borrador v0.1: moverlo a `docs/word/historico/`.
- Agregar un enlace al documento de requisitos en el `README.md`.

## Tarea 2 — Análisis de brechas (entregable: `docs/brechas-requisitos-v1.1.md`)

Leé el documento de requisitos completo y el código, y generá un informe con:

### 2.1 Matriz de cobertura

Una tabla con **cada RF y RNF** y las columnas: `ID | Estado | Dónde está en el código | Qué falta`.

Valores de `Estado`:
- ✅ **Implementado**
- 🟡 **Parcial**
- ❌ **Falta**
- ↔️ **Diferente**: el código lo resuelve de otra forma que el documento.

Hacé lo mismo con los casos de uso CU-01 a CU-17 y los módulos MOD-01 a MOD-14.

### 2.2 Diferencias ya conocidas entre código y documento

Verificalas y clasificá cada una:
- **(a)** el código debe cambiar,
- **(b)** el documento debe actualizarse porque el código está mejor resuelto, o
- **(c)** decisión mía.

| Tema | Código actual | Documento v1.1 | Mi sugerencia |
|---|---|---|---|
| Identificadores | `UUID` | `int` en el diagrama de entidades | (b) mantener UUID |
| Entidades `Cliente` y `Producto` | Existen | No figuran en el modelo de datos | (b) agregarlas al documento |
| Importación de tarjeta de combustible (Excel/CSV, sinónimos, sin duplicados) | Implementada | No tiene RF propio | (b) agregar RF y documentar como segundo canal de ingesta junto a Telegram |
| Consumo de referencia | Por **camión** (`consumo_referencia_l100km`) | Por **ruta y estado de carga** (cargado / vacío) | (a) evolucionar: agregar `Ruta` y tramos cargado/vacío, y usar el valor del camión como respaldo |
| Viaje | `origen` y `destino` como texto; sin estado de carga | `RUTA` con país, km y referencias; `estado_carga` | (a) |
| Moneda | Solo `precio_litro`; sin moneda | `monto_original`, `moneda`, `id_tipo_cambio`, `monto_ars` | (a) introducir un objeto de valor `Dinero` y la entidad `TipoCambio` |
| Alertas | Booleano calculado en el reporte | Tabla `ALERTA` con estado y resolución (RF-16 a RF-20) | (a) |
| Frontend | Jinja2 (server-side) | React + TypeScript | (c) |
| Estructura de carpetas | Capas globales (`domain/`, `application/`…) | Carpeta por módulo con sus capas | (c) |
| Entorno | Windows nativo, PostgreSQL 17 local, Programador de tareas | WSL2 + Docker Compose, Celery + Redis | (c) |
| Python | 3.13 | 3.12 | (b) actualizar el documento a 3.13 |
| Colores de marca | `#0706E5` y `#F56A11` (extraídos del logo) | Aproximaciones | (b) el documento debe usar los del código |

### 2.3 Decisiones que necesito tomar

Para cada tema marcado (c), presentá las opciones con ventajas, costo de migración y tu recomendación para un desarrollador solo. En particular:
- **Jinja2 vs. React:** ¿conviene mantener Jinja2 (quizás con HTMX) o migrar a React? ¿Cuándo?
- **Estructura:** ¿migrar a carpetas por módulo ahora, más adelante, o usar subpaquetes por módulo dentro de cada capa?
- **Celery en Windows:** cuando lleguen las tareas en segundo plano (procesar tickets con IA), ¿WSL2 + Docker, o una alternativa compatible con Windows?

### 2.4 Plan de sesiones

Proponé las próximas sesiones siguiendo el **orden de la sección 15.2** del documento, partiendo de lo que ya existe. Por cada sesión:
- objetivo,
- RF y CU que cubre,
- cambios de dominio y migraciones,
- tests nuevos,
- riesgo.

Sugerencia de arranque (validala o mejorala):
- **Sesión 4 — Alinear el núcleo:** `Ruta` y estado de carga en `Viaje`; referencia por ruta; `Dinero` y `TipoCambio`; `Alerta` como entidad; auditoría (RF-55).
- **Sesión 5 — Usuarios y roles** (MOD-13, ROL-01 a ROL-07) con autenticación en el panel.
- **Sesión 6 — Bot de Telegram + extracción de tickets con Claude** (MOD-14, CU-01, CU-02), con los puertos `ExtractorComprobantes` y `AlmacenArchivos`.

## Tarea 3 — Propuesta de actualización del documento (v1.2)

Listá los cambios que el documento de requisitos necesita para reflejar lo que el código ya resolvió mejor (todos los puntos clasificados como **(b)**). No edites el documento: solo dejá la lista al final de `docs/brechas-requisitos-v1.1.md`.

## Al terminar

Mostrame:
1. Un resumen de la cobertura (cuántos RF están en cada estado).
2. Las decisiones pendientes.
3. El plan de sesiones.

Esperá mi aprobación antes de empezar la Sesión 4.
