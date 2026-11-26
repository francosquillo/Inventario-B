# Design — paso-5f-procesos-ordenes (C-06f)

## Context

Ver `proposal.md` (Why). Estado observado (C-01..C-06e archivados):

- **Esquema** (`inventario/repositories/sqlite_repo.py`, `_ESQUEMA_PLANTILLA`): `categorias(id, clave UNIQUE CHECK formato, nombre UNIQUE COLLATE NOCASE 1-40)`, `productos(..., categoria_id REFERENCES categorias(id))` (sin `ON DELETE`: la FK bloquea borrar una categoría usada), `ordenes(id, numero UNIQUE, fecha, usuario_id, created_at)`, `orden_items(orden_id REFERENCES ordenes ON DELETE CASCADE, producto_id, cantidad, PK(orden_id, producto_id))`. `PRAGMA foreign_keys = ON` en `conectar`.
- **Arranque**: `inicializar_esquema` = `executescript(ESQUEMA_SQL)` (todo `IF NOT EXISTS`) → `_migrar_movimientos` → `_migrar_productos_categoria` (que llama a `_sembrar_categorias`: siembra **si el catálogo está vacío**) → `NORMALIZAR_FECHAS_SQL` → `commit`. Las migraciones usan `_transaccion` (`BEGIN IMMEDIATE`, rollback y re-raise).
- **Órdenes**: `SqliteOrdenRepository.crear` valida duplicado/productos/stock e inserta orden + ítems + descuentos dentro de `_transaccion`; `_SQL_LISTAR_ORDENES` (JOIN con ítems) + `_a_ordenes` (agrupa por id) alimentan `listar`, `_leer_orden` y `_buscar_orden_por_numero`; `borrar` reintegra, borra ítems y orden en una transacción. `Orden(id, numero, fecha, usuario, items)`. `OrdenService.crear(numero, fecha, componentes, usuario_id)` valida y consolida.
- **Categorías (C-06e)**: `CategoriaService` (listar/crear/renombrar), normalización pura en `services/normalizacion.py` (`clave_desde_texto`, `validar_clave_categoria`, `normalizar_nombre_categoria`), router `api/routers/categorias.py`, errores `CategoriaDuplicada` 409 / `CategoriaNoEncontrada` 404 registrados en `api/app.py`. OpenAPI: 17 rutas.
- **Web**: "Nueva orden" en `static/index.html` (`#modal-orden`, `fieldset` Componentes, líneas creadas en `inventario.js`); `/ordenes` arma cada `<article class="ord">` en `ordenes.js` (`articulo(o)`), "Exportar PDF" marca el artículo con `data-exportar` y llama a `Exportar.imprimir({titulo, linea, base, modo: "orden"})`; la hoja impresa muestra el artículo tal cual (salvo botones).
- **Datos reales**: `dev-local.db` (`*.db` en `.gitignore`).

## Goals / Non-Goals

**Goals:**
- Procesos por orden (catálogo + personalizados) que sobreviven a renombres y borrados del catálogo.
- Alta y borrado de orden siguen siendo una sola transacción, ahora con procesos (regla dura 3).
- Migración aditiva: solo tablas nuevas, cero cambios en filas existentes.
- Borrado de categorías seguro (nunca deja productos apuntando a nada ni cambia su categoría en silencio).
- Siembras que no resucitan lo que el usuario borró.

**Non-Goals:**
- Pantalla web para administrar procesos o categorías (solo API, decisión del usuario).
- Editar los procesos de una orden ya creada (las órdenes no se editan, RN-OR-10).
- Procesos en `/reportes`, filtro por proceso en `/ordenes`, cantidades/precios/horas por proceso.
- Promover un personalizado al catálogo automáticamente.

## Decisions

### D1 — Modelo: catálogo `procesos` + `orden_procesos` con snapshot del nombre (decisiones 1, 2, 3)

```sql
CREATE TABLE procesos (
    id INTEGER PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE CHECK (<mismo formato que categorias.clave>),
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(trim(nombre)) BETWEEN 1 AND 60)
);
CREATE TABLE orden_procesos (
    orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE,
    posicion INTEGER NOT NULL CHECK (typeof(posicion) = 'integer' AND posicion >= 1),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60),
    personalizado INTEGER NOT NULL CHECK (personalizado IN (0, 1)),
    PRIMARY KEY (orden_id, posicion),
    UNIQUE (orden_id, nombre COLLATE NOCASE)
);
```

- ★ **Snapshot sin FK al catálogo**: cada proceso de una orden guarda el nombre tal como era al crearla y si fue personalizado. Renombrar o borrar un proceso del catálogo no toca órdenes pasadas (una orden es un registro histórico del trabajo hecho) y el borrado del catálogo no necesita 409. Alternativa: `proceso_id` FK + snapshot (permite reportes por proceso a futuro y "seguir" renombres, pero suma `ON DELETE SET NULL`, otra columna que migrar en C-07 y una semántica dudosa: ¿se muestra el nombre viejo o el nuevo?). Alternativa descartada: solo FK (un renombre reescribe la historia y el borrado exige 409 o cascada).
- ★ **Clave + nombre en el catálogo** (igual que categorías): la clave es el identificador de la API (`POST /api/ordenes` manda claves; `PATCH/DELETE /api/procesos/{clave}`), el nombre es para mostrar. Reutiliza `clave_desde_texto`/formato de clave.
- `posicion` conserva el orden de carga (D3) y es la PK junto a `orden_id`; `UNIQUE (orden_id, nombre COLLATE NOCASE)` es la red de la regla "sin nombres repetidos en una orden" (el service compara con `casefold()`, que además cubre tildes/Ñ).
- `ON DELETE CASCADE` como red; el borrado igual borra explícitamente (D5), como con `orden_items`.
- Sin índice extra: `orden_procesos` se lee siempre por `orden_id` (prefijo de la PK).

### D2 — Siembra solo al crear el catálogo (decisión 13; refina C-06e D1)

Hoy `_sembrar_categorias` siembra si `categorias` está vacía: con el borrado nuevo, borrar las tres y reiniciar las resucitaría. ★ **Sembrar solo cuando la tabla se crea en ese arranque**:

- `inicializar_esquema` consulta `sqlite_master` **antes** de `executescript` para saber si `categorias` existía; `_migrar_productos_categoria` siembra solo si no existía (la condición "vacía" desaparece). Bases de C-06e: la tabla existe → nunca se resiembra (hoy ya tienen filas, sin cambio visible).
- `procesos` y `orden_procesos` **no** van en `ESQUEMA_SQL`: los crea `_crear_procesos(conn)` (D4) dentro de una `_transaccion` junto con la siembra, solo si `procesos` no existe. Así "crear + sembrar" es atómico y la condición "recién creada" es exacta.
- Alternativa: tabla/flag de "siembras hechas" (`PRAGMA user_version` o tabla `meta`): más mecanismo para lo mismo. Alternativa: aceptar la resiembra (sorprende al usuario que borró a propósito).

### D3 — Reglas de los procesos de una orden (decisiones 4-9)

Validación en `OrdenService.crear(numero, fecha, componentes, usuario_id, procesos=None, procesos_personalizados=None)`, dentro de la fase "datos inválidos" (antes de duplicado/productos/stock, prioridad de RN-OR sin cambios), en este orden: número → fecha → componentes → `procesos` → `procesos_personalizados`.

- ★ **Opcionales y múltiples**: cero o más procesos (las órdenes existentes no tienen; no todo trabajo encaja en el catálogo). Componentes siguen obligatorios (no se crean órdenes "solo procesos"; Non-Goal).
- `procesos`: `None` → `[]`; si no es lista o algún elemento no es `str` → "El campo procesos debe ser una lista de textos."; cada clave `strip().lower()`; ★ **repetidas se consolidan** (se conserva la primera aparición, coherente con RN-OR-11); clave inexistente → "El proceso 'x' no existe." (clave normalizada; recortada a 30 + "…" si es más larga, como categorías). El service resuelve clave → nombre con `ProcesoRepository.listar()` y pasa al repo **nombres** ya resueltos.
- `procesos_personalizados`: `None` → `[]`; tipo inválido → "El campo procesos_personalizados debe ser una lista de textos."; ★ **hasta 10** ("La orden admite hasta 10 procesos personalizados."); cada uno recortado, ★ **1 a 60 caracteres** (mismo tope que el nombre del catálogo) → "Proceso personalizado N: El nombre es obligatorio." / "…admite hasta 60 caracteres."; espacios internos se conservan.
- ★ **Sin duplicar el catálogo**: un personalizado igual (casefold) a **cualquier** proceso del catálogo → "Proceso personalizado N: 'x' ya está en la lista de procesos; marcalo ahí." (evita dos "Limpieza" distintas en reportes futuros y empuja a usar el catálogo). Alternativas: convertirlo en silencio al proceso del catálogo, o permitirlo.
- ★ **Personalizados repetidos** (casefold) → "Proceso personalizado N: 'x' está repetido." (N = el segundo). Alternativa: consolidar en silencio.
- **Orden de carga**: catálogo en el orden recibido, luego personalizados en el orden recibido (`posicion` 1..n). La web manda los del catálogo en el orden de las líneas.
- Carrera: un proceso borrado entre la validación y el `INSERT` no rompe nada (snapshot, sin FK); la orden queda con el nombre que se validó. Aceptado.

### D4 — Migración aditiva (decisión 12)

`_crear_procesos(conn)` en `sqlite_repo.py`, llamada en `inicializar_esquema` **después de `_migrar_productos_categoria` y antes de `NORMALIZAR_FECHAS_SQL`** (ese `UPDATE` abre una transacción implícita y `_transaccion` exige conexión libre):

1. Si `procesos` existe en `sqlite_master` → salir (idempotente; `orden_procesos` se crea con `IF NOT EXISTS` en el mismo bloque por las dudas).
2. En `_transaccion`: contar `ordenes`, `orden_items`, `productos`, `categorias`, `movimientos`; `CREATE TABLE procesos`, `CREATE TABLE orden_procesos`; sembrar `cambio-motor`/`cambio-filtro`/`limpieza`; verificar conteos iguales; ante error → rollback (el DDL de SQLite es transaccional: no quedan tablas) y la excepción sube.
3. `log.info("Agregados los procesos de órdenes (%d orden(es) conservadas, sin procesos).", n)`.

No hay `ALTER` ni reconstrucción: ninguna tabla existente cambia. Prueba de falla: siembra que viola el CHECK inyectada en el test → no existen las tablas nuevas.

### D5 — Repositorios y entidades (decisiones 1, 10)

- `domain/entities.py`: `Proceso(clave, nombre)`; `ProcesoOrden(nombre, personalizado)`; `Orden.procesos: "tuple[ProcesoOrden, ...]" = ()` (default para no romper constructores).
- `repositories/base.py`: `ProcesoRepository` (`listar`, `obtener`, `crear`, `renombrar`, `borrar`); `CategoriaRepository.borrar(clave)`; `OrdenRepository.crear(..., procesos=())` recibe `ProcesoOrden` ya validados.
- `SqliteOrdenRepository._crear_en_transaccion`: tras ítems y descuentos, `INSERT INTO orden_procesos (orden_id, posicion, nombre, personalizado)` por cada proceso, dentro de la misma `_transaccion` (★ todo o nada; un `IntegrityError` del UNIQUE se propaga como error inesperado porque el service ya lo validó).
- Lectura: ★ consulta separada por lote, no un JOIN más (multiplicaría filas ítems × procesos): `_leer_procesos(ids)` → `SELECT orden_id, nombre, personalizado FROM orden_procesos WHERE orden_id IN (…) ORDER BY orden_id, posicion`, y `_a_ordenes` recibe el mapa. `listar`, `_leer_orden` y `_buscar_orden_por_numero` lo usan. Placeholders `?` siempre.
- `borrar`: `DELETE FROM orden_procesos WHERE orden_id = ?` + ítems + orden en la misma `_transaccion`; la orden devuelta (leída antes) trae sus procesos.
- `SqliteProcesoRepository` calcado de `SqliteCategoriaRepository` (`IntegrityError` → `ProcesoDuplicado` distinguiendo clave/nombre); `borrar(clave)` en `_transaccion`: lee, si no existe `ProcesoNoEncontrado`, `DELETE`, devuelve el `Proceso` borrado.

### D6 — Borrado de categorías (decisiones 14, 15)

- ★ **409 si algún producto (activo o dado de baja) la usa**: "La categoría 'x' está asignada a N producto(s)." Seguro y reversible: nada cambia en silencio; el usuario reasigna con "Modificar stock" (permite cambiar la categoría de activos y dados de baja) y vuelve a borrar. Alternativa: pasar esos productos a "Sin categoría" (`NULL`) y borrar (más cómodo pero destructivo y silencioso; en C-07 sería otra RPC multi-tabla). Revierte la sub-decisión 2.6 de C-06e por pedido del usuario (2026-11-24).
- `SqliteCategoriaRepository.borrar(clave)` en `_transaccion` (`BEGIN IMMEDIATE`): obtener (404 si no) → `SELECT COUNT(*) FROM productos WHERE categoria_id = ?` → si > 0 `CategoriaEnUso(clave, n)` → `DELETE`. La FK sin `ON DELETE` es la red (un `IntegrityError` FK se traduce a `CategoriaEnUso` recontando).
- `CategoriaService.borrar(clave)`: normaliza (recorte + minúsculas; vacía → 422 de formato) y delega. Error nuevo `CategoriaEnUso` → 409 en `api/app.py`.
- La web toma el catálogo al abrir cada página; un producto cuya categoría ya no existe no puede darse (409), así que no hay claves huérfanas.

### D7 — API (decisiones 10, 11, 16)

- `OrdenRequest` gana `procesos: Optional[Any] = None` y `procesos_personalizados: Optional[Any] = None` (tipos laxos: el service da los mensajes en español, como `categoria` en C-06e). Ausentes = `[]`.
- `OrdenOut` gana `procesos: List[ProcesoOrdenOut(nombre, personalizado)]`; aparece en alta, listado y `orden` del borrado (una sola forma de orden ★). Tests de diccionario exacto se actualizan (aditivo para clientes).
- ★ Forma `{nombre, personalizado}` sin `clave`: con snapshot la clave no identifica nada estable (el proceso pudo borrarse o renombrarse). Alternativa: guardar también la clave snapshot (útil para un filtro futuro; YAGNI).
- Router nuevo `api/routers/procesos.py` (`prefix="/api/procesos"`, `tags=["procesos"]`, `dependencies=[Depends(get_current_user)]`): `GET ""`, `POST ""` (`ProcesoAltaRequest {nombre, clave?}` → 201), `PATCH "/{clave}"` (`ProcesoRenombreRequest {nombre}`; `clave` en el cuerpo → 422 "La clave de un proceso no se puede cambiar."), `DELETE "/{clave}"` → 200 `ProcesoOut`. ★ El DELETE devuelve lo borrado (como `DELETE /api/productos/{codigo}`), no 204.
- `api/routers/categorias.py` suma `DELETE "/{clave}"` → 200 `CategoriaOut`; responses 404/409.
- Errores nuevos: `ProcesoDuplicado(campo, valor)` 409 ("Ya existe un proceso con clave 'x'." / "…con nombre 'X'."), `ProcesoNoEncontrado(clave)` 404 ("No existe un proceso con clave 'x'."), `CategoriaEnUso(clave, n)` 409.
- `ProcesoService(proceso_repo)`: listar/crear/renombrar/borrar; normalización con `normalizar_nombre_proceso` (1-60, "El nombre del proceso admite hasta 60 caracteres.") y la validación de clave con mensaje propio ("La clave del proceso admite solo…"). ★ Se generaliza la normalización de C-06e con un parámetro de mensaje/tope en lugar de copiarla.
- ★ Cualquier usuario con sesión administra (hoy solo `admin`, sin roles). Mismas defensas: sesión (401), cuerpo solo JSON (422 con `text/plain`/formularios), sin CORS.
- OpenAPI: **19** rutas (+`/api/procesos`, +`/api/procesos/{clave}`; `/api/categorias/{clave}` suma `DELETE` sin ruta nueva).

### D8 — "Nueva orden": líneas de procesos (decisiones 17-20, revisadas por el usuario 2026-11-24)

- Bloque **"Procesos"** debajo de **Componentes**; los procesos se agregan **línea por línea** como los componentes. Cada línea tiene un `select` con los procesos del catálogo (por nombre) más la opción **"Personalizado"**, y un botón "Quitar"; el botón **"Agregar proceso"** suma líneas. Una orden puede quedar con cero líneas de proceso (a diferencia de los componentes).
- Elegir "Personalizado" abre en esa línea una caja de texto ("Proceso personalizado", `maxlength=60`); volver a un proceso del catálogo la oculta y **su texto no se envía** (se conserva mientras la línea exista, por si se vuelve a elegir). Hasta **10 personalizados** por orden: al llegar, "Personalizado" queda deshabilitado en las demás líneas con la ayuda "Una orden admite hasta 10 procesos personalizados.".
- **Regla de repetidos (simple y consistente con el service y los componentes)**: el mismo proceso del catálogo en dos líneas **se cuenta una vez** (se consolida en silencio, sin error); un personalizado igual a un nombre del catálogo o repetido entre personalizados (sin distinguir mayúsculas) es **error** marcado en su línea.
- Catálogo: `GET /api/procesos` al abrir la página (junto con categorías). Si falla: "No se pudo cargar la lista de procesos." bajo el bloque; los selects ofrecen solo "Personalizado".
- Validación en el navegador (regla dura 3, mismas reglas que D3) en un módulo puro nuevo `static/js/procesos.js` (`Procesos.armar(lineas, catalogo)` con `lineas = [{valor: clave | "personalizado", texto}]` → `{procesos, procesos_personalizados, errores[]}`, con `errores[i]` por línea), testeable con Node como `busqueda.js`. `procesos` sale en el orden de las líneas, sin repetir. Errores junto a la caja de texto con `aria-invalid` + `aria-describedby`.
- Errores de la API: 422 "Proceso personalizado N: …" → marca la N-ésima línea personalizada; "El proceso 'x' no existe." → mensaje bajo el bloque y recarga del catálogo (las líneas con procesos que ya no existen quedan sin selección). El modal queda abierto con todo cargado.
- Siempre se envían ambos campos (`[]` si no hay).

### D9 — `/ordenes` y PDF de una orden (decisiones 21-24)

- ★ **Fila de chips** bajo la cabecera de cada orden: etiqueta "Procesos:" + un `<ul>` con un `<li class="chip">` por proceso (texto con `textContent`), envolviendo en móvil. Alternativa: línea de texto separada por " · " (más simple, menos escaneable).
- ★ **Sin distinguir personalizados** visualmente (lo que importa es qué se hizo; la API conserva el dato). Alternativa: sufijo atenuado "(personalizado)".
- ★ **Órdenes sin procesos no muestran la fila** (las viejas quedan como hoy). Alternativa: "Sin procesos registrados" atenuado.
- El modal de borrado no cambia (el texto ya resume la orden).
- PDF: el encabezado de C-06c **no cambia** ("Orden OT-XXXX" / "Fecha: … · N componentes"). ★ El mismo bloque del artículo se imprime como sección **"Procesos realizados"** (título chico + lista, uno por línea, chips sin fondo en papel) **debajo de la tabla de componentes** (decisión 24 revisada por el usuario, 2026-11-24); omitido sin procesos. En pantalla la etiqueta dice "Procesos:"; en impresión "Procesos realizados" (dos `span` con `hidden` por medio, o CSS `@media print`). Alternativa: sumar "· N procesos" a la línea del encabezado (rompe la revisión "mínimo" del usuario).
- ★ Sin procesos en `/reportes` ni filtro por proceso en `/ordenes` (no pedido; se puede sumar después).

### D10 — Paridad Supabase (C-07) (decisión 25)

`procesos` igual que `categorias` (clave única con CHECK regex, `create unique index on procesos (lower(nombre))`, nombre 1-60), siembra en el script de esquema (una sola vez); `orden_procesos(orden_id bigint references ordenes(id) on delete cascade, posicion int, nombre text check (length(btrim(nombre)) between 1 and 60), personalizado boolean, primary key (orden_id, posicion))` + `create unique index on orden_procesos (orden_id, lower(nombre))`. La RPC `crear_orden` gana `p_procesos jsonb` (`[{nombre, personalizado}]`, ya validados por el service) y los inserta en la misma transacción; la RPC de borrado borra procesos (o confía en la cascada). CRUD de procesos y borrado de categorías como operaciones directas de una fila (23505 → 409; 23503 al borrar una categoría usada → `CategoriaEnUso` 409 tras recontar). RLS como `ordenes`. Anotar en `CHANGES.md` § C-07 al archivar.

### D11 — Tests (Strict TDD, `unittest`, SQLite real)

- Migración: `tests/test_sqlite_migracion_procesos.py` con el DDL de C-06e **copiado literal** (seis tablas), archivo temporal y `:memory:`: tablas nuevas + siembra, filas existentes intactas, órdenes con `procesos == ()`, idempotencia (3 arranques), catálogo vaciado no se resiembra, falla inyectada → sin tablas nuevas.
- Siembra de categorías: base nueva siembra; categorías borradas todas → reinicio sin resiembra (cambia el test de C-06e que asumía "vacía → siembra" si existe).
- Repositorios, services, API, JS puro (`procesos.js`) con Node, guardas estáticas (`index.html`, `ordenes.js`), navegador en el verify.

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-24)
- Mockups: openspec/changes/paso-5f-procesos-ordenes/mockups/ (`nueva-orden.html`, `ordenes.html`, `README.md`)
- Approval: approved (2026-11-24, by user)
- Preview: rendered (2026-11-24, 390x844 y 1440x900 vía http local; P1 con print emulado; mockups/previews/)
- Visual verify: passed (2026-11-26) — N1, N2, L1 y P1 comprobados a 390x844 y 1440x900 contra la app real; capturas en `mockups/verify/`. No cubierto en navegador: 422 por proceso borrado con el modal abierto.

Base: mockups aprobados de C-06e (modal "Nueva orden" con filtro por categoría por línea) y C-06c (`/ordenes` con "Exportar PDF" por orden y hoja impresa), tokens `design-system/tokens.css` + `ui.css`, tema oscuro único, cabecera de texto "Inventario". Estados previstos:

| ID | Pantalla | Estado |
|----|----------|--------|
| N1 | Nueva orden | Bloque "Procesos" bajo Componentes: una línea con un proceso del catálogo y una línea "Personalizado" con su caja de texto, más "Agregar proceso" (LITE) |
| N2 | Nueva orden | Errores en el navegador: caja personalizada vacía ("El nombre es obligatorio.") y otra igual al catálogo ("'limpieza' ya está en la lista de procesos; marcalo ahí.") (LITE) |
| L1 | Órdenes | Lista con `OT-0042` con fila "Procesos:" (chips) y `OT-0041` sin procesos (sin fila) (LITE) |
| P1 | Impresión | `OT-0042`: encabezado "Orden OT-0042" / "Fecha: … · 2 componentes", tabla de componentes y debajo el bloque "Procesos realizados" (uno por línea); sin bloque si no hay procesos (LITE) |

Mockups LITE (acordado con el orquestador): solo N1, N2, L1 y P1; el tope de 10, el catálogo caído y el 422 se verifican en el verify real.

Pantallas a 390x844 y 1440x900; P1 con `print` emulado (sin PDF A4) en `mockups/previews/`. Una vez aprobados, son criterio de aceptación de los grupos de frontend de `tasks.md` y del verify.

## Risks / Trade-offs

- [Migración sobre `dev-local.db` real] → solo crea tablas nuevas en una transacción con verificación de conteos; backup previo `dev-local.bak-5f.db` en la raíz (ignorado por `*.db`) y verify sobre una **copia**. Rollback: código anterior (ignora las tablas nuevas) o restaurar el backup.
- [Cambio de la regla de siembra de categorías] → solo afecta bases donde `categorias` aún no existe (nuevas o pre-C-06e); test explícito de ambas ramas.
- [Snapshot sin FK] → no se puede reportar "órdenes con el proceso X" si X se renombró; aceptado (no pedido) y reversible sumando una columna en el futuro.
- [`OrdenOut` con campo nuevo] → aditivo; se actualizan tests de diccionario exacto (alta, listado, borrado).
- [Consulta extra por lote para procesos] → una consulta más por listado (volumen chico); evita el producto cartesiano ítems × procesos.
- [409 al borrar categoría usada] → fricción (hay que reasignar productos primero); mensaje con la cantidad para que el usuario sepa cuánto falta. Alternativa "Sin categoría" lista si el usuario la prefiere.
- [Catálogo de procesos cargado una vez por página] → un proceso creado/borrado por API aparece/desaparece al recargar; el 422 cubre el caso borrado (N6).
- [Unicidad por `casefold` vs `COLLATE NOCASE`] → el service es la regla; la BD (solo ASCII) es la red. "Limpieza" vs "Límpieza" serían distintos; aceptado.

## Migration Plan

1. Antes del primer arranque con este change: copiar `dev-local.db` a `dev-local.bak-5f.db` (README; lo hace el usuario o el apply en el grupo 1 sin abrir el original).
2. Arrancar uvicorn: `_crear_procesos` crea `procesos` (con los 3 de ejemplo) y `orden_procesos`; log "Agregados los procesos de órdenes (N orden(es) conservadas, sin procesos).".
3. Arranques siguientes: nada (las tablas existen; no se resiembra aunque se vacíen).
4. Rollback: volver al código anterior (ignora las tablas) o restaurar `dev-local.bak-5f.db`.

## Open Questions

- Ninguna bloqueante: todas las decisiones de abajo tienen recomendación ★ y esperan la revisión del usuario una por una; si alguna cambia, se ajustan specs, design, mockups y tasks antes del apply.
- Al archivar: KB 02 (endpoints nuevos, 19 rutas), 04 (tablas `procesos`/`orden_procesos`, siembra solo al crear), 05 (RN-OR de procesos, RN-PR de borrado de categoría), 06 (US-006/US-007 con procesos, administración por API), 07 (flujos de alta/listado/PDF con procesos, borrado de categoría y de proceso en `/docs`); `CHANGES.md` C-06f `[x]` y paridad C-07 de D10.

## Decisiones para revisión del usuario

> Governance ALTO. **Revisadas por el usuario (2026-11-24)**: 1-16, 21, 22, 23, 25 y 26 aprobadas como recomendadas (★); 17, 18, 19, 20 y 24 modificadas/adaptadas por el usuario (abajo). ★ = recomendada. **Decidido por el usuario (2026-11-24)**: catálogo con Cambio motor / Cambio filtro / Limpieza; "Personalizado" con texto libre solo en esa orden (no entra al catálogo ni se ofrece en otras); administración de procesos solo por API con crear, renombrar y **borrar**; **borrar categorías** por API (revierte C-06e 2.6); alta atómica con stock + procesos; borrar orden borra sus procesos; procesos en `/ordenes` y en el PDF de la orden; órdenes existentes sin procesos; nota de paridad C-07.

1. **Modelo** — ★ tabla `procesos` (clave + nombre) + `orden_procesos` con snapshot del nombre y marca de personalizado, sin FK al catálogo. Alt.: snapshot + FK `proceso_id`; solo FK. _Aprobada por el usuario (2026-11-24)._
2. **Clave en el catálogo** — ★ sí, clave estable derivada del nombre (como categorías). Alt.: solo nombre. _Aprobada por el usuario (2026-11-24)._
3. **Renombrar/borrar del catálogo y órdenes pasadas** — ★ no las afecta (conservan el nombre de cuando se creó la orden); borrar está permitido aunque haya órdenes que lo usen. _Aprobada por el usuario (2026-11-24)._
4. **Procesos opcionales** — ★ una orden puede tener cero procesos. _Aprobada por el usuario (2026-11-24)._
5. **Varios por orden** — ★ sí, sin límite para los del catálogo. _Aprobada por el usuario (2026-11-24)._
6. **Proceso del catálogo repetido en la misma orden** — ★ se cuenta una vez (como los componentes repetidos). Alt.: 422. _Aprobada por el usuario (2026-11-24)._
7. **Cantidad de personalizados** — ★ hasta 10 por orden. _Aprobada por el usuario (2026-11-24)._
8. **Largo y espacios** — ★ 1 a 60 caracteres tras recortar; vacío → error. Mismo tope para el nombre del catálogo. _Aprobada por el usuario (2026-11-24)._
9. **Personalizado con el nombre de uno del catálogo / repetidos** — ★ ambos se rechazan con mensaje por posición ("…ya está en la lista de procesos; marcalo ahí." / "…está repetido."). Alt.: convertir/consolidar en silencio. _Aprobada por el usuario (2026-11-24)._
10. **API del alta** — ★ dos campos opcionales: `procesos` (claves) y `procesos_personalizados` (textos). Alt.: una sola lista de objetos `{clave}|{nombre}`. _Aprobada por el usuario (2026-11-24)._
11. **Respuesta de órdenes** — ★ `procesos: [{nombre, personalizado}]` en el orden de carga (catálogo primero, luego personalizados), en alta, listado y borrado. _Aprobada por el usuario (2026-11-24)._
12. **Migración** — ★ solo tablas nuevas en una transacción, siembra de los 3 procesos; órdenes existentes sin procesos; backup `dev-local.bak-5f.db`. _Aprobada por el usuario (2026-11-24)._
13. **Siembra** — ★ solo cuando se crea cada catálogo (categorías y procesos), para que borrar todo y reiniciar no los resucite. Alt.: flag de "sembrado"; aceptar la resiembra. _Aprobada por el usuario (2026-11-24)._
14. **Borrar categoría usada por productos** — ★ 409 "La categoría 'x' está asignada a N producto(s)." (cuenta activos y dados de baja). Alt.: pasar esos productos a "Sin categoría" y borrar. _Aprobada por el usuario (2026-11-24)._
15. **Respuesta de los DELETE de catálogo** — ★ 200 con `{clave, nombre}` borrado; 404 si no existe. Alt.: 204 sin cuerpo. _Aprobada por el usuario (2026-11-24)._
16. **Endpoints de procesos** — ★ `GET`/`POST /api/procesos`, `PATCH`/`DELETE /api/procesos/{clave}`; clave inmutable (422), nombre único sin mayúsculas (409); 19 rutas en OpenAPI. _Aprobada por el usuario (2026-11-24)._
17. **Ubicación en "Nueva orden"** — bloque "Procesos" **debajo de Componentes**. _Modificada por el usuario (2026-11-24)._
18. **Control** — líneas con `select` (procesos del catálogo + "Personalizado") y "Quitar", agregadas con "Agregar proceso", como los componentes; cero líneas permitido. _Modificada por el usuario (2026-11-24)._
19. **Personalizado** — elegirlo abre una caja de texto en la línea (1-60 caracteres, hasta 10 por orden); misma validación (vacío, igual al catálogo o repetido → error en la línea). Un mismo proceso del catálogo en dos líneas se cuenta una vez (consolidado en silencio, igual que el service). _Modificada por el usuario (2026-11-24)._
20. **Cambiar una línea de "Personalizado" a un proceso del catálogo** — oculta la caja y su texto no se envía. _Adaptada y aprobada por el usuario (2026-11-24)._
21. **Mostrar en `/ordenes`** — ★ fila "Procesos:" con chips bajo la cabecera de la orden. Alt.: texto separado por " · ". _Aprobada por el usuario (2026-11-24)._
22. **Distinguir personalizados** — ★ no, en pantalla ni en PDF (la API conserva el dato). Alt.: sufijo "(personalizado)". _Aprobada por el usuario (2026-11-24)._
23. **Órdenes sin procesos** — ★ no muestran la fila. Alt.: "Sin procesos registrados". _Aprobada por el usuario (2026-11-24)._
24. **PDF de una orden** — encabezado sin cambios + bloque "Procesos realizados" (uno por línea) **debajo de la tabla de componentes**; omitido sin procesos. _Modificada por el usuario (2026-11-24)._
25. **Reportes y filtros** — ★ sin procesos en `/reportes` ni filtro por proceso en `/ordenes` por ahora. _Aprobada por el usuario (2026-11-24)._
26. **Paridad C-07** — ★ mismas tablas e índices en Postgres; RPC `crear_orden` con `p_procesos`; CRUD de procesos y borrado de categoría como operaciones directas (23505/23503 → 409). _Aprobada por el usuario (2026-11-24)._
