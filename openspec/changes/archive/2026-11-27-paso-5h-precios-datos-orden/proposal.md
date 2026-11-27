# Proposal — paso-5h-precios-datos-orden (C-06h)

## Why

El usuario quiere que la orden de trabajo sirva para cobrarle al cliente (pedido del 2026-11-26/27): hoy una orden registra servicio general (C-06g), procesos (C-06f) y piezas (C-03), pero **ningún precio**, ni a quién pertenece la lancha ni cuándo entra y sale del taller. Este change agrega **precios tipeados por el usuario** (servicio general, cada ítem y cada servicio adicional), **dos subtotales y un total**, y los **datos del cliente y la embarcación** (cliente, celular, casco, motor, trailer, fecha de ingreso y de egreso). Va antes de C-06i (editar órdenes y checkeo final), C-06j (formato de impresión nuevo) y C-07 (las columnas nuevas viajan a Supabase).

Governance **ALTO**: migración de esquema sobre órdenes existentes (`dev-local.db` real), validación de montos y fechas en frontend y backend, alta atómica de la orden (regla dura 3); con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

Pedido del usuario: "Sistema de precios para las órdenes, todos tipeados por el usuario, uno para el servicio general, otro individual por ítem y otro por servicios adicionales (que ahora aparecen como procesos en las órdenes); también agregar a la orden cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso". Agregado por el usuario (2026-11-27): la orden muestra **"Subtotal servicios"** (servicio general + servicios adicionales), **"Subtotal ítems"** (todos los ítems) y **"Total"** (suma de ambos), calculados, en "Nueva orden" (en vivo), en `/ordenes` y en el PDF; un precio vacío cuenta como 0. Los precios se cargan **al crear** la orden. Decidido por el usuario (2026-11-27): **todos los datos del cliente y la embarcación son opcionales** (cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso). Modificado por el usuario (2026-11-27): la **"Fecha" de la orden queda exactamente como hoy** (obligatoria, junto al número, usada por filtros, reportes y el PDF); ingreso y egreso son **dos columnas nuevas y opcionales**, sin relación con `fecha`. El resto son recomendaciones (★) de `design.md` para confirmar.

- **Precios** (opcionales, ≥ 0, sin precio = `NULL`): guardados en **centavos enteros** (nunca float) como snapshot en `orden_servicio`, `orden_items` y `orden_procesos`; mostrados en pesos argentinos (`$ 12.500,00`). El precio de un ítem es el **importe de la línea** (lo que se cobra por esa pieza en esa cantidad), no un precio unitario.
- **Subtotales y total** calculados (no guardados): `subtotal_servicios`, `subtotal_items` y `total`, en centavos, devueltos por la API en cada orden; precio vacío = 0.
- **Datos de la orden**: `cliente` (hasta 80), `celular` (validación permisiva de formato), `casco`, `motor`, `trailer` (hasta 60), `fecha_ingreso` y `fecha_egreso` (`YYYY-MM-DD`; egreso ≥ ingreso solo si están ambas), **todos opcionales** (decidido por el usuario, 2026-11-27); solo se validan si se cargan. La `fecha` de la orden **no cambia**.
- **API (aditivo, sin romper clientes)**: campos nuevos opcionales en `POST /api/ordenes`: `cliente`, `fecha_ingreso`, `fecha_egreso`, `celular`, `casco`, `motor`, `trailer`, `precio` en cada componente, `precio_servicio`, y cada elemento de `procesos`/`procesos_personalizados` puede ser también un objeto con `precio` (`{clave, precio}` / `{nombre, precio}`); el texto suelto sigue valiendo. Las respuestas de órdenes suman los datos, los precios, los subtotales y el total.
- **Migración idempotente** en una transacción: columnas nuevas (`ALTER TABLE ... ADD COLUMN`, diez columnas) en `ordenes`, `orden_items`, `orden_procesos` y `orden_servicio`; las órdenes existentes quedan sin datos ni precios (`NULL`, subtotales y total en 0). Backup de `dev-local.db` antes del primer arranque.
- **Web**:
  - "Nueva orden": "Fecha" sin cambios junto al número; bloque "Cliente y embarcación" (cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso); precio del servicio general; "Importe" por línea de ítem; precio por servicio adicional; resumen con "Subtotal servicios", "Subtotal ítems" y "Total" que se actualiza al tipear. Validación en el navegador igual que en la API.
  - **"Procesos" pasa a llamarse "Servicios adicionales" solo en la interfaz** (etiquetas, botones, fila de `/ordenes` y título impreso); API, tablas y mensajes del backend siguen diciendo "procesos".
  - `/ordenes`: fecha como hoy; datos del cliente y la embarcación con ingreso/egreso en su fila, precios por línea y el resumen de subtotales y total en cada orden.
  - PDF de una orden: mismo esquema de C-06c/C-06g (encabezado "Fecha: …" sin cambios), con los datos (incluidos ingreso y egreso), una columna "Importe", los precios del servicio y de los servicios adicionales, y el resumen de subtotales y total al final.
- **Fuera de alcance**: editar órdenes ya creadas y checkeo final (C-06i); formato de impresión nuevo (C-06j); lista de precios automática; filtros o reportes por cliente o por monto; moneda distinta de ARS.

## Capabilities

### New Capabilities
- `precios-ordenes`: precios tipeados del servicio general, de cada ítem y de cada servicio adicional (centavos, opcionales, ≥ 0), su validación, su guardado atómico con la orden, y los subtotales y el total calculados.
- `datos-cliente-ordenes`: cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso de una orden (opcionales, independientes de la fecha de la orden), con su validación y guardado.

### Modified Capabilities
- `ordenes-trabajo`: prioridad de los rechazos con los datos y precios nuevos.
- `consulta-ordenes`: cada orden consultada incluye datos del cliente y la embarcación, fechas de ingreso y egreso, precios, subtotales y total.
- `api-http`: campos nuevos opcionales en el alta y en las respuestas de órdenes.
- `inicializacion-base-datos`: incorporación idempotente de las columnas nuevas a bases nuevas y existentes.
- `interfaz-web`: "Nueva orden" con datos, precios y resumen en vivo; "Servicios adicionales" en lugar de "Procesos"; datos, precios y resumen en `/ordenes` y en el PDF de una orden.

## Impact

- **Backend**: `inventario/repositories/sqlite_repo.py` (`_migrar_precios_datos_orden`, alta/lectura con columnas nuevas), `repositories/base.py` (firma de `OrdenRepository.crear`), `domain/entities.py` (`DatosOrden`, `precio` en `ItemOrden`/`ProcesoOrden`/`ServicioOrden`, subtotales y total de `Orden`), `services/orden_service.py` + `services/normalizacion.py` (validación de datos y precios), `api/schemas.py`, `api/routers/ordenes.py`.
- **Frontend**: `static/index.html` + `static/js/inventario.js` ("Nueva orden"), módulos JS puros nuevos `static/js/precios.js` (parseo/formato ARS y cálculo de subtotales) y `static/js/datos-orden.js` (validación de datos), `static/js/procesos.js` (etiquetas y repetidos), `static/ordenes.html` + `static/js/ordenes.js`, `static/css/app.css`.
- **Tests** (`unittest`, SQLite real; JS puro con Node): migración desde el esquema de C-06g copiado literal, repositorio, service, API (diccionarios exactos de órdenes actualizados con los campos nuevos), JS, guardas estáticas.
- **Datos**: `dev-local.db` gana columnas `NULL`; ninguna fila cambia. Verify sobre una **copia**.
- **C-07**: columnas equivalentes en Postgres (`bigint` centavos con CHECK); la RPC `crear_orden` gana los datos y los precios.
- **KB al archivar**: 02 (API), 04 (columnas nuevas), 05 (RN de precios, subtotales, datos y fechas), 06 (US-006/US-007), 07 (flujos de alta, listado y PDF).
