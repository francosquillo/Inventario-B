# Tasks

> **Decisiones aprobadas por el usuario el 2026-11-20**: 1-3 y 5-13 como recomendadas (★); la 4 cambió a la opción B (el tope 1..10.000 rige solo por línea; el total consolidado solo lo limita el stock).
>
> Strict TDD: en cada comportamiento, RED (test que falla por la razón correcta) → GREEN (mínimo código) → TRIANGULATE (segundo caso distinto) → REFACTOR (tests verdes tras cada paso).
> Comando (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .` — un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
> FastAPI/Pydantic solo en `inventario/api/` (Regla dura 1). Sin mocks de base: `:memory:` en repos/services, archivo temporal en API y concurrencia (Regla dura 4). Sin dependencias nuevas. Sin commits (Regla dura 6).
> Reloj fijo de los tests: `FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)` → `"2026-11-19T15:30:00-03:00"`.

## 0. Red de seguridad

- [x] 0.1 Correr la suite completa antes de tocar nada y anotar el baseline (`Ran N tests ... OK`); si algo falla, detenerse y reportarlo como falla preexistente

## 1. Transacción endurecida (S-2 de C-02, design D3 / decisión 11)

- [x] 1.1 Hacer que `insertar_producto`, `insertar_usuario` e `insertar_movimiento` de `tests/helpers.py` confirmen (`conn.commit()`); verificar que la suite completa sigue verde con el mismo número de tests que el baseline
- [x] 1.2 RED: en `tests/test_sqlite_stock_repository.py`, con un `INSERT` en `productos` sin confirmar en la misma conexión, `registrar_egreso` lanza `RuntimeError` y `conn.rollback()` deja la tabla sin esa fila; verificar que falla (hoy confirma en silencio)
- [x] 1.3 GREEN: `_transaccion` lanza `RuntimeError` si `conn.in_transaction` (sin commit implícito), con comentario que explique el motivo; verificar verde y suite completa verde

## 2. Dominio y helpers compartidos

- [x] 2.1 RED→GREEN: en `tests/test_domain.py`, `Orden(id, numero, fecha, usuario, items)`, `ItemOrden(codigo, nombre, cantidad)` y `Faltante(codigo, disponible, solicitado)` son inmutables (`FrozenInstanceError`); agregarlos en `inventario/domain/entities.py`; verificar verde
- [x] 2.2 RED→GREEN: `OrdenDuplicada("OT-0001")`, `ProductosNoEncontrados(("X-00",))`, `ProductosNoEncontrados(("X-00", "C-99"))` y `StockInsuficienteOrden((Faltante("A-01", 1, 2), Faltante("B-02", 0, 1)))` heredan de `InventarioError`, exponen sus atributos y producen exactamente los mensajes de design D6; implementar en `inventario/domain/errors.py`; verificar verde
- [x] 2.3 TRIANGULATE: un solo faltante produce "Stock insuficiente para la orden: 'A-01' (disponible 1, solicitado 2)."; los errores de C-02 conservan sus mensajes; verificar verdes
- [x] 2.4 RED→GREEN: en `tests/test_fechas.py`, la función de `inventario/services/fechas.py` (design D5) acepta `2026-11-20` → `date`, rechaza `20/11/2026`, `2026-11-20T10:00`, `2026-11-20\n` y dígitos Unicode con el mensaje de formato, y `2026-02-30` con el de fecha inválida, usando los mensajes que recibe; verificar verde
- [x] 2.5 REFACTOR: `MovimientosService` usa `services/fechas.py` y `validar_cantidad` pasa de `stock_service.py` a `services/normalizacion.py`; verificar `tests.test_movimientos_service`, `tests.test_stock_service` y `tests.test_api_movimientos` verdes sin modificar sus mensajes

## 3. Repositorio de órdenes SQLite atómico — spec `ordenes-trabajo`

- [x] 3.1 RED: en `tests/test_sqlite_orden_repository.py` (`:memory:` + `insertar_usuario`), `crear("OT-0001", date(2026, 11, 20), [("A-01", 2), ("B-02", 10)], uid, FECHA_FIJA)` sobre `A-01` stock 5 y `B-02` stock 10 devuelve una `Orden` con username, líneas ordenadas por código, y deja stock 3 y 0; verificar que falla por `ImportError`
- [x] 3.2 GREEN: declarar `OrdenRepository` en `repositories/base.py` e implementar `SqliteOrdenRepository.crear` con `_transaccion` según design D2 (sin escribir `movimientos`); verificar verde
- [x] 3.3 TRIANGULATE alta: filas en `ordenes` (`numero`, `fecha == "2026-11-20"`, `usuario_id`, `created_at == "2026-11-19T15:30:00-03:00"`) y en `orden_items`; `B-02` con stock 0 sigue activo; cero filas en `movimientos`; orden con un solo componente; verificar verdes
- [x] 3.4 TRIANGULATE rechazos sin escritura: número existente → `OrdenDuplicada`; `X-00` inexistente → `ProductosNoEncontrados(("X-00",))`; `X-00` + `C-99` inactivo → ambos en orden de aparición y `C-99` sigue inactivo; un faltante y varios faltantes (`A-01` 1/2, `D-04` 9/1, `B-02` 0/1 → `A-01` y `B-02` en ese orden); en cada caso ni orden ni líneas y stock intacto en **todos** los productos; verificar verdes
- [x] 3.5 TRIANGULATE prioridad: duplicado + stock insuficiente → `OrdenDuplicada`; inexistente + stock insuficiente → `ProductosNoEncontrados`; verificar verdes
- [x] 3.6 TRIANGULATE atomicidad sin mocks: con `usuario_id` inexistente (FK activa) la orden de `A-01` x 2 y `B-02` x 3 propaga `sqlite3.IntegrityError`, sin orden ni líneas y con stock 5 y 10 intactos; `datetime` naive en `creada_en` → `ValueError` sin escritura; verificar verdes
- [x] 3.7 TRIANGULATE concurrencia (archivo temporal, dos conexiones, `threading.Barrier`, cerrar conexiones antes del cleanup): (a) órdenes `OT-1` y `OT-2` con `A-01` x 3 sobre stock 5 → exactamente un `StockInsuficienteOrden`, stock 2, una orden; (b) dos `OT-0009` con `A-01` x 1 sobre stock 10 → exactamente un `OrdenDuplicada`, stock 9, una orden; verificar verde repitiéndolo 5 veces seguidas
- [x] 3.8 REFACTOR: SQL como constantes del módulo, armado de la lista `IN` solo con placeholders, traducción del `IntegrityError` de `ordenes.numero` a `OrdenDuplicada`, docstrings; `tests.test_sqlite_orden_repository` y `tests.test_sqlite_stock_repository` verdes

## 4. OrdenService — validación, normalización y consolidación (spec `ordenes-trabajo`)

- [x] 4.1 RED: en `tests/test_orden_service.py` (`:memory:` + repo real + reloj fijo), `crear("  ot-0003 ", "2026-11-20", [(" a-01 ", 2)], uid)` guarda `OT-0003` con la línea `A-01` x 2 y `created_at` del reloj inyectado; verificar que falla por `ImportError`
- [x] 4.2 GREEN: implementar `OrdenService` en `inventario/services/orden_service.py` según design D4; verificar verde
- [x] 4.3 TRIANGULATE número y fecha: `"   "` → "El campo numero es obligatorio."; 31 caracteres → "El campo numero admite hasta 30 caracteres."; `5` → "El campo numero debe ser texto."; fecha `None`/`""` → "El campo fecha es obligatorio."; `20/11/2026` → formato; `2026-02-30` → "La fecha (2026-02-30) no es una fecha válida."; `2025-01-15` y una fecha futura aceptadas; verificar verdes
- [x] 4.4 TRIANGULATE componentes: lista vacía → "La orden requiere al menos un componente."; 101 líneas → "La orden admite hasta 100 componentes."; segunda línea con cantidad `0`, `2.5`, `"5"`, `True` o `10_001` → "Componente 2: La cantidad debe ser un entero entre 1 y 10.000."; código vacío o de 51 en la línea 1 → "Componente 1: ..." con el mensaje de C-02; verificar verdes
- [x] 4.5 TRIANGULATE consolidación: `A-01` x 2 + `a-01` x 1 → una línea x 3 y stock 2; `A-01` x 3 + `A-01` x 3 sobre stock 5 → `StockInsuficienteOrden` con solicitado 6; `A-01` x 6000 + `A-01` x 6000 sobre stock 12000 → una línea x 12000 y stock 0 (aceptada, sin 422); la misma orden sobre stock 11000 → `StockInsuficienteOrden` con disponible 11000 y solicitado 12000 y stock intacto; una línea individual de 10_001 sigue siendo 422 (4.4); verificar verdes
- [x] 4.6 TRIANGULATE sin escritura: cada validación fallida deja `ordenes`, `orden_items`, stock y `movimientos` sin cambios; verificar verdes
- [x] 4.7 REFACTOR: mensajes como constantes, formato de miles en una función privada; `tests.test_orden_service` verde

## 5. Mensajes 422 para órdenes — spec `api-http` (design D9)

- [x] 5.1 RED: en `tests/test_errores_validacion.py`, con errores reales de `OrdenRequest` (`ValidationError.errors()`), un segundo componente sin `codigo` → "Componente 2: El campo codigo es obligatorio."; verificar que falla (falta el schema o el prefijo)
- [x] 5.2 GREEN: agregar `ComponenteRequest`/`OrdenRequest` en `api/schemas.py` (design D8) y el prefijo de línea en `mensaje_validacion`; verificar verde
- [x] 5.3 TRIANGULATE: `componentes` `[]` → "La orden requiere al menos un componente."; 101 → "La orden admite hasta 100 componentes."; `componentes` no lista → "El campo componentes debe ser una lista."; línea que no es objeto → "Componente 1: debe ser un objeto con codigo y cantidad."; `cantidad` `"5"` en la línea 1 → "Componente 1: La cantidad debe ser un entero entre 1 y 10.000."; `fecha` faltante → "El campo fecha es obligatorio."; `numero` de 31 → "El campo numero admite hasta 30 caracteres."; los casos de C-02 siguen verdes; verificar verdes

## 6. API HTTP de órdenes — spec `api-http`

- [x] 6.1 RED: en `tests/test_api_ordenes.py` (`TestClient`, archivo temporal vía `tests/helpers.py`), `POST /api/ordenes` sin sesión → 401; verificar que falla (404 por ruta inexistente)
- [x] 6.2 GREEN: `api/routers/ordenes.py` (`status_code=201`), `OrdenOut`/`ComponenteOut`, `get_orden_service` en `dependencies.py`, registro del router y de los handlers de `OrdenDuplicada` (409), `ProductosNoEncontrados` (404) y `StockInsuficienteOrden` (409 con `faltantes`) en `app.py`; verificar verde
- [x] 6.3 TRIANGULATE éxito: el escenario "Orden creada" del spec (`ot-0001`, líneas `b-02`/`A-01`/`B-02`) → 201 con el cuerpo exacto; `GET /api/inventario` muestra 3 y 5; `GET /api/movimientos` responde `[]`; verificar verdes
- [x] 6.4 TRIANGULATE rechazos: 409 stock con `detail` y `faltantes` exactos e inventario intacto; 409 duplicado sin clave `faltantes`; 404 `X-00`; 422 `componentes: []`, `cantidad: "5"`, `fecha: "20/11/2026"`, cuerpo no JSON; sin sesión con cuerpo inválido → 401; verificar verdes
- [x] 6.5 TRIANGULATE OpenAPI: en `tests/test_api_app.py` (o el test existente de docs) el esquema lista los ocho endpoints; la 422 de `/api/ordenes` referencia `ErrorOut` y la 409 `StockInsuficienteOut`; los 422 de los otros cuatro endpoints siguen con `ErrorOut`; verificar verdes
- [x] 6.6 REFACTOR: router sin lógica (request → tuplas → service → schema), conversión `Orden` → `OrdenOut` en una función de `schemas.py`; `tests.test_api_ordenes` verde

## 7. Verificación integral

- [x] 7.1 Correr la suite completa y comparar con el baseline de 0.1: todos verdes, ninguno perdido; anotar el número final de tests
- [x] 7.2 Verificación manual en `/docs` (`uvicorn inventario.api.main:app --reload`, idealmente con una base existente como `prueba.db`): login; sembrar stock con `POST /api/stock/ingreso`; crear una orden con dos productos y una línea repetida en minúsculas (201, líneas consolidadas, número en mayúsculas); `GET /api/inventario` con el stock descontado; `GET /api/movimientos` sin filas por la orden; repetir el número (409); orden con un faltante y otra con dos (409 con `faltantes`, inventario sin cambios); código inexistente (404); `componentes: []`, cantidad `0` en la línea 2 y fecha `2026-02-30` (422 en español); revisar en Swagger los esquemas de 201, 409 y 422; logout y repetir el alta (401); confirmar con SQL que `orden_items` tiene las líneas esperadas y `ordenes.created_at` usa `-03:00`; anotar el resultado en el verify-report
- [x] 7.3 Confirmar `openspec validate paso-3-crear-ordenes --strict` sin errores y que no hay archivos nuevos fuera de `inventario/`, `tests/` y el change

## 8. Ajustes post-verify (2026-11-20)

- [x] 8.1 W-1 RED/GREEN/TRIANGULATE: `fecha` con espacios, `\n` o tabulación -> 422 con el mensaje de formato (modelo y HTTP); `numero`/`codigo` siguen recortándose; filtros `desde`/`hasta` de movimientos con espacio o `\n` -> 422
- [x] 8.2 W-2 RED/GREEN/TRIANGULATE: `tests/test_api_sesion_inexistente.py` (usuario borrado y usuario recreado con otro id) -> 401 "No autenticado." en `POST /api/ordenes`, ingreso, egreso, `GET /api/movimientos`, `/api/inventario` y `/api/me`, sin datos modificados; `UsuarioRepository.obtener_por_id` + test de repositorio; `get_current_user` consulta la base y limpia la sesión
- [x] 8.3 S-1 RED/GREEN/TRIANGULATE: `null` en `fecha`, `numero`, `componentes`, `codigo`, `username` y `password` -> "obligatorio"; `5` sigue "debe ser texto"; `nombre: null` válido
- [x] 8.4 S-2: test del respaldo `IntegrityError` -> `OrdenDuplicada` con SQLite real (y mutación que lo hace fallar)
- [x] 8.5 Delta `specs/api-http` con el requisito "Sesión de usuario inexistente", sección en `design.md` y `verify-report.md` actualizado; suite completa verde (301) y `openspec validate --strict`

## Workflow follow-up

- Verify del change (`openspec-verify`) contra specs, design y tasks.
- Archivar con `/opsx:archive paso-3-crear-ordenes`, marcar `[x]` C-03 en `CHANGES.md` y actualizar PA-06 en `knowledge-base/10_preguntas_abiertas.md` y el tipo de `ordenes.numero` en `04_modelo_de_datos.md`.
- Esperar "Continuar" del usuario antes de C-04.
