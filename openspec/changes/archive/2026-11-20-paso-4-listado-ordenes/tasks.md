# Tasks

> **Decisiones**: escritas con las opciones ★ de `design.md` § "Decisiones a confirmar por el usuario" — **aprobadas por el usuario el 2026-11-20 (las 11 con ★; la decisión 3 se probó como parcial y se revirtió a exacta). Ajuste del usuario a la decisión 1: `?numero=` inexistente → 404 "No existe una orden con número 'X'."; existente pero fuera del rango → 200 `[]` (se probó un 404 con el rango y se anuló)**.
>
> Strict TDD: en cada comportamiento, RED (test que falla por la razón correcta) → GREEN (mínimo código) → TRIANGULATE (segundo caso distinto) → REFACTOR (tests verdes tras cada paso).
> Comando (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .` — un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
> FastAPI/Pydantic solo en `inventario/api/` (Regla dura 1). Sin mocks de base: `:memory:` en repos/services, archivo temporal en API (Regla dura 4). Sin dependencias nuevas ni DDL. Sin commits (Regla dura 6).
> Siembra de órdenes en tests: `SqliteOrdenRepository.crear(numero, date, items, uid, creada_en)` (o `POST /api/ordenes` en API); baja lógica de producto con `UPDATE productos SET activo = 0` + `commit()` (C-05 aún no existe).

## 0. Red de seguridad

- [x] 0.1 Correr la suite completa antes de tocar nada y anotar el baseline (`Ran N tests ... OK`); si algo falla, detenerse y reportarlo como falla preexistente

## 1. Filtros de fecha compartidos (design D5 / decisión 10)

- [x] 1.1 RED: en `tests/test_fechas.py`, `parsear_filtro_fecha("desde", None)` y `("desde", "")` → `None`; `("hasta", "2026-11-19")` → `date(2026, 11, 19)`; `("desde", "19/11/2026")` → `DatosInvalidos` "La fecha 'desde' debe tener formato AAAA-MM-DD."; `("hasta", "2026-02-30")` → "La fecha 'hasta' (2026-02-30) no es una fecha válida."; `("desde", " 2026-11-20")` → error de formato; verificar que falla por `ImportError`
- [x] 1.2 GREEN: implementar `parsear_filtro_fecha` en `inventario/services/fechas.py`; verificar verde
- [x] 1.3 RED→GREEN→TRIANGULATE: `validar_rango("2026-11-20", "2026-11-19", date(2026,11,20), date(2026,11,19))` → "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."; mismo día, `desde < hasta`, y uno de los dos `None` no lanzan; verificar verdes
- [x] 1.4 REFACTOR: `MovimientosService` usa `parsear_filtro_fecha` y `validar_rango` (se elimina su `_parsear_fecha` local); `tests.test_movimientos_service`, `tests.test_api_movimientos` y `tests.test_fechas` verdes sin modificar ninguna aserción existente

## 2. Repositorio: `OrdenRepository.listar` — spec `consulta-ordenes` (design D1-D3)

- [x] 2.1 RED: en `tests/test_sqlite_orden_repository.py` (`:memory:`), con `OT-1` (2026-11-18), `OT-2` (2026-11-20) y `OT-3` (2026-11-17) creadas con `crear`, `listar(None, None, None)` devuelve `OT-2`, `OT-1`, `OT-3` como `Orden` con id, número, `date`, username e ítems; verificar que falla (`AttributeError`, el método no existe)
- [x] 2.2 GREEN: declarar `listar` en `OrdenRepository` (`repositories/base.py`) e implementarlo en `SqliteOrdenRepository` con la consulta única de design D2 (`LEFT JOIN` a ítems y productos, sin filtro por `activo`, agrupado por `o.id`); verificar verde
- [x] 2.3 TRIANGULATE orden y datos: a igual fecha `OT-B` (cargada después) antes que `OT-A`; `OT-VIEJA` con fecha 2025-01-15 y `creada_en` posterior queda después de `OT-NUEVA` con fecha 2026-11-19 y `creada_en` anterior (ordena por `fecha`, no `created_at`); componentes de `B-02` x 5 y `A-01` x 2 salen ordenados por código con nombre y cantidad; sin órdenes → `[]`; verificar verdes
- [x] 2.4 TRIANGULATE producto dado de baja: tras `UPDATE productos SET activo = 0` sobre `C-99`, la orden con `A-01` y `C-99` sigue listando ambos componentes con nombre y cantidad; verificar verde
- [x] 2.5 TRIANGULATE fechas: con órdenes del 17, 18, 19 y 20 de noviembre, `desde=18`/`hasta=19` → 19 y 18 (bordes incluidos); `desde=hasta=19` → solo la del 19; solo `desde=18` → 20, 19, 18; solo `hasta=18` → 18, 17; rango de diciembre → `[]`; verificar verdes
- [x] 2.6 TRIANGULATE número: `numero="OT-0002"` → solo esa orden con sus ítems; `OT-1` con `OT-1` y `OT-10` existentes → solo `OT-1`; `OT-0001` (fecha 17) con `desde=18` → `[]`; verificar verdes
- [x] 2.6c TRIANGULATE `existe_numero`: `OT-0001` creada → `existe_numero("OT-0001")` es `True`; `OT-9999` y `OT-1` (solo existe `OT-10`) → `False`; verificar que falla antes (`AttributeError`) y pasa tras agregar el método al contrato y a `SqliteOrdenRepository`
- [x] 2.7 TRIANGULATE sin N+1: con `conn.set_trace_callback` registrando sentencias, listar tres órdenes de dos componentes ejecuta exactamente un `SELECT`; verificar verde
- [x] 2.8 REFACTOR: SQL como constantes del módulo, condiciones solo con placeholders `?`, mapeo fila→`Orden` en una función; `_leer_orden` del alta reutiliza la misma consulta con `WHERE o.id = ?`; `tests.test_sqlite_orden_repository` completo (alta incluida) y `tests.test_orden_service` verdes

## 3. `OrdenService.listar` — spec `consulta-ordenes` (design D4)

- [x] 3.1 RED: en `tests/test_orden_service.py` (repo real `:memory:`), `listar()` sin argumentos devuelve las órdenes sembradas de la más nueva a la más vieja; verificar que falla (`AttributeError`)
- [x] 3.2 GREEN: implementar `OrdenService.listar(numero=None, desde=None, hasta=None)` según design D4; verificar verde
- [x] 3.3 TRIANGULATE número: `"  ot-0003 "` encuentra `OT-0003`; `None`, `""` y `"   "` = sin filtro (todas); 31 caracteres → `DatosInvalidos` "El campo numero admite hasta 30 caracteres."; verificar verdes
- [x] 3.3b RED→GREEN→TRIANGULATE no encontrada: `listar("ot-9 ")` sin esa orden → `OrdenNoEncontrada` con mensaje "No existe una orden con número 'OT-9'." (definir la excepción en `domain/errors.py`); `OT-0001` (fecha 17) con `desde=18` → `[]` sin error (existe, fuera del rango; llama a `existe_numero` solo porque el resultado es vacío); con `desde=17` → esa orden; `"   "` sin ninguna orden → `[]`; `OT-9` con `desde=19/11/2026` → `DatosInvalidos` de `desde` (no el 404); verificar verdes
- [x] 3.4 TRIANGULATE fechas: `desde="19/11/2026"` → "La fecha 'desde' debe tener formato AAAA-MM-DD."; `hasta="2026-02-30"` → "La fecha 'hasta' (2026-02-30) no es una fecha válida."; `desde="2026-11-20", hasta="2026-11-19"` → "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."; `desde=""`, `hasta=""` → todas; solo `desde` y solo `hasta` filtran; verificar verdes
- [x] 3.5 TRIANGULATE prioridad: número de 31 caracteres + `desde` inválido → mensaje del número; `desde` y `hasta` inválidos a la vez → mensaje de `desde`; verificar verdes
- [x] 3.6 REFACTOR: sin duplicar la normalización del alta (`_normalizar_numero` compartido); `tests.test_orden_service` verde

## 4. API: `GET /api/ordenes` — spec `api-http` (design D6)

- [x] 4.1 RED: en `tests/test_api_ordenes.py`, `GET /api/ordenes` sin sesión → 401; verificar que falla (hoy 405, el método no existe)
- [x] 4.2 GREEN: endpoint `GET ""` en `api/routers/ordenes.py` (`def` plano, `get_current_user`, `response_model=List[OrdenOut]`, 404 y 422 con `ErrorOut`), reutilizando `orden_out`; verificar verde
- [x] 4.3 TRIANGULATE éxito: con sesión, tras `POST /api/ordenes` de `OT-0001` (fecha 2026-11-20, `B-02` "Tuerca" x 5 y `A-01` "Tornillo" x 2) → 200 con la lista que contiene exactamente el cuerpo del escenario "Listado sin filtros" y el mismo `id` del 201; sin órdenes → `[]`; verificar verdes
- [x] 4.4 TRIANGULATE filtros: `?numero=ot-0002&desde=2026-11-20&hasta=2026-11-20` → solo `OT-0002`; `?desde=2026-11-18` → rango abierto; `?numero=&desde=&hasta=` → todas; `?numero=ot-9` inexistente → 404 con `detail` "No existe una orden con número 'OT-9'."; `?numero=OT-0001&desde=2026-11-18` con `OT-0001` del 17 → 200 `[]`; con `desde=2026-11-17` → 200 con la orden; `?numero=OT-9&desde=19/11/2026` → 422 (prioridad); registrar `OrdenNoEncontrada` → 404 en `api/app.py`; componente `C-99` dado de baja (UPDATE sobre el archivo temporal) sigue en la orden y `GET /api/inventario` no lo muestra; verificar verdes
- [x] 4.5 TRIANGULATE errores: 422 con `detail` exacto para `desde=19/11/2026`, `hasta=2026-02-30`, `desde=2026-11-20&hasta=2026-11-19` y `numero` de 31 caracteres; tras logout → 401; verificar verdes
- [x] 4.6 TRIANGULATE sesión inexistente: en `tests/test_api_sesion_inexistente.py`, `GET /api/ordenes` con la sesión de un usuario borrado y con la de un usuario recreado con otro id → 401 "No autenticado."; verificar verdes
- [x] 4.7 TRIANGULATE OpenAPI: el esquema sigue listando los ocho endpoints; `/api/ordenes` tiene `get` y `post`; la 200 de `get` es un array de `OrdenOut`; la 404 y la 422 de `get` y la 422 de `post` referencian `ErrorOut`; la 409 de `post` sigue con `StockInsuficienteOut`; verificar verdes
- [x] 4.8 REFACTOR: router sin lógica (query → service → schema); `tests.test_api_ordenes` y `tests.test_api_sesion_inexistente` verdes

## 5. Verificación integral

- [x] 5.1 Correr la suite completa y comparar con el baseline de 0.1: todos verdes, ninguno perdido; anotar el número final de tests
- [x] 5.2 Confirmar que no hay archivos nuevos fuera de `inventario/`, `tests/` y el change, ni dependencias nuevas, ni FastAPI importado en `domain/`, `services/` o `repositories/` (`grep -rn "fastapi" inventario/domain inventario/services inventario/repositories` vacío)
- [x] 5.3 Correr `openspec validate paso-4-listado-ordenes --strict` sin errores
- [x] 5.4 Verificación manual en `/docs` (la hace el orquestador; `uvicorn inventario.api.main:app --reload`, idealmente con una base existente como `prueba.db`): login; crear dos o tres órdenes con fechas distintas; `GET /api/ordenes` sin filtros (más nueva primero, componentes por código); rango con bordes, un solo día, solo `desde`, solo `hasta`; `numero` en minúsculas con espacios un número inexistente (404 con el mensaje) y un número existente fuera del rango (200 `[]`); `desde=2026-02-30`, `desde=19/11/2026` y rango invertido (422 en español); dar de baja un producto por SQL y ver que sigue en la orden; revisar en Swagger los esquemas de 200 y 422 del `GET`; logout y repetir (401); anotar el resultado en el verify-report

## 6. Ajustes post-verify

- [x] 6.1 S-1: tests de repositorio para orden sin ítems (sola y mezclada con órdenes normales) y para orden con todos los productos dados de baja; mutación del guard `codigo is not None` verificada y restaurada
- [x] 6.2 S-2: tests de servicio con subclase espía del `SqliteOrdenRepository` real que fijan cuándo se llama a `existe_numero`; mutación verificada y restaurada
- [x] 6.3 Suite completa verde (348 tests) y `openspec validate paso-4-listado-ordenes --strict` sin errores

## Workflow follow-up

- Verify del change (`openspec-verify`) contra specs, design y tasks.
- Archivar con `/opsx:archive paso-4-listado-ordenes`, marcar `[x]` C-04 en `CHANGES.md` y actualizar la KB: RN-OR-07 y US-007 (rangos abiertos y búsqueda por número, quitar "a confirmar"), Flujo 5 de `07_flujos_principales.md` y la tabla de endpoints de `02_descripcion_general.md` según la decisión 1.
- Esperar "Continuar" del usuario antes de C-05.
