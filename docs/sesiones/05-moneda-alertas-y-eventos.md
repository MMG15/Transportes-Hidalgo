# Sesión 5 — Moneda, alertas y eventos de dominio

**Objetivo:** que todo gasto guarde su importe en la moneda original y en pesos argentinos con una
cotización fija, y que las alertas pasen de ser una marca calculada a una entidad con estado que
alguien analiza y resuelve.

**Requisitos:** RF-16, RF-18, RF-19 (en el panel), RF-20, RF-39 (carga manual), RF-40, RF-41 ·
**Casos de uso:** CU-06, CU-13 (carga manual y corrección) · **Módulos:** MOD-05, MOD-10.

## Qué se hizo

### Módulo `monedas` (MOD-10)
- **`TipoCambio`**: cotización de un día (cuántos ARS vale 1 CLP) con su fuente. Una por día.
- **Regla única de conversión** (`convertir_a_pesos`): un gasto en CLP usa la cotización de su
  fecha; si ese día no hay, la última anterior, y el gasto queda marcado **"revisar"** (CU-12 E1).
- **Corrección** (CU-13 E1): si la cotización ya se usó en algún gasto, hay que confirmarlo; los
  gastos conservan la cotización que se les aplicó (RF-41).
- Página **Tipo de cambio** en el panel y API `/api/v1/tipos-cambio`.

### Moneda en las cargas de combustible
- La carga guarda un **`ImporteGasto`**: monto original, moneda, cotización, monto en ARS y qué tipo
  de cambio se aplicó. Se puede informar el monto total del ticket o el precio por litro.
- La importación de archivos acepta las columnas opcionales `importe` y `moneda`.
- **RF-18:** una carga que supera el tanque **se registra** y genera una alerta (antes se rechazaba).
  Sólo se rechaza si supera el **doble** del tanque, porque eso es un error de tipeo o de lectura.

### Módulo `alertas` (MOD-05)
- **`Alerta`** con tipo, origen (tabla + id del registro que la generó), valores detectado y de
  referencia, y ciclo de vida: **abierta → en análisis → justificada / desvío confirmado**.
  Resolverla exige un comentario; confirmar el desvío la **escala a Gerencia** (CU-06).
- Se generan solas:
  - **Desvío de consumo por tramo** (RF-16) al cerrar un tramo, al finalizar el viaje o cuando llega
    un ticket tarde. Si al recalcular el consumo vuelve a la normalidad, el sistema cierra la alerta;
    una alerta resuelta por una persona nunca se reabre.
  - **Carga mayor al tanque** (RF-18).
- Página **Alertas** (abiertas / todas, con botones para resolver) y el **tablero** muestra las
  alertas abiertas. API `/api/v1/alertas`.
- Comando `flota recalcular-alertas`: evalúa los viajes ya cerrados (útil después de migrar).

### Eventos de dominio
- Los casos de uso **registran eventos** (`ViajeFinalizado`, `TramoCerrado`, `CargaRegistrada`,
  `AlertaGenerada`, `AlertaEscalada`) y la unidad de trabajo los **publica después del commit**.
- `bootstrap.py` arma el **bus de eventos** y suscribe los manejadores del módulo de alertas.
- Resultado: `viajes` y `combustible` no conocen a `alertas`, aunque `alertas` reaccione a ellos.

### Base de datos
- Migración `619242b605d9`: tablas `tipos_cambio` y `alertas`; en `cargas_combustible`, el precio
  por litro pasa a ser un importe completo. Probada en PostgreSQL y SQLite (subida y bajada) sin
  perder datos: el total de importes antes y después de migrar es idéntico.

### Tests
- De 59 a **90**: `test_monedas.py`, `test_alertas.py`, `test_eventos.py` y casos nuevos en
  combustible, API y panel. Los tests de integración usan el bus real: prueban que finalizar un
  viaje genere su alerta.

## Conceptos nuevos

### Objetos de valor (`Dinero`)
No tienen identidad: dos `Dinero(100, CLP)` son el mismo valor. Son **inmutables** y se comparan por
contenido. `Dinero` define `__add__`, `__sub__`, `__mul__` y `__lt__`, así se opera como con
números, pero **sumar ARS con CLP da error**. En una dataclass `frozen=True` se normalizan campos
con `object.__setattr__`.

### Eventos de dominio y patrón Observador
Un evento describe algo que **ya pasó** (`ViajeFinalizado`). Quien lo publica no sabe quién lo
escucha. El bus (`BusEventos`) guarda, por tipo de evento, la lista de funciones a llamar.
Publicar **después del commit** evita avisar algo que finalmente no se guardó. Si un manejador
falla, se registra con `logging` y no se deshace la operación original.

### Closures
`manejadores.suscribir(...)` define funciones adentro de otra función. Esas funciones "recuerdan"
la configuración (umbral, tolerancia, cómo crear la unidad de trabajo) para cuando llegue el evento.

### Inversión de dependencias entre módulos
El repositorio de tipos de cambio necesita saber si una cotización ya se usó en **cualquier**
tabla de gastos, pero no puede importar a combustible (combustible depende de monedas). La solución:
la raíz de composición (`unidad_de_trabajo.py`) le **pasa** la lista de tablas de gastos.

### Migraciones con `UPDATE` en una sola sentencia
`cargas.update().values(monto_original=round(litros * precio_litro, 2), ...)` transforma todos los
datos en la base, sin traerlos a Python.

## Pendiente para próximas sesiones
- Sesión 6: usuarios, roles y auditoría. Las alertas ya tienen el campo `usuario_id`; hoy se
  resuelven sin usuario y desde la Sesión 6 quedará registrado quién lo hizo.
- RF-19 por Telegram o correo: Sesión 12 (los eventos `AlertaGenerada` y `AlertaEscalada` ya existen).
- RF-39 automática (cotización desde una fuente externa): Sesión 10.
