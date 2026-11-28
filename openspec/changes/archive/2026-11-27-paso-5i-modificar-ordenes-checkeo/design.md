# Design — paso-5i-modificar-ordenes-checkeo (C-06i)

## Context

Ver `proposal.md` (Why). Estado observado (C-01..C-06h2 archivados):

- **Esquema** (`inventario/repositories/sqlite_repo.py`): `ordenes` (+ datos del cliente de C-06h), `orden_items (orden_id, producto_id, cantidad, precio_centavos, PK (orden_id, producto_id))`, `orden_procesos (orden_id, posicion, nombre, personalizado, precio_centavos)`, `orden_servicio (orden_id PK, nombre, precio_centavos)` + `orden_servicio_chequeos`. Migraciones aditivas, idempotentes, en `_transaccion` (`BEGIN IMMEDIATE`) con verificación de conteos (`_crear_procesos`, `_crear_servicios_generales`, `_migrar_datos_precios_orden`), llamadas desde `inicializar_esquema` antes de `NORMALIZAR_FECHAS_SQL`.
- **Alta** `SqliteOrdenRepository.crear`: una `_transaccion`; productos **activos** por código (`ProductosNoEncontrados` si falta alguno), `Faltante(codigo, disponible, solicitado)` → `StockInsuficienteOrden` con todos; `_SQL_RESTAR` con guarda `stock >= ?` y `rowcount`. **No escribe movimientos** (RN-ST-06).
- **Borrado** `borrar(numero, reintegrar)`: una `_transaccion`; `_reintegrar` suma la cantidad y **reactiva** (`_SQL_SUMAR_Y_ACTIVAR`, RN-OR-12); devuelve `Reintegro`s; sin movimientos (DD-09).
- **Service** `OrdenService.crear`: número → fecha → datos → `_consolidar` (componentes, suma repetidos e importes) → `_resolver_servicio` (snapshot del catálogo) → procesos → personalizados; todo `DatosInvalidos` (422) antes de tocar el repo.
- **API**: `POST/GET /api/ordenes`, `DELETE /api/ordenes/{numero:path}`; `OrdenRequest` laxo (`Optional[Any]`); `orden_out`. 21 rutas en OpenAPI.
- **Web**: el formulario "Nueva orden" vive en `static/index.html` (`#modal-orden`) y su lógica en `static/js/inventario.js` (1415 líneas: líneas de componentes `.line`, procesos `.pline`, servicio, datos, importes, resumen en vivo con `Precios.resumen`, mapeo de 409/404 a líneas). `/ordenes` (`ordenes.js`) solo lista, exporta e invoca el borrado. El navegador **no** valida stock: la etiqueta del producto muestra "(stock N)" y el 409 se pinta bajo la línea ("Disponible X, solicitado Y").
- KB RN-OR-10: "Las órdenes no se editan en v1" → este change lo reemplaza.

## Goals / Non-Goals

**Goals:**
- Editar el contenido completo de una orden con las mismas reglas del alta, ajustando stock por diferencia en **una** transacción (regla dura 3), sin carreras.
- Chequeo final fijo con precio opcional, sumado a los totales.
- Reutilizar la validación del alta (backend) y el formulario de "Nueva orden" (frontend), sin duplicar lógica.
- Migración aditiva e idempotente; API compatible hacia atrás.

**Non-Goals:**
- Renumerar órdenes; historial/auditoría de ediciones; bloqueo optimista entre usuarios (ver Q6, Q7).
- Catálogo editable de ítems de chequeo; formato de impresión nuevo (C-06j).
- Movimientos de stock por ediciones (ver D3).

## Decisions

### D1 — API: `PUT /api/ordenes/{numero:path}` con reemplazo completo (decisiones 1, 2)

- ★ **PUT** sobre la ruta existente (OpenAPI sigue en 21 rutas). `{numero:path}` como el `DELETE` (admite `/`). Cuerpo `OrdenEdicionRequest` = campos del alta sin `numero` + `chequeo_final` + `conservar_servicio: bool = False`. `numero` en el cuerpo → 422 "El número de la orden no se puede cambiar." (★ número inmutable; Q1). El modelo declara `numero: Optional[Any] = None` y el service lo rechaza si viene distinto de `None`, para conservar el mensaje en español.
- ★ **Reemplazo completo** (PUT semántico): lo que no viene queda vacío. Alternativa PATCH parcial: descartada, obliga a distinguir "ausente" de `null` en cada campo y a mezclar con el contenido viejo; el formulario siempre manda todo.
- ★ **Fecha editable** con la validación del alta (Q2). Afecta filtros/reportes (esperable).
- Respuesta 200 `EdicionOrdenOut {orden: OrdenOut, ajustes: [AjusteOut]}` con `AjusteOut {codigo, nombre, cantidad_anterior, cantidad_nueva, stock, reactivado}` ordenado por código, solo productos con delta ≠ 0 (patrón de `BorradoOrdenOut.reintegros`).
- `PUT` se suma a la guarda "Escrituras solo con cuerpo JSON" (CSRF) y a su test.

### D2 — Ajuste de stock por diferencia, atómico (decisión 3)

`SqliteOrdenRepository.editar(numero, fecha, items, procesos, servicio, datos, chequeo_final, conservar_servicio)`; todo dentro de **una** `_transaccion` (`BEGIN IMMEDIATE` = lock de escritura antes de leer):

1. `_buscar_orden_por_numero` → `OrdenNoEncontrada`.
2. Si `conservar_servicio`: la orden debe tener servicio → si no, `DatosInvalidos("La orden no tiene un servicio general para conservar.")`; se reutiliza su snapshot con el precio nuevo.
3. `anteriores = {producto_id: cantidad}` de `orden_items`; `nuevos` = productos de `items` buscados por código **sin filtrar `activo`** (`id, codigo, nombre, stock, activo`).
4. Por cada producto de la unión: `delta = nueva − anterior`.
   - Código inexistente, o `delta > 0` con producto inactivo → acumula en `ausentes` (`ProductosNoEncontrados`, mismo mensaje que el alta).
   - `delta > 0` y `stock < delta` → `Faltante(codigo, disponible=stock, solicitado=delta)`.
   - Se juntan **todos** los ausentes (primero) y faltantes antes de escribir nada (mismo criterio que el alta).
5. Escritura: `UPDATE ordenes SET fecha, cliente, … , fecha_egreso`; `DELETE` + `INSERT` de `orden_items`, `orden_procesos`, `orden_servicio(+chequeos)` y `orden_chequeo_final`; para `delta > 0` `_SQL_RESTAR` (guarda `stock >= ?`, `rowcount == 1` o `RuntimeError` → rollback); para `delta < 0` `_SQL_SUMAR_Y_ACTIVAR` (★ reactiva, RN-OR-12; Q3).
6. Devuelve `ResultadoEdicionOrden(orden=_leer_orden(id), ajustes=(AjusteStock…))`.

Producto inactivo con `delta == 0` → sin cambios (★ la orden puede conservarlo). Producto inactivo con `delta < 0` → reintegra y reactiva. El orden de escritura no importa porque todo es una transacción; cualquier excepción → `rollback`.

**Concurrencia**: `BEGIN IMMEDIATE` serializa ediciones, altas, borrados y modificaciones de stock en SQLite; los deltas se calculan **dentro** de la transacción contra el estado confirmado, así el stock nunca deriva. Dos usuarios editando la misma orden: gana la última escritura (★ sin bloqueo optimista; Q7). Edición tras borrado → 404. En C-07: RPC `editar_orden` con `SELECT … FOR UPDATE` sobre la orden y los productos (orden por id para evitar deadlocks).

### D3 — Sin movimientos de stock (decisión 4)

★ La edición **no** escribe en `movimientos`, igual que el alta (RN-ST-06) y el borrado (DD-09): el stock descontado por órdenes vive en `orden_items`; si la edición registrara movimientos, la bitácora mostraría reintegros de descuentos que nunca registró. La respuesta (`ajustes`) y el aviso de la web informan el detalle. Alternativa: movimientos `ingreso`/`egreso` por cada delta (requeriría también registrar alta y borrado para ser coherente → fuera de alcance). Q4.

### D4 — Validación compartida con el alta (decisión 5)

- Se extrae de `OrdenService.crear` una función `_validar_contenido(fecha, componentes, datos, servicio, precio_servicio, procesos, personalizados, chequeo_final, conservar_servicio)` que devuelve un `ContenidoOrden` (fecha, items, datos, servicio|None, procesos, chequeo_final). `crear` = número + `_validar_contenido` + `repo.crear`; `editar(numero, cuerpo…)` = número + `numero` en cuerpo + `_validar_contenido` + `repo.editar`.
- Prioridad (spec `edicion-ordenes`): número → número en cuerpo → fecha → ingreso → egreso → cliente → celular → casco → motor → trailer → componentes → servicio → precio del servicio → servicio + conservar a la vez → procesos → personalizados → chequeo → (repo) orden inexistente → servicio a conservar inexistente → productos → stock.
- `conservar_servicio`: `bool` estricto (`True`/`False`/ausente); otro valor → 422 "El campo conservar_servicio debe ser true o false.". Con `conservar_servicio` el service **no** resuelve el catálogo y valida solo `precio_servicio` (sin la regla "precio sin servicio").

### D5 — Servicios del catálogo cambiados desde el alta (decisión 6)

- **Servicio general** (★ `conservar_servicio`): el snapshot de la orden (nombre + chequeos) puede no coincidir con el catálogo (renombrado, chequeos cambiados, borrado). En la web, si la orden tiene servicio, el select arranca con la opción "<Nombre> (actual)" (valor interno `__actual__`) elegida y su "Incluye:" muestra los chequeos guardados; enviar con esa opción → `conservar_servicio: true`. Elegir un servicio del catálogo → re-snapshot con sus chequeos **actuales**. Alternativa: re-snapshot siempre (perdería chequeos que el cliente ya pagó) o refrescar en silencio por nombre.
- **Servicios adicionales** (★ minor default): un proceso guardado `personalizado=false` cuyo nombre coincide (casefold) con un proceso del catálogo se precarga como esa clave; si ya no está en el catálogo, se precarga como **personalizado** con su nombre y precio (al guardar queda `personalizado=true`; visible solo como dato interno). Límite de 10 personalizados: una orden vieja que lo exceda por esta conversión recibe el error normal y el usuario quita alguno (caso extremo).

### D6 — Chequeo final (decisiones 7, 8, 9)

- ★ **Lista fija** (no catálogo): constante en `inventario/domain/chequeo_final.py`: `CHEQUEO_FINAL = (("combustible", "Combustible"), ("puesta-en-marcha", "Puesta en marcha"), ("check-list-y-verificacion-final", "Check-list y verificación final"), ("prueba-en-el-lago", "Prueba en el lago"), ("limpieza-de-cortesia", "Limpieza de cortesía"), ("entrega", "Entrega"))`. El nombre no se guarda (sale de la constante; si un día cambia el texto, cambia en todas las órdenes — aceptable para una lista fija). Alternativa catálogo administrable: tabla, CRUD, API, UI y snapshot → mucho alcance sin pedido.
- **Tabla** `orden_chequeo_final (orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE, clave TEXT NOT NULL CHECK (clave IN (<seis claves>)), precio_centavos INTEGER <_PRECIO_CHECK>, PRIMARY KEY (orden_id, clave))`. Fila = ítem marcado. Borrado de orden: `DELETE` explícito (como procesos/servicio) además del CASCADE.
- **Entidad** `ChequeoFinal(clave, nombre, precio=None)`; `Orden.chequeo_final: tuple[ChequeoFinal, ...] = ()`, devuelto en el orden de la constante (se ordena al leer por posición en la lista, no por SQL alfabético).
- **API**: `chequeo_final` = lista de clave (texto) u objeto `{clave, precio}` (mismo patrón que `procesos` de C-06h). Clave normalizada (recorte + minúsculas); inexistente → "El ítem de chequeo final 'x' no existe."; ★ **repetida → 422** "Chequeo final N: 'x' está repetido." (a diferencia de procesos, que toman la primera: acá cada línea es plata y la web nunca repite). Tipo inválido → "El campo chequeo_final debe ser una lista de claves.". Precio → "Chequeo final N: El precio debe ser…".
- ★ **Total**: el precio del chequeo **suma al Subtotal servicios** (`Orden.subtotal_servicios`); la estructura del resumen (tres renglones) no cambia en pantalla, PDF ni API. Alternativa: cuarto renglón "Subtotal chequeo" (Q5).
- ★ **Dónde se carga**: la API lo acepta en alta y edición; la web lo muestra **solo en "Editar orden"** (es el chequeo previo a la entrega; "Nueva orden" no cambia → sin mockup). Q8.

### D7 — Web: modal "Editar orden" en `/ordenes` con formulario compartido (decisión 10)

- ★ **Extraer** la lógica del formulario de orden de `inventario.js` a `static/js/orden-form.js` (`window.OrdenForm.montar(raiz, opciones)` con modo `"nueva"|"editar"`, sin DOM al cargar, IDs con prefijo por instancia). `index.html` lo sigue usando para "Nueva orden" (sin cambios visibles); `ordenes.html` incluye el mismo markup en `#modal-editar` (copiado del de `index.html`, más el fieldset del chequeo) y carga `procesos.js`, `datos-orden.js`, `busqueda.js`, `orden-form.js`, `chequeo-final.js`. El refactor se hace **primero** y con las guardas existentes de "Nueva orden" en verde (sin cambio de comportamiento). Alternativa: navegar a `/inventario?editar=OT-0043` y reutilizar el modal tal cual (menos código, pero saca al usuario de `/ordenes` y mezcla pantallas). Q9.
- **Precarga**: `GET /api/ordenes?numero=X` (la lista ya la tiene; se usa el objeto en memoria y no se hace otro GET) + `GET /api/inventario` + `GET /api/productos/inactivos` (para los dados de baja de la orden) + catálogos de procesos y servicios. Importes con `Precios.formatear` sin "$ " en la caja (`45.000,00`).
- **Etiqueta del producto**: "(stock N + M en esta orden)" si la orden lo tenía; inactivos de la orden: opción "(dado de baja)" solo en su línea. Sin validación de stock en el navegador (igual que "Nueva orden"); el 409 se pinta bajo la línea ("Disponible X, solicitado Y", con `solicitado` = adicional).
- **Chequeo**: módulo puro `static/js/chequeo-final.js` (`ITEMS` = misma lista que el backend, `leer(estado) → [{clave, precio}]` y `validar`), probado con Node; una guarda compara `ITEMS` con `CHEQUEO_FINAL` de Python. Fieldset "Chequeo final": seis filas `checkbox + nombre + caja .money` (deshabilitada si no está marcada; al desmarcar se vacía). `Precios.resumen` gana `chequeo_final: [...]` sumado a servicios.
- **Resultado**: aviso `#aviso-exito` reutilizado ("Orden OT-0043 actualizada." + lista "ACE-01 −1 descontada (stock 2)" / "FIL-01 +1 devuelta (stock 4, reactivado)" o "Sin cambios de stock."). Errores 422 en la alerta del modal o la línea (mapeo existente), 404 orden → mensaje y recarga al cerrar.
- **Detalle**: fila "Chequeo final:" (chips "Nombre · $ …", solo los hechos) tras "Servicios adicionales:"; PDF: sección "Chequeo final" con **los seis ítems** (ver D11); botón "Editar" con `no-print`.

### D11 — PDF: chequeo final completo, hechos y no hechos (pedido del usuario, 2026-11-27) (decisión 13)

- **Pedido del usuario (2026-11-27)**: "que en el PDF también aparezcan los chequeos finales que no se hicieron, pero que se marque que no se hicieron". La hoja impresa de una orden (Exportar PDF de C-06c, CSS de impresión de C-06h en `app.css`) lista **siempre los seis ítems** en el orden fijo, después de "Servicios adicionales" y antes del resumen:
  - hecho: `[✓] Combustible` · "Hecho" · precio a la derecha (o "—");
  - no hecho: `[ ] Puesta en marcha` · "No se hizo", sin precio (igual `[ ] Check-list y verificación final`).
- **Legible en blanco y negro**: la diferencia es por **símbolo y texto** (`[✓]`/`[ ]` + "Hecho"/"No se hizo"); además el no hecho va en gris de papel, pero ese color es solo un refuerzo y no la única marca. Los corchetes son texto, así que se ven aunque la impresora no imprima fondos ni bordes.
- ★ Una orden **sin ningún ítem marcado** (incluidas las anteriores a C-06i) también imprime la sección con los seis "No se hizo" (lectura literal del pedido; Q11).
- La pantalla `/ordenes` **no cambia**: sigue mostrando solo los hechos (la fila se oculta si no hay ninguno). El pedido es para el PDF.
- **¿C-06i o C-06j?** Va en **C-06i**: el alcance de C-06i en `CHANGES.md` ya incluye "Detalle de la orden y PDF (C-06c) muestran el chequeo final", y el PDF actual es el que se toca acá. C-06j rediseña el formato de impresión y debe **conservar** esta regla (anotarlo en su entrada de `CHANGES.md` al archivar C-06i, o antes si el usuario lo confirma).

### D12 — Nombres: "chequeo" (pedido del usuario, 2026-11-27)

- Todo texto visible dice **"chequeo"** ("Chequeo final", "chequeos finales"); el nombre del change y su carpeta (`paso-5i-modificar-ordenes-checkeo`) quedan como están porque son el identificador de la CLI.
- **Identificadores nuevos con sufijo `_final`** (`chequeo_final`, `orden_chequeo_final`, `CHEQUEO_FINAL`, `ChequeoFinal`, `chequeo-final.js`, capacidad `chequeo-final-ordenes`). Así no se confunden con los **chequeos del servicio general** que ya existen (`orden_servicio_chequeos`, `servicio_chequeos`, `ServicioOrden.chequeos`, campo de API `servicio.chequeos`). Tampoco se pisa el prefijo de error existente "Chequeo N: …" del catálogo de servicios generales (`normalizacion.py`): el chequeo final usa "Chequeo final N: …".

### D8 — Migración (decisión 11)

`_crear_chequeo_final(conn, loguear)` tras `_migrar_datos_precios_orden` y antes de `NORMALIZAR_FECHAS_SQL`: si `orden_chequeo_final` existe → nada; si no, en `_transaccion`: contar `_TABLAS_CONTADAS_PRECIOS`, `CREATE TABLE orden_chequeo_final …`, verificar conteos, log "Agregado el chequeo final de órdenes (N orden(es) conservadas, sin chequeo)." solo si la base existía. Un solo camino para bases nuevas y viejas (no se toca `ESQUEMA_SQL`). Backup `dev-local.bak-5i.db` (copia de archivo) antes del primer arranque; verify sobre una copia.

### D9 — Paridad Supabase (C-07)

`orden_chequeo_final` con `clave text check (clave in (...))`, `precio_centavos bigint check (...)`, PK compuesta; RPC `editar_orden(p_numero, p_fecha, p_datos jsonb, p_items jsonb, p_procesos jsonb, p_servicio jsonb, p_conservar_servicio, p_chequeo_final jsonb)` con `SELECT … FOR UPDATE` de la orden y de los productos involucrados (ordenados por id), cálculo de deltas, faltantes y reintegro con reactivación; `crear_orden` gana `p_chequeo_final`. Anotar en `CHANGES.md` § C-07 al archivar.

### D10 — Tests (Strict TDD, `unittest`, SQLite real)

- Migración: `tests/test_sqlite_migracion_chequeo_final.py` con el DDL de C-06h **copiado literal**; esquema/CHECKs en `tests/test_sqlite_schema.py`.
- Dominio: `tests/test_orden_totales.py` (chequeo en subtotal servicios).
- Repositorio: `tests/test_sqlite_orden_edicion.py` (nuevo): todos los escenarios de stock de `edicion-ordenes` (aumentar, reducir, quitar/agregar, sin cambios, inactivos, faltantes múltiples, faltante + reintegro sin aplicar, falla inyectada → rollback total, dos ediciones seguidas, conservar servicio, ajustes).
- Service: `tests/test_orden_service.py` (validación, prioridad, `numero` en cuerpo, `conservar_servicio`, chequeo).
- API: `tests/test_api_ordenes_edicion.py` (nuevo) + diccionarios exactos actualizados con `chequeo_final` + CSRF con `PUT`.
- JS puro con Node: `tests/test_chequeo_final_js.py`, `tests/test_precios_js.py` (resumen con chequeo); guardas estáticas `tests/test_frontend_ordenes_edicion.py`; navegador en el verify.

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-27)
- Mockups: openspec/changes/paso-5i-modificar-ordenes-checkeo/mockups/ (`ordenes.html` con estados L1, E1, E2 y P1; `README.md`)
- Approval: approved (2026-11-27, by user; amended: 6th item "Check-list y verificación final" added after approval as requested by the user)
- Visual verify: passed (2026-11-27; re-verificado con uvicorn propio sobre una base descartable; L1 (390 y 1440), E1 (390 y 1440) y E2 (390; 409 provocado, error bajo la línea) abiertos en la app real; capturas `mockups/verify/v2-*.png`; consola solo con el 409 provocado; sin scroll horizontal a 390 px; objetivos del chequeo de 44 px; verificación anterior con PDF/P1/N1 vigente en `mockups/verify/`). Diferencia menor aceptada: en el modal de edición no hay columna "Categoría" por línea (igual que el mockup E1).
- Preview: rendered (2026-11-27, re-renderizado E1, E2 y P1 tras sumar el 6.º ítem "Check-list y verificación final" (L1 no cambia: solo muestra ítems hechos); antes: pedido del PDF con chequeos no hechos y "chequeo"; 390x844 y 1440x900 vía http local; `mockups/previews/ordenes-L1-{mobile,desktop}.png`, `ordenes-E1-{mobile,desktop}.png`, `ordenes-E2-{mobile,desktop}.png`, `ordenes-P1-{mobile,desktop}.png`; sin scroll horizontal a 390 px, consola sin errores salvo favicon 404 del servidor de prueba)

Base: mockups aprobados de C-06h (assets copiados), tokens `design-system/tokens.css` + `ui.css`, tema oscuro único, cabecera de texto "Inventario". Solo las pantallas/estados que cambian (ver `mockups/README.md`):

| ID | Pantalla | Estado |
|----|----------|--------|
| L1 | Órdenes | Botón "Editar" en cada orden, fila "Chequeo final:" con precios, aviso "Orden OT-0043 actualizada." con ajustes de stock |
| E1 | Órdenes · modal "Editar orden OT-0043" | Formulario precargado, servicio "(actual)", etiqueta "(stock N + M en esta orden)", fieldset "Chequeo final" con dos marcados (uno con precio), resumen con chequeo incluido, "Guardar cambios" |
| E2 | Órdenes · modal con 409 | Modal abierto tras stock insuficiente: error bajo la línea + alerta general |
| P1 | Órdenes · hoja impresa | PDF de `OT-0043` con la sección "Chequeo final" con los seis ítems: hechos `[✓]` "Hecho" + precio y no hechos `[ ]` "No se hizo" (D11) |

Sin mockup propio (justificado en `mockups/README.md`): "Nueva orden" (sin cambios visibles), errores de validación de importes (estilos aprobados), orden borrada mientras se editaba (alerta estándar), estados de carga/red.

## Risks / Trade-offs

- [Edición mueve stock de varios productos] → una sola `_transaccion` `BEGIN IMMEDIATE`, deltas calculados dentro, guardas `rowcount`, falla inyectada en tests → rollback total.
- [Sin movimientos] → la bitácora no muestra los ajustes de una edición (coherente con alta/borrado); el detalle se informa en la respuesta. Q4.
- [Última escritura gana] → dos personas editando la misma orden pueden pisarse el contenido (no el stock). Pyme de 1-2 usuarios. Q7.
- [Refactor del formulario de 1415 líneas] → se hace en su propio grupo, antes de tocar comportamiento, con todas las guardas de "Nueva orden" (C-06/C-06e/f/g/h/h2) en verde; si se complica, plan B: duplicar el markup y extraer solo funciones puras.
- [Procesos del catálogo borrados pasan a personalizados al editar] → cambio interno de bandera, mismo nombre y precio; documentado.
- [Reactivar al reducir] → un producto dado de baja vuelve a aparecer en el inventario si se reduce su cantidad en una orden (igual que el borrado con reintegro). Q3.
- [Fecha editable] → mover una orden de fecha cambia los reportes de ese rango (esperable).

## Migration Plan

1. Antes del primer arranque: copiar `dev-local.db` a `dev-local.bak-5i.db` (grupo 1 del apply, sin abrir el original).
2. Arrancar uvicorn: `_crear_chequeo_final` crea `orden_chequeo_final` y loguea una vez.
3. Arranques siguientes: nada.
4. Rollback: código anterior (ignora la tabla) o restaurar `dev-local.bak-5i.db`. Las ediciones hechas con el código nuevo ya ajustaron stock y siguen siendo coherentes con el código viejo (solo se pierde el chequeo).

## Decisions (antes Open Questions) — resueltas el 2026-11-27

El usuario aceptó la opción recomendada (★) en todas. Ya no queda ninguna pregunta abierta.

- **Q1 — Número**: decidido (2026-11-27): NO editable (identifica la orden en la URL).
- **Q2 — Fecha**: decidido (2026-11-27): editable con la misma validación del alta.
- **Q3 — Reducir/quitar un producto dado de baja**: decidido (2026-11-27): reintegra el stock y lo reactiva (igual que el borrado con reintegro).
- **Q4 — Movimientos**: decidido (2026-11-27): la edición no deja movimientos (como el alta y el borrado).
- **Q5 — Chequeo en el total**: decidido (2026-11-27): suma al "Subtotal servicios".
- **Q6 — Auditoría**: decidido (2026-11-27): sin registro de quién/cuándo editó.
- **Q7 — Ediciones simultáneas**: decidido (2026-11-27): gana la última escritura (el stock siempre queda bien); sin bloqueo optimista.
- **Q8 — Chequeo en "Nueva orden"**: decidido (2026-11-27): en la web solo en el modal "Editar orden"; la API lo acepta también en el alta.
- **Q9 — Dónde se edita**: decidido (2026-11-27): modal en `/ordenes` con el formulario extraído a un módulo compartido (`orden-form.js`).
- **Q10 — Chequeo**: decidido (2026-11-27), lista fija **ampliada a seis ítems** en este orden: Combustible (`combustible`), Puesta en marcha (`puesta-en-marcha`), Check-list y verificación final (`check-list-y-verificacion-final`), Prueba en el lago (`prueba-en-el-lago`), Limpieza de cortesía (`limpieza-de-cortesia`), Entrega (`entrega`); precio solo si está marcado. El ítem "Check-list y verificación final" lo pidió el usuario después de aprobar los mockups (2026-11-27); el rótulo se respeta tal cual lo escribió.
- **Q11 — PDF de una orden sin chequeo**: decidido (2026-11-27): imprime igual los seis ítems como "No se hizo".

Al archivar: KB 02 (ruta `PUT`, `chequeo_final`), 04 (`orden_chequeo_final`), 05 (RN-OR-10 reemplazada por reglas de edición, ajuste por diferencia, chequeo, subtotal), 06 (US nueva "Editar orden" y chequeo en US-007), 07 (flujo de edición con errores); `CHANGES.md` C-06i `[x]` y paridad C-07 de D9.

## Decisiones para revisión del usuario

> Governance ALTO. ★ = recomendada, **todas aceptadas por el usuario el 2026-11-27** (Q1-Q11 decididas, ver "Decisions"). **Pedido por el usuario (2026-11-26)**: editar servicio general, ítems con precios, servicios adicionales con precios y datos de C-06h; stock por diferencia todo o nada; chequeo final con seis ítems fijos y precio opcional; detalle y PDF con el chequeo.

1. **Ruta** — ★ `PUT /api/ordenes/{numero}` con reemplazo completo; respuesta con `orden` + `ajustes`.
2. **Número y fecha** — ★ número inmutable (Q1), fecha editable (Q2).
3. **Stock** — ★ ajuste por diferencia en una transacción; faltantes y productos inactivos/inexistentes rechazan todo; reducir un inactivo reintegra y reactiva (Q3).
4. **Movimientos** — ★ ninguno (Q4).
5. **Validación** — ★ la misma del alta, extraída a una función compartida; prioridad de D4.
6. **Servicio/procesos cambiados en el catálogo** — ★ `conservar_servicio`; procesos borrados del catálogo pasan a personalizados.
7. **Chequeo** — ★ lista fija con CHECK, no catálogo (Q10, seis ítems); repetido → 422.
8. **Total** — ★ chequeo en "Subtotal servicios" (Q5).
9. **Dónde se carga el chequeo** — ★ solo "Editar orden" en la web; API en alta y edición (Q8).
10. **Web** — ★ modal "Editar orden" en `/ordenes` con el formulario de "Nueva orden" extraído a `orden-form.js` (Q9); mockups L1/E1/E2/P1.
11. **Migración** — ★ tabla nueva `orden_chequeo_final`, idempotente y transaccional; backup `dev-local.bak-5i.db`.
12. **Concurrencia** — ★ `BEGIN IMMEDIATE`, última escritura gana (Q7); sin auditoría (Q6).
13. **PDF del chequeo** — los seis ítems, hechos `[✓]` "Hecho" + precio y no hechos `[ ]` "No se hizo" (_pedido del usuario, 2026-11-27_); también en órdenes sin chequeo (Q11). Va en C-06i; C-06j lo conserva.
14. **Ortografía** — "chequeo" en todo texto visible; identificadores nuevos con `_final` (_pedido del usuario, 2026-11-27_).
