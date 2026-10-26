# Sesión 6 — Usuarios, roles y auditoría

**Objetivo:** que cada persona entre con su usuario, vea sólo los módulos de su rol, y que todo
cambio sobre gastos quede registrado con quién lo hizo.

**Requisitos:** RF-53, RF-55, RNF-03 (en la aplicación; el HTTPS se configura al desplegar) ·
**Casos de uso:** CU-17 (salvo la vinculación con Telegram, que llega con el bot) · **Módulo:** MOD-13.

## Qué se hizo

### Módulo `usuarios` (MOD-13)
- **`Usuario`** con nombre, email (único), rol, habilitado y chat de Telegram para avisos.
- **Roles ROL-01 a ROL-07** y una **matriz de permisos** por módulo (lectura / escritura), tomada de
  las secciones 7 y 12 del documento de requisitos. Ejemplos:
  - Gerencia (ROL-01) lee todo y gestiona alertas.
  - El Administrativo (ROL-03) opera viajes, combustible, alertas, viáticos, peajes y Excel.
  - El Jefe de Taller (ROL-04) ve mantenimiento, neumáticos, stock (lectura) y la flota.
  - El Chofer (ROL-06) no entra al panel: usa Telegram.
  - Sólo el Administrador de sistema (ROL-07) gestiona usuarios.
- **Login** en el panel, **Mi cuenta** (cambiar la contraseña) y **Usuarios** (alta, rol,
  habilitar/deshabilitar, restablecer contraseña).
- El **menú** muestra sólo lo que el rol puede ver; quien no tiene tablero (taller, stock) entra
  directo a su primera página.
- **API:** `POST /api/v1/auth/token` devuelve un token (12 h) para `Authorization: Bearer ...`;
  `/api/v1/auth/yo`, `/api/v1/usuarios`, `/api/v1/auditoria`.
- **Consola:** `flota crear-usuario` (pide la contraseña sin mostrarla). `flota datos-demo` crea un
  usuario por rol con contraseña `demo1234` (sólo para probar).

### Auditoría (RF-55)
- Cada alta o cambio de cargas de combustible, cotizaciones, alertas y usuarios guarda: fecha,
  usuario, tabla, registro, acción, **valor anterior y valor nuevo** (en JSONB). El hash de la
  contraseña nunca se guarda en la auditoría.
- Página **Auditoría** (desde Usuarios), que muestra campo por campo qué cambió.
- Las alertas ahora guardan **quién las resolvió** (RF-20 completo).

### HTMX
- Resolver una alerta reemplaza sólo su fila, sin recargar la página. Es la primera aplicación de
  la decisión "Jinja2 + HTMX" del análisis de brechas.

### Base de datos y tests
- Migración `ae1f345ad947`: tablas `usuarios` y `auditoria` (probada en PostgreSQL y SQLite).
- De 90 a **112 tests**. Los tests de integración ahora inician sesión; se suman
  `test_usuarios.py` (permisos, contraseñas, auditoría) y `test_seguridad.py` (login, 401/403,
  token, redirección segura, HTMX).

## Conceptos nuevos

### Hash de contraseñas (Argon2)
Se guarda una "huella" irreversible de la contraseña, con sal aleatoria: dos usuarios con la misma
contraseña tienen hashes distintos. Para validar el login se calcula de nuevo y se compara. Argon2 es
lento **a propósito**, para que probar millones de contraseñas no sea práctico.

### Middleware y cookies firmadas
`SessionMiddleware` envuelve todos los pedidos y guarda la sesión en una cookie **firmada** con
`SECRET_KEY` (con `itsdangerous`): el usuario la ve pero no puede falsificarla. `same_site="lax"`
protege contra formularios enviados desde otros sitios (CSRF).

### Dependencias encadenadas y objetos llamables
- `Permiso(Modulo.X)` es un objeto con `__call__`: se configura una vez y FastAPI lo llama en cada pedido.
- `Permiso` depende de `usuario_actual`, que depende de la unidad de trabajo: FastAPI resuelve la
  cadena y **reutiliza** cada dependencia dentro del mismo pedido.

### El "actor" viaja con la unidad de trabajo
`usuario_actual` hace `uow.actor = Actor(usuario.id, usuario.nombre)`. Los casos de uso llaman a
`uow.auditar(...)` sin recibir el usuario por parámetro, así sus firmas no cambiaron. Lo que se hace
desde la consola queda como "consola" y lo que hace el sistema solo, como "sistema".

### Seguridad en detalles
- El login responde lo mismo si falla el email o la contraseña: no revela qué emails existen.
- Después del login sólo se redirige a rutas internas (`/algo`, nunca `//otro-sitio`).
- Al iniciar sesión se borra la sesión anterior.

## Pendiente
- Fijar `SECRET_KEY` en el `.env` real. Sin ella, se genera una al arrancar y las sesiones se pierden
  al reiniciar el servidor.
- Vinculación chofer ↔ Telegram (RF-54): con el bot, en la Sesión 9.
