# Proposal — paso-4-listado-ordenes (C-04)

## Why

Desde C-03 el taller puede cargar órdenes de trabajo, pero no tiene forma de consultarlas: la única evidencia de una orden es la respuesta 201 del alta. US-007 pide listar el historial completo, por rango de fechas o buscar una orden por su número. Es el paso 4 del camino crítico y la base de C-05 (borrado de órdenes, que necesita poder ubicar la orden a borrar) y de la pantalla de órdenes de C-06.

## What Changes

- **Listado de órdenes** (`GET /api/ordenes`, requiere sesión): sin filtros devuelve todas las órdenes, de la más nueva a la más vieja según la fecha de la orden (la fecha ingresada a mano, DD-08, no `created_at`) y, ante igual fecha, la última cargada primero.
- **Filtro por rango de fechas** (RN-OR-07, SU-02): `desde` y `hasta` (`YYYY-MM-DD`) inclusivos en ambos extremos; `desde == hasta` busca un solo día. Cada uno es opcional por separado (rango abierto) y un parámetro vacío equivale a no filtrar, igual que `GET /api/movimientos` en C-02 (decisión 2, aprobada 2026-11-20).
- **Validación de fechas** (RN-VA-03): fecha con formato inválido, fecha inexistente (`2026-02-30`) o `desde` posterior a `hasta` → 422 con exactamente los mismos mensajes que la consulta de movimientos.
- **Búsqueda por número** (RN-OR-01): parámetro `numero` en el mismo listado, normalizado igual que en el alta (recorte + MAYÚSCULAS), coincidencia exacta, combinable con las fechas; si ese número no existe responde 404 "No existe una orden con número 'X'." (con X normalizado; si existe pero queda fuera del rango de fechas devuelve `[]`; decisión 1 con ajuste del usuario, 2026-11-20; se descartó `GET /api/ordenes/{numero}` para no chocar con `DELETE /api/ordenes/{id}` de C-05).
- **Detalle de componentes** por orden con la misma forma que la respuesta 201 del alta (`id`, `numero`, `fecha`, `usuario`, `componentes: [{codigo, nombre, cantidad}]` ordenados por código), incluyendo los productos dados de baja (RN-PR-04).
- **Lista sin envolver y sin paginar** en v1, como `/api/inventario` y `/api/movimientos`.
- El endpoint queda visible y ejecutable en `/docs`.

Fuera de alcance: borrado de órdenes y de productos (C-05), edición de órdenes (RN-OR-10, no existe en v1), frontend y paginación (C-06, PA-08), migración a Supabase (C-06). Sin cambios de DDL: el índice sobre `ordenes.fecha` existe desde C-01.

## Capabilities

### New Capabilities

- `consulta-ordenes`: consulta de lectura del historial de órdenes de trabajo: listado ordenado, filtros por rango de fechas de la orden y por número, validación de los filtros y detalle de componentes incluyendo productos inactivos. Es la capability de lectura anunciada en C-03, separada de `ordenes-trabajo` (escritura) igual que `consulta-movimientos` lo está de `movimientos-stock`.

### Modified Capabilities

- `api-http`: se agrega `GET /api/ordenes` con sus respuestas (200/401/404/422); la documentación interactiva incluye el listado de órdenes; el formato del 422 en OpenAPI y el rechazo de sesiones de usuarios inexistentes se extienden al listado.

## Impact

- **Código nuevo**: método `OrdenService.listar(numero, desde, hasta)` en `inventario/services/orden_service.py`; contrato `OrdenRepository.listar` en `inventario/repositories/base.py` y su implementación en `SqliteOrdenRepository` (`inventario/repositories/sqlite_repo.py`), con una sola consulta con JOIN; endpoint `GET ""` en `inventario/api/routers/ordenes.py`.
- **Código modificado (refactor sin cambio de comportamiento)**: la validación de filtros de fecha de `services/movimientos_service.py` (parseo con nombre del parámetro, vacío = sin filtro y chequeo `desde ≤ hasta`) pasa a `services/fechas.py` para que órdenes y movimientos compartan los mensajes exactos; la normalización del número se reutiliza del alta.
- **Tests** (`unittest`, SQLite real, sin mocks): se extienden `tests/test_sqlite_orden_repository.py`, `tests/test_orden_service.py`, `tests/test_fechas.py`, `tests/test_api_ordenes.py`, `tests/test_api_sesion_inexistente.py` y el test de OpenAPI.
- **API**: un método nuevo sobre la ruta existente `/api/ordenes`; los endpoints existentes no cambian. El esquema OpenAPI sigue con ocho rutas.
- **Dependencias**: ninguna nueva. **Base de datos**: sin DDL.
- **C-05**: el listado devuelve el `id` de cada orden, que es lo que necesita `DELETE /api/ordenes/{id}` (Flujo 6).
- **C-06 (Supabase)**: `OrdenRepository.listar` se mapea a un `select` con relaciones embebidas (`ordenes` → `orden_items` → `productos`) o a una vista/RPC de lectura, sin tocar el service.
- **KB**: al archivar, actualizar RN-OR-07 y el Flujo 5 con rangos abiertos y búsqueda por número, y la tabla de endpoints de `02_descripcion_general.md` según la decisión 1 (no se edita la KB en este change).
