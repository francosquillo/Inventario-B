# Design — paso-5g-servicios-generales (C-06g)

## Context

Ver `proposal.md` (Why). Estado observado (C-01..C-06f archivados):

- **Esquema** (`inventario/repositories/sqlite_repo.py`): `ESQUEMA_SQL` (todo `IF NOT EXISTS`) crea `usuarios`, `categorias`, `productos`, `ordenes`, `orden_items`, `movimientos`. `procesos` y `orden_procesos` **no** están en `ESQUEMA_SQL`: los crea `_crear_procesos(conn, loguear)` (`_CREAR_PROCESOS_SQL`, siembra `_PROCESOS_INICIALES`, verificación con `_contar(_TABLAS_CONTADAS)`) dentro de `_transaccion` (`BEGIN IMMEDIATE`), solo si `procesos` no existe. `_CLAVE_CHECK` es el CHECK de formato de clave compartido. `PRAGMA foreign_keys = ON` en `conectar`.
- **Arranque**: `inicializar_esquema` = detectar `categorias`/`ordenes` previas → `executescript(ESQUEMA_SQL)` → `_migrar_movimientos` → `_migrar_productos_categoria(sembrar=…)` → `_crear_procesos(loguear=base_existia)` → `NORMALIZAR_FECHAS_SQL` (abre transacción implícita; `_transaccion` exige conexión libre, por eso todo lo transaccional va antes) → `commit`.
- **Órdenes**: `SqliteOrdenRepository.crear(numero, fecha, items, usuario_id, creada_en, procesos=())` inserta orden + ítems + descuentos (`_crear_en_transaccion`) y luego `orden_procesos`, todo en una `_transaccion`, y devuelve `_leer_orden`. Lecturas: `_SQL_LISTAR_ORDENES` (JOIN con ítems) + `_armar(filas)` = `_a_ordenes(filas, _leer_procesos(conn, ids))` (consulta por lote aparte, para no multiplicar filas). `borrar` borra procesos → ítems → orden en una `_transaccion`. `Orden(id, numero, fecha, usuario, items, procesos=())`.
- **Service**: `OrdenService(orden_repo, proceso_repo, ahora)`; `crear(numero, fecha, componentes, usuario_id, procesos=None, procesos_personalizados=None)` valida número → fecha → componentes → procesos → personalizados (todo "datos inválidos", antes de duplicado/productos/stock) y pasa `ProcesoOrden` resueltos al repo.
- **Catálogo de procesos (C-06f)**: `ProcesoService` (listar/crear/renombrar/borrar, `_validar_nombre_libre` con `casefold`), normalización en `services/normalizacion.py` (`clave_desde_texto`, `validar_clave_proceso`, `normalizar_nombre_proceso`, `MENSAJE_CLAVE_PROCESO`), router `api/routers/procesos.py` (`prefix="/api/procesos"`, sesión obligatoria, `PATCH` con `clave` en el cuerpo → 422), errores `ProcesoDuplicado` 409 / `ProcesoNoEncontrado` 404 en `api/app.py`. OpenAPI: 19 rutas.
- **API de órdenes**: `OrdenRequest` con `procesos`/`procesos_personalizados: Optional[Any]` (tipos laxos, mensajes del service); `OrdenOut.procesos: List[ProcesoOrdenOut]`.
- **Web**: "Nueva orden" en `static/index.html` (`#modal-orden`; `fieldset` "Componentes" y luego `fieldset` "Procesos" con `#ord-procesos`); `inventario.js` carga `/api/procesos` al iniciar (`cargarProcesos`), valida con el módulo puro `static/js/procesos.js` (`Procesos.armar`, probado con Node en `tests/test_procesos_js.py`) y maneja el 422 "El proceso 'x' no existe." recargando el catálogo. `/ordenes`: `ordenes.js` `articulo(o)` arma la fila "Procesos:" (chips; en impresión "Procesos realizados" vía `lbl-screen`/`lbl-print`) y "Exportar PDF" imprime el artículo.
- **Datos reales**: `dev-local.db` (`*.db` en `.gitignore`).

## Goals / Non-Goals

**Goals:**
- Servicio general por orden (0 o 1) con sus chequeos, que sobrevive a renombres, cambios de chequeos y borrados del catálogo.
- Alta y borrado de orden siguen siendo una sola transacción, ahora con servicio (regla dura 3).
- Migración aditiva: solo tablas nuevas, cero cambios en filas existentes; siembra que no resucita lo borrado.
- Reutilizar al máximo el patrón de C-06f (catálogo + snapshot, normalización, router, módulo JS puro).

**Non-Goals:**
- Precios del servicio (C-06h), editar el servicio de una orden ya creada (C-06i), formato de impresión nuevo (C-06j).
- Marcar chequeos hechos/no hechos por orden ni agregar/quitar chequeos al asignar el servicio a una orden.
- Página nueva (ruta de página) para el catálogo: la administración web vive en un modal de `/ordenes` (D12).
- Reordenar chequeos con botones o arrastre: el orden es el de las líneas del formulario (D12).
- Servicio general en `/reportes` o filtro por servicio en `/ordenes`.
- Más de un servicio general por orden.

## Decisions

### D1 — Modelo: catálogo de 2 tablas + snapshot de 2 tablas (decisiones 1, 2, 3, 4)

```sql
CREATE TABLE servicios_generales (
    id INTEGER PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE <_CLAVE_CHECK>,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(trim(nombre)) BETWEEN 1 AND 60)
);
CREATE TABLE servicio_chequeos (
    servicio_id INTEGER NOT NULL REFERENCES servicios_generales(id) ON DELETE CASCADE,
    posicion INTEGER NOT NULL CHECK (typeof(posicion) = 'integer' AND posicion >= 1),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60),
    PRIMARY KEY (servicio_id, posicion),
    UNIQUE (servicio_id, nombre COLLATE NOCASE)
);
CREATE TABLE orden_servicio (
    orden_id INTEGER PRIMARY KEY REFERENCES ordenes(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60)
);
CREATE TABLE orden_servicio_chequeos (
    orden_id INTEGER NOT NULL REFERENCES orden_servicio(orden_id) ON DELETE CASCADE,
    posicion INTEGER NOT NULL CHECK (typeof(posicion) = 'integer' AND posicion >= 1),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60),
    PRIMARY KEY (orden_id, posicion),
    UNIQUE (orden_id, nombre COLLATE NOCASE)
);
```

- ★ **Nombre `servicios_generales`** (no `servicios`): C-06h evaluará renombrar en la UI "procesos" a "servicios adicionales"; un nombre de tabla/ruta sin calificar sería ambiguo. Ruta API `/api/servicios-generales` por lo mismo.
- ★ **Chequeos como tabla hija ordenada** (no texto JSON en una columna): CHECKs por chequeo, unicidad por servicio en la BD, paridad directa con Postgres (C-07). Sin clave por chequeo: un chequeo es solo un texto dentro de su servicio (YAGNI); la API los maneja como lista de textos.
- ★ **`orden_servicio.orden_id` como PK** → la base garantiza **cero o un** servicio por orden. C-06h podrá sumar acá la columna de precio del servicio (una fila por orden).
- ★ **Snapshot sin FK al catálogo** (mismo criterio aprobado en C-06f decisión 1): la orden guarda el nombre y **todos** los chequeos tal como estaban al crearla; renombrar, reemplazar chequeos o borrar el servicio del catálogo no toca órdenes pasadas y el borrado no necesita 409. Alternativa: `servicio_id` FK + snapshot (permitiría reportes por servicio; suma `ON DELETE SET NULL` y otra columna en C-07). Alternativa descartada: solo FK (un cambio de chequeos reescribiría la historia).
- `orden_servicio_chequeos` cuelga de `orden_servicio` (FK a su PK) → no puede haber chequeos de una orden sin servicio. `ON DELETE CASCADE` en las cuatro FK como red; el borrado igual borra explícitamente (D5).
- Sin índices extra: las lecturas van por `servicio_id`/`orden_id` (prefijo de la PK).

### D2 — Reglas del catálogo (decisiones 5, 6, 7)

- Clave y nombre: **mismas reglas que procesos** (clave formato `_CLAVE_CHECK`, derivada del nombre si falta con `clave_desde_texto`; nombre 1-60, único con `casefold`). Mensajes propios: "La clave del servicio general admite solo minúsculas sin tilde, números y guiones (hasta 30 caracteres).", "El nombre del servicio general admite hasta 60 caracteres.", "Ya existe un servicio general con clave 'x'." / "…con nombre 'X'.", "No existe un servicio general con clave 'x'.". ★ Se reutiliza la normalización generalizada de C-06f pasando mensaje/tope (sin copiar código).
- ★ **Chequeos: 1 a 30 por servicio** (un servicio sin chequeos no aporta nada que un proceso no dé; 30 alcanza para un service mayor), cada uno recortado, 1-60 caracteres, espacios internos conservados, **sin repetir** dentro del servicio (`casefold`); el orden recibido es el orden mostrado. Mensajes: "El campo chequeos debe ser una lista de textos.", "El servicio general requiere al menos un chequeo.", "El servicio general admite hasta 30 chequeos.", "Chequeo N: El nombre es obligatorio.", "Chequeo N: El nombre admite hasta 60 caracteres.", "Chequeo N: 'x' está repetido." (N = posición desde 1; el repetido es el segundo).
- ★ **Modificación = `PATCH` con `nombre` y/o `chequeos`**; `chequeos` **reemplaza la lista completa** (borrar filas del servicio + insertar las nuevas) en una sola `_transaccion` junto con el renombre: todo o nada. Sin ninguno de los dos → 422 "Indicá el nombre o los chequeos a modificar."; `clave` en el cuerpo → 422 "La clave de un servicio general no se puede cambiar.". Validación completa (nombre y chequeos) **antes** de escribir. Alternativa: sub-recursos `/api/servicios-generales/{clave}/chequeos[/{posicion}]` (más rutas, posiciones inestables, más difícil de usar desde `/docs`).
- ★ El ejemplo sembrado usa los tres chequeos que dio el usuario ("Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"); el usuario completa el resto desde la web (D12) o por API ("etc." del pedido).

### D3 — Siembra solo al crear el catálogo (decisión 8)

Igual que C-06f D2: `servicios_generales` y sus tres tablas hermanas **no** van en `ESQUEMA_SQL`; las crea `_crear_servicios_generales(conn, loguear)` junto con la siembra de `servicio-20-hs` y sus tres chequeos, en una `_transaccion`, **solo si `servicios_generales` no existe**. Borrar todos los servicios (o cambiar los chequeos del de ejemplo) y reiniciar no resiembra nada.

### D4 — Migración aditiva (decisión 9)

`_crear_servicios_generales(conn, loguear=base_existia)` en `sqlite_repo.py`, llamada en `inicializar_esquema` **después de `_crear_procesos` y antes de `NORMALIZAR_FECHAS_SQL`**:

1. Si `servicios_generales` existe → salir (idempotente).
2. En `_transaccion`: contar `ordenes`, `orden_items`, `productos`, `categorias`, `movimientos`, `procesos`, `orden_procesos`; crear las cuatro tablas (orden: catálogo, chequeos, `orden_servicio`, `orden_servicio_chequeos`); sembrar; verificar conteos iguales; ante error → rollback (el DDL de SQLite es transaccional: no queda ninguna de las cuatro) y la excepción sube.
3. `log.info("Agregados los servicios generales de órdenes (%d orden(es) conservadas, sin servicio).", n)` solo si la base ya existía.

Sin `ALTER` ni reconstrucción. Prueba de falla: siembra que viola un CHECK inyectada en el test → no existe ninguna tabla nueva.

### D5 — Entidades, repositorios y atomicidad (decisión 10)

- `domain/entities.py`: `ServicioGeneral(clave, nombre, chequeos: tuple[str, ...])`; `ServicioOrden(nombre, chequeos: tuple[str, ...])`; `Orden.servicio: Optional[ServicioOrden] = None` (default para no romper constructores).
- `repositories/base.py`: `ServicioGeneralRepository` (`listar`, `obtener`, `crear(clave, nombre, chequeos)`, `modificar(clave, nombre=None, chequeos=None)`, `borrar`); `OrdenRepository.crear(..., procesos=(), servicio=None)` recibe un `ServicioOrden` ya resuelto.
- `SqliteServicioGeneralRepository`: `listar` = una consulta catálogo + una de chequeos (`ORDER BY servicio_id, posicion`), armado en Python, ordenado por nombre (`COLLATE NOCASE`); escrituras en `_transaccion`; `IntegrityError` → `ServicioGeneralDuplicado` distinguiendo clave/nombre (como procesos); `borrar` devuelve el servicio borrado con sus chequeos (el `CASCADE` borra los chequeos; igual se borran explícitamente).
- `SqliteOrdenRepository.crear`: tras ítems, descuentos y procesos, `INSERT INTO orden_servicio` + `orden_servicio_chequeos` (posición 1..n) **dentro de la misma `_transaccion`** (★ todo o nada).
- Lectura: ★ consulta por lote aparte, `_leer_servicios(conn, ids)` → `SELECT s.orden_id, s.nombre, c.posicion, c.nombre FROM orden_servicio s LEFT JOIN orden_servicio_chequeos c ON c.orden_id = s.orden_id WHERE s.orden_id IN (…) ORDER BY s.orden_id, c.posicion` → `{orden_id: ServicioOrden}`; `_armar` lo pasa a `_a_ordenes`. Placeholders `?` siempre.
- `borrar`: `DELETE FROM orden_servicio_chequeos WHERE orden_id = ?` + `DELETE FROM orden_servicio WHERE orden_id = ?` + procesos + ítems + orden en la misma `_transaccion`; la orden devuelta (leída antes) trae su servicio.

### D6 — Servicio en el alta de orden (decisiones 11, 12, 13)

- ★ **Campo `servicio`** en `POST /api/ordenes`: clave (texto) o `null`; ausente, `null` o solo espacios = sin servicio. Normalización `strip().lower()`. No es texto → "El campo servicio debe ser texto."; clave inexistente → "El servicio general 'x' no existe." (clave recortada a 30 + "…" si es más larga, como procesos).
- ★ **Prioridad**: dentro de "datos inválidos", después de componentes y antes de procesos: número → fecha → componentes → **servicio** → procesos → personalizados. Así siguen valiendo los escenarios de C-06f ("componentes vacíos + proceso inexistente → componentes").
- `OrdenService(orden_repo, proceso_repo, servicio_repo, ahora)`: resuelve la clave con `servicio_repo.obtener(clave)` y pasa `ServicioOrden(nombre, chequeos)` al repo. Carrera (servicio borrado o modificado entre la validación y el `INSERT`): la orden queda con lo validado (snapshot, sin FK). Aceptado, como en procesos.
- ★ **Snapshot completo, sin elegir chequeos por orden**: asignar un servicio copia todos sus chequeos. Marcar qué chequeos se hicieron o agregar/quitar por orden queda fuera (ver Open Questions).
- ★ **Servicio y procesos son independientes**: un proceso con el mismo nombre que un chequeo no es error (los chequeos son parte del servicio; los procesos son trabajos sueltos).

### D7 — API (decisión 14)

- `OrdenRequest.servicio: Optional[Any] = None` (tipo laxo; mensajes del service). `OrdenOut.servicio: Optional[ServicioOrdenOut(nombre, chequeos: List[str])] = None`, presente siempre (`null` si no hay) en alta, listado y `orden` del borrado. Tests de diccionario exacto se actualizan (aditivo para clientes).
- Router nuevo `api/routers/servicios_generales.py` (`prefix="/api/servicios-generales"`, `tags=["servicios generales"]`, `dependencies=[Depends(get_current_user)]`): `GET ""` → `List[ServicioGeneralOut{clave, nombre, chequeos}]`; `POST ""` (`ServicioGeneralAltaRequest {nombre, chequeos, clave?}`, tipos laxos `Optional[Any]` para que el service dé los mensajes) → 201; `PATCH "/{clave}"` (`ServicioGeneralCambioRequest {nombre?, chequeos?}`; `clave` en el cuerpo → 422; uso de `model_fields_set` para distinguir "ausente" de `null`) → 200; `DELETE "/{clave}"` → 200 con lo borrado (como procesos).
- Errores nuevos: `ServicioGeneralDuplicado(campo, valor)` 409, `ServicioGeneralNoEncontrado(clave)` 404, registrados en `api/app.py`.
- `ServicioGeneralService(servicio_repo)`: listar/crear/modificar/borrar; validación de chequeos en una función pura (`normalizar_chequeos(valor) -> tuple[str, ...]`) en `services/normalizacion.py`.
- ★ Cualquier usuario con sesión administra (hoy solo `admin`). Mismas defensas: sesión (401), cuerpo solo JSON (422 con `text/plain`/formularios/multipart), sin CORS.
- OpenAPI: **21** rutas.

### D8 — "Nueva orden": bloque "Servicio general" (decisiones 15, 16, 17)

- ★ **Ubicación**: `fieldset` "Servicio general" **entre la fecha y "Componentes"** (el servicio define el trabajo; piezas y procesos lo complementan). Alternativa: debajo de "Procesos".
- ★ **Control**: un `select` (`#ord-servicio`) con "Sin servicio general" (`value=""`, por defecto) + servicios por nombre (`value` = clave). Al elegir uno, debajo, "Incluye:" + lista de solo lectura de sus chequeos (`ul` con `textContent`, `aria-live="polite"`); con "Sin servicio general" la lista se oculta. Al abrir el modal vuelve a "Sin servicio general".
- Catálogo: `GET /api/servicios-generales` al iniciar la página (junto con procesos y categorías). Si falla: "No se pudo cargar la lista de servicios generales." en el bloque y solo "Sin servicio general".
- Validación en el navegador (regla dura 3) con un módulo puro nuevo `static/js/servicios.js`: `Servicios.armar(valor, catalogo)` → `{servicio: clave|null, error: texto|null}` (valor vacío → `null`; clave fuera del catálogo cargado → "El servicio general elegido ya no está disponible.") y `Servicios.chequeosDe(clave, catalogo)` → lista; sin DOM al cargar, `window.Servicios`, testeable con Node como `procesos.js`.
- 422 del servicio ("El servicio general 'x' no existe." o "El campo servicio debe ser texto.") → mensaje junto al bloque (`aria-describedby`), recarga del catálogo, selector a "Sin servicio general", modal abierto con el resto de los datos.
- Siempre se envía `servicio` (`null` si no hay).

### D9 — `/ordenes` y PDF de una orden (decisiones 18, 19, 20)

- ★ **Fila "Servicio general:"** bajo la cabecera de cada orden con servicio, **antes** de la fila "Procesos:": etiqueta + nombre del servicio en negrita + `ul` con un chip por chequeo (`textContent`), envolviendo en móvil. Órdenes sin servicio no muestran la fila (como procesos).
- ★ **PDF**: encabezado de C-06c sin cambios ("Orden OT-XXXX" / "Fecha: … · N componentes"). Bloque **"Servicio general" primero** (cambio del usuario, 2026-11-27): justo después del encabezado y **antes** de la tabla de componentes, con título chico, nombre del servicio y sus chequeos uno por línea; luego la tabla de componentes y después "Procesos realizados" (C-06f). En pantalla la fila "Servicio general:" sigue bajo la cabecera de la orden (L2), así que el orden del artículo ya coincide. Mismo mecanismo `lbl-screen`/`lbl-print` y CSS de impresión de C-06f (chips sin fondo en papel). Omitido sin servicio. C-06j rediseñará la impresión completa.
- ★ Sin servicio en `/reportes` ni filtro por servicio en `/ordenes` (no pedido).

### D10 — Paridad Supabase (C-07) (decisión 21)

Postgres: `servicios_generales` (clave única con CHECK regex, `create unique index on servicios_generales (lower(nombre))`, nombre 1-60), `servicio_chequeos (servicio_id bigint references servicios_generales(id) on delete cascade, posicion int, nombre text, primary key (servicio_id, posicion))` + índice único `(servicio_id, lower(nombre))`; `orden_servicio (orden_id bigint primary key references ordenes(id) on delete cascade, nombre text)`; `orden_servicio_chequeos (orden_id bigint references orden_servicio(orden_id) on delete cascade, posicion int, nombre text, primary key (orden_id, posicion))` + índice único `(orden_id, lower(nombre))`. Siembra en el script de esquema (una vez). La RPC `crear_orden` gana `p_servicio jsonb` (`{nombre, chequeos}` o `null`, ya validado) dentro de la misma transacción. Alta y modificación de servicio (catálogo + chequeos) son multi-tabla → RPC `guardar_servicio_general` (o equivalente transaccional); borrar es una fila (cascade). 23505 → 409. RLS como `ordenes`. Anotar en `CHANGES.md` § C-07 al archivar.

### D12 — Administración del catálogo en la web (decisión 15, Q1 resuelta por el usuario 2026-11-27)

- ★ **Dónde**: botón **"Servicios generales"** (`btn-secondary`) junto al título de `/ordenes`, que abre un modal (`#modal-servicios`). Justificación: los servicios se ven en `/ordenes` (listado y PDF); un modal reusa el patrón de la app (acciones como modales, design system R2) y **no suma rutas de página**, sesión de página ni enlace de navegación (cero cambios en `api-http` § páginas, en `paginas.py` ni en los tests de páginas protegidas). Alternativas: página `/servicios` con enlace en la navegación (más superficie: ruta, guardas de sesión, cabeceras de seguridad, tests); sección fija dentro de `/ordenes` (empuja la lista hacia abajo en móvil); modal desde "Nueva orden" (modal dentro de modal).
- ★ **Un solo modal con tres vistas** (sin modales anidados): **lista** (cada servicio en una tarjeta con nombre, chequeos como chips y "Editar"/"Eliminar"; "Nuevo servicio" arriba), **formulario** (título "Nuevo servicio general" / "Editar servicio general"; "Nombre" `maxlength=60`; fieldset "Chequeos" con líneas numeradas de una caja de texto + "Quitar", "Agregar chequeo", contador "N de 30"; pie "Volver" / "Guardar") y **confirmación de borrado** (mismo texto/botón `btn-danger` que "Borrar orden"). El foco pasa al título de cada vista; `Esc`/× cierra el modal.
- ★ **Sin reordenar**: el orden es el de las líneas; para cambiarlo se reescriben las cajas (YAGNI; el usuario pidió "simple"). La clave no se muestra (se deriva del nombre al crear y es inmutable).
- ★ **Edición = `PATCH` con `nombre` y `chequeos` siempre** (más simple que calcular diferencias; el service ya acepta ambos).
- Validación en el navegador con el mismo módulo puro `static/js/servicios.js`: `Servicios.validarFormulario({nombre, chequeos}, catalogo, claveActual)` → `{nombre, chequeos, errores: {nombre, chequeos: [msg|null…]}}` (mismas reglas y textos que D2, sin el prefijo "Chequeo N:" porque el error va en su línea). Rechazos de la API: 409 nombre → campo Nombre; 422 "Chequeo N: …" → línea N; otro 422 → alerta del formulario; 404 → vuelve a la lista recargada con el mensaje.
- Código: `static/ordenes.html` (botón + modal), `static/js/servicios-admin.js` nuevo (DOM del modal, usa `Api`, `UI`, `Servicios`), `ordenes.js` sin cambios de flujo. Tras guardar/eliminar, mensaje de éxito en `role="status"` dentro del modal ("Servicio general X guardado." / "… eliminado."). La lista de órdenes no se recarga (el snapshot no cambia).

### D11 — Tests (Strict TDD, `unittest`, SQLite real)

- Migración: `tests/test_sqlite_migracion_servicios.py` con el DDL de C-06f **copiado literal** (ocho tablas, con procesos sembrados y órdenes con procesos), archivo temporal y `:memory:`: tablas nuevas + siembra, filas existentes intactas, órdenes con `servicio is None`, idempotencia (3 arranques), catálogo vaciado o modificado no se resiembra, falla inyectada → ninguna tabla nueva.
- Esquema (`tests/test_sqlite_schema.py`): doce tablas; CHECKs, UNIQUE NOCASE, PK de `orden_servicio` (un servicio por orden), FK de chequeos de orden a `orden_servicio`.
- Repositorios, services, API (`tests/test_api_servicios_generales.py`, órdenes, CSRF, OpenAPI 21), JS puro (`tests/test_servicios_js.py` con Node), guardas estáticas (`index.html`, `inventario.js`, `ordenes.html`, `ordenes.js`, `servicios-admin.js`), navegador en el verify.

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-27)
- Mockups: openspec/changes/paso-5g-servicios-generales/mockups/ (`nueva-orden.html`, `ordenes.html`, `README.md`)
- Approval: approved (2026-11-27, by user)
- Visual verify: passed (2026-11-27; app real sobre BD temporal, 390x844 y 1440x900, capturas en `mockups/verify/`; consola sin errores salvo el abort y el 422 provocados a propósito; sin diferencias bloqueantes ni mayores respecto de S1, L2, C1 y C2)
- Preview: rendered (2026-11-27, 390x844 y 1440x900 vía http local; `mockups/previews/nueva-orden-S1-{mobile,desktop}.png`, `ordenes-L2-{mobile,desktop}.png`, `ordenes-C1-{mobile,desktop}.png`, `ordenes-C2-{mobile,desktop}.png`)

Base: mockups aprobados de C-06f, tokens `design-system/tokens.css` + `ui.css`, tema oscuro único, cabecera de texto "Inventario". Solo las pantallas que cambian (pedido del usuario):

| ID | Pantalla | Estado |
|----|----------|--------|
| S1 | Nueva orden | Bloque "Servicio general" entre fecha y Componentes con "Servicio 20 hs" elegido y su lista "Incluye:" |
| L2 | Órdenes | Botón "Servicios generales" junto al título; `OT-0043` con fila "Servicio general:" antes de "Procesos:"; `OT-0042` solo procesos; `OT-0041` sin filas |
| C1 | Órdenes · modal | "Servicios generales", vista lista (tarjetas, "Editar"/"Eliminar", "Nuevo servicio", aviso de éxito) |
| C2 | Órdenes · modal | Vista formulario "Editar servicio general" (Nombre, líneas de chequeos, "Agregar chequeo", "Volver"/"Guardar") |

Sin mockup propio (justificado en `mockups/README.md`): bloque del PDF (mismo estilo que "Procesos realizados" del P1 aprobado, ubicado antes de la tabla de componentes), confirmación de borrado (patrón "Borrar orden"), "Nuevo servicio" (= C2 vacío) y estados de error (estilos ya aprobados). Una vez aprobados, S1, L2, C1 y C2 son criterio de aceptación de los grupos 7, 8, 8b y del verify.

## Risks / Trade-offs

- [Migración sobre `dev-local.db` real] → solo crea tablas nuevas en una transacción con verificación de conteos; backup previo `dev-local.bak-5g.db` y verify sobre una **copia**. Rollback: código anterior (ignora las tablas nuevas) o restaurar el backup.
- [Snapshot sin FK] → no se puede reportar "órdenes con el servicio X" si X se renombró; aceptado (no pedido) y reversible sumando una columna.
- [`PATCH` reemplaza toda la lista de chequeos] → para cambiar uno hay que mandar todos; a cambio, una sola operación atómica y simple desde `/docs`. El `GET` devuelve la lista lista para copiar y editar.
- [`OrdenOut` con campo nuevo] → aditivo; se actualizan tests de diccionario exacto (alta, listado, borrado).
- [Una consulta por lote más al listar órdenes] → volumen chico; evita multiplicar filas ítems × procesos × chequeos.
- [Catálogo cargado una vez por página] → un servicio creado/borrado desde `/ordenes` o por API aparece/desaparece en "Nueva orden" al recargar `/inventario`; el 422 cubre el caso borrado.
- [Modal con tres vistas] → más estado en un solo modal; se acota con un único módulo (`servicios-admin.js`) y la validación pura testeada con Node.
- [Unicidad por `casefold` vs `COLLATE NOCASE`] → el service es la regla; la BD (solo ASCII) es la red, como en procesos.

## Migration Plan

1. Antes del primer arranque con este change: copiar `dev-local.db` a `dev-local.bak-5g.db` (el apply lo hace en el grupo 1 sin abrir el original).
2. Arrancar uvicorn: `_crear_servicios_generales` crea las cuatro tablas, siembra "Servicio 20 hs" con sus tres chequeos y loguea "Agregados los servicios generales de órdenes (N orden(es) conservadas, sin servicio).".
3. Arranques siguientes: nada (las tablas existen; no se resiembra aunque se vacíen o modifiquen).
4. Rollback: volver al código anterior (ignora las tablas) o restaurar `dev-local.bak-5g.db`.

## Open Questions

Resueltas por el usuario el **2026-11-27**:

- **Q1 — Administración**: **también desde la web** (no solo API) → D12 (modal "Servicios generales" en `/ordenes`).
- **Q2 — Chequeos por orden**: **sin** tildar ni editar chequeos por orden en este change; queda para C-06i.
- **Q3 — Cero o un servicio por orden**: confirmado.
- **Q4 — Límites** (1-30 chequeos, 1-60 caracteres): se mantienen las recomendaciones.
- **Q5 — Ubicación**: en "Nueva orden" se mantiene la recomendación (entre fecha y Componentes); en el PDF el usuario lo cambió (2026-11-27): bloque "Servicio general" **primero**, tras el encabezado y antes de la tabla de componentes; luego la tabla y "Procesos realizados".

Al archivar: KB 02 (endpoints nuevos, 21 rutas), 04 (cuatro tablas nuevas, snapshot, siembra solo al crear), 05 (RN-OR de servicio general y reglas del catálogo), 06 (US-006/US-007 con servicio, administración del catálogo desde `/ordenes` y por API), 07 (flujos de alta/listado/PDF con servicio y administración del catálogo en la web); `CHANGES.md` C-06g `[x]` y paridad C-07 de D10.

## Decisiones para revisión del usuario

> Governance MEDIO/ALTO. ★ = recomendada. **Revisión del usuario (2026-11-27)**: Q1-Q5 resueltas (ver Open Questions); 3, 4 (límites = 6), 13, 15, 16 y 19 confirmadas o modificadas abajo; el resto sigue como ★. **Pedido por el usuario (2026-11-26)**: catálogo de servicios generales con chequeos incluidos (ej. "Servicio 20 hs" = chequeo de motor, de combustible, eléctrico, etc.); alta/edición/borrado del catálogo y sus chequeos; asignación al crear la orden en la misma transacción que el stock; visible en listado y PDF; borrar la orden borra su servicio; órdenes existentes sin servicio; sin precios.

1. **Modelo** — ★ `servicios_generales` + `servicio_chequeos` (catálogo) y `orden_servicio` + `orden_servicio_chequeos` (snapshot), sin FK al catálogo. Alt.: snapshot + FK `servicio_id`; chequeos como JSON en una columna.
2. **Nombre** — ★ "servicios generales" en tablas y ruta (`/api/servicios-generales`) para no chocar con los "servicios adicionales" de C-06h. Alt.: `servicios` / `/api/servicios`.
3. **Cero o un servicio por orden** — ★ opcional y uno solo (PK `orden_id`). _Confirmada por el usuario (2026-11-27)._
4. **Renombrar/cambiar chequeos/borrar del catálogo y órdenes pasadas** — ★ no las afecta; borrar permitido aunque haya órdenes que lo usen.
5. **Clave del catálogo** — ★ clave estable derivada del nombre, mismas reglas que procesos.
6. **Chequeos** — ★ 1 a 30 por servicio, 1-60 caracteres, sin repetir (sin distinguir mayúsculas), en el orden dado. _Confirmada por el usuario (2026-11-27)._
7. **Modificar chequeos** — ★ `PATCH` con `nombre` y/o `chequeos` (reemplazo completo, atómico). Alt.: sub-recursos por chequeo.
8. **Siembra** — ★ "Servicio 20 hs" con "Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico", solo al crear el catálogo.
9. **Migración** — ★ solo tablas nuevas en una transacción; órdenes existentes sin servicio; backup `dev-local.bak-5g.db`.
10. **Atomicidad** — ★ orden + ítems + stock + procesos + servicio + chequeos en una transacción; borrado igual.
11. **API del alta** — ★ campo `servicio` (clave o `null`; vacío = sin servicio).
12. **Prioridad del error** — ★ dentro de "datos inválidos": número → fecha → componentes → servicio → procesos → personalizados.
13. **Chequeos por orden** — ★ se copian todos; sin tildar ni editar por orden. _Confirmada por el usuario (2026-11-27); tildar queda para C-06i._
14. **Respuestas** — ★ `servicio: null | {nombre, chequeos: [texto]}` en alta, listado y borrado; endpoints `GET`/`POST /api/servicios-generales`, `PATCH`/`DELETE /api/servicios-generales/{clave}` (DELETE devuelve lo borrado); 21 rutas.
15. **Administración** — API **y web**: modal "Servicios generales" en `/ordenes` con lista, formulario (nombre + líneas de chequeos) y confirmación de borrado (D12). _Modificada por el usuario (2026-11-27)._
16. **Ubicación en "Nueva orden"** — ★ bloque entre la fecha y Componentes. _Confirmada por el usuario (2026-11-27)._
17. **Control** — ★ `select` con "Sin servicio general" + catálogo y lista "Incluye:" de solo lectura con los chequeos.
18. **`/ordenes`** — ★ fila "Servicio general:" (nombre + chips de chequeos) antes de "Procesos:"; sin fila si no hay.
19. **PDF** — encabezado sin cambios; bloque "Servicio general" **primero** (tras el encabezado, antes de la tabla de componentes), luego la tabla y "Procesos realizados"; omitido si no hay. _Modificada por el usuario (2026-11-27)._
20. **Reportes y filtros** — ★ sin servicio en `/reportes` ni filtro por servicio en `/ordenes`.
21. **Paridad C-07** — ★ mismas tablas e índices en Postgres; `crear_orden` con `p_servicio`; alta/modificación de servicio por RPC transaccional.
