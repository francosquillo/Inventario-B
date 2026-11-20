# Proposal — paso-2-movimientos-stock (C-02)

## Why

Después de C-01 el sistema autentica y lista el inventario, pero el stock solo se puede cargar escribiendo en la base a mano. El taller necesita registrar las entradas de mercadería y las bajas sin orden (rotura, pérdida, consumo interno) para que el inventario refleje la realidad, dejando una bitácora de quién movió qué y cuándo (US-004, US-005), y poder consultar esa bitácora. Es el paso 2 del camino crítico y la base de C-03 (órdenes), que reutiliza el mismo patrón de operación atómica.

## What Changes

- **Ingreso de stock por código** (`POST /api/stock/ingreso`): si el código existe y está activo, suma la cantidad; si existe inactivo (borrado lógico), lo reactiva y suma; si no existe, crea el producto con el `nombre` recibido y esa cantidad. Un código nuevo sin nombre (o con nombre vacío) se rechaza sin crear nada.
- **Egreso manual de stock** (`POST /api/stock/egreso`): descuenta una cantidad entera ≤ stock actual de un producto activo existente; si excede, se rechaza informando el stock disponible y el stock no cambia. El stock nunca queda negativo; con stock 0 el producto sigue existiendo.
- **Código normalizado**: se recortan espacios y se pasa a MAYÚSCULAS (`'rd-6204'` se guarda y se busca como `'RD-6204'`), máximo 50 caracteres; la misma normalización vale para ingreso, egreso y el filtro de movimientos.
- **Cantidad por operación**: entero estricto de 1 a 10.000.
- **Registro en `movimientos`**: cada ingreso o egreso inserta una fila (fecha y hora local de Argentina generada por la aplicación, ISO 8601 con offset fijo `-03:00`, p. ej. `2026-11-19T15:30:00-03:00`; producto; tipo `ingreso`/`egreso`; cantidad; usuario de la sesión), sin motivo. La actualización de stock y el movimiento son atómicos (una transacción SQLite; todo o nada), con el mismo contrato que en C-06 implementará una función RPC de Postgres. El reloj es inyectable para tests deterministas.
- **Consulta de movimientos** (`GET /api/movimientos`): lista la bitácora, más nueva primero, con filtros opcionales `codigo`, `desde` y `hasta` (fechas locales inclusivas `YYYY-MM-DD`); incluye movimientos de productos inactivos. Resuelve la pregunta abierta PA-04. Sin paginación en este paso (PA-08).
- **Doble validación**: Pydantic estricto en la capa HTTP y validación propia en el service (recorte, mayúsculas, campos obligatorios, rango de cantidad, formato y orden de fechas).
- **Errores de validación en español con formato único**: todo 422 (de Pydantic o del dominio) responde `{"detail": "<mensaje en español>"}` (un solo string, el primer error si hay varios) mediante un handler de `RequestValidationError` en `inventario/api/`. Aplica también a `POST /api/login` de C-01. El OpenAPI declara ese formato para 422.
- Los tres endpoints requieren sesión (401 sin sesión) y quedan visibles y ejecutables en `/docs`.
- Sin cambios de DDL: la tabla `movimientos` ya existe desde C-01. Se agrega una normalización idempotente de fechas legadas (filas con `CURRENT_TIMESTAMP` UTC) al inicializar la base.

Fuera de alcance: paginación del listado de movimientos (PA-08), editar el nombre de un producto existente, borrado de productos (C-05), frontend (C-06).

## Capabilities

### New Capabilities

- `movimientos-stock`: ingreso y egreso manual de stock por código interno, alta y reactivación de productos vía ingreso, registro atómico de cada movimiento en la bitácora `movimientos` con fecha local de Argentina, y las reglas de validación de cantidades, códigos y nombres.
- `consulta-movimientos`: lectura de la bitácora de movimientos con filtros por código y rango de fechas locales, orden y datos expuestos.

### Modified Capabilities

- `api-http`: se agregan los endpoints protegidos `POST /api/stock/ingreso`, `POST /api/stock/egreso` y `GET /api/movimientos` con sus códigos de estado (200/401/404/409/422); los errores de validación pasan a `{"detail": "<mensaje en español>"}` en todos los endpoints (se modifica "Rechazo de cuerpos malformados"); la documentación interactiva pasa a listar siete endpoints.

## Impact

- **Código nuevo**: `inventario/domain/tiempo.py` (zona fija `-03:00` y `ahora_argentina`); `inventario/services/normalizacion.py` (`normalizar_codigo`); `inventario/services/stock_service.py` y `inventario/services/movimientos_service.py`; contratos `StockRepository` y `MovimientoRepository` en `inventario/repositories/base.py` y sus implementaciones `SqliteStockRepository` y `SqliteMovimientoRepository` en `inventario/repositories/sqlite_repo.py`; entidades `ResultadoIngreso` y `Movimiento` en `inventario/domain/entities.py`; errores de dominio nuevos en `inventario/domain/errors.py`; `inventario/api/routers/stock.py` y `inventario/api/routers/movimientos.py`; schemas `IngresoRequest`/`EgresoRequest`/`IngresoOut`/`MovimientoOut` en `inventario/api/schemas.py`; `ErrorOut`; dependencias `get_stock_service`/`get_movimientos_service`, handlers de errores de dominio y el handler de `RequestValidationError` con `inventario/api/errores_validacion.py` (mapeo a mensajes en español).
- **Código modificado**: `inicializar_esquema` en `sqlite_repo.py` agrega la normalización idempotente de fechas legadas de `movimientos`; `api/app.py` registra el handler de validación; la ruta de login declara `ErrorOut` para 422.
- **Tests nuevos** (`unittest`, SQLite real): `tests/test_tiempo.py`, `tests/test_errores_validacion.py`, `tests/test_sqlite_stock_repository.py`, `tests/test_sqlite_movimiento_repository.py`, `tests/test_stock_service.py` y `tests/test_movimientos_service.py` sobre `:memory:`; `tests/test_api_stock.py` y `tests/test_api_movimientos.py` con `TestClient` sobre archivo temporal; helpers en `tests/helpers.py`. `tests/test_api_auth.py` (C-01) se extiende para verificar el `detail` en español (hoy solo verifica el status 422, sigue verde).
- **API**: tres endpoints nuevos; los existentes solo cambian el cuerpo de sus 422 (de lista en inglés a texto en español).
- **Dependencias**: ninguna nueva (sin `zoneinfo`/`tzdata`: offset fijo).
- **Base de datos**: sin cambios de DDL; bases locales existentes (p. ej. `prueba.db`) siguen funcionando y sus movimientos legados, si los hubiera, se normalizan al arrancar.
- **C-06 (Supabase)**: `StockRepository` se mapea 1:1 a dos funciones RPC (`registrar_ingreso`, `registrar_egreso`) que reciben la fecha; `MovimientoRepository.listar` a un `select` con JOIN o vista. `movimientos.fecha` pasa a `timestamptz`.
