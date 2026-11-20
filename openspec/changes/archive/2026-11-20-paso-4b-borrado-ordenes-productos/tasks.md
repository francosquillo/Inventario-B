# Tasks

> **Governance ALTO.** El usuario revisó las 10 decisiones de `design.md` el 2026-11-20 (borrado de orden **por número**, no por id; el resto aprobado). Estas tareas ya reflejan esa revisión; no hay decisiones pendientes antes del apply.
>
> **Strict TDD**: en cada comportamiento, RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo se escribe y se ejecuta primero; si pasa sin cambios de código, anotar por qué) → REFACTOR (tests verdes tras cada paso).
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - FastAPI/Pydantic solo en `inventario/api/` (Regla dura 1).
> - Sin mocks de base: `:memory:` en repos y services; archivo temporal en API y concurrencia (Regla dura 4). Las fallas se fuerzan con SQLite real: triggers `TEMP` o filas huérfanas con `PRAGMA foreign_keys = OFF`.
> - Sin dependencias nuevas ni DDL.
> - Sin commits (Regla dura 6).
>
> Cada escritura debe ir dentro de su propio `_transaccion` (`BEGIN IMMEDIATE`). Ningún test puede dejar `conn.in_transaction` en `True`.

## 0. Red de seguridad

- [x] 0.1 Correr la suite completa antes de tocar nada y anotar el baseline (`Ran N tests ... OK`, esperado 348); si algo falla, detenerse y reportarlo como falla preexistente

## 1. Dominio: entidades (design D1)

- [x] 1.1 RED: en `tests/test_domain.py`, `Reintegro` y `ResultadoBorradoOrden` son frozen (asignar un campo lanza `FrozenInstanceError`) y exponen sus campos; verificar que falla por `ImportError`. No se crea ningún error nuevo: el borrado reutiliza `OrdenNoEncontrada` (C-04)
- [x] 1.2 GREEN: agregar `Reintegro`/`ResultadoBorradoOrden` en `domain/entities.py`; verificar verde

## 2. Repositorio: `OrdenRepository.borrar` — spec `ordenes-trabajo` (design D2)

En `tests/test_sqlite_orden_repository.py` (`:memory:`). La siembra se hace con `crear` (`A-01` stock 5 → orden x2 deja 3; `B-02` stock 5 → orden x5 deja 0).

- [x] 2.1 RED: `borrar("OT-0001", False)` → devuelve `ResultadoBorradoOrden` con la `Orden` previa (con su `id`), `reintegrado=False` y `reintegros=()`; ya no hay filas en `ordenes` ni en `orden_items` para ese id; el stock de `A-01` sigue en 3. Verificar que falla (`AttributeError`)
- [x] 2.2 GREEN: declarar `borrar` en `OrdenRepository` (`repositories/base.py`, docstring de D1) e implementar en `SqliteOrdenRepository` el camino sin reintegro dentro de `_transaccion`: buscar la orden por número, `DELETE` explícito (con el id leído) de ítems y orden, `rowcount == 1`. Agregar `_buscar_orden_por_numero` (devuelve `None` si no existe) con `_SQL_LISTAR_ORDENES + " WHERE o.numero = ?"`; `_leer_orden` por id no cambia. Verificar verde junto con los tests de alta y listado
- [x] 2.3 RED→GREEN reintegro: `borrar("OT-0001", True)` con `A-01` x2 y `B-02` x5 → stock 5 y 5, orden y líneas eliminadas, `reintegrado=True`, `reintegros` = `(A-01, Tornillo, 2, 5, False)`, `(B-02, ..., 5, 5, False)` ordenados por código. Verificar rojo y luego verde (reutilizando `_SQL_SUMAR_Y_ACTIVAR`)
- [x] 2.4 TRIANGULATE reactivación: `C-99` dado de baja (`UPDATE activo = 0`) con stock 1 y orden `C-99` x4 → con `True`, `C-99` queda activo, stock 5 y `reactivado=True`, y aparece en `SqliteProductoRepository.listar_activos()`; con `False` (otra orden igual) sigue inactivo con stock 1. Verificar
- [x] 2.5 TRIANGULATE aislamiento: con `OT-0001` y `OT-0002` sobre `A-01`, borrar `OT-0001` con reintegro solo devuelve su cantidad, y `OT-0002` sigue en `listar` con sus líneas. Verificar
- [x] 2.6 RED→GREEN inexistente: `borrar("OT-0999", True)` y `borrar("OT-0999", False)` → `OrdenNoEncontrada` ("No existe una orden con número 'OT-0999'."); borrar dos veces el mismo número → la segunda lanza `OrdenNoEncontrada` y el stock se reintegró una sola vez; en ningún caso queda `conn.in_transaction`. Verificar
- [x] 2.6b TRIANGULATE número con `/`: con la orden `OT/2026/01` y otra `OT-0001`, `borrar("OT/2026/01", True)` borra solo esa y `OT-0001` sigue. Verificar
- [x] 2.7 TRIANGULATE bitácora: con un movimiento de ingreso previo, borrar con y sin reintegro deja `helpers.movimientos(conn)` idéntico. Verificar
- [x] 2.8 RED→GREEN atomicidad (falla a mitad del reintegro): crear `TEMP TRIGGER BEFORE UPDATE OF stock ON productos WHEN OLD.codigo = 'B-02' BEGIN SELECT RAISE(ABORT, 'falla forzada'); END` y luego `borrar("OT-0001", True)`. Debe lanzar `sqlite3.DatabaseError`; la orden y sus dos líneas siguen; `A-01` sigue en 3 y `B-02` en 0; `in_transaction` es `False`. Verificar que el test falla si el reintegro se hiciera fuera de la transacción (mutación anotada y revertida)
- [x] 2.9 TRIANGULATE atomicidad (falla al borrar): trigger `BEFORE DELETE ON ordenes` con `RAISE(ABORT)`; tras `borrar("OT-0001", True)` todo el stock y el estado `activo` (incluido un `C-99` que se habría reactivado) quedan como antes y la orden sigue. Verificar
- [x] 2.10 RED→GREEN línea huérfana (decisión 4): con `PRAGMA foreign_keys = OFF` borrar la fila de `B-02` y volver a `ON`; `borrar("OT-0001", True)` lanza `RuntimeError`, la orden sigue y `A-01` sigue en 3; `borrar("OT-0001", False)` de esa misma orden sí la borra. Verificar
- [x] 2.11 RED→GREEN concurrencia (archivo temporal, dos conexiones, `threading.Barrier`, 5 rondas como `test_dos_egresos_simultaneos_solo_uno_pasa`): dos `borrar("OT-0001", True)` simultáneos (mismo número) → resultados `["inexistente", "ok"]`, stock final de `A-01` = 5, cero órdenes. Verificar
- [x] 2.12 REFACTOR: SQL como constantes del módulo, solo placeholders `?`, sin duplicar el mapeo de `Orden`; `tests.test_sqlite_orden_repository` completo verde

## 3. Repositorio: `ProductoRepository.dar_de_baja` — spec `baja-productos` (design D3)

En `tests/test_sqlite_repositories.py` o en un archivo nuevo, `tests/test_sqlite_producto_repository.py` (`:memory:`).

- [x] 3.1 RED: `dar_de_baja("A-01")` con stock 7 → devuelve `Producto(activo=False, stock=7)`; la fila sigue con nombre y stock; `listar_activos()` ya no lo incluye. Verificar que falla (`AttributeError`)
- [x] 3.2 GREEN: contrato en `base.py` e implementación en `SqliteProductoRepository` dentro de `_transaccion` (`UPDATE ... WHERE codigo = ? AND activo = 1`, `rowcount`); verificar verde
- [x] 3.3 TRIANGULATE: stock 0 → inactivo con 0; inexistente `Z-99` → `ProductoNoEncontrado` "No existe un producto activo con código 'Z-99'."; ya inactivo → `ProductoNoEncontrado` y stock intacto; movimientos previos intactos y sin filas nuevas; `in_transaction` es `False` tras cada rechazo. Verificar
- [x] 3.4 TRIANGULATE efectos cruzados a nivel repo: tras la baja, `SqliteStockRepository.registrar_egreso` → `ProductoNoEncontrado`; `SqliteOrdenRepository.crear` con ese código → `ProductosNoEncontrados`; `SqliteOrdenRepository.listar` sigue mostrando el componente en una orden previa; `registrar_ingreso` x3 → activo con stock 10 y `reactivado=True`. Verificar
- [x] 3.5 RED→GREEN concurrencia (archivo temporal, hilos): dos `dar_de_baja("A-01")` simultáneos → una sola baja y un `ProductoNoEncontrado`. Verificar
- [x] 3.6 REFACTOR; módulos de repositorio verdes

## 4. Services (design D4)

- [x] 4.1 RED: en `tests/test_orden_service.py` (repo real `:memory:`), `borrar("OT-0001", "true")` reintegra y `borrar("OT-0001", "false")` no. Verificar que falla (`AttributeError`)
- [x] 4.2 GREEN: `OrdenService.borrar` con el parseo de `reintegrar` de la decisión 2; verificar verde
- [x] 4.3 TRIANGULATE `reintegrar`:
  - `None` y `""` → `DatosInvalidos` "El campo reintegrar es obligatorio.";
  - `"si"`, `"1"`, `"TRUE"`, `" true"` → "El campo reintegrar debe ser true o false.";
  - `True`/`False` de Python funcionan;
  - en todos los rechazos la orden sigue y el stock no cambia.

  Verificar
- [x] 4.4 TRIANGULATE número y prioridad:
  - `"  ot-0001 "` normaliza y borra `OT-0001`;
  - `""`, `"   "` y `None` → `DatosInvalidos` "El campo numero es obligatorio."; 31 caracteres → "El campo numero admite hasta 30 caracteres."; 30 caracteres (con espacios alrededor) pasa la validación; en los rechazos la orden existente sigue y el stock no cambia;
  - número válido inexistente (`"ot-0999"`) → `OrdenNoEncontrada` con `OT-0999`;
  - número inexistente con `reintegrar=None` → error de `reintegrar`; número en blanco con `reintegrar="si"` → error de `reintegrar` (primero gana el de `reintegrar`).

  Verificar
- [x] 4.5 RED→GREEN: en un archivo nuevo, `tests/test_producto_service.py`, `ProductoService.dar_de_baja("  a-01 ")` da de baja `A-01`. `""`/`"   "` → "El campo codigo es obligatorio."; 51 caracteres → "El campo codigo admite hasta 50 caracteres."; `z-99` → `ProductoNoEncontrado` con `Z-99`. Crear `services/producto_service.py`; verificar
- [x] 4.6 REFACTOR: sin duplicar la normalización (`normalizar_codigo`); módulos de service verdes

## 5. API: `DELETE /api/ordenes/{numero}` — spec `api-http` (design D5)

En `tests/test_api_ordenes.py` (`TestClient`, archivo temporal).

- [x] 5.1 RED: sin sesión, `DELETE /api/ordenes/OT-0001?reintegrar=true` → 401 y la orden sigue. Verificar que falla (hoy 405)
- [x] 5.2 GREEN: endpoint `DELETE /{numero:path}` (`def` plano, descripción con la nota de codificar `?` y `#`, `reintegrar` obligatorio con enum en el schema, `BorradoOrdenOut`/`ReintegroOut` en `schemas.py`, 404/422 con `ErrorOut`); `OrdenNoEncontrada` ya mapea a 404 en `app.py`; verificar verde
- [x] 5.3 TRIANGULATE éxito: `DELETE /api/ordenes/ot-0001?reintegrar=true` → cuerpo exacto del escenario "Borrado con reintegro" (con `C-99` dado de baja por `DELETE /api/productos/C-99` si el grupo 6 ya existe, o por `UPDATE` sobre el archivo); después `GET /api/ordenes` no la lista y `GET /api/inventario` muestra 5 y 5; "Borrado sin reintegro" → `reintegrado: false`, `reintegros: []`, stock intacto; `GET /api/movimientos` idéntico antes y después. Verificar
- [x] 5.4 TRIANGULATE errores: sin `reintegrar` → 422 "El campo reintegrar es obligatorio."; `?reintegrar=` → mismo 422; `si`/`1`/`TRUE` → 422 "El campo reintegrar debe ser true o false."; `/%20%20?reintegrar=true` → 422 "El campo numero es obligatorio."; número de 31 caracteres → 422 "El campo numero admite hasta 30 caracteres."; `ot-0999` → 404 "No existe una orden con número 'OT-0999'."; segundo `DELETE` → 404 sin cambiar stock; en cada rechazo la orden sigue en `GET /api/ordenes`. Verificar
- [x] 5.4b TRIANGULATE número normalizado y con `/`: `/%20ot-0001%20?reintegrar=false` → 200 con `"numero": "OT-0001"`; orden `OT/2026/01` sembrada → `DELETE /api/ordenes/OT/2026/01?reintegrar=true` → 200; un número con `?` o `#` codificado (`OT%3F1`, `OT%231`) llega completo al service (200 si existe, 404 con el número completo si no). Verificar
- [x] 5.5 REFACTOR: router sin lógica (path/query → service → schema); `tests.test_api_ordenes` verde

## 6. API: `DELETE /api/productos/{codigo}` — spec `api-http` y `baja-productos` (design D5)

En un archivo nuevo, `tests/test_api_productos.py`.

- [x] 6.1 RED: sin sesión, `DELETE /api/productos/A-01` → 401 y `A-01` sigue activo. Verificar que falla (hoy 404 de ruta)
- [x] 6.2 GREEN: router `api/routers/productos.py` con `DELETE /{codigo:path}`, `get_producto_service` en `dependencies.py`, `include_router` en `app.py`; verificar verde
- [x] 6.3 TRIANGULATE éxito: `DELETE /api/productos/a-01` → 200 `{"codigo": "A-01", "nombre": "Tornillo", "stock": 7, "sin_stock": false}`; `GET /api/inventario` sin `A-01`; `CAJA/10` sembrado → `DELETE /api/productos/CAJA/10` → 200 con ese código. Verificar
- [x] 6.4 TRIANGULATE efectos cruzados: escenario "Efectos en el resto de la API" (orden previa sigue mostrando `A-01`; egreso y alta de orden → 404 con el mensaje exacto) y "Reingreso tras la baja" (200, `stock` 10, `reactivado` true); `GET /api/movimientos?codigo=A-01` sigue devolviendo sus movimientos. Verificar
- [x] 6.5 TRIANGULATE errores: `z-99` → 404 "No existe un producto activo con código 'Z-99'."; segunda baja → 404; `%20%20` → 422 "El campo codigo es obligatorio."; 51 caracteres → 422 "El campo codigo admite hasta 50 caracteres."; ningún rechazo modifica datos. Verificar
- [x] 6.6 REFACTOR; `tests.test_api_productos` verde

## 7. Integración transversal: sesión, OpenAPI y verificación

- [x] 7.1 TRIANGULATE sesión inexistente: en `tests/test_api_sesion_inexistente.py`, con la sesión de un usuario borrado y con la de un usuario recreado con otro id, `DELETE /api/ordenes/OT-0001?reintegrar=true` y `DELETE /api/productos/A-01` → 401 "No autenticado."; la orden sigue, el producto sigue activo y el stock no cambia. Verificar
- [x] 7.2 TRIANGULATE OpenAPI (`tests/test_api_app.py`, `tests/test_api_movimientos.py`, `tests/test_api_ordenes.py`): están las diez rutas, incluidas `/api/ordenes/{numero}` (`delete`, parámetro de path `numero`, `reintegrar` en query, `required`, enum `["true","false"]`) y `/api/productos/{codigo}` (`delete`); las 404 y 422 de ambos referencian `ErrorOut`; la 200 del borrado de orden referencia `BorradoOrdenOut`. Solo se agregan rutas a las tuplas existentes, sin cambiar otras aserciones. Verificar
- [x] 7.3 Correr la suite completa contra el baseline de 0.1: todos verdes, ninguno perdido; anotar el número final. Confirmar que `grep -rn "fastapi" inventario/domain inventario/services inventario/repositories` sale vacío, que no hay dependencias nuevas ni DDL, y que `git status` no muestra archivos fuera de `inventario/`, `tests/` y el change
- [x] 7.4 Correr `openspec validate paso-4b-borrado-ordenes-productos --strict` sin errores
- [x] 7.5 Verificación manual en `/docs` (la hace el orquestador; **copiar antes la base, p. ej. `prueba.db` → `prueba.bak.db`**; `uvicorn inventario.api.main:app --reload`). Pasos:
  - login;
  - ingresar `A-01` y `B-02`, crear `OT-0001` y anotar el stock;
  - `DELETE /api/ordenes/{numero}` sin elegir `reintegrar` (422);
  - con número en blanco (422), número inexistente (404) y número en minúsculas con espacios (normalizado);
  - con `false` (stock igual, orden fuera del listado);
  - crear otra orden, dar de baja uno de sus productos, borrarla con `true` (stock devuelto y `reactivado: true` en la respuesta y en el inventario);
  - repetir el `DELETE` (404);
  - `DELETE /api/productos/{codigo}` con stock > 0 (200, fuera del inventario, sigue en órdenes viejas);
  - repetir (404);
  - egreso y orden con ese código (404); reingreso (reactiva y suma);
  - `GET /api/movimientos` sin filas por los borrados;
  - logout y repetir los `DELETE` (401).

  Anotar el resultado en el verify-report

## 8. Ajustes post-verify

- [x] 8.1 RED: tests de `reintegrar` repetido (true+false, false+true, true+true, si+no; 422 antes que 404 y número inválido; 401 sin sesión gana), con stock y orden intactos; vistos fallar.
- [x] 8.2 GREEN: comprobación en el router `borrar_orden` con `request.query_params.getlist` y 422 en español; OpenAPI sin cambios.
- [x] 8.3 Escenario "Reintegrar repetido" en el delta spec `api-http`, nota en `design.md` y `verify-report.md` actualizado.

## Workflow follow-up

- Verify del change (`openspec-verify`) contra specs, design y tasks, incluida la revisión de los riesgos R1-R10 de `design.md`.
- Archivar con `/opsx:archive paso-4b-borrado-ordenes-productos`, marcar `[x]` C-05 en `CHANGES.md` y actualizar la KB:
  - en `02_descripcion_general.md`, la tabla de endpoints: `DELETE /api/productos/{codigo}` y `/api/inventario` en lugar de `GET /api/productos`;
  - el Flujo 6 de `07_flujos_principales.md`: ítems borrados explícitamente y respuesta con el detalle del reintegro;
  - los criterios de US-008/US-009;
  - el nombre del método en `08_arquitectura_propuesta.md`.
- Esperar "Continuar" del usuario antes de C-06.
