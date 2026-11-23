# Proposal — paso-5b-fixes-menores (C-06b)

## Why

Usando la web local de C-06, el usuario encontró que los modales "Ingreso de stock" y "Egreso de stock" no se ajustan a cómo trabaja el taller: el ingreso mezcla dar de alta un producto con sumar unidades (el nombre es "a veces obligatorio" y lo decide el backend), el egreso solo resta de a un producto y no hay forma de **corregir** un stock contado a mano ni de renombrar un producto o recuperar uno dado de baja sin pasar por un ingreso. Tampoco se puede crear un producto con stock 0 (por ejemplo, para cargarlo antes de que llegue). Se resuelve ahora, antes de migrar a Supabase (C-07), para que la migración nazca con el modelo de datos definitivo (tipo de movimiento `ajuste`).

Governance **MEDIO/ALTO**: lógica de negocio de stock (MEDIO) más una migración de esquema que reconstruye la tabla `movimientos` de bases existentes (ALTO: toca datos del usuario).

## What Changes

- **"Nuevo ingreso"** (reemplaza a "Ingreso de stock" en la web): alta de producto con **Código, Nombre y Stock, los tres obligatorios**; el stock inicial puede ser **0**. Endpoint nuevo `POST /api/productos`.
  - Código de un producto **activo** → 409 "Ya existe un producto con código 'X'.".
  - Código de un producto **dado de baja** → se reactiva con el nombre y el stock nuevos (el stock reemplaza al conservado).
  - El alta con stock > 0 registra un movimiento `ingreso`; con stock 0 no registra movimiento; la reactivación que cambia el stock registra un `ajuste`.
- **"Modificar stock"** (reemplaza a "Egreso de stock" en la web): modal multi-línea como "Nueva orden". Por línea, el usuario elige un producto y:
  - **"Fijar en"**: el stock nuevo absoluto (entero 0..10.000) → movimiento de tipo nuevo **`ajuste`** con el stock anterior y el nuevo; o
  - **"Sumar"**: una cantidad entera 1..10.000 que se suma → movimiento `ingreso`;
  - y, **opcionalmente, un nombre nuevo** (sin movimiento).
  - El selector ofrece también los productos **dados de baja** (marcados); modificarlos los **reactiva** dentro de la misma operación y el resumen lo indica ("reactivado").
  - Todo o nada (transacción): si una línea falla, no se aplica ninguna y las líneas con error se marcan (como los 404/409/422 por línea de la nueva orden). Un mismo producto no puede repetirse en un lote. Hasta 100 líneas.
  - Endpoints nuevos `POST /api/stock/modificaciones` y `GET /api/productos/inactivos` (para el selector).
- **Bitácora**: `movimientos.tipo` admite `ajuste`; columnas nuevas `stock_anterior` y `stock_nuevo` (solo en `ajuste`). `GET /api/movimientos` agrega esos dos campos (null en ingresos y egresos) — cambio **aditivo** en la respuesta.
- **Migración SQLite** idempotente al arrancar: las bases existentes (p. ej. `dev-local.db`) reconstruyen `movimientos` dentro de una transacción conservando todas las filas e ids.
- **Regla de cantidades**: "cantidad > 0" se relaja **solo** para el stock inicial del alta y el stock fijado por un ajuste (>= 0). Ingreso, egreso, "Sumar" y órdenes siguen exigiendo 1..10.000.
- `POST /api/stock/ingreso` y `POST /api/stock/egreso` **siguen en la API** (y sus tests, sin cambios) pero la web deja de usarlos. Las órdenes no cambian.

Fuera de alcance: UI de movimientos (sigue fuera de v1), control de concurrencia optimista en "Fijar en" (ver design, Riesgos), auditoría de cambios de nombre, paridad Postgres (se implementa en C-07; aquí solo se documenta).

## Capabilities

### New Capabilities

- `alta-productos`: alta explícita de un producto con código, nombre y stock inicial (>= 0), rechazo de códigos activos repetidos y reactivación de códigos dados de baja con nombre y stock nuevos.
- `modificacion-stock`: modificación de stock en lote (fijar en un valor absoluto o sumar), cambio opcional de nombre, reactivación de productos dados de baja, registro como `ajuste`/`ingreso` y atomicidad del lote.

### Modified Capabilities

- `consulta-movimientos`: cada movimiento incluye el tipo `ajuste` y, para él, el stock anterior y el nuevo.
- `inicializacion-base-datos`: el esquema admite el tipo `ajuste` con sus columnas y migra de forma idempotente las bases creadas antes de este change.
- `api-http`: endpoints `POST /api/productos`, `POST /api/stock/modificaciones` y `GET /api/productos/inactivos`; `GET /api/movimientos` agrega `stock_anterior` y `stock_nuevo`.
- `interfaz-web`: se quitan los modales "Ingreso de stock" y "Egreso de stock"; se agregan "Nuevo ingreso" y "Modificar stock"; cambian la barra de acciones, el cartel de inventario vacío, la validación del navegador y el ejemplo de teclado de los modales.

## Impact

- **Backend**: `domain/entities.py` y `domain/errors.py` (resultados de alta/modificación, `ProductoDuplicado`); `services/stock_service.py` (alta y modificación, validación de líneas); `repositories/base.py` y `sqlite_repo.py` (esquema, migración, alta, modificación atómica, listado de inactivos, consulta de movimientos con las columnas nuevas); `api/schemas.py`, `api/errores_validacion.py` ("Línea N: …"), `api/routers/productos.py` y `stock.py`, handler 409 en `app.py`. FastAPI sigue fuera de `domain/`, `services/` y `repositories/`.
- **Frontend**: `static/index.html`, `static/js/inventario.js` y `static/js/validacion.js` (dos modales nuevos, sin `innerHTML`); `ordenes.js` sin cambios.
- **Tests** (`unittest`, SQLite real): servicio, repositorio, migración sobre una base con el esquema viejo, endpoints con `TestClient`, guardas estáticas del frontend. Los tests existentes de ingreso/egreso no cambian; los de OpenAPI suman los paths nuevos.
- **Sin dependencias nuevas.**
- **Datos**: migración de `movimientos` en bases existentes (con respaldo recomendado de `dev-local.db` antes del primer arranque).
- **Documentación al archivar**: KB 04 (tipo `ajuste`, columnas, stock inicial 0), 05 (RN de cantidades, alta, ajuste, reactivación por modificación), 06 (US-004/US-005 reescritas: Nuevo ingreso / Modificar stock), 07 (flujos de alta y modificación). C-07 hereda la paridad Postgres (anotado en `CHANGES.md`).
