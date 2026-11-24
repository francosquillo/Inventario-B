# Proposal — paso-5e-categorias-productos (C-06e)

## Why

El usuario quiere **agrupar los productos por categoría** (pedido del 2026-11-24) para encontrar rápido las piezas de un mismo tipo en el inventario y al armar una orden: hoy solo hay código y nombre, y el buscador de C-06c obliga a adivinar texto. Se arranca con tres categorías de ejemplo: **motor, aceite y filtro**. Va después de C-06d y antes de C-06f/C-07 porque es el primer change de esta tanda que **cambia el esquema** (más simple que la tabla nueva de C-06f) y conviene que la columna nueva viaje a Supabase junto con el resto en C-07.

Governance **MEDIO/ALTO**: migración de esquema al arrancar sobre datos existentes (`dev-local.db` debe conservar todos sus productos, órdenes y movimientos), con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

- **Catálogo de categorías** (tabla nueva `categorias`, ampliable): cada categoría tiene una clave estable en minúsculas (`motor`, `aceite`, `filtro`) y un nombre para mostrar (`Motor`, `Aceite`, `Filtro`). Se siembran al crear el catálogo (solo si está vacío, idempotente). **Administración solo por API** (decisión del usuario, 2026-11-24): se pueden crear y renombrar categorías desde `/docs`, sin pantalla en la web; la clave es inmutable.
- **Categoría por producto, opcional**: `productos` gana una referencia a la categoría que puede quedar vacía (= "Sin categoría"). Los productos existentes quedan "Sin categoría" (no hay dato del que inferirla).
- **Migración idempotente al arrancar**: si `productos` no tiene la columna de categoría, se agrega con `ALTER TABLE ... ADD COLUMN` (sin reconstruir la tabla, que es referenciada por `orden_items` y `movimientos`) en una transacción; las filas existentes se conservan intactas. Arranques siguientes no tocan nada. Backup previo de `dev-local.db` documentado en el README.
- **API**:
  - Endpoint nuevo `GET /api/categorias` (protegido): lista `{clave, nombre}` ordenada por nombre.
  - Endpoints nuevos de administración (protegidos, solo cuerpo JSON como los demás): `POST /api/categorias` `{nombre, clave?}` → 201 (clave derivada del nombre si falta; 409 por clave o nombre repetidos) y `PATCH /api/categorias/{clave}` `{nombre}` → 200 (solo renombra; 404 si no existe; 409 si el nombre es de otra). Sin borrado (sub-decisión abierta en design).
  - `GET /api/reportes/productos-en-ordenes` agrega `categoria` (clave o `null`) a cada fila, sin filtro de categoría.
  - `GET /api/inventario`, `GET /api/productos/inactivos` y las demás respuestas de producto incluyen `categoria` (clave o `null`).
  - `POST /api/productos` acepta `categoria` opcional (clave, sin distinguir mayúsculas; ausente o `null` = sin categoría); la reactivación de un dado de baja reemplaza también la categoría. Categoría inexistente → 422 "La categoría 'x' no existe.".
  - `POST /api/stock/modificaciones`: cada línea acepta `categoria` opcional (ausente = no cambia; `null` = quitar; clave = asignar); la respuesta agrega `categoria` y `categoria_anterior` por línea. Cambiar solo la categoría no registra movimientos ni reactiva un dado de baja.
  - OpenAPI pasa de 15 a 17 rutas `/api/...` (`/api/categorias` y `/api/categorias/{clave}`).
- **Web `/inventario`**:
  - Columna "Categoría" en la tabla (nombre o "Sin categoría").
  - Filtro "Categoría" (`<select>`: Todas las categorías, cada categoría, Sin categoría) junto al buscador, **combinable** con la búsqueda de C-06c (ambos a la vez), sin llamar a la API; el conteo dice "V de T productos" con cualquier filtro activo; cartel sin coincidencias con "Limpiar filtros"; el filtro se conserva al recargar tras una acción.
  - "Exportar PDF" exporta exactamente lo visible (búsqueda + categoría), con la columna Categoría y el nombre de la categoría filtrada en la línea del encabezado.
  - "Nuevo ingreso": selector "Categoría" (por defecto "Sin categoría").
  - "Modificar stock": selector de categoría por línea, precargado con la categoría actual del producto (activos y dados de baja); el resumen muestra el cambio de categoría.
  - **"Nueva orden"** (decisión del usuario, 2026-11-24): en cada línea de componente el selector de producto permite **elegir entre todos los productos o filtrarlos por categoría** (selector de categoría por línea, "Todas" por defecto).
- **Web `/reportes`** (decisión del usuario, 2026-11-24): columna "Categoría" en la tabla y en el PDF del reporte (Código, Nombre, Categoría, Cantidad, Órdenes), sin filtro de categoría.
- **Sin cambios** en órdenes (backend), `/ordenes`, el PDF de una orden ni el endpoint legado `POST /api/stock/ingreso` (crea productos sin categoría). Sin dependencias nuevas.

## Capabilities

### New Capabilities
- `categorias-productos`: catálogo de categorías (clave + nombre, sembrado con motor/aceite/filtro), alta y renombre de categorías (clave derivada e inmutable, unicidad de clave y nombre), categoría opcional por producto, normalización de la clave y listado de categorías.

### Modified Capabilities
- `inicializacion-base-datos`: el esquema incluye `categorias` y la categoría de `productos`; migración idempotente de `productos` existentes y siembra de las categorías.
- `consulta-inventario`: el listado de activos incluye la categoría de cada producto.
- `alta-productos`: categoría opcional en el alta; la reactivación reemplaza la categoría.
- `modificacion-stock`: cambio opcional de categoría por línea (sin movimiento ni reactivación por sí solo); "línea sin cambios" contempla la categoría.
- `api-http`: `GET`/`POST /api/categorias` y `PATCH /api/categorias/{clave}` (y sus errores, solo cuerpo JSON); `categoria` en respuestas de producto, en el reporte y en los cuerpos de alta y modificación; errores 422 de categoría; OpenAPI con 17 rutas.
- `reporte-ordenes`: cada fila del reporte incluye la categoría actual del producto.
- `interfaz-web`: columna y filtro de categoría en el inventario (combinado con el buscador, conteo, sin coincidencias, recarga, PDF); categoría en "Nuevo ingreso" y "Modificar stock"; filtro por categoría en el selector de producto de "Nueva orden"; columna Categoría en la tabla y el PDF de `/reportes`.

## Impact

- **Backend**: `inventario/repositories/sqlite_repo.py` (DDL de `categorias` y columna nueva, migración `_migrar_productos_categoria` + siembra, lecturas/escrituras con categoría), `repositories/base.py` (`CategoriaRepository`), `domain/entities.py` (`Categoria`; `categoria` en `Producto`, `LineaModificacion`, `ResultadoModificacion`), `domain/errors.py` (`CategoriaInexistente` o `DatosInvalidos`), `services/stock_service.py` (normalización y validación de la categoría), servicio nuevo `services/categoria_service.py` (listar, crear, renombrar), `domain/errors.py` (`CategoriaDuplicada` 409, `CategoriaNoEncontrada` 404), reporte (`ProductoEnOrdenes.categoria` y su SQL), `api/schemas.py`, `api/dependencies.py`, router nuevo `api/routers/categorias.py`, `api/app.py`.
- **Frontend**: `static/index.html`, `static/js/inventario.js`, `static/js/busqueda.js` (filtro combinado, puro), `static/reportes.html` + `static/js/reportes.js` (columna Categoría), `static/css/app.css` (solo si hace falta: columna en impresión/móvil).
- **Tests** (`unittest`, SQLite real `:memory:` y archivo temporal para la migración): migración desde el DDL viejo copiado literal, repositorios, services, API con `TestClient`, OpenAPI (17 rutas), administración de categorías, reporte con categoría, guardas estáticas y JS puro con Node.
- **Datos**: `dev-local.db` se migra al primer arranque (columna nueva vacía para todos los productos; nada se borra). Verify sobre una **copia**.
- **C-07**: tabla `categorias` (clave única, índice único sobre `lower(nombre)`) y `productos.categoria_id` (FK nullable) en Postgres con la misma siembra; alta/renombre de categorías como operaciones directas de una fila (violación de unicidad → 409); las RPC de alta y modificación de productos aceptan la categoría; la RPC del reporte devuelve la categoría; RLS igual que `productos`.
- **KB al archivar**: 04 (tabla `categorias`, columna nueva), 05 (reglas RN-PR de categoría y de administración del catálogo), 06 (US-004/US-005 y US-006 con categoría, reporte con columna Categoría, administración por API), 07 (flujos con filtro y categoría).
