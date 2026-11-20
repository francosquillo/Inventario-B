# Tasks

> **Aprobado por el usuario el 2026-11-19** (revisión una por una de las decisiones de `design.md`). Aprobadas tal cual: 1, 3, 4, 5, 6, 8, 10, 12. Cambiadas: 2 (código en MAYÚSCULAS), 7 (cantidad 1..10.000), 9 (fecha local Argentina `-03:00` con reloj inyectable), 11 (nuevo `GET /api/movimientos`). Nueva: 13 (todo 422 como `{"detail": "<mensaje en español>"}`). Detalle en `design.md` → "Aprobación del usuario". Governance MEDIO: el change queda listo para apply.
>
> Strict TDD: en cada comportamiento, RED (test que falla por la razón correcta) → GREEN (mínimo código) → TRIANGULATE (segundo caso distinto) → REFACTOR (tests verdes tras cada paso).
> Comando (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .` — un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
> FastAPI/Pydantic solo en `inventario/api/` (Regla dura 1). Sin mocks de base: `:memory:` en repos/services, archivo temporal en API y en el test de concurrencia (Regla dura 4, design D8). Sin dependencias nuevas (sin `zoneinfo`/`tzdata`). Sin commits (Regla dura 6).
> Reloj fijo de los tests: `FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)` → `"2026-11-19T15:30:00-03:00"`.

## 0. Red de seguridad

- [x] 0.1 Correr la suite completa (`.venv/Scripts/python -m unittest discover -s tests -t .`) antes de tocar nada y anotar el baseline (`Ran N tests ... OK`); si algo falla, detenerse y reportarlo como falla preexistente

## 1. Dominio, tiempo y helpers de test

- [x] 1.1 RED→GREEN: en `tests/test_tiempo.py`, `ahora_argentina()` devuelve un `datetime` aware con `utcoffset() == timedelta(hours=-3)` y `microsecond == 0`, y `ZONA_AR` tiene offset `-03:00`; crear `inventario/domain/tiempo.py` (D6, sin `zoneinfo`); verificar verde
- [x] 1.2 RED→GREEN: en `tests/test_domain.py`, `ResultadoIngreso(producto, creado, reactivado)` y `Movimiento(fecha, codigo, nombre, tipo, cantidad, usuario)` son inmutables (asignar un campo lanza `FrozenInstanceError`); agregar ambos dataclasses frozen en `inventario/domain/entities.py` (D1, D9); verificar verde
- [x] 1.3 RED→GREEN: tests de los errores nuevos en `tests/test_domain.py`: heredan de `InventarioError`; `NombreRequerido("N-02")`, `ProductoNoEncontrado("X-00")` y `StockInsuficiente("A-01", disponible=5, solicitado=6)` producen los mensajes de D4 y exponen `codigo`/`disponible`/`solicitado`; `DatosInvalidos("msg")` conserva el mensaje; implementar en `inventario/domain/errors.py`; verificar verde
- [x] 1.4 Agregar a `tests/helpers.py` `insertar_usuario(conn, username="admin") -> id` (hash/salt ficticios), `movimientos(conn)` (filas `tipo, cantidad, codigo, usuario_id, fecha` con JOIN a productos, ordenadas por id), `insertar_movimiento(conn, fecha, producto_id, tipo, cantidad, usuario_id)` (fecha como texto) y mover `sembrar(ruta, productos)` desde `tests/test_api_inventario.py`; verificar que `tests.test_api_inventario` sigue verde

## 2. Repositorio de stock SQLite atómico — spec `movimientos-stock`

- [x] 2.1 RED: en `tests/test_sqlite_stock_repository.py` (`:memory:` + `insertar_usuario`), `registrar_ingreso("A-01", 3, None, uid, FECHA_FIJA)` sobre `A-01` activo stock 5 deja stock 8 y devuelve `ResultadoIngreso(creado=False, reactivado=False)`; verificar que falla por `ImportError`
- [x] 2.2 GREEN: declarar `StockRepository` (ABC, firmas con `fecha: datetime`) en `repositories/base.py` e implementar `SqliteStockRepository.registrar_ingreso` con `_transaccion` (`BEGIN IMMEDIATE`/commit/rollback) e `INSERT INTO movimientos` con fecha explícita (D2, D6); verificar verde
- [x] 2.3 TRIANGULATE ingreso: stock 0 → 4; nombre distinto en código existente se ignora; alta de `N-01` "Arandela 6mm" con stock 10 activo (`creado=True`); reactivación de `C-99` inactivo stock 2 → activo stock 5, nombre intacto, un solo `C-99` (`reactivado=True`); código inexistente con `nombre=None` → `NombreRequerido` y ni producto ni movimiento; verificar verdes
- [x] 2.4 TRIANGULATE fecha del movimiento: suma y alta registran exactamente una fila `ingreso` con cantidad, producto, `usuario_id` y `fecha == "2026-11-19T15:30:00-03:00"`; con `datetime(2026, 11, 19, 18, 30, tzinfo=timezone.utc)` se guarda `"2026-11-19T15:30:00-03:00"`; un `datetime` naive lanza `ValueError` sin escribir nada; verificar verdes
- [x] 2.5 RED→GREEN egreso: `registrar_egreso("A-01", 3, uid, FECHA_FIJA)` sobre stock 8 → stock 5 y un movimiento `egreso` con la fecha fija; implementar con SELECT + `UPDATE ... WHERE id = ? AND activo = 1 AND stock >= ?` + verificación de `rowcount` (D2); verificar verde
- [x] 2.6 TRIANGULATE egreso: todo el stock → 0, sigue activo; exceso (6 sobre 5) → `StockInsuficiente` con `disponible=5`, stock intacto, sin movimiento; stock 0 → rechazo; código inexistente e inactivo → `ProductoNoEncontrado` sin cambios; verificar verdes
- [x] 2.7 TRIANGULATE atomicidad (sin mocks): con `usuario_id` inexistente (FK activa) el ingreso sobre `A-01` deja stock 5, el alta de `N-05` no crea el producto y el egreso deja stock 5; en los tres casos se propaga `sqlite3.IntegrityError` y no hay movimientos; verificar verdes
- [x] 2.8 TRIANGULATE concurrencia: clase con archivo SQLite temporal (`tempfile.TemporaryDirectory`, cerrar conexiones antes del cleanup), dos hilos con conexiones propias y `threading.Barrier` hacen `registrar_egreso("A-01", 3, uid, FECHA_FIJA)` sobre stock 5 → exactamente un `StockInsuficiente`, stock final 2 y un único movimiento; verificar verde repitiéndolo 5 veces seguidas
- [x] 2.9 REFACTOR: SQL como constantes del módulo, mapeo de filas con `_a_producto`, serialización de fecha en una función privada `_fecha_a_texto`, docstrings; `.venv/Scripts/python -m unittest tests.test_sqlite_stock_repository -v` verde

## 3. Normalización idempotente de fechas legadas — spec `movimientos-stock`

- [x] 3.1 RED: en `tests/test_sqlite_schema.py` (módulo de esquema de C-01), con `:memory:`, `inicializar_esquema`, una fila de `movimientos` insertada con `fecha = "2026-11-19 18:30:00"` y una segunda llamada a `inicializar_esquema` → la fecha queda `"2026-11-19T15:30:00-03:00"`; verificar que falla (la fecha sigue legada)
- [x] 3.2 GREEN: agregar en `inicializar_esquema` el `UPDATE movimientos ... WHERE fecha NOT LIKE '____-__-__T__:__:__-03:00'` + `commit` (D6); verificar verde
- [x] 3.3 TRIANGULATE: una fila ya normalizada (`"2026-11-18T09:00:00-03:00"`) no cambia; llamar `inicializar_esquema` tres veces deja las mismas fechas; base sin movimientos no falla; los tests de esquema de C-01 siguen verdes; verificar verdes
- [x] 3.4 REFACTOR: SQL de normalización como constante con comentario; suite completa verde

## 4. StockService — validación, normalización y reloj (spec `movimientos-stock`)

- [x] 4.1 RED: en `tests/test_stock_service.py` (`:memory:` + `SqliteStockRepository` real + `ahora=lambda: FECHA_FIJA`), `ingresar("  A-01  ", 2, None, uid)` suma sobre `A-01` sin crear otro producto y el movimiento tiene la fecha fija; verificar que falla por `ImportError`
- [x] 4.2 GREEN: crear `services/normalizacion.py` con `normalizar_codigo` (strip + upper + validación, D3/D7) e implementar `StockService(stock_repo, ahora=ahora_argentina)` con `ingresar` y `egresar` delegando en el repositorio; verificar verde
- [x] 4.3 TRIANGULATE mayúsculas: `ingresar("rd-6204", 4, "Rodamiento 6204", uid)` crea `RD-6204`; luego `ingresar("Rd-6204", 2, None, uid)` → un único producto `RD-6204` con stock 6 y dos movimientos; `egresar(" a-01 ", 1, uid)` sobre `A-01` stock 5 → stock 4 y no existe `a-01`; `ProductoNoEncontrado`/`StockInsuficiente` muestran el código en mayúsculas; verificar verdes
- [x] 4.4 TRIANGULATE cantidades: `0`, `-1`, `2.5`, `"5"`, `True`, `10_001` → `DatosInvalidos("La cantidad debe ser un entero entre 1 y 10.000.")` en ingreso y en egreso; `10_000` aceptado (stock 5 → 10.005); stock y movimientos sin cambios tras cada rechazo; verificar verdes
- [x] 4.5 TRIANGULATE textos: código `"   "`, `""` o no `str` → "El campo codigo es obligatorio." (no `str` puede usar el mismo mensaje u otro en español); código de 51 caracteres (tras `upper()`) → "El campo codigo admite hasta 50 caracteres."; nombre `"  Buje  "` en alta queda "Buje"; nombre `"   "` en código nuevo → `NombreRequerido`; nombre de 121 caracteres → "El campo nombre admite hasta 120 caracteres."; verificar verdes
- [x] 4.6 TRIANGULATE reloj: un reloj inyectado que cuenta llamadas se invoca una vez por operación aceptada y ninguna vez cuando la validación falla; sin reloj inyectado, el movimiento tiene fecha con sufijo `-03:00`; verificar verdes
- [x] 4.7 REFACTOR: constantes `CODIGO_MAX = 50`, `NOMBRE_MAX = 120`, `CANTIDAD_MAX = 10_000` y mensajes como constantes; confirmar con `grep` que `inventario/services/` no importa `sqlite3`, `fastapi` ni `pydantic`; `tests.test_stock_service` verde

## 5. Repositorio de movimientos (lectura) — spec `consulta-movimientos`

- [x] 5.1 RED: en `tests/test_sqlite_movimiento_repository.py` (`:memory:` + `insertar_usuario` + `insertar_movimiento`), con tres movimientos de fechas 18, 19 y 17 de noviembre, `listar(None, None, None)` los devuelve en orden 19, 18, 17 como `Movimiento` con `fecha` aware `-03:00`, `codigo`, `nombre`, `tipo`, `cantidad` y `usuario == "admin"`; verificar que falla por `ImportError`
- [x] 5.2 GREEN: declarar `MovimientoRepository` (ABC) en `repositories/base.py` e implementar `SqliteMovimientoRepository.listar` con JOIN a productos y usuarios y `ORDER BY m.fecha DESC, m.id DESC` (D9); verificar verde
- [x] 5.3 TRIANGULATE: misma fecha → el de mayor id primero; base sin movimientos → `[]`; movimientos de un producto inactivo se incluyen; filtro `codigo="A-01"` solo trae `A-01`; código inexistente → `[]`; verificar verdes
- [x] 5.4 TRIANGULATE fechas: con movimientos `2026-11-17T23:59:59-03:00`, `2026-11-18T00:00:00-03:00`, `2026-11-19T23:59:59-03:00`, `2026-11-20T00:00:00-03:00`, `listar(None, date(2026,11,18), date(2026,11,19))` trae solo los dos del medio; solo `desde` y solo `hasta` funcionan por separado; código + fechas combinados; verificar verdes
- [x] 5.5 REFACTOR: armado de la consulta con lista de condiciones y parámetros (siempre parametrizada), mapeo `_a_movimiento`; `tests.test_sqlite_movimiento_repository` verde

## 6. MovimientosService — validación de filtros (spec `consulta-movimientos`)

- [x] 6.1 RED: en `tests/test_movimientos_service.py` (`:memory:` + repo real), `listar(codigo=" rd-6204 ")` devuelve los movimientos de `RD-6204`; verificar que falla por `ImportError`
- [x] 6.2 GREEN: implementar `MovimientosService(movimiento_repo).listar(codigo=None, desde=None, hasta=None)` reutilizando `normalizar_codigo` y parseando fechas (D9); verificar verde
- [x] 6.3 TRIANGULATE: `codigo` `""`/`"   "` y `desde`/`hasta` `""` se tratan como sin filtro; `desde="19/11/2026"` → `DatosInvalidos("La fecha 'desde' debe tener formato AAAA-MM-DD.")`; `hasta="20261119"` → `DatosInvalidos("La fecha 'hasta' debe tener formato AAAA-MM-DD.")`; `hasta="2026-02-30"` (formato OK, fecha inexistente) → `DatosInvalidos("La fecha 'hasta' (2026-02-30) no es una fecha válida.")`; `desde="2026-11-20", hasta="2026-11-19"` → `DatosInvalidos("La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).")`; `desde == hasta` es válido; código de 51 caracteres → `DatosInvalidos`; verificar verdes
- [x] 6.4 REFACTOR: regex de fecha como constante compilada, función privada `_parsear_fecha(nombre, valor)`; `grep` confirma que el service no importa `sqlite3`/`fastapi`/`pydantic`; `tests.test_movimientos_service` verde

## 7. Errores de validación en español — spec `api-http` (D10)

- [x] 7.1 RED: en `tests/test_errores_validacion.py`, obtener errores reales validando `LoginRequest` con `{"username": "admin"}` (`ValidationError.errors()`) y verificar que `mensaje_validacion(errores)` devuelve "El campo password es obligatorio."; verificar que falla por `ImportError`
- [x] 7.2 GREEN: crear `inventario/api/errores_validacion.py` con `mensaje_validacion` (casos de D10: faltante/vacío) ; verificar verde
- [x] 7.3 TRIANGULATE mapeo: `string_too_long` en `username` (65) → "El campo username admite hasta 64 caracteres."; `string_type` (`username: 5`) → "El campo username debe ser texto."; cualquier error de `cantidad` (`"5"`, `2.5`, `0`, `True`, `10001`) en `IngresoRequest` → "La cantidad debe ser un entero entre 1 y 10.000."; `codigo` de 51 → "El campo codigo admite hasta 50 caracteres."; `nombre` de 121 → "El campo nombre admite hasta 120 caracteres."; varios errores (`{"cantidad": 0}`) → solo el primero ("El campo codigo es obligatorio."); un tipo desconocido (dict sintético mínimo `{"type": "otro", "loc": ("body", "x"), "msg": "..."}`) → "El campo x no es válido."; sin campo → "Los datos enviados no son válidos."; verificar verdes
- [x] 7.4 RED→GREEN handler: en `tests/test_api_auth.py` (C-01), extender `test_422_por_cuerpo_invalido` y `test_422_por_longitud_excesiva` para verificar que `r.json()["detail"]` es `str` con el mensaje en español esperado (cuerpo ausente → "El cuerpo de la petición es obligatorio."); agregar JSON mal formado (`content='{"username": "admin",'`, `Content-Type: application/json`) → "El cuerpo de la petición no es JSON válido."; registrar `@app.exception_handler(RequestValidationError)` en `api/app.py`; verificar verde
- [x] 7.5 TRIANGULATE OpenAPI: agregar `ErrorOut {detail: str}` en `api/schemas.py` y `responses={422: {"model": ErrorOut, ...}}` en la ruta de login; test sobre `GET /openapi.json`: el 422 de `/api/login` referencia `ErrorOut` (no `HTTPValidationError`); si FastAPI igual agrega `HTTPValidationError`, documentarlo como limitación conocida en el verify-report en lugar de parchear `openapi()`; verificar verde
- [x] 7.6 REFACTOR: tabla de mensajes como constantes/diccionario por tipo, función `_campo(loc)`; `tests.test_errores_validacion` y `tests.test_api_auth` verdes

## 8. API HTTP de stock — spec `api-http`

- [x] 8.1 RED: en `tests/test_api_stock.py`, `POST /api/stock/ingreso` sin sesión con cuerpo válido → 401 y sin cambios en la base; verificar que falla (404 por ruta inexistente)
- [x] 8.2 GREEN: schemas `IngresoRequest`, `EgresoRequest`, `IngresoOut` (D5, `le=10_000`) en `api/schemas.py`; `get_stock_service` en `dependencies.py`; `routers/stock.py` con ambos endpoints `def` usando `Depends(get_current_user)` y `responses={422: {"model": ErrorOut}}`; `include_router` en `app.py`; verificar verde
- [x] 8.3 TRIANGULATE ingreso con sesión: suma → 200 con claves exactas `{codigo, nombre, stock, sin_stock, creado, reactivado}`; alta → `creado: true` y `GET /api/inventario` la incluye; alta con `"rd-6204"` → `codigo: "RD-6204"`; reactivación → `reactivado: true`; el movimiento registrado tiene el `usuario_id` del admin de la sesión y fecha con sufijo `-03:00`; verificar verdes
- [x] 8.4 RED→GREEN errores de dominio: handlers en `app.py` para `DatosInvalidos`/`NombreRequerido` (422), `ProductoNoEncontrado` (404) y `StockInsuficiente` (409) con `{"detail": "<mensaje>"}`; tests: código nuevo sin nombre → 422 con `detail` texto y el producto no existe; egreso `X-00` y `C-99` inactivo → 404; egreso `"a-01"` sobre `A-01` → 200 `codigo: "A-01"`; egreso 6 sobre 5 → 409 con "disponible 5" en `detail` y stock intacto; egreso de todo → 200 `sin_stock: true`; verificar verdes
- [x] 8.5 TRIANGULATE validación HTTP (todas con `detail` `str` en español de D10): `cantidad` `"5"`, `2.5`, `0`, `true`, `10001` → "La cantidad debe ser un entero entre 1 y 10.000."; `cantidad` `10000` → 200; `cantidad` faltante → "El campo cantidad es obligatorio."; `codigo` faltante o `""` → "El campo codigo es obligatorio."; `codigo` de 51 → "El campo codigo admite hasta 50 caracteres."; `codigo` `"   "` → 422 (del service) sin crear producto; `nombre` de 121 → 422; sin sesión con cuerpo inválido → 401; egreso sin sesión → 401; verificar verdes
- [x] 8.6 REFACTOR: routers sin lógica (request → service → schema), `ProductoOut`/`IngresoOut` construidos con una función de mapeo compartida; `.venv/Scripts/python -m unittest tests.test_api_stock -v` verde

## 9. API HTTP de movimientos — spec `api-http` y `consulta-movimientos`

- [x] 9.1 RED: en `tests/test_api_movimientos.py`, `GET /api/movimientos` sin sesión → 401; verificar que falla (404 por ruta inexistente)
- [x] 9.2 GREEN: schema `MovimientoOut {fecha: datetime, codigo, nombre, tipo, cantidad, usuario}`; `get_movimientos_service` en `dependencies.py`; `routers/movimientos.py` con `GET` `def`, query params `codigo`/`desde`/`hasta` como `str | None`, `Depends(get_current_user)` y `responses={422: {"model": ErrorOut}}`; `include_router`; verificar verde
- [x] 9.3 TRIANGULATE con sesión: tras un ingreso por API, `GET /api/movimientos` → 200 con lista de objetos de claves exactas `{fecha, codigo, nombre, tipo, cantidad, usuario}`, `usuario: "admin"` y `fecha` con sufijo `-03:00`; con movimientos sembrados (`insertar_movimiento`) de fechas conocidas, el orden es del más nuevo al más viejo y `fecha` se serializa exactamente `"2026-11-19T15:30:00-03:00"`; sin movimientos → `[]`; verificar verdes
- [x] 9.4 TRIANGULATE filtros y errores: `?codigo=a-01&desde=2026-11-18&hasta=2026-11-19` filtra; producto inactivo incluido; `?desde=19/11/2026` → 422 "La fecha 'desde' debe tener formato AAAA-MM-DD."; `?desde=2026-02-30` → 422 "La fecha 'desde' (2026-02-30) no es una fecha válida."; `?desde=2026-11-20&hasta=2026-11-19` → 422 con el mensaje de D9; `?codigo=` → sin filtro; verificar verdes
- [x] 9.5 TRIANGULATE docs: `GET /openapi.json` lista los siete endpoints (`/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos`) y el 422 de stock y movimientos referencia `ErrorOut`; actualizar el test existente de `/docs` si enumera rutas; verificar verde
- [x] 9.6 REFACTOR: router sin lógica, mapeo `Movimiento → MovimientoOut` en una función; `.venv/Scripts/python -m unittest tests.test_api_movimientos -v` verde

## 10. Verificación integral

- [x] 10.1 Correr la suite completa (`.venv/Scripts/python -m unittest discover -s tests -t .`) y comparar con el baseline de 0.1: todos verdes, ninguno perdido
- [x] 10.2 Verificación manual en `/docs` (`uvicorn inventario.api.main:app --reload`, idealmente con una base existente como `prueba.db` para comprobar que arranca): login; ingreso de un código nuevo en minúsculas con nombre (queda en mayúsculas); suma; egreso parcial; egreso excedido (409); egreso de código inexistente (404); ingreso con `cantidad` 10001 y con JSON inválido (422 con `detail` en español); `GET /api/movimientos` sin filtros (más nuevo primero, fechas `-03:00`, usuario `admin`), con `codigo` en minúsculas, con `desde`/`hasta` del día y con `desde > hasta` (422); revisar en Swagger que el 422 muestra el esquema `ErrorOut`; logout y repetir un ingreso y un `GET /api/movimientos` (401); confirmar con SQL que `movimientos` tiene las filas esperadas; anotar el resultado en el verify-report
- [x] 10.3 Confirmar `openspec validate paso-2-movimientos-stock --strict` sin errores y que no hay archivos nuevos fuera de `inventario/`, `tests/` y el change

## 11. Ajustes post-verify (W-1, W-2, W-3, S-3, S-4)

- [x] 11.1 W-3: `re.fullmatch` + `[0-9]` en el filtro de fechas (RED/GREEN en `tests/test_movimientos_service.py`)
- [x] 11.2 W-1: recorte antes de medir en `IngresoRequest`/`EgresoRequest` (tests en `tests/test_api_stock.py`)
- [x] 11.3 W-2/S-4: fechas legadas no interpretables no rompen arranque ni listado, con aviso (tests en `tests/test_sqlite_schema.py` y `tests/test_sqlite_movimiento_repository.py`)
- [x] 11.4 S-3: test HTTP de "Varios errores"
- [x] 11.5 Suite completa verde y `openspec validate --strict`

## Workflow follow-up

- Verify del change (`openspec-verify`) contra specs, design y tasks.
- `/opsx:archive paso-2-movimientos-stock` y marcar `[x]` C-02 en `CHANGES.md`; esperar "Continuar" antes de C-03.
- Aparte (no en este change): actualizar `knowledge-base/10_preguntas_abiertas.md` marcando PA-04 como resuelta por D9.
