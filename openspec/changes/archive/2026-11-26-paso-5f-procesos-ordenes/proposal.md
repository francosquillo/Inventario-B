# Proposal — paso-5f-procesos-ordenes (C-06f)

## Why

El usuario quiere que cada orden de trabajo registre **los procesos hechos a la lancha** (pedido del 2026-11-24): hoy una orden solo dice qué piezas se usaron, no qué trabajo se hizo. Se arranca con un catálogo de tres procesos de ejemplo (**Cambio motor, Cambio filtro, Limpieza**) más la opción **"Personalizado"** para escribir procesos propios de una orden. En el mismo paso, el usuario pide poder **borrar categorías de producto** por la API (revierte la sub-decisión 2.6 de C-06e). Va antes de C-07 para que las tablas nuevas viajen a Supabase junto con el resto.

Governance **ALTO**: toca la creación y el borrado atómicos de órdenes (regla dura 3) y agrega tablas con migración sobre `dev-local.db` real; con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

Decidido por el usuario (2026-11-24): catálogo con 3 ejemplos; opción "Personalizado" con texto libre que queda **solo en esa orden** (no se agrega al catálogo ni se ofrece en otras órdenes); administración del catálogo de procesos **solo por API** (crear, renombrar y **borrar**); borrado de categorías por API; alta atómica con stock + procesos; borrar una orden borra sus procesos; procesos visibles en `/ordenes` y en el PDF de la orden; órdenes existentes quedan sin procesos. El resto de las reglas son recomendaciones (★) de `design.md` pendientes de revisión del usuario.

- **Catálogo de procesos** (tabla nueva `procesos`, clave estable + nombre, como las categorías): sembrado con `cambio-motor` "Cambio motor", `cambio-filtro` "Cambio filtro" y `limpieza` "Limpieza" **solo al crear el catálogo**.
- **Procesos de una orden** (tabla nueva `orden_procesos`): cada orden tiene **cero o más** procesos; cada uno guarda una **copia del nombre** (snapshot) y si fue personalizado, así renombrar o borrar un proceso del catálogo **no altera** órdenes pasadas. Procesos del catálogo repetidos se consolidan; personalizados de 1 a 60 caracteres, hasta 10 por orden, sin repetir nombres dentro de la orden ni coincidir con un proceso del catálogo.
- **Alta de orden**: `POST /api/ordenes` acepta `procesos` (claves del catálogo) y `procesos_personalizados` (textos), opcionales; orden, líneas, procesos y descuentos de stock en **una sola transacción**. Errores de procesos → 422 (prioridad "datos inválidos").
- **Lecturas y borrado**: `GET /api/ordenes`, la respuesta del alta y la `orden` del borrado incluyen `procesos` (`[{nombre, personalizado}]` en el orden cargado); borrar una orden borra sus procesos en la misma transacción.
- **Administración de procesos por API** (sin pantalla): `GET`/`POST /api/procesos`, `PATCH`/`DELETE /api/procesos/{clave}`; clave inmutable, nombre único sin distinguir mayúsculas (409), 404 si no existe. Borrar un proceso usado por órdenes pasadas está permitido (gracias al snapshot).
- **Borrado de categorías por API**: `DELETE /api/categorias/{clave}` → 200 con la categoría borrada; 404 si no existe; **409 si algún producto (activo o dado de baja) la usa** ("La categoría 'x' está asignada a N producto(s).").
- **Siembra**: categorías y procesos se siembran solo cuando su tabla se crea en ese arranque (no al encontrarla vacía), para que borrar todas las categorías o procesos no los resucite al reiniciar.
- **Migración idempotente**: las dos tablas nuevas se crean con `CREATE TABLE IF NOT EXISTS` (sin tocar tablas existentes); las órdenes existentes quedan sin procesos. Backup de `dev-local.db` antes del primer arranque.
- OpenAPI pasa de 17 a **19** rutas `/api/...` (`/api/procesos` y `/api/procesos/{clave}`; `/api/categorias/{clave}` suma `DELETE`).
- **Web**:
  - "Nueva orden": bloque **"Procesos"** debajo de Componentes, con líneas como las de componentes: un selector con los procesos del catálogo y **"Personalizado"** (abre una caja de texto), "Quitar" por línea y **"Agregar proceso"**; hasta 10 personalizados; validación en el navegador igual que en la API.
  - `/ordenes`: cada orden con procesos muestra una fila **"Procesos:"** con un chip por proceso bajo su cabecera; órdenes sin procesos no muestran la fila.
  - PDF de una orden: encabezado sin cambios ("Orden OT-XXXX" + "Fecha: … · N componentes"); luego la tabla de componentes y **debajo** un bloque **"Procesos realizados"** con la lista (omitido si no hay).
- **Sin cambios**: `/inventario` (salvo el modal "Nueva orden"), `/reportes` (sin procesos), filtros de `/ordenes` (sin filtro por proceso), movimientos. Sin dependencias nuevas.

## Capabilities

### New Capabilities
- `procesos-ordenes`: catálogo de procesos (clave + nombre, sembrado con 3 ejemplos), alta, renombre y borrado del catálogo, procesos del catálogo y personalizados de una orden (reglas de validación, snapshot del nombre, orden), y su persistencia/borrado junto con la orden.

### Modified Capabilities
- `categorias-productos`: el catálogo se administra también con borrado; nueva regla de borrado (409 si hay productos); la siembra ocurre solo al crear el catálogo.
- `ordenes-trabajo`: la atomicidad del alta incluye los procesos; el borrado elimina los procesos; el resultado del borrado informa los procesos de la orden.
- `consulta-ordenes`: cada orden consultada incluye sus procesos.
- `inicializacion-base-datos`: esquema con `procesos` y `orden_procesos`; siembra solo al crear cada catálogo; incorporación de procesos a bases existentes.
- `api-http`: `procesos`/`procesos_personalizados` en el alta de orden; `procesos` en las respuestas de órdenes; endpoints de procesos; `DELETE /api/categorias/{clave}`; cuerpos JSON en las escrituras nuevas; OpenAPI con 19 rutas.
- `interfaz-web`: sección de procesos en "Nueva orden"; procesos en `/ordenes` y en el PDF de una orden.

## Impact

- **Backend**: `inventario/repositories/sqlite_repo.py` (DDL `procesos` y `orden_procesos`, siembra al crear, `SqliteProcesoRepository`, alta/lectura/borrado de órdenes con procesos, `borrar` de categorías), `repositories/base.py` (`ProcesoRepository`, `CategoriaRepository.borrar`), `domain/entities.py` (`Proceso`, `ProcesoOrden`; `Orden.procesos`), `domain/errors.py` (`ProcesoDuplicado`, `ProcesoNoEncontrado`, `CategoriaEnUso`), `services/normalizacion.py` (normalización de nombres de proceso), `services/proceso_service.py` (nuevo), `services/orden_service.py` (validación de procesos), `services/categoria_service.py` (`borrar`), `api/schemas.py`, `api/dependencies.py`, `api/routers/procesos.py` (nuevo), `api/routers/categorias.py`, `api/routers/ordenes.py`, `api/app.py` (handlers 404/409).
- **Frontend**: `static/index.html` + `static/js/inventario.js` (sección de procesos en "Nueva orden"), módulo JS puro para validar/armar los procesos (testeable con Node), `static/ordenes.html` + `static/js/ordenes.js` (fila de procesos y bloque del PDF), `static/css/app.css` (chips y hoja impresa, solo si hace falta).
- **Tests** (`unittest`, SQLite real `:memory:`/archivo temporal): migración desde el esquema de C-06e copiado literal, repositorios, services, API con `TestClient` (procesos, órdenes con procesos, borrado de categorías, CSRF, OpenAPI 19 rutas), JS puro con Node, guardas estáticas.
- **Datos**: `dev-local.db` gana dos tablas vacías + 3 procesos sembrados al primer arranque; nada existente cambia. Verify sobre una **copia**.
- **C-07**: tablas `procesos` (clave única con CHECK, índice único `lower(nombre)`) y `orden_procesos` (FK a `ordenes` con `on delete cascade`); la RPC `crear_orden` gana `p_procesos` (jsonb con nombre y personalizado) dentro de la misma transacción; borrado de orden borra procesos; CRUD de procesos y borrado de categorías como operaciones directas (23505 → 409; 23503 → 409 para categoría en uso).
- **KB al archivar**: 02 (API), 04 (tablas nuevas), 05 (RN-OR de procesos, RN-PR de borrado de categoría), 06 (US-006/US-007 con procesos, administración por API), 07 (flujos de orden con procesos y borrado de categoría).
