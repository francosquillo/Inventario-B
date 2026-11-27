# Proposal — paso-5g-servicios-generales (C-06g)

## Why

El usuario quiere registrar en cada orden de trabajo el **servicio general** que se le hizo a la lancha (pedido del 2026-11-26): un servicio con nombre propio que agrupa una lista fija de chequeos. Ejemplo: **"Servicio 20 hs"** = chequeo de motor, chequeo de combustible, chequeo eléctrico, etc. Hoy una orden solo registra piezas (C-03) y procesos sueltos (C-06f); no hay forma de decir "a esta lancha se le hizo el service de 20 horas" sin cargar cada chequeo a mano. Va antes de C-06h (precios: uno por servicio general), C-06i (editar órdenes) y C-07 (las tablas nuevas viajan a Supabase con el resto).

Governance **MEDIO/ALTO**: toca la creación y el borrado atómicos de órdenes (regla dura 3) y agrega tablas con migración sobre `dev-local.db` real; con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

Pedido del usuario (2026-11-26): catálogo de servicios generales, cada uno con sus chequeos incluidos; alta/edición/borrado del catálogo y de sus chequeos (patrón del catálogo de procesos de C-06f); asignar un servicio general al crear la orden, en la misma transacción que descuenta stock; mostrarlo en `/ordenes` y en el PDF de la orden; borrar la orden borra su servicio; órdenes existentes sin servicio. **Sin precios** (C-06h), **sin editar órdenes** (C-06i), **sin formato de impresión nuevo** (C-06j). Decidido por el usuario (2026-11-27): el catálogo se administra **también desde la web** (Q1); cero o un servicio por orden (Q3); sin tildar chequeos por orden en este change (Q2, queda para C-06i); límites y ubicación en "Nueva orden" recomendados (Q4/Q5); en el PDF el bloque "Servicio general" va **primero**, antes de la tabla de componentes (cambio del usuario, 2026-11-27). El resto son recomendaciones (★) de `design.md`.

- **Catálogo de servicios generales** (tablas nuevas `servicios_generales` con clave estable + nombre, y `servicio_chequeos` con la lista ordenada de chequeos de cada uno): sembrado con `servicio-20-hs` "Servicio 20 hs" = "Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico" **solo al crear el catálogo**. Cada servicio tiene de 1 a 30 chequeos (1 a 60 caracteres, sin repetir dentro del servicio).
- **Servicio general de una orden** (tablas nuevas `orden_servicio` y `orden_servicio_chequeos`): cada orden tiene **cero o un** servicio general; se guarda una **copia** del nombre y de todos sus chequeos (snapshot, sin FK al catálogo), así renombrar, cambiar los chequeos o borrar un servicio del catálogo **no altera** órdenes pasadas.
- **Alta de orden**: `POST /api/ordenes` acepta `servicio` (clave del catálogo, opcional; `null`/ausente/vacío = sin servicio); orden, líneas, servicio con sus chequeos, procesos y descuentos de stock en **una sola transacción**. Errores del servicio → 422 (prioridad "datos inválidos").
- **Lecturas y borrado**: `GET /api/ordenes`, la respuesta del alta y la `orden` del borrado incluyen `servicio` (`null` o `{nombre, chequeos: [texto, …]}`); borrar una orden borra su servicio y sus chequeos en la misma transacción.
- **Administración por API**: `GET`/`POST /api/servicios-generales`, `PATCH`/`DELETE /api/servicios-generales/{clave}`. `PATCH` cambia el nombre y/o **reemplaza la lista completa de chequeos** en una transacción; clave inmutable; nombre único sin distinguir mayúsculas (409); 404 si no existe. Borrar un servicio usado por órdenes pasadas está permitido (snapshot).
- **Migración idempotente**: las cuatro tablas nuevas se crean en una transacción junto con la siembra, solo si no existen; no se toca ninguna tabla existente; las órdenes existentes quedan sin servicio. Backup de `dev-local.db` antes del primer arranque.
- OpenAPI pasa de 19 a **21** rutas `/api/...` (`/api/servicios-generales` y `/api/servicios-generales/{clave}`).
- **Web**:
  - "Nueva orden": bloque **"Servicio general"** con un selector ("Sin servicio general" por defecto + catálogo por nombre) y, al elegir uno, la lista de solo lectura de los chequeos que incluye; validación en el navegador igual que en la API.
  - **Administración en la web** (decisión del usuario, 2026-11-27): botón **"Servicios generales"** junto al título de `/ordenes` que abre un modal con la lista del catálogo (nombre + chequeos) y acciones **"Nuevo servicio"**, **"Editar"** y **"Eliminar"**; el mismo modal pasa a un formulario con el nombre y la lista ordenada de chequeos ("Agregar chequeo", "Quitar"); eliminar pide confirmación. Usa los endpoints de arriba; sin rutas de página nuevas.
  - `/ordenes`: cada orden con servicio muestra una fila **"Servicio general:"** con el nombre y sus chequeos como chips; órdenes sin servicio no muestran la fila.
  - PDF de una orden: encabezado sin cambios; bloque **"Servicio general"** (nombre + chequeos, uno por línea) **primero**, justo después del encabezado y antes de la tabla de componentes; luego la tabla y después "Procesos realizados"; omitido si no hay.
- **Sin cambios**: `/inventario` (salvo el modal "Nueva orden"), `/reportes`, filtros de `/ordenes`, movimientos, procesos. Sin dependencias nuevas.

## Capabilities

### New Capabilities
- `servicios-generales`: catálogo de servicios generales con sus chequeos (clave + nombre + lista ordenada de chequeos, sembrado con "Servicio 20 hs"), alta, modificación (nombre y/o chequeos) y borrado del catálogo, asignación de cero o un servicio a una orden con snapshot del nombre y los chequeos, y su persistencia/borrado junto con la orden.

### Modified Capabilities
- `ordenes-trabajo`: la atomicidad del alta incluye el servicio general; el borrado elimina el servicio de la orden; el resultado del borrado lo informa.
- `consulta-ordenes`: cada orden consultada incluye su servicio general (o ninguno).
- `inicializacion-base-datos`: esquema con las cuatro tablas nuevas; siembra solo al crear el catálogo; incorporación de servicios generales a bases existentes.
- `api-http`: `servicio` en el alta de orden y en las respuestas de órdenes; endpoints de servicios generales; cuerpos JSON en las escrituras nuevas; OpenAPI con 21 rutas.
- `interfaz-web`: bloque "Servicio general" en "Nueva orden"; administración del catálogo desde `/ordenes` (modal "Servicios generales"); servicio general en `/ordenes` y en el PDF de una orden.

## Impact

- **Backend**: `inventario/repositories/sqlite_repo.py` (DDL de las cuatro tablas, `_crear_servicios_generales` con siembra, `SqliteServicioGeneralRepository`, alta/lectura/borrado de órdenes con servicio), `repositories/base.py` (`ServicioGeneralRepository`; `OrdenRepository.crear(..., servicio=None)`), `domain/entities.py` (`ServicioGeneral`, `ServicioOrden`; `Orden.servicio`), `domain/errors.py` (`ServicioGeneralDuplicado`, `ServicioGeneralNoEncontrado`), `services/normalizacion.py` (nombre de servicio y de chequeo, clave), `services/servicio_general_service.py` (nuevo), `services/orden_service.py` (validación del servicio), `api/schemas.py`, `api/dependencies.py`, `api/routers/servicios_generales.py` (nuevo), `api/routers/ordenes.py`, `api/app.py` (router y handlers 404/409).
- **Frontend**: `static/index.html` + `static/js/inventario.js` (bloque "Servicio general" en "Nueva orden"), módulo JS puro nuevo `static/js/servicios.js` (selección en la orden y validación del formulario del catálogo; testeable con Node), `static/ordenes.html` + `static/js/ordenes.js` (fila de servicio y bloque del PDF) y `static/js/servicios-admin.js` nuevo (modal de administración), `static/css/app.css` (solo si hace falta).
- **Tests** (`unittest`, SQLite real `:memory:`/archivo temporal): migración desde el esquema de C-06f copiado literal, repositorios, services, API con `TestClient` (servicios generales, órdenes con servicio, CSRF, OpenAPI 21 rutas), JS puro con Node, guardas estáticas.
- **Datos**: `dev-local.db` gana cuatro tablas (1 servicio + 3 chequeos sembrados) al primer arranque; nada existente cambia. Verify sobre una **copia**.
- **C-06h**: el precio del servicio general irá como columna de `orden_servicio` (una fila por orden). **C-07**: tablas equivalentes en Postgres; la RPC `crear_orden` gana `p_servicio` (jsonb `{nombre, chequeos}`); la modificación de un servicio (nombre + reemplazo de chequeos) es multi-tabla → RPC o transacción equivalente.
- **KB al archivar**: 02 (API, 21 rutas), 04 (tablas nuevas), 05 (RN-OR de servicio general y RN del catálogo), 06 (US-006/US-007 con servicio, administración desde `/ordenes` y por API), 07 (flujos de alta/listado/PDF con servicio y administración del catálogo en la web).
