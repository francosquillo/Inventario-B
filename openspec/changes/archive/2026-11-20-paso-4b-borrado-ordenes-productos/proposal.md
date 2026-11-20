# Proposal — paso-4b-borrado-ordenes-productos (C-05)

## Why

Desde C-03/C-04 el taller carga y consulta órdenes, pero una orden cargada por error no se puede corregir (RN-OR-10: no hay edición) y un producto que ya no se usa no se puede sacar del inventario. US-008 y US-009 piden borrar una orden (decidiendo cada vez si se reintegra el stock) y dar de baja un producto. Es el último paso de la Fase 1 y deja completa la API que C-06 conecta al frontend (modales de borrado) y migra a Supabase.

Governance **ALTO**: el borrado de una orden es físico e irreversible y el reintegro modifica stock de varios productos a la vez.

## What Changes

- **Borrado de orden** (`DELETE /api/ordenes/{numero}?reintegrar=true|false`, requiere sesión; US-008). El borrado es **por número de orden, no por id** (decisión 1 del usuario, 2026-11-20): el número es único, se normaliza como en el alta (recorte + MAYÚSCULAS), la ruta acepta números con `/` y los clientes codifican `?` y `#`:
  - `reintegrar` es obligatorio y explícito en cada llamada, sin valor por defecto (RN-OR-08, RN-VA-05, IN-02); ausente o inválido → 422 en español sin tocar nada.
  - `reintegrar=true`: suma a cada producto la cantidad de su línea, reactiva los productos dados de baja (RN-OR-12, SU-06) y borra la orden y sus líneas, todo en una única transacción (RN-OR-09).
  - `reintegrar=false`: borra solo la orden y sus líneas; el stock no cambia.
  - Ni el reintegro ni el borrado escriben en `movimientos` (DD-09, RN-ST-06).
  - Respuesta 200 con la orden tal como era y el detalle del reintegro por producto (stock final y si se reactivó); número en blanco o de más de 30 caracteres → 422; número inexistente → 404 "No existe una orden con número 'X'." (el mensaje de C-04). Dos borrados simultáneos de la misma orden: uno gana y el otro recibe 404 (el stock se reintegra una sola vez).
- **Baja de producto** (`DELETE /api/productos/{codigo}`, requiere sesión; US-009):
  - Borrado lógico (`activo = 0`, RN-PR-03): conserva stock, historial de movimientos y órdenes; código normalizado (recorte + MAYÚSCULAS) como en el resto de la API.
  - Sale del inventario y de la selección de componentes; las órdenes históricas lo siguen mostrando (RN-PR-04); un ingreso posterior lo reactiva sumando al stock conservado (RN-PR-06, ya implementado en C-02).
  - Inexistente o ya inactivo → 404 con el mensaje existente "No existe un producto activo con código 'X'.". Sin fila en `movimientos`.
- Ambos endpoints visibles y ejecutables en `/docs`; la confirmación previa (modal) es del frontend de C-06.
- Las 10 decisiones de `design.md` fueron revisadas por el usuario el 2026-11-20 (borrado por número; casilla "Devolver stock" marcada por defecto en C-06; el resto aprobado) y están reflejadas en specs y tareas.

Fuera de alcance: modales de confirmación y UI (C-06), funciones RPC de Postgres `borrar_orden`/`baja_producto` (C-06), edición de órdenes (RN-OR-10), borrado físico de productos, papelera o deshacer, auditoría de borrados.

## Capabilities

### New Capabilities

- `baja-productos`: baja lógica de productos: qué cambia (`activo`), qué se conserva (stock, movimientos, órdenes), efectos sobre inventario y nuevas órdenes, rechazos y concurrencia. Separada de `movimientos-stock` (que ya posee la reactivación por ingreso) porque no mueve stock.

### Modified Capabilities

- `ordenes-trabajo`: se agregan los requisitos de borrado de orden: con y sin reintegro, reactivación de productos al reintegrar, atomicidad y concurrencia, reintegro fuera de la bitácora, decisión explícita de reintegro y orden inexistente.
- `api-http`: se agregan `DELETE /api/ordenes/{numero}` y `DELETE /api/productos/{codigo}` con sus respuestas (200/401/404/422); la documentación interactiva pasa de ocho a diez rutas; el rechazo de sesiones de usuarios inexistentes y el formato del 422/404 en OpenAPI se extienden a los dos endpoints nuevos.

## Impact

- **Código nuevo**:
  - `OrdenRepository.borrar(numero, reintegrar)` (contrato en `repositories/base.py`, implementación en `SqliteOrdenRepository` dentro de `_transaccion`).
  - `ProductoRepository.dar_de_baja(codigo)` (contrato e implementación en `SqliteProductoRepository`).
  - `OrdenService.borrar(numero, reintegrar)` (reutiliza `_normalizar_numero` y `OrdenNoEncontrada`) y un `ProductoService` nuevo (`services/producto_service.py`).
  - Entidades de resultado del borrado (`domain/entities.py`) sin errores de dominio nuevos.
  - `DELETE /{numero:path}` en `api/routers/ordenes.py` y un router nuevo `api/routers/productos.py`, con sus schemas de respuesta en `api/schemas.py`; los handlers en `api/app.py`.
- **Tests** (`unittest`, SQLite real, sin mocks):
  - repositorios en `:memory:`; la atomicidad se prueba forzando fallas reales con un trigger temporal y con una fila de producto faltante;
  - concurrencia con archivo temporal e hilos;
  - API con `TestClient`;
  - se extienden `test_api_sesion_inexistente` y los tests de OpenAPI.
- **API**: dos rutas nuevas; los endpoints existentes no cambian de contrato.
- **Dependencias**: ninguna nueva.
- **Base de datos**: sin DDL (el borrado por número hace innecesario migrar `ordenes.id` a `AUTOINCREMENT`).
- **C-06**: los dos métodos de repositorio se reemplazan 1:1 por funciones RPC (`borrar_orden(p_numero, p_reintegrar)` y la baja, un `update` simple), sin tocar services ni API. El modal de borrado de orden de C-06 lleva la casilla "Devolver stock" marcada por defecto (decisión 2).
- **KB**: al archivar, actualizar en `02_descripcion_general.md` la tabla de endpoints (dice `DELETE /api/productos/<id>` y `GET /api/productos`; lo real es `{codigo}` y `/api/inventario`), el Flujo 6 (ítems borrados explícitamente, respuesta) y US-008/US-009 (marcar criterios). No se edita la KB en este change.
