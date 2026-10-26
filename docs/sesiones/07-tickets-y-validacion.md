# Sesión 7 — Tickets (comprobantes) y validación de cargas

**Objetivo:** recibir la foto o el PDF de cada ticket, conservarla como respaldo y que
Administración valide los datos mirando la imagen. Es la base que la lectura con IA (Sesión 8) y el
bot de Telegram (Sesión 9) van a usar.

**Requisitos:** RF-02, RF-04, RF-06, RF-07, RF-08 · **Caso de uso:** CU-02 · **Módulo:** MOD-03.

## Qué se hizo

### Decisión de diseño: el comprobante es una entidad propia
Un ticket puede llegar incompleto o ilegible. Si se guardara como `CargaCombustible`, la carga
perdería sus garantías (litros, camión y fecha obligatorios) y el cálculo de consumo tendría que
manejar cargas a medias. Por eso hay dos entidades:

- **`Comprobante`**: la foto o PDF tal como llegó (canal, estado, datos leídos, problemas).
- **`CargaCombustible`**: se crea recién cuando los datos están completos y validados, y queda
  vinculada a su comprobante.

Se propone llevar este cambio al documento de requisitos v1.2 (punto 15 del análisis de brechas).

### Módulo `comprobantes`
- **Recibir** (RF-02): Administración sube la foto (o la toma con la cámara del celular) o el PDF.
  Sólo JPG, PNG, WEBP o PDF de hasta 10 MB.
- **Guardar el original** (RF-07): puerto `AlmacenArchivos` con un adaptador en disco, en
  `archivos/comprobantes/<tipo>/<año>/<mes>/`. La carpeta está fuera de git y va en el respaldo.
- **Pendientes** (RF-06): sin lectura automática, todo comprobante queda "pendiente de
  validación" con el motivo. La página **Tickets** los lista por orden de llegada.
- **Validar** (CU-02): pantalla con la **imagen al lado del formulario**, que se precarga con lo
  que haya leído la IA. Al confirmar se registra la carga con todas sus reglas (tanque, duplicados,
  moneda, fecha), en **una sola transacción** junto con el cambio de estado del comprobante.
- **Descartar** (CU-02 E1): ilegible o ajeno a la empresa, con motivo.
- Todo queda en la **auditoría**; al validar, el antes y el después muestran qué se corrigió.
- Eventos `ComprobanteRecibido` y `ComprobantePendiente`: los van a usar la IA y el bot.

### Cargas de combustible
- **Estado de validación:** *validada* (por una persona), *validada por IA* (Sesión 8) o
  **anulada**. Las anuladas siguen en la base y en la auditoría, pero no cuentan para el consumo.
  Al anular se recalculan las alertas del viaje (evento `CargaAnulada`).
- **Fecha no futura** (RF-04), con una hora de margen para relojes desfasados.
- **Duplicados** (RF-08): además de la referencia y de camión + fecha + litros, ahora también
  camión + estación + fecha y hora + monto, el criterio del documento.
- Orígenes nuevos: `ticket` (foto subida al panel) y `telegram`.
- En la tabla de cargas, un 🧾 lleva al ticket de la carga y se puede **anular** con motivo.

### Base de datos y tests
- Migración `e433dbe34ca5`: tabla `comprobantes` y columnas nuevas en `cargas_combustible`. Las
  cargas existentes quedan "validada". Probada en PostgreSQL y SQLite.
- De 112 a **125 tests**: `test_comprobantes.py` (unitarios y de integración). Los tests guardan
  los archivos en una carpeta temporal que pytest borra sola (`tmp_path`).

## Conceptos nuevos

### Subida de archivos (`UploadFile`) y `async`
Un formulario con `enctype="multipart/form-data"` envía archivos; FastAPI los entrega como
`UploadFile`. La ruta es `async def` y usa `await archivo.read()`: mientras espera la lectura, el
servidor puede atender otros pedidos.

### Respuestas binarias
`Response(contenido, media_type="image/png")` devuelve la imagen tal cual. El encabezado
`X-Content-Type-Options: nosniff` impide que el navegador la interprete como otra cosa.

### Defensa contra *path traversal*
El sistema elige el nombre del archivo (un UUID) y verifica con `Path.is_relative_to` que la ruta
final quede dentro de la carpeta. Un nombre malicioso como `../../config` no puede salir de ella.

### Límites de transacción
`registrar_en(uow, datos)` contiene las reglas y guarda sin confirmar; `ejecutar(datos)` abre y
confirma la transacción. Así otro caso de uso puede combinar varios pasos en una sola transacción.

### `dataclasses.replace` para "sacar una foto" del estado
`antes = replace(comprobante)` crea una copia antes de modificarlo; la auditoría guarda `antes`
y `después`.

## Pendiente
- Sesión 8: lectura automática con IA (Claude) al recibir el comprobante. Si los datos son válidos
  y la confianza es buena, la carga se crea sola como "validada por IA"; si no, queda pendiente con
  los datos precargados.
