# Proposal — paso-5d-reporte-ordenes-fechas (C-06d)

## Why

El usuario necesita saber **cuánto de cada producto se usó en órdenes durante un período** (pedido del 2026-11-24): hoy solo puede recorrer `/ordenes` y sumar a mano los componentes de cada orden. Un reporte agregado por producto, filtrable por un solo producto y exportable a PDF, resuelve eso sin tocar el esquema. Se hace después de C-06c porque reutiliza su mecanismo de PDF (`static/js/exportar.js` + `@media print`) y antes de C-07 para que la consulta nueva se migre a Supabase junto con las demás.

Governance **MEDIO**: consulta agregada de solo lectura sobre datos existentes (sin escrituras ni cambios de esquema), con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

- **Endpoint nuevo de solo lectura** `GET /api/reportes/productos-en-ordenes?desde=&hasta=&codigo=` (protegido, 401 sin sesión): devuelve un total por producto con la suma de cantidades de las órdenes cuya fecha cae en el rango **inclusivo** `desde`..`hasta` (`desde` obligatorio; `hasta` opcional, vacío = hoy en hora de Argentina; `AAAA-MM-DD`, fechas reales, `desde <= hasta` efectivo; decisión del usuario 2026-11-24; 422 en español con el formato uniforme de C-06b). Cada fila: código, nombre, si está activo, cantidad total y cantidad de órdenes en que aparece. Orden: cantidad total descendente y, a igual cantidad, código. `codigo` opcional (normalizado como en movimientos) filtra un solo producto; un código sin uso en el rango (o inexistente) devuelve `[]`. Incluye productos dados de baja.
- **Endpoint nuevo de solo lectura** `GET /api/reportes/productos-usados` (protegido): los productos que aparecen en al menos una orden de cualquier fecha (activos y dados de baja), con código, nombre y si está activo, ordenados por código. Alimenta el selector de producto (decisión del usuario 2026-11-24).
- **Agregación en el repositorio** (una consulta `GROUP BY` sobre `ordenes` + `orden_items` + `productos`), con un service que valida fechas y código (reutiliza `services/fechas.py` y `normalizar_codigo`), sin FastAPI fuera de `inventario/api/`.
- **Pantalla nueva `/reportes`** (protegida, redirige a `/` sin sesión) con la pestaña **"Reportes"** en la navegación, junto a Inventario y Órdenes: filtros Desde (obligatorio) y Hasta (opcional), precompletados con el mes en curso (día 1 a hoy) pero **sin generar el reporte hasta pulsar "Generar"** (estado inicial con un cartel neutro), y Producto (todos, o uno de los productos usados en órdenes, en grupos "Activos" y "Dados de baja"; decisiones del usuario 2026-11-24), botón "Generar", tabla Código / Nombre / Cantidad / Órdenes con la marca "dado de baja", línea de resumen "AAAA-MM-DD a AAAA-MM-DD · N productos", estados inicial / cargando / error / vacío ("No hay productos usados en órdenes entre … y …"). Validación de fechas también en el navegador.
- **Exportar el reporte a PDF** con el mecanismo de C-06c: botón "Exportar PDF" (deshabilitado antes de generar y sin filas) que imprime solo la tabla del último reporte generado, con encabezado mínimo "Reporte de productos en órdenes" + una línea "AAAA-MM-DD a AAAA-MM-DD · N productos" (con el `hasta` efectivo) (con el código delante si se filtró por producto) y nombre de archivo sugerido `reporte-AAAA-MM-DD_AAAA-MM-DD` (o `reporte-<codigo>-AAAA-MM-DD_AAAA-MM-DD`). Extensión mínima de `exportar.js`: nombre de archivo explícito (sin la fecha de exportación) admitiendo `_`.
- Sin cambios de esquema ni de las rutas existentes; sin dependencias nuevas.

## Capabilities

### New Capabilities
- `reporte-ordenes`: consulta agregada de productos usados en órdenes por rango de fechas (totales por producto, filtro por un producto, `desde` obligatorio y `hasta` opcional = hoy, orden, inclusión de dados de baja, resultado vacío) y lista de productos usados en alguna orden.

### Modified Capabilities
- `api-http`: endpoints `GET /api/reportes/productos-en-ordenes` (y sus errores) y `GET /api/reportes/productos-usados`; `/reportes` como página protegida; OpenAPI pasa de 13 a 15 rutas `/api/...`.
- `interfaz-web`: pantalla de reportes, pestaña "Reportes" en la navegación de las páginas protegidas, exportación del reporte a PDF.
- `exportacion-pdf`: nombre de archivo sugerido de un reporte por rango (sin la fecha de exportación).

## Impact

- **Backend**: `inventario/domain/entities.py` (entidades de fila del reporte y de producto usado), `inventario/repositories/base.py` + `sqlite_repo.py` (agregación y productos usados), nuevo `inventario/services/reporte_service.py` (con fuente de tiempo inyectable para el `hasta` = hoy), nuevo `inventario/api/routers/reportes.py`, `api/schemas.py`, `api/dependencies.py`, `api/app.py`, `api/routers/paginas.py` (`/reportes`).
- **Frontend**: nuevos `static/reportes.html` y `static/js/reportes.js`; `static/index.html` y `static/ordenes.html` (pestaña "Reportes"); `static/js/exportar.js` (nombre explícito); `static/css/app.css` (solo si hace falta una regla de impresión del modo `reporte`).
- **Tests** (`unittest`, SQLite real): repositorio, service, API con `TestClient`, páginas, OpenAPI (15 rutas), guardas estáticas del frontend y funciones puras de JS con Node.
- **C-07**: la agregación debe replicarse en Supabase (funciones RPC `productos_en_ordenes(p_desde, p_hasta, p_codigo)` y `productos_usados()`; PostgREST no agrega con `GROUP BY` sin RPC). El `hasta` = hoy se resuelve en el service, no en SQL.
- **KB al archivar**: 06 (US-014 Reporte de productos en órdenes) y 07 (flujo del reporte y su exportación).
