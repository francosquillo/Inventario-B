# Proposal — paso-5i-modificar-ordenes-checkeo (C-06i)

## Why

Hoy una orden de trabajo no se puede corregir una vez creada (RN-OR-10, "las órdenes no se editan en v1"): si falta una pieza, cambia el servicio, hay que cargar un precio o los datos del cliente, la única salida es borrarla (con o sin reintegro) y volver a crearla. El usuario pidió (2026-11-26) **modificar órdenes existentes** —servicio general, ítems con sus precios, servicios adicionales con sus precios y los datos de C-06h— con el stock ajustado por diferencia, y un **chequeo final** fijo (Combustible, Puesta en marcha, Check-list y verificación final, Prueba en el lago, Limpieza de cortesía y Entrega), cada ítem con un precio opcional. Va antes de C-06j (la impresión necesita el chequeo) y de C-07 (la edición viaja a una RPC de Supabase).

Governance **ALTO**: la edición mueve stock de varios productos a la vez (regla dura 3: todo o nada en una transacción, stock insuficiente → error sin cambios), hay una migración de esquema sobre `dev-local.db` real y validación en frontend y backend; con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

Las ★ eran recomendaciones de `design.md`; el usuario las aceptó todas el 2026-11-27 (Q1-Q11 decididas, ver "Decisions" de `design.md`). La lista de chequeo quedó en **seis** ítems (se sumó "Check-list y verificación final").

- **Editar una orden existente** (identificada por su número, que no cambia ★): se reemplaza su contenido completo —fecha ★, datos del cliente y la embarcación, servicio general y su precio, componentes con importe, servicios adicionales con precio y chequeo final— con las **mismas validaciones del alta** (C-03/C-06f/C-06g/C-06h).
- **Ajuste de stock por diferencia, atómico**: por cada producto, `delta = cantidad nueva − cantidad anterior`; delta > 0 descuenta (exige producto activo y stock suficiente), delta < 0 reintegra (★ reactivando el producto si estaba dado de baja, como el borrado con reintegro, RN-OR-12), delta 0 no toca nada (aunque el producto esté dado de baja). Todo en **una sola transacción** con la reescritura de la orden; cualquier faltante o error → **ninguna** modificación. ★ Sin movimientos de stock (como el alta y el borrado, RN-ST-06 / DD-09).
- **Chequeo final** fijo: lista cerrada de seis ítems (★ constante + CHECK en la base, no catálogo); cada ítem marcado puede llevar un precio opcional (centavos, mismas reglas que C-06h). ★ El precio del chequeo **suma al "Subtotal servicios"** (y por lo tanto al Total). ★ Se carga desde "Editar orden" (la API también lo acepta en el alta).
- **API (aditivo)**: `PUT /api/ordenes/{numero}` (200 con la orden actualizada y el detalle de ajustes de stock; 404 orden inexistente; 404 productos no activos; 409 stock insuficiente con `faltantes`; 422 datos inválidos). Campo opcional `chequeo_final` en el alta y en la edición; las respuestas de órdenes suman `chequeo_final`. OpenAPI sigue en 21 rutas (`PUT` es una operación nueva sobre la ruta existente `/api/ordenes/{numero}`).
- **Servicio general conservado**: al editar, el servicio de la orden (snapshot) puede conservarse tal cual aunque el catálogo haya cambiado (`conservar_servicio`), o reemplazarse por uno del catálogo, o quitarse.
- **Migración idempotente y transaccional**: tabla nueva `orden_chequeo_final`; ninguna fila existente cambia; backup `dev-local.bak-5i.db` antes del primer arranque.
- **Web**:
  - `/ordenes`: botón **"Editar"** en cada orden → modal **"Editar orden OT-XXXX"** (★ en la misma pantalla) con el formulario de "Nueva orden" precargado, el número fijo, ayuda de stock por línea que cuenta lo ya descontado por la orden, fieldset **"Chequeo final"** (seis casillas, importe habilitado solo si está marcada) y resumen en vivo; aviso de éxito con los ajustes de stock.
  - Detalle en `/ordenes` muestra el **chequeo final** (solo los ítems hechos, con su precio). El **PDF de una orden** (C-06c) lista **los seis ítems**: los hechos con `[✓]`, "Hecho" y su precio, y los no hechos con `[ ]` y "No se hizo" (pedido del usuario, 2026-11-27); la marca es texto y símbolo, legible impresa en blanco y negro.
- **Fuera de alcance**: cambiar el número de una orden ★; historial/auditoría de ediciones ★; formato de impresión nuevo (C-06j); catálogo editable de ítems de chequeo; edición concurrente con bloqueo optimista ★.

## Capabilities

### New Capabilities
- `edicion-ordenes`: modificación de una orden existente por número (reemplazo completo de su contenido), ajuste de stock por diferencia atómico, conservación del servicio general, rechazos y su prioridad.
- `chequeo-final-ordenes`: lista fija de ítems de chequeo final de una orden, marcado y precio opcional por ítem, validación y guardado con la orden.

### Modified Capabilities
- `precios-ordenes`: el "Subtotal servicios" suma los precios del chequeo final.
- `consulta-ordenes`: cada orden consultada incluye su chequeo final.
- `api-http`: nueva ruta `PUT /api/ordenes/{numero}` con sus rechazos; campo `chequeo_final` en el alta y en las respuestas.
- `inicializacion-base-datos`: incorporación idempotente de la tabla del chequeo final a bases nuevas y existentes.
- `interfaz-web`: botón y modal "Editar orden" en `/ordenes`, chequeo final en el modal, en la orden en pantalla y en su PDF, aviso con los ajustes de stock.

## Impact

- **Backend**: `inventario/repositories/sqlite_repo.py` (`_crear_chequeo_final`, `editar` atómico con ajuste por diferencia, lectura/escritura del chequeo, borrado en cascada), `repositories/base.py` (`OrdenRepository.editar`, `chequeo_final` en `crear`), `domain/entities.py` (`ChequeoFinal`, `Orden.chequeo_final`, `subtotal_servicios`, `AjusteStock`, `ResultadoEdicionOrden`), `domain/chequeo_final.py` (lista fija), `services/orden_service.py` (`editar`, validación compartida con `crear`, `_resolver_chequeo_final`), `api/schemas.py`, `api/routers/ordenes.py`.
- **Frontend**: `static/ordenes.html` + `static/js/ordenes.js` (botón, modal, aviso, chequeo en el detalle y en el PDF), lógica del formulario de orden extraída a un módulo compartido `static/js/orden-form.js` ★ (la usan "Nueva orden" e "Editar orden"), módulo puro `static/js/chequeo-final.js`, `static/js/precios.js` (resumen con chequeo), `static/css/app.css`.
- **Tests** (`unittest`, SQLite real; JS puro con Node): migración desde el esquema de C-06h copiado literal, repositorio (ajuste por diferencia, atomicidad, faltantes, reactivación), service (validación y prioridad), API (`TestClient`, diccionarios exactos con `chequeo_final`, OpenAPI 21 rutas con `PUT` en `/api/ordenes/{numero}`), JS y guardas estáticas.
- **Datos**: `dev-local.db` gana una tabla vacía; ninguna fila cambia. Verify sobre una **copia**.
- **KB**: RN-OR-10 deja de valer (se reemplaza por las reglas de edición). Al archivar: KB 04, 05, 06 y 07 (más 02 por la ruta nueva).
- **C-07**: tabla `orden_chequeo_final` en Postgres y RPC `editar_orden` (ajuste por diferencia con `SELECT … FOR UPDATE`).
