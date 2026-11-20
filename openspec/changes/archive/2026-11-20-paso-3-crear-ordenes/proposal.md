# Proposal — paso-3-crear-ordenes (C-03)

## Why

Después de C-02 el taller puede cargar y dar de baja stock a mano, pero el uso principal del sistema es descontar los componentes que consume cada orden de trabajo. Hoy eso obligaría a hacer un egreso por pieza, sin atomicidad entre piezas y sin dejar constancia de la orden (US-006). Es el paso 3 del camino crítico y la base de C-04 (listado de órdenes) y C-05 (borrado con reintegro).

## What Changes

- **Alta de orden** (`POST /api/ordenes`, requiere sesión): recibe `numero`, `fecha` (`YYYY-MM-DD`, ingresada a mano, DD-08) y `componentes` (lista de `{codigo, cantidad}`), y crea la orden con el usuario de la sesión.
- **Número de orden único** (RN-OR-01): texto alfanumérico normalizado (recorte + MAYÚSCULAS, longitud acotada); un número repetido se rechaza sin modificar nada. Resuelve la pregunta abierta PA-06 (tipo del número), confirmado por el usuario el 2026-11-20.
- **Componentes válidos** (RN-OR-03, RN-OR-06): al menos un componente; cada uno es un producto activo existente (código normalizado igual que en C-02) con cantidad entera de 1 a 10.000. Los productos inexistentes o inactivos se rechazan informando todos los códigos.
- **Consolidación** (RN-OR-11): las líneas repetidas del mismo producto se suman en una sola línea antes de validar el stock; el tope de 10.000 rige por línea; el total consolidado por producto no tiene tope y solo lo limita el stock.
- **Todo o nada** (RN-OR-04, RN-OR-05): se valida el stock de TODOS los componentes; si alguno no alcanza, se rechaza la orden completa informando cada faltante (código, disponible, solicitado) y no se modifica nada. Si alcanza, en una única transacción se inserta la orden, se insertan sus `orden_items` y se descuenta el stock de cada producto.
- **Sin bitácora** (RN-ST-06): los descuentos por orden NO generan filas en `movimientos`; quedan reflejados en `orden_items`.
- **Errores en español con el formato de C-02**: 422 de validación con `{"detail": "<texto>"}`; 404 por productos inexistentes/inactivos; 409 por número duplicado y por stock insuficiente (este último con la lista estructurada de faltantes además del texto).
- **Endurecimiento de la transacción SQLite** (sugerencia S-2 del verify de C-02): la unidad de trabajo atómica deja de confirmar en silencio trabajo pendiente de la conexión (a confirmar por el usuario).
- El endpoint queda visible y ejecutable en `/docs`.

Fuera de alcance: listado y búsqueda de órdenes (`GET /api/ordenes`, C-04), borrado de órdenes y reintegro (C-05), edición de órdenes (RN-OR-10, no existe en v1), frontend (C-06). Sin cambios de DDL: `ordenes` y `orden_items` existen desde C-01.

## Capabilities

### New Capabilities

- `ordenes-trabajo`: ciclo de vida de escritura de las órdenes de trabajo: alta con número único, fecha manual y componentes, consolidación de líneas, validación de stock de todos los componentes y descuento atómico, sin registro en `movimientos`. C-05 agregará el borrado con o sin reintegro; la consulta (C-04) irá en una capability de lectura aparte, igual que `consulta-movimientos`.

### Modified Capabilities

- `api-http`: se agrega el endpoint protegido `POST /api/ordenes` con sus códigos (201/401/404/409/422); la documentación interactiva pasa a listar ocho endpoints; los mensajes de validación uniformes y el formato del 422 en OpenAPI se extienden a los campos y a la ruta de órdenes.

## Impact

- **Código nuevo**: entidades `Orden`, `ItemOrden` y `Faltante` en `inventario/domain/entities.py`; errores `OrdenDuplicada`, `ProductosNoEncontrados` y `StockInsuficienteOrden` en `inventario/domain/errors.py`; contrato `OrdenRepository` en `inventario/repositories/base.py` y `SqliteOrdenRepository` en `inventario/repositories/sqlite_repo.py`; `inventario/services/orden_service.py`; validación de fechas compartida extraída a `inventario/services/fechas.py`; `inventario/api/routers/ordenes.py`; schemas `OrdenRequest`, `ComponenteRequest`, `OrdenOut`, `StockInsuficienteOut` en `inventario/api/schemas.py`; dependencia `get_orden_service`.
- **Código modificado**: `_transaccion` en `sqlite_repo.py` (S-2); `api/app.py` (router y handlers nuevos); `api/errores_validacion.py` (campos `numero`, `fecha`, `componentes` y prefijo de línea); `services/movimientos_service.py` pasa a usar `services/fechas.py` sin cambiar sus mensajes; `tests/helpers.py` (helpers de órdenes y, según la decisión S-2, `commit` en los helpers de siembra).
- **Tests nuevos** (`unittest`, SQLite real, sin mocks): `tests/test_sqlite_orden_repository.py` (`:memory:` + clase de concurrencia sobre archivo temporal), `tests/test_orden_service.py`, `tests/test_fechas.py`, `tests/test_api_ordenes.py` (`TestClient`); se extienden `tests/test_domain.py`, `tests/test_errores_validacion.py` y `tests/test_api_app.py`/OpenAPI.
- **API**: un endpoint nuevo; los existentes no cambian.
- **Dependencias**: ninguna nueva.
- **Base de datos**: sin DDL; bases locales existentes siguen sirviendo.
- **C-06 (Supabase)**: `OrdenRepository.crear` se mapea 1:1 a una función RPC `crear_orden(...)` con `SELECT ... FOR UPDATE` y `RAISE` con SQLSTATE propios traducidos a los mismos errores de dominio.
- **KB**: al archivar, PA-06 queda resuelta (actualización de `knowledge-base/10_preguntas_abiertas.md` y `04_modelo_de_datos.md` aparte; no se edita la KB en este change).
